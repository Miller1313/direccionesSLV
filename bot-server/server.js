// bot-server/server.js
require('dotenv').config();
const express = require('express');
const axios = require('axios');
const fs = require('fs').promises;
const path = require('path');
const cron = require('node-cron');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());
app.use(express.static('../')); // Servir archivos estáticos

// Cargar configuración
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;
const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const GITHUB_USERNAME = process.env.GITHUB_USERNAME;
const GITHUB_REPO = process.env.GITHUB_REPO;

// Ruta de salud
app.get('/health', (req, res) => {
    res.json({
        status: 'ok',
        service: 'Honduras Bot Server',
        timestamp: new Date().toISOString(),
        endpoints: ['/health', '/update-github', '/locations', '/telegram-test']
    });
});

// Obtener todas las ubicaciones
app.get('/locations', async (req, res) => {
    try {
        const data = await fs.readFile(path.join(__dirname, '../honduras-database.json'), 'utf8');
        const jsonData = JSON.parse(data);
        res.json(jsonData);
    } catch (error) {
        res.status(500).json({ error: 'Error leyendo la base de datos' });
    }
});

// Actualizar GitHub con nueva ubicación
app.post('/update-github', async (req, res) => {
    try {
        const newLocation = req.body.location;
        
        if (!newLocation) {
            return res.status(400).json({ error: 'No se proporcionó ubicación' });
        }

        // 1. Leer archivo JSON actual
        const filePath = path.join(__dirname, '../honduras-database.json');
        const data = await fs.readFile(filePath, 'utf8');
        const jsonData = JSON.parse(data);

        // 2. Agregar nueva ubicación
        const newId = jsonData.locations.length + 1;
        const locationWithId = {
            id: newId,
            ...newLocation,
            timestamp: new Date().toISOString(),
            approved: newLocation.approved || false,
            source: newLocation.source || 'user'
        };

        jsonData.locations.push(locationWithId);
        jsonData.lastUpdated = new Date().toISOString();
        jsonData.statistics.totalLocations = jsonData.locations.length;
        jsonData.statistics.userAddedLocations += 1;
        
        if (!locationWithId.approved) {
            jsonData.statistics.pendingLocations += 1;
        } else {
            jsonData.statistics.approvedLocations += 1;
        }

        // 3. Guardar localmente
        await fs.writeFile(filePath, JSON.stringify(jsonData, null, 2));

        // 4. Intentar subir a GitHub
        let githubSuccess = false;
        let githubMessage = 'No se intentó subir a GitHub';

        if (GITHUB_TOKEN && GITHUB_USERNAME && GITHUB_REPO) {
            try {
                const fileContent = Buffer.from(JSON.stringify(jsonData, null, 2)).toString('base64');
                
                // Primero, obtener el SHA del archivo actual
                const getResponse = await axios.get(
                    `https://api.github.com/repos/${GITHUB_USERNAME}/${GITHUB_REPO}/contents/honduras-database.json`,
                    {
                        headers: {
                            'Authorization': `token ${GITHUB_TOKEN}`,
                            'Accept': 'application/vnd.github.v3+json'
                        }
                    }
                );

                const sha = getResponse.data.sha;

                // Actualizar el archivo
                const updateResponse = await axios.put(
                    `https://api.github.com/repos/${GITHUB_USERNAME}/${GITHUB_REPO}/contents/honduras-database.json`,
                    {
                        message: `📌 Actualización: Nueva ubicación "${newLocation.name}" - ${new Date().toLocaleString()}`,
                        content: fileContent,
                        sha: sha,
                        committer: {
                            name: 'Honduras Bot',
                            email: 'bot@honduras.com'
                        }
                    },
                    {
                        headers: {
                            'Authorization': `token ${GITHUB_TOKEN}`,
                            'Accept': 'application/vnd.github.v3+json'
                        }
                    }
                );

                githubSuccess = true;
                githubMessage = 'GitHub actualizado exitosamente';
                
                console.log('GitHub actualizado:', updateResponse.data.commit.html_url);

            } catch (githubError) {
                console.error('Error actualizando GitHub:', githubError.message);
                githubMessage = `Error GitHub: ${githubError.message}`;
            }
        }

        // 5. Enviar notificación a Telegram
        let telegramSuccess = false;
        if (TELEGRAM_BOT_TOKEN && TELEGRAM_CHAT_ID) {
            try {
                const message = newLocation.approved 
                    ? `✅ <b>NUEVA UBICACIÓN AGREGADA (Aprobada)</b>\n📍 ${newLocation.name}\n🏙️ ${newLocation.municipio}\n📅 ${new Date().toLocaleString()}`
                    : `📋 <b>NUEVA SOLICITUD PENDIENTE</b>\n📍 ${newLocation.name}\n🏙️ ${newLocation.municipio}\n👤 Agregada por usuario\n📅 ${new Date().toLocaleString()}`;

                await axios.post(
                    `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`,
                    {
                        chat_id: TELEGRAM_CHAT_ID,
                        text: message,
                        parse_mode: 'HTML'
                    }
                );

                telegramSuccess = true;
            } catch (telegramError) {
                console.error('Error enviando a Telegram:', telegramError.message);
            }
        }

        // 6. Responder al cliente
        res.json({
            success: true,
            message: 'Ubicación agregada exitosamente',
            locationId: newId,
            localSave: true,
            githubUpdate: githubSuccess,
            githubMessage: githubMessage,
            telegramSent: telegramSuccess,
            timestamp: new Date().toISOString()
        });

    } catch (error) {
        console.error('Error en /update-github:', error);
        res.status(500).json({ 
            success: false, 
            error: error.message,
            timestamp: new Date().toISOString()
        });
    }
});

// Probar conexión con Telegram
app.post('/telegram-test', async (req, res) => {
    try {
        if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
            return res.status(400).json({ error: 'Telegram no configurado' });
        }

        const message = '✅ ¡Prueba de conexión exitosa! El servidor está funcionando correctamente.';
        
        const response = await axios.post(
            `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`,
            {
                chat_id: TELEGRAM_CHAT_ID,
                text: message,
                parse_mode: 'HTML'
            }
        );

        res.json({
            success: true,
            telegram: response.data.ok,
            message: 'Mensaje de prueba enviado a Telegram'
        });

    } catch (error) {
        res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
});

// Sincronizar con GitHub cada hora
cron.schedule('0 * * * *', async () => {
    console.log('Ejecutando sincronización automática con GitHub...');
    
    if (GITHUB_TOKEN && GITHUB_USERNAME && GITHUB_REPO) {
        try {
            const filePath = path.join(__dirname, '../honduras-database.json');
            const data = await fs.readFile(filePath, 'utf8');
            const jsonData = JSON.parse(data);
            const fileContent = Buffer.from(data).toString('base64');
            
            // Obtener SHA del archivo actual
            const getResponse = await axios.get(
                `https://api.github.com/repos/${GITHUB_USERNAME}/${GITHUB_REPO}/contents/honduras-database.json`,
                {
                    headers: {
                        'Authorization': `token ${GITHUB_TOKEN}`,
                        'Accept': 'application/vnd.github.v3+json'
                    }
                }
            );

            const sha = getResponse.data.sha;

            // Actualizar
            await axios.put(
                `https://api.github.com/repos/${GITHUB_USERNAME}/${GITHUB_REPO}/contents/honduras-database.json`,
                {
                    message: `🔄 Sincronización automática - ${new Date().toLocaleString()}`,
                    content: fileContent,
                    sha: sha
                },
                {
                    headers: {
                        'Authorization': `token ${GITHUB_TOKEN}`,
                        'Accept': 'application/vnd.github.v3+json'
                    }
                }
            );

            console.log('Sincronización automática completada');
            
        } catch (error) {
            console.error('Error en sincronización automática:', error.message);
        }
    }
});

// Iniciar servidor
app.listen(PORT, () => {
    console.log(`🚀 Servidor ejecutándose en http://localhost:${PORT}`);
    console.log(`📞 Endpoints disponibles:`);
    console.log(`   http://localhost:${PORT}/health`);
    console.log(`   http://localhost:${PORT}/locations`);
    console.log(`   http://localhost:${PORT}/update-github (POST)`);
    console.log(`   http://localhost:${PORT}/telegram-test (POST)`);
});