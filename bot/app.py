from flask import Flask, request, jsonify
import os
import json
import base64
import requests
from datetime import datetime
import uuid  # <-- AHORA SÍ ESTÁ AQUÍ
import re    # <-- También agregué re para expresiones regulares
import time  # <-- Y time para timestamps

app = Flask(__name__)

# Configuración
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO = os.getenv('GITHUB_REPO')
GITHUB_FILE = 'locations.json'

# Almacenamiento simple en memoria
pending_requests = {}

@app.route('/')
def home():
    return "🤖 Bot de Aprobación Honduras - Online"

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    """Webhook para Telegram - VERSIÓN SIMPLIFICADA Y FUNCIONAL"""
    data = request.json
    print(f"📥 Webhook recibido: {data}")
    
    # Manejar mensajes de texto
    if 'message' in data:
        message = data['message'].get('text', '')
        chat_id = data['message']['chat']['id']
        
        print(f"📱 Mensaje: {message} | Chat: {chat_id}")
        
        # Comandos básicos
        if message == '/start':
            send_telegram_message(chat_id, 
                "🤖 *Bot de Aprobación Honduras*\n\n"
                "Enviaré solicitudes de nuevas ubicaciones.\n\n"
                "*Comandos:*\n"
                "/start - Iniciar bot\n"
                "/lista - Ver solicitudes pendientes\n"
                "/ayuda - Mostrar ayuda")
        
        elif message == '/lista' or message == '/list':
            show_pending_requests(chat_id)
        
        elif message == '/ayuda' or message == '/help':
            send_telegram_message(chat_id,
                "📋 *Ayuda del Bot*\n\n"
                "*Uso:*\n"
                "1. El bot recibe solicitudes del formulario web\n"
                "2. Aparecerán con botones para aprobar/rechazar\n"
                "3. Usa los botones para gestionar las solicitudes")
        
        # Manejar aprobación por texto (compatibilidad)
        elif message.lower().startswith('✅ aprobar'):
            handle_text_approval(chat_id, message)
        
        # Manejar rechazo por texto (compatibilidad)
        elif message.lower().startswith('❌ rechazar'):
            handle_text_rejection(chat_id, message)
    
    # Manejar botones inline
    elif 'callback_query' in data:
        callback = data['callback_query']
        chat_id = callback['message']['chat']['id']
        message_id = callback['message']['message_id']
        callback_data = callback['data']
        
        print(f"🔄 Callback recibido: {callback_data}")
        
        # Responder inmediatamente
        answer_callback_query(callback['id'])
        
        # Procesar acciones
        if callback_data.startswith('approve_'):
            request_id = callback_data.replace('approve_', '')
            handle_button_approval(request_id, chat_id, message_id)
            
        elif callback_data.startswith('reject_'):
            request_id = callback_data.replace('reject_', '')
            handle_button_rejection(request_id, chat_id, message_id)
            
        elif callback_data.startswith('copy_'):
            request_id = callback_data.replace('copy_', '')
            handle_copy_coords(request_id, callback['id'])
    
    return jsonify({"status": "ok"})

@app.route('/send-notification', methods=['POST'])
def send_notification():
    """Endpoint para que tu HTML envíe solicitudes - VERSIÓN FUNCIONAL"""
    print("🔔 Recibiendo solicitud del HTML...")
    
    try:
        data = request.json
        print(f"📦 Datos recibidos: {data}")
        
        location = data.get('location')
        chat_id = data.get('telegram_chat_id')
        
        if not location or not chat_id:
            print("❌ Error: Datos incompletos")
            return jsonify({"error": "Datos incompletos"}), 400
        
        # Generar ID único usando uuid
        request_id = str(uuid.uuid4())[:8]  # Tomar los primeros 8 caracteres
        
        # Guardar en memoria
        pending_requests[request_id] = {
            'location': location,
            'chat_id': chat_id,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"💾 Guardada solicitud {request_id}: {location.get('name')}")
        
        # Crear URL de Google Maps
        try:
            coords = location['coords'].split(',')
            lat = coords[0].strip()
            lon = coords[1].strip()
            maps_url = f"https://www.google.com/maps?q={lat},{lon}"
        except:
            maps_url = f"https://www.google.com/maps/search/{location.get('name', '')}"
        
        # Crear mensaje con formato Markdown
        message = f"""📍 *NUEVA SOLICITUD DE DIRECCIÓN*

*📌 Nombre:* {location.get('name', 'Sin nombre')}
*📍 Coordenadas:* `{location.get('coords', 'No especificadas')}`
*🏙️ Municipio:* {location.get('municipio', 'No especificado')}
*🏛️ Departamento:* {location.get('departamento', 'No especificado')}
*📋 Tipo:* {location.get('type', 'colonia')}

*🔍 Detectado:* {location.get('detected', 'No disponible')}

*🆔 ID:* `{request_id}`"""
        
        # Crear teclado con botones
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Aprobar", "callback_data": f"approve_{request_id}"},
                    {"text": "❌ Rechazar", "callback_data": f"reject_{request_id}"}
                ],
                [
                    {"text": "🗺️ Ver en Google Maps", "url": maps_url}
                ],
                [
                    {"text": "📋 Copiar coordenadas", "callback_data": f"copy_{request_id}"}
                ]
            ]
        }
        
        # Enviar a Telegram
        print(f"📤 Enviando a Telegram (chat: {chat_id})...")
        success = send_telegram_message(chat_id, message, keyboard)
        
        if success:
            print("✅ Mensaje enviado exitosamente")
            return jsonify({
                "success": True, 
                "request_id": request_id,
                "message": "Solicitud enviada a Telegram"
            })
        else:
            print("❌ Error enviando a Telegram")
            return jsonify({"error": "No se pudo enviar a Telegram"}), 500
            
    except Exception as e:
        print(f"❌ Error en send_notification: {str(e)}")
        return jsonify({"error": f"Error interno: {str(e)}"}), 500

@app.route('/approve/<request_id>', methods=['GET'])
def approve_route(request_id):
    """Ruta para aprobar desde enlace web"""
    print(f"🌐 Aprobando desde URL: {request_id}")
    
    if request_id in pending_requests:
        data = pending_requests[request_id]
        
        # Actualizar GitHub
        success = update_github_file(data['location'])
        
        if success:
            # Notificar
            send_telegram_message(
                data['chat_id'], 
                f"✅ *{data['location'].get('name')}* aprobada y agregada a GitHub!"
            )
            
            # Eliminar de pendientes
            del pending_requests[request_id]
            
            return """
            <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: green;">✅ ¡Ubicación Aprobada!</h1>
                <p>La ubicación ha sido agregada a la base de datos.</p>
                <p><small>ID: {}</small></p>
                <a href="/">Volver al inicio</a>
            </body>
            </html>
            """.format(request_id)
        else:
            return "❌ Error al actualizar GitHub"
    
    return "❌ Solicitud no encontrada o ya procesada"

def handle_text_approval(chat_id, message):
    """Manejar aprobación por texto"""
    print(f"📝 Aprobación por texto: {message}")
    
    # Buscar ID en el mensaje usando regex
    id_match = re.search(r'✅ aprobar_(\w+)', message.lower())
    
    if id_match:
        request_id = id_match.group(1)
        if request_id in pending_requests:
            data = pending_requests[request_id]
            
            # Actualizar GitHub
            success = update_github_file(data['location'])
            
            if success:
                send_telegram_message(
                    chat_id, 
                    f"✅ *{data['location'].get('name')}* aprobada y agregada a GitHub!"
                )
                del pending_requests[request_id]
            else:
                send_telegram_message(chat_id, "❌ Error al actualizar GitHub")
        else:
            send_telegram_message(chat_id, "❌ Solicitud no encontrada")
    else:
        # Aprobar la primera solicitud pendiente
        for req_id, data in pending_requests.items():
            if data['chat_id'] == chat_id:
                success = update_github_file(data['location'])
                
                if success:
                    send_telegram_message(
                        chat_id, 
                        f"✅ *{data['location'].get('name')}* aprobada y agregada a GitHub!"
                    )
                    del pending_requests[req_id]
                else:
                    send_telegram_message(chat_id, "❌ Error al actualizar GitHub")
                break
        else:
            send_telegram_message(chat_id, "📭 No hay solicitudes pendientes")

def handle_text_rejection(chat_id, message):
    """Manejar rechazo por texto"""
    print(f"📝 Rechazo por texto: {message}")
    
    # Buscar ID en el mensaje usando regex
    id_match = re.search(r'❌ rechazar_(\w+)', message.lower())
    
    if id_match:
        request_id = id_match.group(1)
        if request_id in pending_requests:
            data = pending_requests[request_id]
            send_telegram_message(
                chat_id, 
                f"❌ *{data['location'].get('name')}* rechazada."
            )
            del pending_requests[request_id]
        else:
            send_telegram_message(chat_id, "❌ Solicitud no encontrada")
    else:
        # Rechazar la primera solicitud pendiente
        for req_id, data in pending_requests.items():
            if data['chat_id'] == chat_id:
                send_telegram_message(
                    chat_id, 
                    f"❌ *{data['location'].get('name')}* rechazada."
                )
                del pending_requests[req_id]
                break
        else:
            send_telegram_message(chat_id, "📭 No hay solicitudes pendientes")

def handle_button_approval(request_id, chat_id, message_id):
    """Manejar aprobación desde botón"""
    print(f"🔄 Aprobando desde botón: {request_id}")
    
    if request_id in pending_requests:
        data = pending_requests[request_id]
        
        # Actualizar GitHub
        success = update_github_file(data['location'])
        
        if success:
            # Editar mensaje original
            edit_telegram_message(
                chat_id, 
                message_id,
                f"✅ *APROBADO*\n\n"
                f"*{data['location'].get('name')}* ha sido agregada a GitHub!"
            )
            
            # Enviar confirmación
            send_telegram_message(
                chat_id,
                f"✅ *{data['location'].get('name')}* aprobada y agregada a GitHub!"
            )
            
            # Eliminar de pendientes
            del pending_requests[request_id]
            print(f"✅ Solicitud {request_id} aprobada exitosamente")
        else:
            edit_telegram_message(
                chat_id, 
                message_id,
                "❌ Error al actualizar GitHub"
            )
            print(f"❌ Error actualizando GitHub para {request_id}")
    else:
        edit_telegram_message(
            chat_id, 
            message_id,
            "❌ Solicitud no encontrada"
        )
        print(f"⚠️ Solicitud {request_id} no encontrada")

def handle_button_rejection(request_id, chat_id, message_id):
    """Manejar rechazo desde botón"""
    print(f"🔄 Rechazando desde botón: {request_id}")
    
    if request_id in pending_requests:
        data = pending_requests[request_id]
        
        # Editar mensaje original
        edit_telegram_message(
            chat_id, 
            message_id,
            f"❌ *RECHAZADO*\n\n"
            f"*{data['location'].get('name')}* ha sido rechazada."
        )
        
        # Eliminar de pendientes
        del pending_requests[request_id]
        print(f"❌ Solicitud {request_id} rechazada")
    else:
        edit_telegram_message(
            chat_id, 
            message_id,
            "❌ Solicitud no encontrada"
        )

def handle_copy_coords(request_id, callback_id):
    """Manejar copia de coordenadas"""
    print(f"📋 Copiando coordenadas: {request_id}")
    
    if request_id in pending_requests:
        data = pending_requests[request_id]
        coords = data['location'].get('coords', '')
        
        # Responder con coordenadas
        answer_callback_query(
            callback_id, 
            f"📍 Coordenadas:\n`{coords}`\n\nCopia manualmente",
            show_alert=True
        )
    else:
        answer_callback_query(
            callback_id, 
            "❌ Solicitud no encontrada",
            show_alert=True
        )

def show_pending_requests(chat_id):
    """Mostrar solicitudes pendientes"""
    print(f"📋 Mostrando pendientes para chat: {chat_id}")
    
    user_requests = [
        (req_id, data) for req_id, data in pending_requests.items() 
        if data['chat_id'] == chat_id
    ]
    
    if not user_requests:
        send_telegram_message(chat_id, "📭 No hay solicitudes pendientes.")
        return
    
    message = "📋 *Solicitudes Pendientes:*\n\n"
    
    for req_id, data in user_requests:
        loc = data['location']
        message += f"*📍 {loc.get('name', 'Sin nombre')}*\n"
        message += f"   🆔: `{req_id}`\n"
        message += f"   📍: `{loc.get('coords', '')}`\n"
        message += f"   🏙️: {loc.get('municipio', 'N/A')}\n\n"
    
    send_telegram_message(chat_id, message)

def update_github_file(location):
    """Actualizar archivo en GitHub - VERSIÓN FUNCIONAL"""
    print(f"🔄 Actualizando GitHub: {location.get('name')}")
    
    try:
        # 1. Obtener archivo actual
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        print(f"📥 Obteniendo archivo: {url}")
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Error obteniendo archivo: {response.status_code} - {response.text}")
            return False
        
        file_data = response.json()
        
        # 2. Decodificar contenido
        current_content = base64.b64decode(file_data['content']).decode('utf-8')
        current_json = json.loads(current_content) if current_content.strip() else {}
        
        print(f"📄 Archivo actual tiene {len(current_json)} entradas")
        
        # 3. Crear clave única
        name = location.get('name', 'Ubicación sin nombre')
        key = name.lower()\
            .replace(' ', '_')\
            .replace('ñ', 'n')\
            .replace('á', 'a')\
            .replace('é', 'e')\
            .replace('í', 'i')\
            .replace('ó', 'o')\
            .replace('ú', 'u')\
            .replace('ü', 'u')\
            .replace('.', '')\
            .replace(',', '')\
            .replace("'", '')\
            .replace('"', '')\
            .strip('_')
        
        # Si la clave ya existe, agregar sufijo
        original_key = key
        counter = 1
        while key in current_json:
            key = f"{original_key}_{counter}"
            counter += 1
        
        print(f"🔑 Clave generada: {key}")
        
        # 4. Agregar nueva entrada
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
        
        print(f"📤 Subiendo cambios a GitHub...")
        
        update_response = requests.put(url, headers=headers, json={
            "message": f"📍 Agregar: {name} ({location.get('municipio', '')})",
            "content": new_content_b64,
            "sha": file_data['sha']
        })
        
        print(f"📨 Respuesta GitHub: {update_response.status_code}")
        
        if update_response.status_code == 200:
            print("✅ GitHub actualizado exitosamente")
            return True
        else:
            print(f"❌ Error GitHub: {update_response.text}")
            return False
        
    except Exception as e:
        print(f"❌ Error en update_github_file: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def send_telegram_message(chat_id, text, reply_markup=None):
    """Enviar mensaje a Telegram"""
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
        
        print(f"📤 Enviando a Telegram...")
        response = requests.post(url, json=data, timeout=10)
        
        print(f"📨 Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Error Telegram: {response.text}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Error en send_telegram_message: {str(e)}")
        return False

def edit_telegram_message(chat_id, message_id, new_text):
    """Editar mensaje en Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText"
        
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": new_text,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(url, json=data, timeout=10)
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Error editando mensaje: {str(e)}")
        return False

def answer_callback_query(callback_id, text=None, show_alert=True):
    """Responder a callback query"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery"
        
        data = {
            "callback_query_id": callback_id,
            "show_alert": show_alert
        }
        
        if text:
            data["text"] = text
        
        response = requests.post(url, json=data, timeout=5)
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Error en answer_callback_query: {str(e)}")
        return False

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Iniciando servidor en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=True)