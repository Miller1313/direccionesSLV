// bot-sender.js
// Configuración - ¡ACTUALIZA ESTOS VALORES!

const TELEGRAM_BOT_TOKEN = '8554913344:AAFx8KcrJhXDLuB7ufOXhVqf9y8CqtzjLW4'; // Ej: "6123456789:AAHabcdefghijk"
const ADMIN_CHAT_ID = '5770086010';    // Ej: "123456789"
const SERVER_URL = 'https://miller1313.github.io/direccionesSLV/'; // O tu URL del servidor

// Función principal para enviar a Telegram
async function enviarSolicitudTelegram(locationData) {
    try {
        // Mostrar carga
        showLoading('Enviando solicitud...');
        
        // Enviar al servidor del bot
        const response = await fetch(`${SERVER_URL}/solicitud`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                ...locationData,
                botToken: TELEGRAM_BOT_TOKEN,
                adminChatId: ADMIN_CHAT_ID
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess('✅ Solicitud enviada al administrador');
            
            // Crear link directo a Telegram
            const telegramLink = `https://t.me/${result.botUsername || 'HondurasLocBot'}`;
            
            // Opcional: Abrir Telegram
            setTimeout(() => {
                if (confirm('¿Abrir Telegram para ver el estado?')) {
                    window.open(telegramLink, '_blank');
                }
            }, 1500);
            
        } else {
            throw new Error(result.error || 'Error desconocido');
        }
        
    } catch (error) {
        console.error('Error enviando a Telegram:', error);
        
        // Fallback: Enviar directamente via API de Telegram
        await enviarDirectoATelegram(locationData);
    }
}

// Fallback: Envío directo (sin servidor)
async function enviarDirectoATelegram(locationData) {
    try {
        const mensaje = `
🆕 *NUEVA SOLICITUD DE UBICACIÓN*

📍 *Lugar:* ${locationData.name}
🏙️ *Municipio:* ${locationData.municipio}
🗺️ *Departamento:* ${locationData.departamento}
📊 *Tipo:* ${locationData.type}
🌐 *Coordenadas:* ${locationData.lat}, ${locationData.lon}
🕐 *Enviado:* ${new Date().toLocaleString()}
📱 *Desde:* ${window.location.hostname}

_El administrador revisará esta solicitud pronto._
        `;
        
        const response = await fetch(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                chat_id: ADMIN_CHAT_ID,
                text: mensaje,
                parse_mode: 'Markdown',
                reply_markup: {
                    inline_keyboard: [
                        [
                            {
                                text: "🌐 Ver en Google Maps",
                                url: `https://www.google.com/maps?q=${locationData.lat},${locationData.lon}`
                            }
                        ],
                        [
                            {
                                text: "📍 Copiar coordenadas",
                                callback_data: `coords_${locationData.lat},${locationData.lon}`
                            }
                        ]
                    ]
                }
            })
        });
        
        const result = await response.json();
        
        if (result.ok) {
            showSuccess('✅ Solicitud enviada directamente a Telegram');
        } else {
            throw new Error(result.description);
        }
        
    } catch (error) {
        console.error('Error en fallback:', error);
        showError('❌ No se pudo enviar. Contacta al administrador manualmente.');
    }
}

// Funciones de UI
function showLoading(message) {
    // Puedes implementar un spinner o alert
    alert(`⏳ ${message}`);
}

function showSuccess(message) {
    alert(message);
}

function showError(message) {
    alert(message);
}

// Para desarrollo: Verificar conexión
async function verificarConexion() {
    try {
        const response = await fetch(`${SERVER_URL}/health`);
        const data = await response.json();
        console.log('✅ Servidor del bot conectado:', data);
        return true;
    } catch (error) {
        console.warn('⚠️ Servidor no disponible, usando método directo');
        return false;
    }
}

// Inicializar
document.addEventListener('DOMContentLoaded', () => {
    console.log('🤖 Bot sender cargado correctamente');
    
    // Verificar conexión al cargar
    verificarConexion();
});

// Exportar función principal
window.enviarSolicitudTelegram = enviarSolicitudTelegram;