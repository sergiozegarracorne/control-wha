require('dotenv').config();
const express = require('express');
const http = require('http');
const { Server } = require("socket.io");
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(cors());
app.use(express.json());

const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: "*", 
    methods: ["GET", "POST"]
  }
});

// --- AUTH HELPERS ---
const AUTH_FILE = path.join(__dirname, 'auth.json');

const getAuth = () => {
    if (!fs.existsSync(AUTH_FILE)) {
        try {
            fs.writeFileSync(AUTH_FILE, '{}');
            return {};
        } catch (e) {
            console.error("Error creando auth.json", e);
            return {};
        }
    }
    
    try {
        const data = fs.readFileSync(AUTH_FILE, 'utf8');
        return JSON.parse(data);
    } catch (e) {
        console.error("Error leyendo/parseando auth.json", e);
        return {};
    }
};

const saveAuth = (data) => {
    try {
        fs.writeFileSync(AUTH_FILE, JSON.stringify(data, null, 2));
    } catch (e) {
        console.error("Error guardando auth.json", e);
    }
};

// Middleware to track connection time or other metadata if needed
io.use((socket, next) => {
  socket.connectedAt = new Date();
  next();
});

io.on('connection', (socket) => {
  console.log('Cliente conectado:', socket.id);

  socket.on('register', (data) => {
    // Reload auth from file to get latest tokens
    const authData = getAuth();

    if (data && data.ruc) {
      // 0. SECURITY CHECK: Token Validation
      const validToken = authData[data.ruc];
      const providedToken = data.token;

      // Allow if token matches OR if no token is set in DB yet (optional, but unsafe, let's enforce)
      // For now, if validToken is undefined, we block access to be safe.
      if (!validToken || validToken !== providedToken) {
          console.log(`⛔ ACCESO DENEGADO: RUC ${data.ruc} intentó conectar con token inválido: ${providedToken}`);
          socket.emit('force_disconnect', { reason: "Error de Autenticación: Token inválido o RUC no autorizado." });
          socket.disconnect(true);
          return;
      }

      const room = `ruc_${data.ruc}`;
      
      // 1. Check for existing clients in this room (Single Session Policy - STRICT LOCK)
      const existingSockets = io.sockets.adapter.rooms.get(room);
      if (existingSockets && existingSockets.size > 0) {
          console.log(`🔒 ACCESO BLOQUEADO: RUC ${data.ruc} intentó conectar pero ya tiene sesión activa.`);
          
          socket.emit('force_disconnect', { 
              reason: "ACCESO DENEGADO: Ya existe una ventana de WhatsApp abierta para este RUC. Ciérrela primero o use esa." 
          });
          socket.disconnect(true);
          return;
      }

      console.log(`Cliente ${socket.id} registrado con RUC: ${data.ruc}`);
      socket.ruc = data.ruc; // Save RUC in socket object
      socket.join(room);
    }
  });

  // Broadcast Client Status (e.g. Browser Closed)
  socket.on('client_status', (data) => {
      console.log(`📢 Client Status Update [${data.ruc}]:`, data.status);
      if (data.ruc) {
          io.to(`ruc_${data.ruc}`).emit('client_status', data);
      }
  });

  socket.on('disconnect', () => {
    console.log('Cliente desconectado:', socket.id);
  });
});

// endpoint for sending messages
app.post('/api/venta', (req, res) => {
  const { ruc, phone_number, message, image_path } = req.body;

  if (!ruc || !phone_number || !message) {
    return res.status(400).json({ error: "Faltan datos (ruc, phone_number, message)" });
  }

  console.log(`Recibida venta para RUC ${ruc} -> Tel: ${phone_number}`);
  
  // Emit to specific room
  io.to(`ruc_${ruc}`).emit('enviar_whatsapp', {
    phone_number,
    message,
    image_path
  });

  res.json({ status: "Evento emitido a RUC " + ruc, data: req.body });
});

// 1. Ver conexiones activas
app.get('/api/clients', (req, res) => {
  const clients = [];
  const sockets = io.sockets.sockets; // Map

  for (const [id, socket] of sockets) {
    clients.push({
      id: id,
      ruc: socket.ruc || "Anónimo",
      connectedAt: socket.connectedAt,
      address: socket.handshake.address
    });
  }
  
  res.json({ count: clients.length, clients });
});

// 2. Desconectar cliente (Anti-Spam o Mantenimiento)
app.post('/api/disconnect', (req, res) => {
  const { socket_id, ruc } = req.body;
  
  if (!socket_id && !ruc) {
    return res.status(400).json({ error: "Debe enviar socket_id O ruc" });
  }

  let disconnectedCount = 0;
  const sockets = io.sockets.sockets;

  for (const [id, socket] of sockets) {
    if (socket_id && id === socket_id) {
      socket.disconnect(true);
      disconnectedCount++;
    } else if (ruc && socket.ruc == ruc) {
       socket.disconnect(true);
       disconnectedCount++;
    }
  }

  if (disconnectedCount > 0) {
    return res.json({ status: "success", message: `Desconectados ${disconnectedCount} clientes.` });
  } else {
    return res.status(404).json({ error: "No se encontró cliente con esos datos." });
  }
});

// 3. ADMIN DASHBOARD UI
app.get('/admin', (req, res) => {
    res.send(`
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Panel de Tokens - Control WHA</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <div class="container py-5">
            <h1 class="mb-4">🔐 Gestión de Clientes (RUC & Tokens)</h1>
            
            <div class="card shadow mb-4">
                <div class="card-body">
                    <h5 class="card-title">Agregar / Editar Cliente</h5>
                    <form id="authForm" class="row g-3">
                        <div class="col-md-5">
                            <input type="number" class="form-control" id="ruc" placeholder="RUC (Ej: 2060...)" required>
                        </div>
                        <div class="col-md-5">
                            <input type="text" class="form-control" id="token" placeholder="Token Secreto" required>
                        </div>
                        <div class="col-md-2">
                            <button type="submit" class="btn btn-primary w-100">Guardar</button>
                        </div>
                    </form>
                </div>
            </div>

            <div class="card shadow">
                <div class="card-body">
                    <h5 class="card-title">Clientes Registrados</h5>
                    <table class="table table-striped table-hover mt-3">
                        <thead class="table-dark">
                            <tr>
                                <th>RUC</th>
                                <th>Token</th>
                                <th>Acciones</th>
                            </tr>
                        </thead>
                        <tbody id="tableBody"></tbody>
                    </table>
                </div>
            </div>
        </div>

        <script>
            const API_URL = '/api/auth';

            async function loadClients() {
                const res = await fetch(API_URL);
                const data = await res.json();
                const tbody = document.getElementById('tableBody');
                tbody.innerHTML = '';

                for (const [ruc, token] of Object.entries(data)) {
                    tbody.innerHTML += \`
                        <tr>
                            <td>\${ruc}</td>
                            <td><code>\${token}</code></td>
                            <td>
                                <button class="btn btn-sm btn-warning me-2" onclick="edit('\${ruc}', '\${token}')">Editar</button>
                                <button class="btn btn-sm btn-danger" onclick="del('\${ruc}')">Eliminar</button>
                            </td>
                        </tr>
                    \`;
                }
            }

            function edit(ruc, token) {
                document.getElementById('ruc').value = ruc;
                document.getElementById('token').value = token;
            }

            async function del(ruc) {
                if(!confirm('¿Seguro de eliminar el RUC ' + ruc + '?')) return;
                await fetch(API_URL, { 
                    method: 'DELETE', 
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ ruc }) 
                });
                loadClients();
            }

            document.getElementById('authForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const ruc = document.getElementById('ruc').value;
                const token = document.getElementById('token').value;

                await fetch(API_URL, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ ruc, token })
                });
                
                document.getElementById('authForm').reset();
                loadClients();
            });

            loadClients();
        </script>
    </body>
    </html>
    `);
});

// 4. API Endpoints for Auth CRUD
app.get('/api/auth', (req, res) => res.json(getAuth()));

app.post('/api/auth', (req, res) => {
    const { ruc, token } = req.body;
    if (!ruc || !token) return res.status(400).json({ error: "Faltan datos" });
    
    const data = getAuth();
    data[ruc] = token;
    saveAuth(data);
    res.json({ status: "success", message: "Guardado" });
});

app.delete('/api/auth', (req, res) => {
    const { ruc } = req.body;
    if (!ruc) return res.status(400).json({ error: "Falta RUC" });

    const data = getAuth();
    if (data[ruc]) {
        delete data[ruc];
        saveAuth(data);
        res.json({ status: "success", message: "Eliminado" });
    } else {
        res.status(404).json({ error: "No encontrado" });
    }
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Socket Server corriendo en http://localhost:${PORT}`);
});
