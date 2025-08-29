# EJERCICIO 2: PROTOCOLOS PETICIÓN-RESPUESTA DE 2, 3 Y 4 VÍAS
# ==============================================================

import socket
import threading
import time
import json

class ProtocoloBase:
    """
    Clase base para implementar diferentes protocolos de comunicación.
    Cada proceso tendrá puertos distintos para envío y recepción.
    """
    
    def __init__(self, nombre, puerto_envio, puerto_recepcion):
        self.nombre = nombre
        self.puerto_envio = puerto_envio
        self.puerto_recepcion = puerto_recepcion
        
        # Socket para recibir mensajes
        self.socket_receptor = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket_receptor.bind(('localhost', puerto_recepcion))
        
        # Socket para enviar mensajes
        self.socket_emisor = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        self.ejecutando = True
        self.hilo_receptor = None
    
    def iniciar_receptor(self):
        """Inicia el hilo receptor de mensajes"""
        self.hilo_receptor = threading.Thread(target=self._receptor_loop, daemon=True)
        self.hilo_receptor.start()
    
    def _receptor_loop(self):
        """Loop principal del receptor de mensajes"""
        while self.ejecutando:
            try:
                self.socket_receptor.settimeout(1.0)
                mensaje, direccion = self.socket_receptor.recvfrom(1024)
                data = json.loads(mensaje.decode('utf-8'))
                self._procesar_mensaje(data, direccion)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Error en receptor {self.nombre}: {e}")
    
    def enviar_mensaje(self, mensaje, puerto_destino):
        """Envía un mensaje a un puerto específico"""
        mensaje_json = json.dumps(mensaje).encode('utf-8')
        self.socket_emisor.sendto(mensaje_json, ('localhost', puerto_destino))
        print(f"[{self.nombre}] Enviado: {mensaje}")
    
    def _procesar_mensaje(self, mensaje, direccion):
        """Método a sobrescribir en clases derivadas"""
        print(f"[{self.nombre}] Recibido: {mensaje}")
    
    def cerrar(self):
        """Cierra los sockets y detiene la ejecución"""
        self.ejecutando = False
        if self.hilo_receptor:
            self.hilo_receptor.join()
        self.socket_receptor.close()
        self.socket_emisor.close()

# ==============================================
# PROTOCOLO DE 2 VÍAS (REQUEST-RESPONSE SIMPLE)
# ==============================================

class Cliente2Vias(ProtocoloBase):
    """
    Cliente para protocolo de 2 vías:
    1. Cliente envía petición
    2. Servidor envía respuesta
    """
    
    def __init__(self, puerto_recepcion=5001):
        super().__init__("Cliente2V", 5000, puerto_recepcion)
        self.respuestas_recibidas = []
    
    def enviar_peticion(self, peticion, puerto_servidor=5000):
        """Envía una petición al servidor"""
        mensaje = {
            'tipo': 'REQUEST',
            'id': int(time.time() * 1000),  # ID único basado en timestamp
            'datos': peticion,
            'puerto_respuesta': self.puerto_recepcion
        }
        self.enviar_mensaje(mensaje, puerto_servidor)
        return mensaje['id']
    
    def _procesar_mensaje(self, mensaje, direccion):
        super()._procesar_mensaje(mensaje, direccion)
        if mensaje.get('tipo') == 'RESPONSE':
            self.respuestas_recibidas.append(mensaje)

class Servidor2Vias(ProtocoloBase):
    """
    Servidor para protocolo de 2 vías:
    Responde automáticamente a cada petición recibida
    """
    
    def __init__(self, puerto_recepcion=5000):
        super().__init__("Servidor2V", 5001, puerto_recepcion)
    
    def _procesar_mensaje(self, mensaje, direccion):
        super()._procesar_mensaje(mensaje, direccion)
        
        if mensaje.get('tipo') == 'REQUEST':
            # Procesar petición y enviar respuesta
            respuesta = {
                'tipo': 'RESPONSE',
                'id': mensaje.get('id'),
                'datos': f"Procesado: {mensaje.get('datos')}",
                'estado': 'SUCCESS'
            }
            
            puerto_respuesta = mensaje.get('puerto_respuesta')
            if puerto_respuesta:
                self.enviar_mensaje(respuesta, puerto_respuesta)

# ==============================================
# PROTOCOLO DE 3 VÍAS (THREE-WAY HANDSHAKE)
# ==============================================

class Cliente3Vias(ProtocoloBase):
    """
    Cliente para protocolo de 3 vías:
    1. Cliente envía SYN (petición de conexión)
    2. Servidor envía SYN-ACK (confirmación)
    3. Cliente envía ACK (acknowledgment final)
    """
    
    def __init__(self, puerto_recepcion=5002):
        super().__init__("Cliente3V", 5003, puerto_recepcion)
        self.conexiones_activas = {}
    
    def iniciar_conexion_3vias(self, puerto_servidor=5003):
        """Inicia handshake de 3 vías"""
        conexion_id = int(time.time() * 1000)
        
        # Paso 1: Enviar SYN
        syn_mensaje = {
            'tipo': 'SYN',
            'conexion_id': conexion_id,
            'puerto_respuesta': self.puerto_recepcion
        }
        self.enviar_mensaje(syn_mensaje, puerto_servidor)
        
        self.conexiones_activas[conexion_id] = {'estado': 'SYN_SENT'}
        return conexion_id
    
    def _procesar_mensaje(self, mensaje, direccion):
        super()._procesar_mensaje(mensaje, direccion)
        
        if mensaje.get('tipo') == 'SYN_ACK':
            # Paso 3: Responder con ACK
            conexion_id = mensaje.get('conexion_id')
            
            ack_mensaje = {
                'tipo': 'ACK',
                'conexion_id': conexion_id
            }
            
            # Enviar ACK de vuelta al servidor
            puerto_servidor = mensaje.get('puerto_respuesta', 5003)
            self.enviar_mensaje(ack_mensaje, puerto_servidor)
            
            # Marcar conexión como establecida
            if conexion_id in self.conexiones_activas:
                self.conexiones_activas[conexion_id]['estado'] = 'ESTABLECIDA'
                print(f"[{self.nombre}] ¡Conexión {conexion_id} establecida con éxito!")

class Servidor3Vias(ProtocoloBase):
    """
    Servidor para protocolo de 3 vías:
    Maneja el handshake de establecimiento de conexión
    """
    
    def __init__(self, puerto_recepcion=5003):
        super().__init__("Servidor3V", 5002, puerto_recepcion)
        self.conexiones_pendientes = {}
    
    def _procesar_mensaje(self, mensaje, direccion):
        super()._procesar_mensaje(mensaje, direccion)
        
        if mensaje.get('tipo') == 'SYN':
            # Paso 2: Responder con SYN-ACK
            conexion_id = mensaje.get('conexion_id')
            
            syn_ack_mensaje = {
                'tipo': 'SYN_ACK',
                'conexion_id': conexion_id,
                'puerto_respuesta': self.puerto_recepcion
            }
            
            puerto_cliente = mensaje.get('puerto_respuesta')
            self.enviar_mensaje(syn_ack_mensaje, puerto_cliente)
            
            # Guardar conexión pendiente
            self.conexiones_pendientes[conexion_id] = {'estado': 'SYN_ACK_SENT'}
        
        elif mensaje.get('tipo') == 'ACK':
            # Conexión completada
            conexion_id = mensaje.get('conexion_id')
            if conexion_id in self.conexiones_pendientes:
                self.conexiones_pendientes[conexion_id]['estado'] = 'ESTABLECIDA'
                print(f"[{self.nombre}] ¡Conexión {conexion_id} establecida con éxito!")

# ==============================================
# PROTOCOLO DE 4 VÍAS (FOUR-WAY HANDSHAKE)
# ==============================================

class Cliente4Vias(ProtocoloBase):
    """
    Cliente para protocolo de 4 vías:
    1. Cliente envía SYN
    2. Servidor envía ACK
    3. Servidor envía SYN
    4. Cliente envía ACK
    """
    
    def __init__(self, puerto_recepcion=5004):
        super().__init__("Cliente4V", 5005, puerto_recepcion)
        self.conexiones_4vias = {}
    
    def iniciar_conexion_4vias(self, puerto_servidor=5005):
        """Inicia handshake de 4 vías"""
        conexion_id = int(time.time() * 1000)
        
        # Paso 1: Enviar SYN inicial
        syn_mensaje = {
            'tipo': 'SYN',
            'conexion_id': conexion_id,
            'puerto_respuesta': self.puerto_recepcion,
            'secuencia': 1
        }
        self.enviar_mensaje(syn_mensaje, puerto_servidor)
        
        self.conexiones_4vias[conexion_id] = {'estado': 'SYN1_SENT', 'paso': 1}
        return conexion_id
    
    def _procesar_mensaje(self, mensaje, direccion):
        super()._procesar_mensaje(mensaje, direccion)
        conexion_id = mensaje.get('conexion_id')
        
        if mensaje.get('tipo') == 'ACK' and mensaje.get('secuencia') == 1:
            # Paso 2 completado, esperar SYN del servidor
            if conexion_id in self.conexiones_4vias:
                self.conexiones_4vias[conexion_id]['estado'] = 'ACK1_RECIBIDO'
                self.conexiones_4vias[conexion_id]['paso'] = 2
        
        elif mensaje.get('tipo') == 'SYN' and mensaje.get('secuencia') == 2:
            # Paso 4: Responder con ACK final
            ack_final = {
                'tipo': 'ACK',
                'conexion_id': conexion_id,
                'secuencia': 2
            }
            
            puerto_servidor = mensaje.get('puerto_respuesta', 5005)
            self.enviar_mensaje(ack_final, puerto_servidor)
            
            # Conexión establecida
            if conexion_id in self.conexiones_4vias:
                self.conexiones_4vias[conexion_id]['estado'] = 'ESTABLECIDA'
                self.conexiones_4vias[conexion_id]['paso'] = 4
                print(f"[{self.nombre}] ¡Conexión 4-vías {conexion_id} establecida completamente!")

class Servidor4Vias(ProtocoloBase):
    """
    Servidor para protocolo de 4 vías:
    Maneja ambas partes del handshake bidireccional
    """
    
    def __init__(self, puerto_recepcion=5005):
        super().__init__("Servidor4V", 5004, puerto_recepcion)
        self.conexiones_4vias = {}
    
    def _procesar_mensaje(self, mensaje, direccion):
        super()._procesar_mensaje(mensaje, direccion)
        conexion_id = mensaje.get('conexion_id')
        
        if mensaje.get('tipo') == 'SYN' and mensaje.get('secuencia') == 1:
            # Paso 2: Responder con ACK al SYN inicial
            ack_respuesta = {
                'tipo': 'ACK',
                'conexion_id': conexion_id,
                'secuencia': 1
            }
            
            puerto_cliente = mensaje.get('puerto_respuesta')
            self.enviar_mensaje(ack_respuesta, puerto_cliente)
            
            # Paso 3: Enviar nuestro propio SYN
            time.sleep(0.1)  # Pequeño delay para simular procesamiento
            syn_servidor = {
                'tipo': 'SYN',
                'conexion_id': conexion_id,
                'puerto_respuesta': self.puerto_recepcion,
                'secuencia': 2
            }
            self.enviar_mensaje(syn_servidor, puerto_cliente)
            
            # Guardar estado de conexión
            self.conexiones_4vias[conexion_id] = {'estado': 'SYN2_SENT', 'paso': 3}
        
        elif mensaje.get('tipo') == 'ACK' and mensaje.get('secuencia') == 2:
            # Paso 4 completado - conexión establecida
            if conexion_id in self.conexiones_4vias:
                self.conexiones_4vias[conexion_id]['estado'] = 'ESTABLECIDA'
                self.conexiones_4vias[conexion_id]['paso'] = 4
                print(f"[{self.nombre}] ¡Conexión 4-vías {conexion_id} establecida completamente!")

# ==============================================
# FUNCIÓN DEMO PARA PROBAR TODOS LOS PROTOCOLOS
# ==============================================

def demo_protocolos():
    """
    Demuestra el funcionamiento de los tres protocolos.
    """
    print("=== DEMO DE PROTOCOLOS PETICIÓN-RESPUESTA ===\n")
    
    try:
        # --- DEMO PROTOCOLO 2 VÍAS ---
        print("1. PROTOCOLO DE 2 VÍAS (REQUEST-RESPONSE)")
        print("-" * 40)
        
        servidor2 = Servidor2Vias()
        cliente2 = Cliente2Vias()
        
        servidor2.iniciar_receptor()
        cliente2.iniciar_receptor()
        time.sleep(0.5)
        
        # Enviar peticiones
        cliente2.enviar_peticion("Hola servidor!")
        cliente2.enviar_peticion("¿Cómo estás?")
        time.sleep(2)
        
        print(f"Respuestas recibidas: {len(cliente2.respuestas_recibidas)}\n")
        
        # --- DEMO PROTOCOLO 3 VÍAS ---
        print("2. PROTOCOLO DE 3 VÍAS (THREE-WAY HANDSHAKE)")
        print("-" * 45)
        
        servidor3 = Servidor3Vias()
        cliente3 = Cliente3Vias()
        
        servidor3.iniciar_receptor()
        cliente3.iniciar_receptor()
        time.sleep(0.5)
        
        # Iniciar handshake de 3 vías
        conexion_id = cliente3.iniciar_conexion_3vias()
        time.sleep(2)
        
        print(f"Estado conexión 3-vías: {cliente3.conexiones_activas.get(conexion_id, {}).get('estado', 'DESCONOCIDO')}\n")
        
        # --- DEMO PROTOCOLO 4 VÍAS ---
        print("3. PROTOCOLO DE 4 VÍAS (FOUR-WAY HANDSHAKE)")
        print("-" * 45)
        
        servidor4 = Servidor4Vias()
        cliente4 = Cliente4Vias()
        
        servidor4.iniciar_receptor()
        cliente4.iniciar_receptor()
        time.sleep(0.5)
        
        # Iniciar handshake de 4 vías
        conexion_id = cliente4.iniciar_conexion_4vias()
        time.sleep(3)
        
        print(f"Estado conexión 4-vías: {cliente4.conexiones_4vias.get(conexion_id, {}).get('estado', 'DESCONOCIDO')}")
        print(f"Paso completado: {cliente4.conexiones_4vias.get(conexion_id, {}).get('paso', 0)}\n")
        
        print("Demo completada con éxito!")
        
    except Exception as e:
        print(f"Error en demo: {e}")
    finally:
        # Limpiar recursos
        for obj in [servidor2, cliente2, servidor3, cliente3, servidor4, cliente4]:
            if 'obj' in locals():
                obj.cerrar()

if __name__ == "__main__":
    demo_protocolos()