# 🔌 Ejercicios de Programación con Sockets

Una colección completa de ejercicios prácticos para dominar la programación de red usando sockets en Python. Este repositorio implementa tres ejercicios fundamentales que abarcan desde comunicación básica UDP hasta protocolos robustos TCP con mecanismos de confiabilidad.

## 📚 Contenido

- [Ejercicio 1: Comunicación UDP](#ejercicio-1-comunicación-udp)
- [Ejercicio 2: Protocolos Petición-Respuesta](#ejercicio-2-protocolos-petición-respuesta)
- [Ejercicio 3: Comunicación TCP Confiable](#ejercicio-3-comunicación-tcp-confiable)
- [Ejecución de los ejercicicos](#Ejecución-de-los-ejercicicos)
- [Arquitectura Técnica](#arquitectura-técnica)

## 🚀 Ejercicio 1: Comunicación UDP

### Descripción
Implementación de comunicación básica usando sockets UDP (datagramas) para enviar y recibir mensajes de texto entre dos computadoras diferentes.

### Características
- ✅ **Servidor UDP** que escucha conexiones entrantes
- ✅ **Cliente UDP** que envía mensajes de texto
- ✅ Comunicación **sin conexión** (protocolo de datagramas)
- ✅ Manejo de **timeouts** y errores de red
- ✅ Codificación **UTF-8** para soporte internacional
- ✅ Demo local para pruebas

### Conceptos Implementados
- **SOCK_DGRAM**: Sockets de tipo datagrama
- **sendto()** y **recvfrom()**: Funciones UDP específicas
- **Comunicación stateless**: Cada mensaje es independiente
- **Manejo de direcciones**: IP y puerto del remitente

### Estructura del Código
```
udp_communication.py
├── servidor_udp()     # Servidor que escucha mensajes
├── cliente_udp()      # Cliente que envía mensajes
└── ejecutar_demo_udp() # Demo para pruebas locales
```

---

## 🔄 Ejercicio 2: Protocolos Petición-Respuesta

### Descripción
Implementación de tres protocolos de comunicación diferentes (2, 3 y 4 vías) donde cada proceso utiliza puertos distintos para envío y recepción de mensajes.

### Protocolos Implementados

#### 🔹 Protocolo de 2 Vías (Request-Response)
```
Cliente → [REQUEST] → Servidor
Cliente ← [RESPONSE] ← Servidor
```

#### 🔹 Protocolo de 3 Vías (Three-Way Handshake)
```
Cliente → [SYN] → Servidor
Cliente ← [SYN-ACK] ← Servidor  
Cliente → [ACK] → Servidor
```

#### 🔹 Protocolo de 4 Vías (Four-Way Handshake)
```
Cliente → [SYN] → Servidor
Cliente ← [ACK] ← Servidor
Cliente ← [SYN] ← Servidor
Cliente → [ACK] → Servidor
```

### Características Técnicas
- ✅ **Puertos separados** para cada proceso (envío/recepción)
- ✅ **Estados de conexión** rastreados automáticamente
- ✅ **IDs únicos** para cada intercambio de mensajes
- ✅ **Serialización JSON** para estructura de datos
- ✅ **Threading** para operaciones concurrentes
- ✅ **Timeouts configurables** para cada protocolo

### Casos de Uso
- **2 vías**: APIs REST, consultas simples
- **3 vías**: Establecimiento de conexiones TCP
- **4 vías**: Protocolos de autenticación mutua

---

## 🛡️ Ejercicio 3: Comunicación TCP Confiable

### Descripción
Implementación avanzada de una interfaz de comunicación robusta usando TCP con mecanismos adicionales de confiabilidad, detección de errores y recuperación automática.

### Características Avanzadas
- ✅ **Acknowledgments de aplicación** para mensajes críticos
- ✅ **Detección proactiva** de desconexiones
- ✅ **Reintento automático** con backoff exponencial
- ✅ **Heartbeat periódico** para monitoreo de conexiones
- ✅ **Estadísticas en tiempo real** de rendimiento
- ✅ **Chat interactivo** como demostración práctica
- ✅ **Manejo robusto de errores** y recuperación

### Mecanismos de Confiabilidad

#### 🔒 Control de Flujo
- **Recepción completa**: Garantiza que todos los bytes sean recibidos
- **Longitud prefijada**: Cada mensaje incluye su tamaño
- **Fragmentación TCP**: Manejo correcto de paquetes divididos

#### 🔄 Recuperación de Errores
- **Detección automática** de conexiones perdidas
- **Reconexión inteligente** con múltiples intentos
- **Cola de mensajes** para reenvío automático
- **Timeouts configurables** por tipo de operación

#### 📊 Monitoreo y Estadísticas
```python
stats = {
    'mensajes_enviados': 0,
    'mensajes_recibidos': 0, 
    'acks_enviados': 0,
    'acks_recibidos': 0,
    'reconexiones': 0,
    'errores': 0
}
```

### Componentes Principales
```
tcp_comunicacion_confiable.py
├── ComunicacionTCPConfiable    # Clase principal de comunicación
├── ChatTCPConfiable           # Interfaz de chat interactivo
├── demo_tcp_confiable()       # Demostración automática
└── main()                     # Menú principal de opciones
```

---


## 🛠️ Ejecución de los ejercicicos


### Ejercicio 1 - UDP
```bash
# Terminal 1 (Servidor)
python ejercicio1_udp.py
# Ejecutar: servidor_udp()

# Terminal 2 (Cliente) 
python ejercicio1_udp.py
# Ejecutar: cliente_udp()
```

### Ejercicio 2 - Protocolos
```bash
python ejercicio2_protocolos.py
# Ejecuta automáticamente demo de los 3 protocolos
```

### Ejercicio 3 - TCP Confiable
```bash
python ejercicio3_tcp.py
# Seguir el menú interactivo:
# 1. Servidor de chat
# 2. Cliente de chat  
# 3. Demo automática
```

---


## 🏗️ Arquitectura Técnica

### Diagrama de Componentes

```
┌─────────────────────┐    ┌─────────────────────┐
│   Ejercicio 1 UDP   │    │   Ejercicio 2       │
│                     │    │   Protocolos        │
│ ┌─────────────────┐ │    │                     │
│ │ Servidor UDP    │ │    │ ┌─────────────────┐ │
│ │ - Puerto: 12345 │ │    │ │ Protocolo 2-vías│ │
│ │ - recv/sendto   │ │    │ │ REQUEST/RESPONSE│ │
│ └─────────────────┘ │    │ └─────────────────┘ │
│                     │    │                     │
│ ┌─────────────────┐ │    │ ┌─────────────────┐ │
│ │ Cliente UDP     │ │    │ │ Protocolo 3-vías│ │
│ │ - Timeout: 5s   │ │    │ │ SYN/SYN-ACK/ACK │ │
│ │ - UTF-8         │ │    │ └─────────────────┘ │
│ └─────────────────┘ │    │                     │
└─────────────────────┘    │ ┌─────────────────┐ │
                           │ │ Protocolo 4-vías│ │
                           │ │ Handshake Dual  │ │
                           │ └─────────────────┘ │
                           └─────────────────────┘

┌─────────────────────────────────────────────────────┐
│              Ejercicio 3 TCP Confiable              │
│                                                     │
│ ┌─────────────────┐    ┌─────────────────────────┐  │
│ │ Servidor TCP    │    │ Mecanismos Confiabilidad│  │
│ │ - Multi-cliente │    │                         │  │
│ │ - Threading     │    │ • ACK automáticos       │  │
│ │ - Heartbeat     │    │ • Reintento exponencial │  │
│ └─────────────────┘    │ • Detección desconexión │  │
│                        │ • Cola mensajes         │  │
│ ┌─────────────────┐    │ • Estadísticas tiempo   │  │
│ │ Cliente TCP     │    │   real                  │  │
│ │ - Reconexión    │    └─────────────────────────┘  │
│ │ - Auto-retry    │                                 │
│ │ - Chat UI       │    ┌─────────────────────────┐  │
│ └─────────────────┘    │ Interfaz Chat           │  │
│                        │ - Comandos interactivos │  │
│                        │ - /stats /quit /help    │  │
│                        │ - Mensajería tiempo real│  │
│                        └─────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

*⭐ Si este proyecto te resulta útil, ¡no olvides darle una estrella en GitHub!*