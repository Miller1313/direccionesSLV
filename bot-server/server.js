// bot-server/server.js
require('dotenv').config();
const express = require('express');
const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());

// Configuración
const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const ADMIN_CHAT_ID = process.env.ADMIN_CHAT_ID;
const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const GITHUB_REPO = process.env.GITHUB_REPO;

// Inicializar bot de Telegram
const bot = new TelegramBot(BOT_TOKEN, { polling: true });

console.log('🤖 Bot de Telegram inicializado...');

// Almacenar solicitudes pendientes
const solicitudesPendientes = new Map();

// Ruta de salud
app.get('/health', (req, res) => {
    res.json({ 
        status: 'ok', 
        bot: 'conectado',
        github: 'configurado',
        tiempo: new Date().toISOString()
    });
});

// Ruta para recibir solicitudes del frontend
app.post('/solicitud', async (req, res) => {
    try {
        const locationData = req.body;
        const solicitudId = Date.now();
        
        console.log('📨 Nueva solicitud:', locationData.name);
        
        // Guardar en memoria
        solicitudesPendientes.set(solicitudId.toString(), {
            ...locationData,
            id: solicitudId,
            status: 'pending',
            receivedAt: new Date().toISOString()
        });
        
        // Enviar mensaje a Telegram
        const mensajeTelegram = await bot.sendMessage(ADMIN_CHAT_ID, 
            `🆕 *NUEVA SOLICITUD DE UBICACIÓN*\n\n` +
            `📍 *Lugar:* ${locationData.name}\n` +
            `🏙️ *Municipio:* ${locationData.municipio}\n` +
            `🗺️ *Departamento:* ${locationData.departamento}\n` +
            `📊 *Tipo:* ${locationData.type}\n` +
            `🌐 *Coordenadas:* ${locationData.lat}, ${locationData.lon}\n` +
            `🕐 *Enviado:* ${new Date().toLocaleString()}\n` +
            `📱 *Desde IP:* ${req.ip}\n\n` +
            `_Selecciona una acción:_`,
            {
                parse_mode: 'Markdown',
                reply_markup: {
                    inline_keyboard: [
                        [
                            { 
                                text: '✅ APROBAR Y GUARDAR', 
                                callback_data: `aprobar_${solicitudId}`
                            },
                            { 
                                text: '❌ RECHAZAR', 
                                callback_data: `rechazar_${solicitudId}`
                            }
                        ],
                        [
                            { 
                                text: '🗺️ Ver en Google Maps', 
                                url: `https://www.google.com/maps?q=${locationData.lat},${locationData.lon}`
                            }
                        ],
                        [
                            { 
                                text: '📋 Copiar coordenadas', 
                                callback_data: `copiar_${locationData.lat},${locationData.lon}`
                            }
                        ]
                    ]
                }
            }
        );
        
        // Guardar ID del mensaje
        solicitudesPendientes.get(solicitudId.toString()).messageId = mensajeTelegram.message_id;
        
        res.json({ 
            success: true, 
            messageId: mensajeTelegram.message_id,
            botUsername: (await bot.getMe()).username
        });
        
    } catch (error) {
        console.error('Error en /solicitud:', error);
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// Manejar respuestas del bot (cuando tú haces click)
bot.on('callback_query', async (query) => {
    try {
        const [action, data] = query.data.split('_');
        const chatId = query.message.chat.id;
        const messageId = query.message.message_id;
        
        console.log(`🔘 Acción: ${action}, Datos: ${data}`);
        
        if (action === 'aprobar') {
            // Obtener datos de la solicitud
            const solicitud = solicitudesPendientes.get(data);
            
            if (!solicitud) {
                await bot.answerCallbackQuery(query.id, { text: '❌ Solicitud no encontrada' });
                return;
            }
            
            // Actualizar estado
            solicitud.status = 'approved';
            solicitud.approvedAt = new Date().toISOString();
            solicitud.approvedBy = chatId;
            
            // 1. Actualizar GitHub
            await actualizarGitHub(solicitud);
            
            // 2. Notificar al admin
            await bot.editMessageText(
                `✅ *SOLICITUD APROBADA*\n\n` +
                `📍 ${solicitud.name}\n` +
                `🏙️ ${solicitud.municipio}, ${solicitud.departamento}\n` +
                `📊 ${solicitud.type}\n\n` +
                `_✅ Aprobado y guardado en la base de datos_\n` +
                `_🕐 ${new Date().toLocaleString()}_`,
                {
                    chat_id: chatId,
                    message_id: messageId,
                    parse_mode: 'Markdown'
                }
            );
            
            // Eliminar botones
            await bot.editMessageReplyMarkup(
                { inline_keyboard: [] },
                { chat_id: chatId, message_id: messageId }
            );
            
            await bot.answerCallbackQuery(query.id, { text: '✅ Aprobado y guardado en GitHub' });
            
        } else if (action === 'rechazar') {
            const solicitud = solicitudesPendientes.get(data);
            
            await bot.editMessageText(
                `❌ *SOLICITUD RECHAZADA*\n\n` +
                `📍 ${solicitud?.name || 'Ubicación desconocida'}\n\n` +
                `_❌ Rechazada por el administrador_\n` +
                `_🕐 ${new Date().toLocaleString()}_`,
                {
                    chat_id: chatId,
                    message_id: messageId,
                    parse_mode: 'Markdown'
                }
            );
            
            await bot.editMessageReplyMarkup(
                { inline_keyboard: [] },
                { chat_id: chatId, message_id: messageId }
            );
            
            solicitudesPendientes.delete(data);
            await bot.answerCallbackQuery(query.id, { text: '❌ Solicitud rechazada' });
            
        } else if (action === 'copiar') {
            await bot.answerCallbackQuery(query.id, { 
                text: `📋 Copiado: ${data}`,
                show_alert: false 
            });
        }
        
    } catch (error) {
        console.error('Error en callback_query:', error);
        await bot.answerCallbackQuery(query.id, { 
            text: '❌ Error procesando la acción',
            show_alert: true 
        });
    }
});

// Función para actualizar GitHub
async function actualizarGitHub(solicitud) {
    try {
        const GITHUB_API = 'https://api.github.com';
        const FILE_PATH = 'honduras-database.json';
        const FILE_URL = `${GITHUB_API}/repos/${GITHUB_REPO}/contents/${FILE_PATH}`;
        
        console.log('🔄 Actualizando GitHub...');
        
        // 1. Obtener archivo actual
        const { data: fileData } = await axios.get(FILE_URL, {
            headers: { Authorization: `token ${GITHUB_TOKEN}` }
        });
        
        // Decodificar contenido actual
        const currentContent = JSON.parse(
            Buffer.from(fileData.content, 'base64').toString('utf-8')
        );
        
        // 2. Preparar nueva ubicación
        const nuevaUbicacion = {
            id: `loc_${Date.now()}`,
            name: solicitud.name,
            lat: solicitud.lat,
            lon: solicitud.lon,
            municipio: solicitud.municipio,
            departamento: solicitud.departamento,
            type: solicitud.type,
            approved: true,
            approvedAt: solicitud.approvedAt,
            approvedBy: 'telegram_bot',
            addedAt: solicitud.receivedAt
        };
        
        // 3. Agregar a la base de datos
        if (!currentContent.locations) {
            currentContent.locations = [];
        }
        
        currentContent.locations.push(nuevaUbicacion);
        currentContent.lastUpdated = new Date().toISOString();
        currentContent.totalLocations = currentContent.locations.length;
        
        // 4. Subir archivo actualizado
        const newContent = Buffer.from(
            JSON.stringify(currentContent, null, 2)
        ).toString('base64');
        
        await axios.put(FILE_URL, {
            message: `🤖 Nueva ubicación: ${solicitud.name}`,
            content: newContent,
            sha: fileData.sha
        }, {
            headers: { Authorization: `token ${GITHUB_TOKEN}` }
        });
        
        console.log('✅ GitHub actualizado correctamente');
        return true;
        
    } catch (error) {
        console.error('❌ Error actualizando GitHub:', error.response?.data || error.message);
        throw error;
    }
}

// Comandos del bot
bot.onText(/\/start/, (msg) => {
    const chatId = msg.chat.id;
    
    if (chatId.toString() === ADMIN_CHAT_ID) {
        bot.sendMessage(chatId,
            `👑 *MODO ADMINISTRADOR ACTIVADO*\n\n` +
            `🤖 *Bot:* Honduras Locations Bot\n` +
            `📊 *Estado:* Operativo\n` +
            `🔔 *Notificaciones:* Activadas\n\n` +
            `_Recibirás notificaciones de nuevas solicitudes._\n` +
            `_Usa los botones inline para aprobar/rechazar._`,
            { parse_mode: 'Markdown' }
        );
    } else {
        bot.sendMessage(chatId,
            `👋 ¡Hola! Soy el bot de ubicaciones de Honduras.\n\n` +
            `📍 Solo administradores pueden usar este bot.\n` +
            `🌐 Visita: ${process.env.FRONTEND_URL || 'tu-sitio.com'}`,
            { parse_mode: 'Markdown' }
        );
    }
});

bot.onText(/\/status/, async (msg) => {
    const chatId = msg.chat.id;
    
    if (chatId.toString() === ADMIN_CHAT_ID) {
        const pendientes = Array.from(solicitudesPendientes.values())
            .filter(s => s.status === 'pending').length;
        
        bot.sendMessage(chatId,
            `📊 *ESTADO DEL SISTEMA*\n\n` +
            `🤖 *Bot:* Conectado ✅\n` +
            `⏳ *Pendientes:* ${pendientes} solicitud(es)\n` +
            `🕐 *Hora servidor:* ${new Date().toLocaleString()}\n` +
            `🌐 *Frontend:* ${process.env.FRONTEND_URL || 'No configurado'}\n\n` +
            `_Última actualización GitHub:_\n` +
            `_${new Date().toISOString()}_`,
            { parse_mode: 'Markdown' }
        );
    }
});

// Iniciar servidor
app.listen(PORT, () => {
    console.log(`🚀 Servidor del bot corriendo en puerto ${PORT}`);
    console.log(`🤖 Bot: @${bot.options.username}`);
    console.log(`👑 Admin: ${ADMIN_CHAT_ID}`);
    console.log(`🌐 Health check: http://localhost:${PORT}/health`);
});