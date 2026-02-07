from flask import Flask, request, jsonify
import os
import json
import base64
import requests
from datetime import datetime

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
    data = request.json
    
    if 'message' in data:
        message = data['message']['text']
        chat_id = data['message']['chat']['id']
        
        # Comandos básicos
        if message == '/start':
            send_telegram(chat_id, 
                "🤖 *Bot de Aprobación Honduras*\n\n"
                "Enviaré solicitudes de nuevas ubicaciones.\n"
                "Responde:\n"
                "✅ aprobar - Para agregar a GitHub\n"
                "❌ rechazar - Para descartar")
        
        # Si es aprobación
        elif '✅ aprobar' in message:
            handle_approval(chat_id)
        
        # Si es rechazo
        elif '❌ rechazar' in message:
            handle_rejection(chat_id)
        
        # Si es una solicitud
        elif 'NUEVA SOLICITUD' in message:
            handle_new_request(message, chat_id)
    
    return jsonify({"status": "ok"})

@app.route('/send-notification', methods=['POST'])
def send_notification():
    """Endpoint para que tu HTML envíe solicitudes"""
    data = request.json
    location = data.get('location')
    chat_id = data.get('telegram_chat_id')
    
    if not location or not chat_id:
        return jsonify({"error": "Datos incompletos"}), 400
    
    # Guardar solicitud pendiente
    import time
    request_id = str(int(time.time()))
    pending_requests[request_id] = {
        'location': location,
        'chat_id': chat_id
    }
    
    # Crear mensaje para Telegram
    message = f"""📍 *NUEVA SOLICITUD DE DIRECCIÓN*

*Nombre:* {location['name']}
*Coordenadas:* `{location['coords']}`
*Municipio:* {location.get('municipio', 'No especificado')}
*Departamento:* {location.get('departamento', 'No especificado')}
*Tipo:* {location.get('type', 'colonia')}

*ID:* `{request_id}`

Para aprobar, responde:
✅ aprobar_{request_id}

Para rechazar:
❌ rechazar_{request_id}"""
    
    # Enviar a Telegram
    success = send_telegram(chat_id, message)
    
    if success:
        return jsonify({"success": True, "request_id": request_id})
    else:
        return jsonify({"error": "No se pudo enviar a Telegram"}), 500

@app.route('/approve/<request_id>', methods=['GET'])
def approve_route(request_id):
    """Ruta para aprobar desde un enlace (útil para móvil)"""
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

def handle_approval(chat_id):
    """Manejar aprobación desde Telegram"""
    # Buscar solicitud pendiente para este chat
    for req_id, data in pending_requests.items():
        if data['chat_id'] == chat_id:
            success = update_github(data['location'])
            
            if success:
                send_telegram(chat_id, f"✅ *{data['location']['name']}* aprobada y agregada a GitHub!")
                del pending_requests[req_id]
            else:
                send_telegram(chat_id, "❌ Error al actualizar GitHub")
            break

def handle_rejection(chat_id):
    """Manejar rechazo desde Telegram"""
    for req_id, data in pending_requests.items():
        if data['chat_id'] == chat_id:
            send_telegram(chat_id, f"❌ *{data['location']['name']}* rechazada.")
            del pending_requests[req_id]
            break

def handle_new_request(message, chat_id):
    """Procesar nueva solicitud (para webhook directo)"""
    lines = message.split('\n')
    location = {}
    
    for line in lines:
        if '*Nombre:*' in line:
            location['name'] = line.split('*Nombre:*')[1].strip()
        elif '*Coordenadas:*' in line:
            location['coords'] = line.split('*Coordenadas:*')[1].strip().replace('`', '')
        elif '*Municipio:*' in line:
            location['municipio'] = line.split('*Municipio:*')[1].strip()
        elif '*Departamento:*' in line:
            location['departamento'] = line.split('*Departamento:*')[1].strip()
        elif '*Tipo:*' in line:
            location['type'] = line.split('*Tipo:*')[1].strip()
    
    if location.get('name'):
        import time
        request_id = str(int(time.time()))
        pending_requests[request_id] = {
            'location': location,
            'chat_id': chat_id
        }
        
        send_telegram(chat_id,
            f"📍 *Nueva Solicitud*\n\n"
            f"*{location['name']}*\n"
            f"Coords: `{location['coords']}`\n\n"
            f"Responde:\n"
            f"✅ aprobar\n"
            f"❌ rechazar")

def update_github(location):
    """Actualizar GitHub automáticamente"""
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
        
        return update_response.status_code == 200
        
    except Exception as e:
        print(f"Error GitHub: {e}")
        return False

def send_telegram(chat_id, text):
    """Enviar mensaje a Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        response = requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        })
        return response.status_code == 200
    except:
        return False

if __name__ == '__main__':
    # Configurar puerto para Render
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)