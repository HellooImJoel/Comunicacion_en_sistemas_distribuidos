# EJERCICIO 3: INTERFAZ DE COMUNICACIÓN CONFIABLE CON TCP
# ========================================================

import socket
import threading
import time
import json
import struct
import logging

# Configurar logging para depuración
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ComunicacionTCPConfiable:
    """
    Clase que implementa una interfaz de comunicación confiable usando TCP.
    
    TCP ya proporciona confiabilidad básica, pero agregamos funcionalidades adicionales:
    - Detección y recuperación de desconexiones
    - Acknowledgments de aplicación para mensajes críticos
    - Reintento automático de operaciones
    - Heartbeat para monitorear conexiones
    - Manejo robusto de errores
    """
    
    def __init__(self, nombre, es_servidor=False, host='localhost', puerto=8080):
        self.nombre = nombre
        self.es_servidor = es_servidor
        self.host = host
        self.puerto = puerto
        
        # Sockets y conexión
        self.socket_principal = None
        self.socket_cliente = None
        self.conexion_activa = False
        
        # Control de hilos
        self.hilo_escucha = None
        self.hilo_heartbeat = None
        self.ejecutando = False
        
        # Cola de mensajes y acknowledgments
        self.mensajes_pendientes = {}  # ID -> mensaje (para reenvío)
        self.acks_recibidos = set()
        self.callback_mensaje = None
        
        # Configuración de confiabilidad
        self.timeout_ack = 5.0  # Segundos para esperar ACK
        self.max_reintentos = 3
        self.intervalo_heartbeat = 10.0  # Segundos entre heartbeats
        
        # Contadores y estadísticas
        self.mensaje_id = 0
        self.stats = {
            'mensajes_enviados': 0,
            'mensajes_recibidos': 0,
            'acks_enviados': 0,
            'acks_recibidos': 0,
            'reconexiones': 0,
            'errores': 0
        }

    def iniciar(self, callback_mensaje=None):
        """
        Inicia la comunicación TCP confiable.
        
        Args:
            callback_mensaje: Función que se llama al recibir mensajes (opcional)
        """
        self.callback_mensaje = callback_mensaje
        self.ejecutando = True
        
        if self.es_servidor:
            self._iniciar_servidor()
        else:
            self._iniciar_cliente()
        
        # Iniciar hilo de heartbeat
        self.hilo_heartbeat = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.hilo_heartbeat.start()
        
        logging.info(f"{self.nombre} iniciado {'como servidor' if self.es_servidor else 'como cliente'}")

    def _iniciar_servidor(self):
        """Configura el servidor TCP"""
        try:
            self.socket_principal = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Permitir reutilizar la dirección inmediatamente
            self.socket_principal.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket_principal.bind((self.host, self.puerto))
            self.socket_principal.listen(1)
            
            logging.info(f"Servidor escuchando en {self.host}:{self.puerto}")
            
            # Hilo para aceptar conexiones
            self.hilo_escucha = threading.Thread(target=self._aceptar_conexiones, daemon=True)
            self.hilo_escucha.start()
            
        except Exception as e:
            logging.error(f"Error iniciando servidor: {e}")
            self.stats['errores'] += 1

    def _iniciar_cliente(self):
        """Configura el cliente TCP"""
        self._conectar_servidor()

    def _conectar_servidor(self):
        """Conecta al servidor con reintentos automáticos"""
        reintentos = 0
        
        while self.ejecutando and reintentos < self.max_reintentos:
            try:
                self.socket_cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket_cliente.settimeout(10.0)  # Timeout de conexión
                self.socket_cliente.connect((self.host, self.puerto))
                
                self.conexion_activa = True
                logging.info(f"Cliente conectado a {self.host}:{self.puerto}")
                
                # Iniciar hilo de recepción
                self.hilo_escucha = threading.Thread(target=self._manejar_cliente, 
                                                   args=(self.socket_cliente,), daemon=True)
                self.hilo_escucha.start()
                
                if reintentos > 0:
                    self.stats['reconexiones'] += 1
                
                return True
                
            except Exception as e:
                reintentos += 1
                logging.warning(f"Intento de conexión {reintentos} falló: {e}")
                
                if reintentos < self.max_reintentos:
                    time.sleep(2 ** reintentos)  # Backoff exponencial
                else:
                    logging.error("No se pudo conectar al servidor después de múltiples intentos")
                    self.stats['errores'] += 1
        
        return False

    def _aceptar_conexiones(self):
        """Loop para aceptar conexiones de clientes (servidor)"""
        while self.ejecutando:
            try:
                socket_cliente, direccion = self.socket_principal.accept()
                logging.info(f"Cliente conectado desde {direccion}")
                
                self.socket_cliente = socket_cliente
                self.conexion_activa = True
                
                # Manejar cliente en hilo separado
                hilo_cliente = threading.Thread(target=self._manejar_cliente, 
                                               args=(socket_cliente,), daemon=True)
                hilo_cliente.start()
                
            except Exception as e:
                if self.ejecutando:
                    logging.error(f"Error aceptando conexión: {e}")
                    self.stats['errores'] += 1

    def _manejar_cliente(self, socket_cliente):
        """Maneja la comunicación con un cliente específico"""
        try:
            while self.ejecutando and self.conexion_activa:
                # Recibir longitud del mensaje (4 bytes)
                longitud_data = self._recibir_completo(socket_cliente, 4)
                if not longitud_data:
                    break
                
                longitud_mensaje = struct.unpack('!I', longitud_data)[0]
                
                # Recibir el mensaje completo
                mensaje_data = self._recibir_completo(socket_cliente, longitud_mensaje)
                if not mensaje_data:
                    break
                
                # Procesar mensaje
                self._procesar_mensaje_recibido(mensaje_data.decode('utf-8'), socket_cliente)
                
        except Exception as e:
            logging.error(f"Error manejando cliente: {e}")
            self.stats['errores'] += 1
        finally:
            self._limpiar_conexion(socket_cliente)

    def _recibir_completo(self, socket_obj, longitud):
        """
        Recibe exactamente 'longitud' bytes del socket.
        TCP puede fragmentar los datos, así que necesitamos asegurar recepción completa.
        """
        datos = b''
        while len(datos) < longitud:
            try:
                fragmento = socket_obj.recv(longitud - len(datos))
                if not fragmento:
                    return None  # Conexión cerrada
                datos += fragmento
            except socket.timeout:
                continue
            except Exception as e:
                logging.error(f"Error recibiendo datos: {e}")
                return None
        return datos

    def _procesar_mensaje_recibido(self, mensaje_texto, socket_cliente):
        """Procesa un mensaje recibido y maneja los diferentes tipos"""
        try:
            mensaje = json.loads(mensaje_texto)
            tipo_mensaje = mensaje.get('tipo')
            
            self.stats['mensajes_recibidos'] += 1
            logging.info(f"[{self.nombre}] Recibido: {mensaje}")
            
            if tipo_mensaje == 'HEARTBEAT':
                # Responder al heartbeat
                respuesta = {'tipo': 'HEARTBEAT_RESPONSE', 'timestamp': time.time()}
                self._enviar_mensaje_raw(respuesta, socket_cliente)
                
            elif tipo_mensaje == 'HEARTBEAT_RESPONSE':
                # Heartbeat confirmado - conexión activa
                pass
                
            elif tipo_mensaje == 'ACK':
                # Acknowledgment recibido
                mensaje_id = mensaje.get('mensaje_id')
                self.acks_recibidos.add(mensaje_id)
                self.stats['acks_recibidos'] += 1
                logging.info(f"[{self.nombre}] ACK recibido para mensaje {mensaje_id}")
                
                # Remover de mensajes pendientes
                if mensaje_id in self.mensajes_pendientes:
                    del self.mensajes_pendientes[mensaje_id]
                
            elif tipo_mensaje == 'MENSAJE':
                # Mensaje de aplicación
                mensaje_id = mensaje.get('id')
                
                # Enviar ACK automáticamente
                if mensaje_id:
                    ack = {'tipo': 'ACK', 'mensaje_id': mensaje_id}
                    self._enviar_mensaje_raw(ack, socket_cliente)
                    self.stats['acks_enviados'] += 1
                
                # Procesar contenido del mensaje
                if self.callback_mensaje:
                    self.callback_mensaje(mensaje.get('contenido'), mensaje.get('remitente'))
                else:
                    print(f"[{self.nombre}] Mensaje de {mensaje.get('remitente', 'desconocido')}: {mensaje.get('contenido')}")
                    
        except json.JSONDecodeError:
            logging.error(f"Error decodificando mensaje JSON: {mensaje_texto}")
            self.stats['errores'] += 1
        except Exception as e:
            logging.error(f"Error procesando mensaje: {e}")
            self.stats['errores'] += 1

    def enviar_mensaje(self, contenido, requiere_ack=True):
        """
        Envía un mensaje de forma confiable.
        
        Args:
            contenido: Contenido del mensaje
            requiere_ack: Si True, espera acknowledgment y reintenta si es necesario
            
        Returns:
            bool: True si el mensaje fue enviado exitosamente
        """
        if not self.conexion_activa or not self.socket_cliente:
            logging.warning("No hay conexión activa")
            return False
        
        self.mensaje_id += 1
        mensaje = {
            'tipo': 'MENSAJE',
            'id': self.mensaje_id,
            'contenido': contenido,
            'remitente': self.nombre,
            'timestamp': time.time(),
            'requiere_ack': requiere_ack
        }
        
        # Enviar mensaje
        if self._enviar_mensaje_raw(mensaje, self.socket_cliente):
            self.stats['mensajes_enviados'] += 1
            
            if requiere_ack:
                # Guardar para posible reenvío
                self.mensajes_pendientes[self.mensaje_id] = mensaje
                
                # Esperar ACK con timeout
                return self._esperar_ack(self.mensaje_id)
            
            return True
        
        return False

    def _enviar_mensaje_raw(self, mensaje, socket_destino):
        """Envía un mensaje serializado a través del socket"""
        try:
            mensaje_json = json.dumps(mensaje)
            mensaje_bytes = mensaje_json.encode('utf-8')
            
            # Enviar longitud primero, luego el mensaje
            longitud = struct.pack('!I', len(mensaje_bytes))
            socket_destino.sendall(longitud + mensaje_bytes)
            
            return True
            
        except Exception as e:
            logging.error(f"Error enviando mensaje: {e}")
            self._manejar_error_conexion()
            self.stats['errores'] += 1
            return False

    def _esperar_ack(self, mensaje_id):
        """Espera el ACK de un mensaje con timeout y reintentos"""
        reintentos = 0
        
        while reintentos < self.max_reintentos:
            # Esperar ACK
            tiempo_inicio = time.time()
            while time.time() - tiempo_inicio < self.timeout_ack:
                if mensaje_id in self.acks_recibidos:
                    self.acks_recibidos.remove(mensaje_id)
                    return True
                time.sleep(0.1)
            
            # Timeout - reenviar mensaje
            reintentos += 1
            if reintentos < self.max_reintentos and mensaje_id in self.mensajes_pendientes:
                logging.warning(f"Timeout para mensaje {mensaje_id}, reintento {reintentos}")
                mensaje = self.mensajes_pendientes[mensaje_id]
                self._enviar_mensaje_raw(mensaje, self.socket_cliente)
        
        # Falló después de todos los reintentos
        logging.error(f"Mensaje {mensaje_id} falló después de {self.max_reintentos} intentos")
        if mensaje_id in self.mensajes_pendientes:
            del self.mensajes_pendientes[mensaje_id]
        
        return False

    def _heartbeat_loop(self):
        """Envía heartbeats periódicos para mantener la conexión"""
        while self.ejecutando:
            time.sleep(self.intervalo_heartbeat)
            
            if self.conexion_activa and self.socket_cliente:
                heartbeat = {
                    'tipo': 'HEARTBEAT',
                    'timestamp': time.time(),
                    'remitente': self.nombre
                }
                
                if not self._enviar_mensaje_raw(heartbeat, self.socket_cliente):
                    logging.warning("Heartbeat falló - posible problema de conexión")
                    self._manejar_error_conexion()

    def _manejar_error_conexion(self):
        """Maneja errores de conexión e intenta reconectar"""
        logging.warning("Detectado error de conexión")
        self.conexion_activa = False
        
        if self.socket_cliente:
            try:
                self.socket_cliente.close()
            except:
                pass
            self.socket_cliente = None
        
        # Si es cliente, intentar reconectar
        if not self.es_servidor and self.ejecutando:
            logging.info("Intentando reconectar...")
            time.sleep(2)
            self._conectar_servidor()

    def _limpiar_conexion(self, socket_cliente):
        """Limpia una conexión cerrada"""
        self.conexion_activa = False
        try:
            socket_cliente.close()
        except:
            pass
        
        logging.info("Conexión cerrada")

    def obtener_estadisticas(self):
        """Retorna estadísticas de la comunicación"""
        return self.stats.copy()

    def cerrar(self):
        """Cierra la comunicación y limpia recursos"""
        logging.info(f"Cerrando {self.nombre}")
        self.ejecutando = False
        self.conexion_activa = False
        
        # Cerrar sockets
        if self.socket_cliente:
            try:
                self.socket_cliente.close()
            except:
                pass
        
        if self.socket_principal:
            try:
                self.socket_principal.close()
            except:
                pass
        
        # Esperar a que terminen los hilos
        if self.hilo_escucha and self.hilo_escucha.is_alive():
            self.hilo_escucha.join(timeout=2)
        
        if self.hilo_heartbeat and self.hilo_heartbeat.is_alive():
            self.hilo_heartbeat.join(timeout=2)

# ==============================================
# INTERFAZ DE CHAT SIMPLE PARA DEMOSTRACIÓN
# ==============================================

class ChatTCPConfiable:
    """
    Interfaz de chat simple que utiliza la comunicación TCP confiable.
    """
    
    def __init__(self, nombre, es_servidor=False, host='localhost', puerto=8080):
        self.nombre = nombre
        self.comunicacion = ComunicacionTCPConfiable(nombre, es_servidor, host, puerto)
        self.ejecutando = False

    def iniciar_chat(self):
        """Inicia el chat interactivo"""
        print(f"=== CHAT TCP CONFIABLE - {self.nombre} ===")
        print("Comandos disponibles:")
        print("  /stats    - Mostrar estadísticas")
        print("  /quit     - Salir del chat")
        print("  /help     - Mostrar esta ayuda")
        print("-" * 50)
        
        # Iniciar comunicación con callback para mensajes
        self.comunicacion.iniciar(callback_mensaje=self._mostrar_mensaje)
        self.ejecutando = True
        
        # Esperar a que se establezca la conexión
        time.sleep(2)
        
        if not self.comunicacion.conexion_activa:
            print("Error: No se pudo establecer la conexión")
            return
        
        print("¡Conexión establecida! Puedes empezar a chatear.\n")
        
        # Loop principal del chat
        try:
            while self.ejecutando:
                try:
                    mensaje = input()
                    
                    if mensaje.startswith('/'):
                        self._procesar_comando(mensaje)
                    elif mensaje.strip():
                        # Enviar mensaje normal
                        if self.comunicacion.enviar_mensaje(mensaje):
                            print(f"[{self.nombre}] → {mensaje}")
                        else:
                            print("⚠️  Error enviando mensaje")
                            
                except KeyboardInterrupt:
                    break
                    
        except Exception as e:
            logging.error(f"Error en chat: {e}")
        finally:
            self.cerrar_chat()

    def _mostrar_mensaje(self, contenido, remitente):
        """Callback para mostrar mensajes recibidos"""
        print(f"[{remitente}] ← {contenido}")

    def _procesar_comando(self, comando):
        """Procesa comandos especiales del chat"""
        if comando == '/quit':
            self.ejecutando = False
            print("Cerrando chat...")
            
        elif comando == '/stats':
            stats = self.comunicacion.obtener_estadisticas()
            print("\n=== ESTADÍSTICAS ===")
            for clave, valor in stats.items():
                print(f"{clave}: {valor}")
            print("===================\n")
            
        elif comando == '/help':
            print("\n=== COMANDOS ===")
            print("/stats - Mostrar estadísticas de comunicación")
            print("/quit  - Salir del chat")
            print("/help  - Mostrar esta ayuda")
            print("================\n")
            
        else:
            print(f"Comando desconocido: {comando}")

    def cerrar_chat(self):
        """Cierra el chat y limpia recursos"""
        self.ejecutando = False
        self.comunicacion.cerrar()
        print("Chat cerrado.")

# ==============================================
# FUNCIÓN DEMO PARA PROBAR LA COMUNICACIÓN TCP
# ==============================================

def demo_tcp_confiable():
    """
    Demuestra la comunicación TCP confiable con servidor y cliente automáticos.
    """
    print("=== DEMO COMUNICACIÓN TCP CONFIABLE ===\n")
    
    # Lista para recopilar mensajes recibidos
    mensajes_servidor = []
    mensajes_cliente = []
    
    def callback_servidor(contenido, remitente):
        mensajes_servidor.append(f"{remitente}: {contenido}")
        print(f"[SERVIDOR] ← {remitente}: {contenido}")
    
    def callback_cliente(contenido, remitente):
        mensajes_cliente.append(f"{remitente}: {contenido}")
        print(f"[CLIENTE] ← {remitente}: {contenido}")
    
    try:
        # Crear servidor y cliente
        servidor = ComunicacionTCPConfiable("Servidor", es_servidor=True, puerto=8081)
        cliente = ComunicacionTCPConfiable("Cliente", es_servidor=False, puerto=8081)
        
        # Iniciar comunicaciones
        servidor.iniciar(callback_mensaje=callback_servidor)
        time.sleep(1)  # Dar tiempo al servidor para inicializar
        
        cliente.iniciar(callback_mensaje=callback_cliente)
        time.sleep(2)  # Esperar conexión
        
        if not cliente.conexion_activa:
            print("❌ Error: No se pudo establecer la conexión")
            return
        
        print("✅ Conexión TCP establecida exitosamente\n")
        
        # Enviar mensajes de prueba
        print("📤 Enviando mensajes de prueba...")
        
        # Mensajes del cliente al servidor
        cliente.enviar_mensaje("¡Hola servidor! Este es un mensaje con ACK requerido.")
        time.sleep(1)
        
        cliente.enviar_mensaje("¿Cómo estás?", requiere_ack=True)
        time.sleep(1)
        
        # Mensajes del servidor al cliente
        servidor.enviar_mensaje("¡Hola cliente! Servidor respondiendo.", requiere_ack=True)
        time.sleep(1)
        
        servidor.enviar_mensaje("Todo funcionando correctamente.")
        time.sleep(2)
        
        # Mostrar estadísticas
        print("\n📊 ESTADÍSTICAS FINALES:")
        print("\nServidor:")
        stats_servidor = servidor.obtener_estadisticas()
        for clave, valor in stats_servidor.items():
            print(f"  {clave}: {valor}")
        
        print("\nCliente:")
        stats_cliente = cliente.obtener_estadisticas()
        for clave, valor in stats_cliente.items():
            print(f"  {clave}: {valor}")
        
        print(f"\n💬 Total mensajes intercambiados: {len(mensajes_servidor) + len(mensajes_cliente)}")
        print("✅ Demo completada exitosamente!")
        
    except Exception as e:
        print(f"❌ Error en demo: {e}")
        logging.error(f"Error en demo TCP: {e}")
    finally:
        # Limpiar recursos
        try:
            servidor.cerrar()
            cliente.cerrar()
        except:
            pass

# ==============================================
# FUNCIÓN PRINCIPAL Y MENÚ DE OPCIONES
# ==============================================

def main():
    """Función principal con menú de opciones"""
    print("=== EJERCICIO 3: COMUNICACIÓN TCP CONFIABLE ===")
    print("Selecciona una opción:")
    print("1. Ejecutar servidor de chat")
    print("2. Ejecutar cliente de chat")
    print("3. Ejecutar demo automática")
    print("4. Salir")
    
    while True:
        try:
            opcion = input("\nOpción (1-4): ").strip()
            
            if opcion == '1':
                nombre = input("Nombre del servidor [Servidor]: ").strip() or "Servidor"
                puerto = input("Puerto [8080]: ").strip() or "8080"
                try:
                    puerto = int(puerto)
                    chat = ChatTCPConfiable(nombre, es_servidor=True, puerto=puerto)
                    chat.iniciar_chat()
                except ValueError:
                    print("Puerto inválido")
                break
                
            elif opcion == '2':
                nombre = input("Nombre del cliente [Cliente]: ").strip() or "Cliente"
                host = input("Host del servidor [localhost]: ").strip() or "localhost"
                puerto = input("Puerto [8080]: ").strip() or "8080"
                try:
                    puerto = int(puerto)
                    chat = ChatTCPConfiable(nombre, es_servidor=False, host=host, puerto=puerto)
                    chat.iniciar_chat()
                except ValueError:
                    print("Puerto inválido")
                break
                
            elif opcion == '3':
                demo_tcp_confiable()
                break
                
            elif opcion == '4':
                print("¡Hasta luego!")
                break
                
            else:
                print("Opción inválida. Intenta de nuevo.")
                
        except KeyboardInterrupt:
            print("\n¡Hasta luego!")
            break

if __name__ == "__main__":
    main()