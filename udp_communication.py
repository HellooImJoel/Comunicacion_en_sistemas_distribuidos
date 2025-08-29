# EJERCICIO 1: COMUNICACIÓN UDP ENTRE DOS COMPUTADORAS
# =======================================================

# SERVIDOR UDP - Ejecutar en una computadora
import socket
import threading

def servidor_udp():
    """
    Servidor UDP que recibe y responde mensajes de texto.
    UDP es un protocolo sin conexión - cada mensaje es independiente.
    """
    # Crear socket UDP (SOCK_DGRAM para datagramas)
    servidor_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Configurar dirección y puerto del servidor
    host = '0.0.0.0'  # Escuchar en todas las interfaces de red
    puerto = 12345
    servidor_socket.bind((host, puerto))
    
    print(f"Servidor UDP escuchando en {host}:{puerto}")
    print("Presiona Ctrl+C para detener el servidor")
    
    try:
        while True:
            # Recibir mensaje del cliente (hasta 1024 bytes)
            # recvfrom() devuelve el mensaje y la dirección del remitente
            mensaje, direccion_cliente = servidor_socket.recvfrom(1024)
            mensaje_decodificado = mensaje.decode('utf-8')
            
            print(f"Mensaje recibido de {direccion_cliente}: {mensaje_decodificado}")
            
            # Responder al cliente
            respuesta = f"Servidor recibió: {mensaje_decodificado}"
            servidor_socket.sendto(respuesta.encode('utf-8'), direccion_cliente)
            
    except KeyboardInterrupt:
        print("\nServidor detenido")
    finally:
        servidor_socket.close()

# CLIENTE UDP - Ejecutar en otra computadora (o misma máquina para pruebas)
def cliente_udp():
    """
    Cliente UDP que envía mensajes de texto al servidor.
    """
    # Crear socket UDP
    cliente_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Dirección del servidor (cambiar por IP real del servidor)
    servidor_host = '127.0.0.1'  # localhost para pruebas locales
    servidor_puerto = 12345
    
    print("Cliente UDP iniciado")
    print("Escribe mensajes para enviar al servidor (o 'salir' para terminar)")
    
    try:
        while True:
            # Obtener mensaje del usuario
            mensaje = input("Mensaje: ")
            
            if mensaje.lower() == 'salir':
                break
                
            # Enviar mensaje al servidor
            cliente_socket.sendto(mensaje.encode('utf-8'), (servidor_host, servidor_puerto))
            
            # Recibir respuesta del servidor
            try:
                # Timeout de 5 segundos para evitar bloqueo indefinido
                cliente_socket.settimeout(5.0)
                respuesta, _ = cliente_socket.recvfrom(1024)
                print(f"Respuesta del servidor: {respuesta.decode('utf-8')}")
            except socket.timeout:
                print("Timeout: No se recibió respuesta del servidor")
                
    except KeyboardInterrupt:
        print("\nCliente detenido")
    finally:
        cliente_socket.close()

# FUNCIÓN PARA EJECUTAR SERVIDOR Y CLIENTE EN HILOS SEPARADOS (PARA PRUEBAS)
def ejecutar_demo_udp():
    """
    Ejecuta servidor y cliente en hilos separados para demostración local.
    En producción, cada uno correría en computadoras diferentes.
    """
    # Crear hilo para el servidor
    hilo_servidor = threading.Thread(target=servidor_udp, daemon=True)
    hilo_servidor.start()
    
    # Dar tiempo al servidor para inicializar
    import time
    time.sleep(1)
    
    # Ejecutar cliente en hilo principal
    cliente_udp()

if __name__ == "__main__":
    print("=== EJERCICIO 1: COMUNICACIÓN UDP ===")
    print("1. Ejecutar solo servidor: servidor_udp()")
    print("2. Ejecutar solo cliente: cliente_udp()")
    print("3. Demo local: ejecutar_demo_udp()")
    print()
    
    # Descomentar la función que desees ejecutar:
    # servidor_udp()     # Solo servidor
    # cliente_udp()      # Solo cliente  
    ejecutar_demo_udp()  # Demo local con ambos