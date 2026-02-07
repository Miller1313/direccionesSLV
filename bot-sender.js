// bot-sender.js
// Este archivo se carga desde tu HTML para enviar notificaciones a Telegram

const TELEGRAM_BOT_TOKEN = '8554913344:AAFx8KcrJhXDLuB7ufOXhVqf9y8CqtzjLW4'; // Reemplaza con tu token real
const TELEGRAM_CHAT_ID = '5770086010'; // Reemplaza con tu chat ID real
const GITHUB_USERNAME = 'Miller1313'; // Reemplaza con tu usuario de GitHub
const GITHUB_REPO = 'direccionesSLV'; // Reemplaza con el nombre de tu repositorio
const GITHUB_TOKEN = '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'; // Token con acceso a repos

async function sendToTelegram(message) {
    try {
        const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`;
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                chat_id: TELEGRAM_CHAT_ID,
                text: message,
                parse_mode: 'HTML'
            })
        });

        const data = await response.json();
        return data.ok === true;
    } catch (error) {
        console.error("Error enviando a Telegram:", error);
        return false;
    }
}

async function triggerGitHubUpdate(userLocation) {
    try {
        // Enviar solicitud a nuestro servidor local/remoto
        const response = await fetch('http://localhost:3000/update-github', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                location: userLocation,
                timestamp: new Date().toISOString()
            })
        });

        if (response.ok) {
            return await response.json();
        } else {
            console.error("Error en la respuesta del servidor:", await response.text());
            return null;
        }
    } catch (error) {
        console.error("Error conectando al servidor:", error);
        
        // Fallback: Enviar solo a Telegram
        const message = `⚠️ <b>UBICACIÓN NUEVA (SIN GITHUB)</b>

📍 <b>${userLocation.name}</b>
🏙️ ${userLocation.municipio}
🗺️ ${userLocation.departamento}

📌 <i>Coordenadas:</i>
Lat: ${userLocation.lat.toFixed(6)}
Lon: ${userLocation.lon.toFixed(6)}

🔗 https://www.google.com/maps?q=${userLocation.lat},${userLocation.lon}

⚠️ <b>Nota:</b> El servidor GitHub está offline. Guarda estos datos manualmente.`;
        
        await sendToTelegram(message);
        return { success: false, message: "Servidor offline, solo Telegram enviado" };
    }
}

// Función para notificar nueva ubicación
async function notifyNewLocation(location, isAdmin = false) {
    let telegramMessage;
    
    if (isAdmin) {
        telegramMessage = `👑 <b>ADMIN AGREGÓ UBICACIÓN</b>

📍 ${location.name}
🏙️ ${location.municipio || 'Sin municipio'}
🗺️ ${location.departamento || 'Sin departamento'}
📅 ${new Date().toLocaleString()}

<a href="https://www.google.com/maps?q=${location.lat},${location.lon}">Ver en Google Maps</a>`;
    } else {
        telegramMessage = `👤 <b>NUEVA UBICACIÓN SOLICITADA</b>

📍 ${location.name}
🏙️ ${location.municipio || 'Sin municipio'}
🗺️ ${location.departamento || 'Sin departamento'}
📊 Tipo: ${location.type}

📌 <i>Coordenadas:</i>
${location.lat.toFixed(6)}, ${location.lon.toFixed(6)}

📅 ${new Date().toLocaleString()}

<a href="https://www.google.com/maps?q=${location.lat},${location.lon}">Ver en Google Maps</a>

⚠️ <i>Pendiente de aprobación</i>`;
    }
    
    // Enviar a Telegram
    const telegramSuccess = await sendToTelegram(telegramMessage);
    
    if (!isAdmin) {
        // Si es usuario normal, también actualizar GitHub
        const githubResult = await triggerGitHubUpdate(location);
        
        return {
            telegram: telegramSuccess,
            github: githubResult
        };
    }
    
    return { telegram: telegramSuccess };
}

// Función para notificar aprobación
async function notifyApproval(location) {
    const message = `✅ <b>UBICACIÓN APROBADA</b>

📍 ${location.name}
🏙️ ${location.municipio}
🗺️ ${location.departamento}

👑 Aprobada por administrador
📅 ${new Date().toLocaleString()}

<a href="https://www.google.com/maps?q=${location.lat},${location.lon}">Ver en Google Maps</a>`;
    
    return await sendToTelegram(message);
}

// Función para notificar rechazo
async function notifyRejection(location) {
    const message = `❌ <b>UBICACIÓN RECHAZADA</b>

📍 ${location.name}
🏙️ ${location.municipio}
🗺️ ${location.departamento}

👑 Rechazada por administrador
📅 ${new Date().toLocaleString()}`;
    
    return await sendToTelegram(message);
}

// Función para notificar importación masiva
async function notifyMassImport(count) {
    const message = `📥 <b>IMPORTACIÓN MASIVA</b>

Se importaron ${count} ubicaciones al sistema.
📅 ${new Date().toLocaleString()}`;
    
    return await sendToTelegram(message);
}

// Función para probar conexión
async function testConnection() {
    try {
        const message = '✅ ¡Conexión de prueba exitosa! El sistema está funcionando correctamente.';
        const success = await sendToTelegram(message);
        
        // También probar GitHub
        const githubTest = await fetch('http://localhost:3000/health');
        
        return {
            telegram: success,
            github: githubTest.ok,
            timestamp: new Date().toISOString()
        };
    } catch (error) {
        return {
            telegram: false,
            github: false,
            error: error.message,
            timestamp: new Date().toISOString()
        };
    }
}

// Exportar funciones para usar en HTML
window.TelegramBot = {
    notifyNewLocation,
    notifyApproval,
    notifyRejection,
    notifyMassImport,
    testConnection,
    sendToTelegram
};

console.log("Bot Sender cargado correctamente");