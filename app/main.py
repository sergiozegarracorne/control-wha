import asyncio
import sys
import socketio

# Windows Helper: Enforce ProactorEventLoopPolicy for Playwright/Subprocesses
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from app.api.routes import router
from app.services.whatsapp import service

from app.core import config

# Socket.IO Client
sio = socketio.AsyncClient()

@sio.event
async def connect():
    print("Conectado al Socket Server (Node.js)")
    if config.RUC:
        print(f"Registrando RUC: {config.RUC}")
        await sio.emit('register', {'ruc': config.RUC})
    else:
        print("⚠️ No se configuro RUC. El servidor no podra enviar mensajes a este cliente especifico.")

@sio.event
async def connect_error(data):
    print(f"Error de conexion Socket.IO: {data}")

@sio.event
async def disconnect():
    print("Desconectado del Socket Server")

@sio.event
async def enviar_whatsapp(data):
    """
    Evento recibido desde el servidor Node.js.
    Data esperada: { "phone_number": "...", "message": "...", "image_path": "..." }
    """
    print(f"📩 Evento recibido: enviar_whatsapp -> {data}")
    phone = data.get('phone_number')
    msg = data.get('message')
    img = data.get('image_path')
    
    if phone and msg:
        success = await service.send_message(phone, msg, img)
        if success:
            print(f"✅ Mensaje enviado a {phone}")
        else:
            print(f"❌ Fallo al enviar a {phone}")
    else:
        print("⚠️ Datos incompletos en el evento")

app = FastAPI(title="Control-WHA (Playwright + Socket.IO)")

app.include_router(router)

@app.get("/", response_class=HTMLResponse)
def home():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Control-WHA</title>
        <style>
            body { font-family: sans-serif; text-align: center; padding: 20px; background: #f0f2f5; }
            .container { background: white; max-width: 600px; margin: 0 auto; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #128C7E; }
            #qr-container { margin: 20px auto; min-height: 264px; display: flex; align-items: center; justify-content: center; }
            #status { font-weight: bold; margin-bottom: 20px; padding: 10px; border-radius: 5px; }
            .status-connected { background: #dcf8c6; color: #075e54; }
            .status-waiting { background: #fff3cd; color: #856404; }
            img { border: 1px solid #ccc; padding: 10px; border-radius: 8px; }
            .socket-status { margin-top: 15px; font-size: 0.9em; color: #666; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>WhatsApp Web API</h1>
            <div id="status">Cargando estado...</div>
            <div id="qr-container"></div>
            <p><small>Controlado por Playwright</small></p>
            <div class="socket-status">Socket Server: <span id="socket-state">Desconocido</span></div>
        </div>

        <script>
            let currentStatus = '';

            async function checkStatus() {
                try {
                    const response = await fetch('/status');
                    const data = await response.json();
                    const statusDiv = document.getElementById('status');
                    const qrContainer = document.getElementById('qr-container');

                    if (data.status !== currentStatus) {
                        currentStatus = data.status;
                        if (data.status === 'connected') {
                            statusDiv.className = 'status-connected';
                            statusDiv.innerText = '✅ Conectado a WhatsApp';
                            qrContainer.innerHTML = '<p>¡Sesión activa!</p>';
                        } else if (data.status === 'waiting_qr') {
                            statusDiv.className = 'status-waiting';
                            statusDiv.innerText = '📷 Escanea el código QR';
                            loadQR();
                        } else {
                            statusDiv.className = '';
                            statusDiv.innerText = '⏳ Iniciando navegador...';
                            qrContainer.innerHTML = '';
                        }
                    }
                    
                    // Simple check just to show text, real status is backend
                    document.getElementById('socket-state').innerText = "Integrado en Backend";
                    
                } catch (error) {
                    console.error('Error:', error);
                }
            }

            async function loadQR() {
                try {
                    const response = await fetch('/qr');
                    if (response.ok) {
                        const data = await response.json();
                        if (data.qr_base64) {
                            const img = document.createElement('img');
                            img.src = 'data:image/png;base64,' + data.qr_base64;
                            document.getElementById('qr-container').innerHTML = '';
                            document.getElementById('qr-container').appendChild(img);
                        }
                    }
                } catch (error) {
                    console.error('Error QR:', error);
                }
            }

            setInterval(checkStatus, 3000);
            checkStatus();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.on_event("startup")
async def startup_event():
    #  Diagnostico de Red
    target_url = config.SOCKET_URL
    print(f"Diagnostico: Verificando acceso a {target_url}...")
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(target_url, timeout=5) as resp:
                print(f"Conexion HTTP Exitosa: Status {resp.status}")
                print(f"   (El servidor responde correctamente)")
    except Exception as e:
        print(f"Diagnostico Fallido: {e}")
        print("   -> Posible bloqueo de Firewall o error DNS en Python.")

    try:
        await service.start()
        asyncio.create_task(service.wait_for_login())
    except Exception as e:
        print(f"⚠️ Error al iniciar WhatsApp Service (probablemente faltan navegadores): {e}")

    # Listen for duplicate session disconnect
    @sio.on('force_disconnect')
    async def on_force_disconnect(data):
        reason = data.get('reason', 'Sesión duplicada.')
        print(f"\n⚠️🛑 CIERRE FORZADO: {reason}")
        
        # Show Blocking Alert (Windows Native)
        try:
            import ctypes
            # 0x10 = Icon Critical, 0x0 = OK Button, 0x1000 = System Modal
            ctypes.windll.user32.MessageBoxW(0, reason + "\n\nEl programa se cerrará.", "Sesión Finalizada", 0x10 | 0x1000)
        except:
            pass

        # Cleanup and Exit
        await service.close()
        # Force Exit
        import os
        os._exit(0)

    # Connect to Socket Server
    try:
        print("Intentando conectar Socket.IO...")
        await sio.connect(
            config.SOCKET_URL,
            transports=['websocket', 'polling'], # Force dual transport support
            wait_timeout=20
        )
    except Exception as e:
        print(f"⚠️ No se pudo conectar al Socket Server: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    await service.close()
    await sio.disconnect()

if __name__ == "__main__":
    import uvicorn
    from app.core import config
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
