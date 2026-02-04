require('dotenv').config();
const express = require('express');
const http = require('http');
const { Server } = require("socket.io");
const cors = require('cors');

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

// Middleware to track connection time or other metadata if needed
io.use((socket, next) => {
  socket.connectedAt = new Date();
  next();
});

io.on('connection', (socket) => {
  console.log('Cliente conectado:', socket.id);

  socket.on('register', (data) => {
    if (data && data.ruc) {
      const room = `ruc_${data.ruc}`;
      
      // 1. Check for existing clients in this room (Single Session Policy)
      const existingSockets = io.sockets.adapter.rooms.get(room);
      if (existingSockets) {
        for (const clientId of existingSockets) {
            const clientSocket = io.sockets.sockets.get(clientId);
            if (clientSocket && clientSocket.id !== socket.id) {
                console.log(`⚠️ DETECTADO DUPLICADO: RUC ${data.ruc}. Desconectando sesión anterior (${clientId}).`);
                
                // Emit alert to the OLD session so it can close gracefully
                clientSocket.emit('force_disconnect', { 
                    reason: "Se ha iniciado sesión de WhatsApp en otra computadora con este mismo RUC." 
                });
                
                // Force disconnect server-side
                clientSocket.disconnect(true);
            }
        }
      }

      console.log(`Cliente ${socket.id} registrado con RUC: ${data.ruc}`);
      socket.ruc = data.ruc; // Save RUC in socket object
      socket.join(room);
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

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Socket Server corriendo en http://localhost:${PORT}`);
});
