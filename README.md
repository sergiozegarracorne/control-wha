# Control-WHA 🤖📱

**Sistema de Automatización de Mensajería WhatsApp (Cliente-Servidor)**

Control-WHA es una solución robusta para enviar mensajes y archivos multimedia de WhatsApp de forma programática. Utiliza una arquitectura híbrida donde un **Servidor Central (Node.js)** orquesta las peticiones y las distribuye a múltiples **Clientes Locales (Python/Playwright)** ubicados físicamente en los negocios.

---

## 🚀 Características Principales

### 1. 🛡️ Seguridad y Anti-Ban

- Usa un navegador **Chromium real** (no APIs no oficiales), lo que reduce drásticamente el riesgo de bloqueo.
- Mantiene la sesión de WhatsApp Web persistente (no necesitas escanear el QR cada vez).

### 2. ⚡ Ruteo Inteligente por RUC

- El sistema soporta múltiples clientes conectados simultáneamente.
- Cada mensaje se enruta al terminal específico usando el **RUC** del negocio.

### 3. 🔒 Política de Sesión Única

- Protección contra duplicados: Si se intenta conectar un segundo terminal con el mismo RUC, el sistema **desconecta automáticamente al anterior** y muestra una alerta de seguridad.

### 4. 📝 Registro Local (Log CSV)

- Cada mensaje enviado (exitoso o fallido) se guarda en un archivo `conversations.csv` localmente para auditoría.

### 5. 🧙‍♂️ Asistente de Configuración (Onboarding)

- Interfaz gráfica (GUI) amigable para la primera ejecución.
- Solicita el RUC del negocio y aceptación de términos de responsabilidad.

---

## 🏛️ Arquitectura

```mermaid
graph LR
    POS[Tu Sistema POS/ERP] -- POST /api/venta --> SERVER(Servidor Node.js)
    SERVER -- Socket.IO (RUC) --> CLIENT(Cliente Python PC Local)
    CLIENT -- Playwright --> WHA[WhatsApp Web]
    WHA --> USER[Cliente Final]
```

---

## 📦 Instalación y Uso

### A. Servidor (Node.js)

El "cerebro" que gestiona las conexiones.

1.  Ir a carpeta `socket-server`.
2.  `npm install`
3.  Configurar `.env` (puerto).
4.  `node index.js`

**Endpoints API:**

- `POST /api/venta`: Enviar mensaje.
  ```json
  { "ruc": "2060...", "phone_number": "519...", "message": "Hola!" }
  ```
- `GET /api/clients`: Ver nodos conectados.
- `POST /api/disconnect`: Forzar desconexión.

---

### B. Cliente (Python / Executable)

El "robot" que va en la computadora del negocio.

#### Opción 1: Ejecutable (Recomendado para Usuario Final)

1.  Descargar/Copiar la carpeta `dist`.
2.  Ejecutar `WhatsAppClient.exe`.
3.  Seguir el asistente para ingresar el RUC.
4.  Escanear el código QR de WhatsApp una sola vez.

#### Opción 2: Código Fuente (Desarrollo)

1.  Instalar Python 3.12+.
2.  `pip install -r requirements.txt`
3.  `playwright install chromium`
4.  Ejecutar:
    ```bash
    python run.py
    ```

---

## ⚠️ Aviso Legal (Disclaimer)

Esta herramienta es una **Versión Beta** desarrollada para fines de automatización interna y pruebas.

- No tiene afiliación con WhatsApp Inc. ni Meta Platforms.
- El usuario asume la responsabilidad total por el uso de la herramienta.
- Se recomienda usar con intervalos de tiempo prudentes para evitar filtros de SPAM.

---

## 🛠️ Tecnologías

- **Python 3**: Lógica del cliente.
- **Playwright**: Automatización del navegador.
- **Node.js + Express**: Servidor API.
- **Socket.IO**: Comunicación tiempo real.
- **Tkinter**: Interfaz de configuración.
- **PyInstaller**: Empaquetado de ejecutable.
