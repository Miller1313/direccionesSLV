from flask import Flask, request, jsonify
import os
import json
import base64
import requests
from datetime import datetime
import uuid  # <-- AHORA SÍ ESTÁ IMPORTADO

app = Flask(__name__)

# Configuración
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO = os.getenv('GITHUB_REPO')
GITHUB_FILE = 'locations.json'

# Almacenamiento simple en memoria (en producción usa Redis o DB)
pending_requests = {}

@app.route('/')
def home():
    return "🤖 Bot de Aprobación Honduras - Online"

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    """Webhook para Telegram"""
    print("📥 Webhook recibido de Telegram")  # Debug
    data = request.json
    
    # Manejar mensajes de texto
    if 'message' in data:
        message = data['message']['text']
        chat_id = data['message']['chat']['id']
        
        # Comandos básicos
        if message == '/start':
            send_telegram(chat_id, 
                "🤖 *Bot de Aprobación Honduras*\n\n"
                "Enviaré solicitudes de nuevas ubicaciones.\n\n"
                "Comandos:\n"
                "/lista - Ver solicitudes pendientes\n"
                "/ayuda - Mostrar ayuda")
        
        elif message == '/lista' or message == '/list':
            show_pending_requests(chat_id)
        
        elif message == '/ayuda' or message == '/help':
            send_telegram(chat_id,
                "📋 *Ayuda del Bot*\n\n"
                "*Comandos:*\n"
                "/start - Iniciar bot\n"
                "/lista - Ver solicitudes pendientes\n"
                "/ayuda - Mostrar este mensaje\n\n"
                "*Uso:*\n"
                "1. El bot recibe solicitudes del formulario web\n"
                "2. Aparecerán con botones para aprobar/rechazar\n"
                "3. Usa los botones para gestionar las solicitudes")
    
    # Manejar botones inline (callback_query)
    elif 'callback_query' in data:
        print("🔄 Botón presionado en Telegram")  # Debug
        callback = data['callback_query']
        chat_id = callback['message']['chat']['id']
        message_id = callback['message']['message_id']
        callback_data = callback['data']
        
        # Responder al callback (quitar "loading" en Telegram)
        answer_callback_query(callback['id'])
        
        # Procesar las acciones
        if callback_data.startswith('approve_'):
            request_id = callback_data.split('_')[1]
            print(f"✅ Aprobando solicitud {request_id}")  # Debug
            handle_approval_button(request_id, chat_id, message_id)
            
        elif callback_data.startswith('reject_'):
            request_id = callback_data.split('_')[1]
            print(f"❌ Rechazando solicitud {request_id}")  # Debug
            handle_rejection_button(request_id, chat_id, message_id)
            
        elif callback_data.startswith('copy_'):
            request_id = callback_data.split('_')[1]
            print(f"📋 Copiando coordenadas {request_id}")  # Debug
            handle_copy_coords(request_id, callback['id'])
    
    return jsonify({"status": "ok"})

@app.route('/send-notification', methods=['POST'])
def send_notification():
    """Endpoint para que tu HTML envíe solicitudes"""
    print("🔔 Recibiendo solicitud de notificación...")  # Debug
    print(f"📦 Datos recibidos: {request.json}")  # Debug
    
    data = request.json
    location = data.get('location')
    chat_id = data.get('telegram_chat_id')
    
    if not location or not chat_id:
        print("❌ Error: Datos incompletos")  # Debug
        return jsonify({"error": "Datos incompletos"}), 400
    
    print(f"📍 Ubicación: {location.get('name')}")  # Debug
    print(f"👤 Chat ID: {chat_id}")  # Debug
    
    # Guardar solicitud pendiente
    import time
    request_id = str(int(time.time()))
    pending_requests[request_id] = {
        'location': location,
        'chat_id': chat_id
    }
    
    print(f"🆔 Request ID generado: {request_id}")  # Debug
    
    # Crear URL para Google Maps
    try:
        coords = location['coords'].split(',')
        lat = coords[0].strip()
        lon = coords[1].strip()
        maps_url = f"https://www.google.com/maps?q={lat},{lon}"
        print(f"🗺️ URL Maps: {maps_url}")  # Debug
    except:
        maps_url = f"https://www.google.com/maps/search/{location['name']}"
    
    # Crear mensaje para Telegram
    message = f"""📍 *NUEVA SOLICITUD DE DIRECCIÓN*

*Nombre:* {location['name']}
*Coordenadas:* `{location['coords']}`
*Municipio:* {location.get('municipio', 'No especificado')}
*Departamento:* {location.get('departamento', 'No especificado')}
*Tipo:* {location.get('type', 'colonia')}

*Detectado:* {location.get('detected', 'No disponible')}

*🆔 ID:* `{request_id}`"""

    # Crear teclado inline con botones
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "✅ Aprobar",
                    "callback_data": f"approve_{request_id}"
                },
                {
                    "text": "❌ Rechazar", 
                    "callback_data": f"reject_{request_id}"
                }
            ],
            [
                {
                    "text": "🗺️ Ver en Google Maps",
                    "url": maps_url
                }
            ],
            [
                {
                    "text": "📋 Copiar coordenadas",
                    "callback_data": f"copy_{request_id}"
                }
            ]
        ]
    }
    
    print("📤 Enviando mensaje a Telegram con botones...")  # Debug
    
    # Enviar a Telegram con botones
    success = send_telegram(chat_id, message, keyboard)
    
    if success:
        print("✅ Mensaje enviado exitosamente a Telegram")  # Debug
        return jsonify({
            "success": True, 
            "request_id": request_id,
            "message": "Solicitud enviada a Telegram"
        })
    else:
        print("❌ Error enviando a Telegram")  # Debug
        return jsonify({
            "error": "No se pudo enviar a Telegram",
            "details": "Verifica el token de Telegram y el chat ID"
        }), 500

@app.route('/approve/<request_id>', methods=['GET'])
def approve_route(request_id):
    """Ruta para aprobar desde un enlace (útil para móvil)"""
    print(f"🌐 Aprobando vía URL: {request_id}")  # Debug
    if request_id in pending_requests:
        data = pending_requests[request_id]
        success = update_github(data['location'])
        
        if success:
            send_telegram(data['chat_id'], f"✅ *{data['location']['name']}* aprobada y agregada a GitHub!")
            del pending_requests[request_id]
            return "✅ ¡Ubicación aprobada y agregada!"
        else:
            return "❌ Error al actualizar GitHub"
    
    return "❌ Solicitud no encontrada o ya procesada"

def handle_approval_button(request_id, chat_id, message_id):
    """Manejar aprobación desde botón"""
    print(f"🔄 Procesando aprobación: {request_id}")  # Debug
    if request_id in pending_requests:
        data = pending_requests[request_id]
        success = update_github(data['location'])
        
        if success:
            # Editar mensaje original para mostrar aprobado
            edit_message(chat_id, message_id, 
                        f"✅ *APROBADO*\n\n"
                        f"*{data['location']['name']}* ha sido agregada a GitHub!")
            
            # Enviar confirmación adicional
            send_telegram(chat_id, f"✅ *{data['location']['name']}* aprobada y agregada a GitHub!")
            
            del pending_requests[request_id]
            print(f"✅ Solicitud {request_id} aprobada y eliminada")  # Debug
        else:
            edit_message(chat_id, message_id, "❌ Error al actualizar GitHub")
            answer_callback_query(chat_id, "❌ Error al actualizar GitHub")
            print(f"❌ Error actualizando GitHub para {request_id}")  # Debug
    else:
        edit_message(chat_id, message_id, "❌ Solicitud no encontrada o ya procesada")
        print(f"⚠️ Solicitud {request_id} no encontrada")  # Debug

def handle_rejection_button(request_id, chat_id, message_id):
    """Manejar rechazo desde botón"""
    print(f"🔄 Procesando rechazo: {request_id}")  # Debug
    if request_id in pending_requests:
        data = pending_requests[request_id]
        
        # Editar mensaje original para mostrar rechazado
        edit_message(chat_id, message_id, 
                    f"❌ *RECHAZADO*\n\n"
                    f"*{data['location']['name']}* ha sido rechazada.")
        
        del pending_requests[request_id]
        print(f"❌ Solicitud {request_id} rechazada y eliminada")  # Debug
    else:
        edit_message(chat_id, message_id, "❌ Solicitud no encontrada")
        print(f"⚠️ Solicitud {request_id} no encontrada")  # Debug

def handle_copy_coords(request_id, callback_id):
    """Manejar copia de coordenadas"""
    print(f"📋 Copiando coordenadas: {request_id}")  # Debug
    if request_id in pending_requests:
        data = pending_requests[request_id]
        coords = data['location']['coords']
        
        # Mostrar alerta con las coordenadas
        answer_callback_query(callback_id, f"📋 Coordenadas:\n`{coords}`\n\n(Copia manualmente)")
        print(f"📋 Mostrando coordenadas: {coords}")  # Debug
    else:
        answer_callback_query(callback_id, "❌ Solicitud no encontrada")

def show_pending_requests(chat_id):
    """Mostrar solicitudes pendientes"""
    print(f"📋 Mostrando solicitudes pendientes para chat: {chat_id}")  # Debug
    user_requests = {k: v for k, v in pending_requests.items() if v['chat_id'] == chat_id}
    
    if not user_requests:
        send_telegram(chat_id, "📭 No hay solicitudes pendientes.")
        return
    
    message = "📋 *Solicitudes Pendientes:*\n\n"
    
    for req_id, data in user_requests.items():
        loc = data['location']
        message += f"*📍 {loc['name']}*\n"
        message += f"   🆔: `{req_id}`\n"
        message += f"   📍: `{loc['coords']}`\n"
        message += f"   🏙️: {loc.get('municipio', 'N/A')}\n\n"
    
    send_telegram(chat_id, message)
    print(f"📤 Enviadas {len(user_requests)} solicitudes pendientes")  # Debug

def update_github(location):
    """Actualizar GitHub automáticamente"""
    print(f"🔄 Actualizando GitHub con: {location['name']}")  # Debug
    try:
        # 1. Obtener archivo actual
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        file_data = response.json()
        
        # 2. Decodificar contenido
        current_content = base64.b64decode(file_data['content']).decode('utf-8')
        current_json = json.loads(current_content)
        
        # 3. Crear clave única
        name = location['name']
        key = name.lower()\
            .replace(' ', '_')\
            .replace('ñ', 'n')\
            .replace('á', 'a')\
            .replace('é', 'e')\
            .replace('í', 'i')\
            .replace('ó', 'o')\
            .replace('ú', 'u')\
            .replace('ü', 'u')\
            .replace(' ', '_')\
            .replace('-', '_')\
            .replace('.', '')\
            .replace(',', '')\
            .replace("'", '')
        
        # Si la clave ya existe, agregar sufijo
        original_key = key
        counter = 1
        while key in current_json:
            key = f"{original_key}_{counter}"
            counter += 1
        
        print(f"🔑 Clave generada para GitHub: {key}")  # Debug
        
        # 4. Agregar nueva entrada CON DATOS DETECTADOS
        current_json[key] = {
            "name": name,
            "lat": float(location['coords'].split(',')[0].strip()),
            "lon": float(location['coords'].split(',')[1].strip()),
            "municipio": location.get('municipio', 'Por determinar'),
            "departamento": location.get('departamento', 'Por determinar'),
            "type": location.get('type', 'colonia'),
            "added": datetime.now().isoformat(),
            "approved": True,
            "source": "user_submission",
            "detected_automatically": True,
            "full_address": location.get('detected', '')
        }
        
        # 5. Subir cambios
        new_content = json.dumps(current_json, indent=2, ensure_ascii=False)
        new_content_b64 = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')
        
        update_response = requests.put(url, headers=headers, json={
            "message": f"📍 Agregar: {name} ({location.get('municipio', '')})",
            "content": new_content_b64,
            "sha": file_data['sha']
        })
        
        success = update_response.status_code == 200
        print(f"📤 GitHub update status: {success}")  # Debug
        return success
        
    except Exception as e:
        print(f"❌ Error GitHub: {e}")  # Debug
        return False

def send_telegram(chat_id, text, reply_markup=None):
    """Enviar mensaje a Telegram con opción de botones"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        
        if reply_markup:
            data["reply_markup"] = reply_markup
        
        print(f"📤 Enviando a Telegram: {chat_id}")  # Debug
        response = requests.post(url, json=data)
        
        print(f"📨 Respuesta Telegram: {response.status_code}")  # Debug
        if response.status_code != 200:
            print(f"❌ Error Telegram: {response.text}")  # Debug
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error enviando mensaje: {e}")  # Debug
        return False

def answer_callback_query(callback_id, text=None, show_alert=True):
    """Responder a callback query de Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery"
        data = {"callback_query_id": callback_id}
        
        if text:
            data["text"] = text
            data["show_alert"] = show_alert
        
        requests.post(url, json=data)
        return True
    except Exception as e:
        print(f"❌ Error answering callback: {e}")
        return False

def edit_message(chat_id, message_id, new_text, reply_markup=None):
    """Editar un mensaje existente en Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText"
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": new_text,
            "parse_mode": "Markdown"
        }
        
        if reply_markup:
            data["reply_markup"] = reply_markup
        
        response = requests.post(url, json=data)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error editando mensaje: {e}")
        return False

if __name__ == '__main__':
    # Configurar puerto para Render
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Iniciando servidor en puerto {port}")  # Debug
    app.run(host='0.0.0.0', port=port)