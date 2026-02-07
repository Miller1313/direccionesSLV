from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import base64
import requests
from datetime import datetime
import uuid
import re
import time
import traceback

app = Flask(__name__)
CORS(app)

# Configuración con valores por defecto para debugging
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
GITHUB_REPO = os.getenv('GITHUB_REPO', 'Miller1313/direccionesSLV')
GITHUB_FILE = 'locations.json'

# Obtener puerto dinámico para Render
PORT = int(os.getenv('PORT', 10000))

# Almacenamiento simple en memoria
pending_requests = {}
app_start_time = time.time()

# ========== MIDDLEWARE PARA LOGGING ==========
@app.before_request
def log_request_info():
    print(f"\n{'='*50}")
    print(f"📨 [{datetime.now().strftime('%H:%M:%S')}] {request.method} {request.path}")
    print(f"📦 Headers: {dict(request.headers)}")
    if request.is_json:
        try:
            data = request.get_json()
            print(f"📦 JSON Data: {json.dumps(data, indent=2)}")
        except:
            print(f"📦 Raw Data: {request.get_data()}")
    print('='*50)

@app.after_request
def log_response_info(response):
    print(f"\n{'='*50}")
    print(f"📤 [{datetime.now().strftime('%H:%M:%S')}] Response: {response.status}")
    print('='*50)
    return response

# ========== RUTAS ==========
@app.route('/')
def home():
    print("🌐 Página de inicio solicitada")
    try:
        # HTML con las llaves CSS escapadas correctamente
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>🤖 Bot de Aprobación Honduras</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    text-align: center; 
                    padding: 50px; 
                    background: #1a1a1a; 
                    color: white; 
                }}
                .container {{ 
                    max-width: 800px; 
                    margin: 0 auto; 
                    background: #262626; 
                    padding: 30px; 
                    border-radius: 15px; 
                    border: 2px solid #34675C; 
                }}
                h1 {{ color: #70c4f4; }}
                .status {{ 
                    background: #4CAF50; 
                    color: white; 
                    padding: 10px 20px; 
                    border-radius: 20px; 
                    display: inline-block; 
                    margin: 20px 0; 
                }}
                .status.error {{ background: #f44336; }}
                .endpoint {{ 
                    background: #2d2d2d; 
                    padding: 15px; 
                    margin: 15px 0; 
                    border-radius: 8px; 
                    text-align: left; 
                    border-left: 4px solid #70c4f4; 
                }}
                code {{ 
                    background: #1a1a1a; 
                    padding: 3px 6px; 
                    border-radius: 4px; 
                    color: #98FFD9; 
                }}
                .config-item {{ margin: 5px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 Bot de Aprobación Honduras</h1>
                
                <div class="status">
                    ✅ SERVIDOR OPERATIVO
                </div>
                
                <p>Servidor para gestión de ubicaciones de Honduras</p>
                
                <div class="endpoint">
                    <strong>📡 Endpoints disponibles:</strong><br><br>
                    <code>GET /</code> - Esta página (status)<br>
                    <code>POST /webhook</code> - Webhook para Telegram<br>
                    <code>POST /send-notification</code> - Enviar solicitudes desde HTML<br>
                    <code>GET /approve/&lt;id&gt;</code> - Aprobar desde navegador
                </div>
                
                <div class="endpoint">
                    <strong>🔧 Configuración actual:</strong><br><br>
                    <div class="config-item">• Puerto: <code>{PORT}</code></div>
                    <div class="config-item">• Telegram Token: <code>{"✅ Configurado" if TELEGRAM_TOKEN else "❌ No configurado"}</code></div>
                    <div class="config-item">• GitHub Repo: <code>{GITHUB_REPO}</code></div>
                    <div class="config-item">• GitHub Token: <code>{"✅ Configurado" if GITHUB_TOKEN else "❌ No configurado"}</code></div>
                    <div class="config-item">• Archivo datos: <code>{GITHUB_FILE}</code></div>
                </div>
                
                <div class="endpoint">
                    <strong>📊 Estado:</strong><br><br>
                    <div class="config-item">• Solicitudes pendientes: <code>{len(pending_requests)}</code></div>
                    <div class="config-item">• Tiempo activo: <code>{int(time.time() - app_start_time)} segundos</code></div>
                </div>
                
                <p><small>🔄 Última actualización: {datetime.now().strftime("%H:%M:%S")}</small></p>
            </div>
        </body>
        </html>
        '''
        return html_content
    except Exception as e:
        print(f"❌ Error en página de inicio: {str(e)}")
        traceback.print_exc()
        return f"Error interno: {str(e)}", 500

@app.route('/health')
def health_check():
    """Endpoint simple para verificar que el servidor está vivo"""
    print("❤️ Health check solicitado")
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "pending_requests": len(pending_requests),
        "config": {
            "telegram_token_configured": bool(TELEGRAM_TOKEN),
            "github_token_configured": bool(GITHUB_TOKEN),
            "github_repo": GITHUB_REPO,
            "port": PORT
        }
    })

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    """Webhook para Telegram"""
    print("📥 Webhook de Telegram recibido")
    
    try:
        data = request.json
        
        if not data:
            print("❌ No hay datos JSON en la solicitud")
            return jsonify({"error": "No data provided"}), 400
        
        print(f"📦 Datos recibidos: {json.dumps(data, indent=2)}")
        
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
            
            # Manejar aprobación por texto
            elif message.lower().startswith('✅ aprobar'):
                handle_text_approval(chat_id, message)
            
            # Manejar rechazo por texto
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
        
    except Exception as e:
        print(f"❌ Error en webhook: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/send-notification', methods=['POST'])
def send_notification():
    """Endpoint para que tu HTML envíe solicitudes"""
    print("🔔 Recibiendo solicitud del HTML...")
    
    try:
        # Verificar que hay datos JSON
        if not request.is_json:
            print("❌ La solicitud no es JSON")
            return jsonify({"error": "Content-Type debe ser application/json"}), 400
        
        data = request.json
        print(f"📦 Datos recibidos: {json.dumps(data, indent=2)}")
        
        location = data.get('location')
        chat_id = data.get('telegram_chat_id')
        
        if not location:
            print("❌ Error: No hay datos de ubicación")
            return jsonify({"error": "Datos de ubicación requeridos"}), 400
        
        if not chat_id:
            print("❌ Error: No hay chat_id")
            return jsonify({"error": "chat_id requerido"}), 400
        
        # Verificar coordenadas
        if 'coords' not in location:
            print("❌ Error: No hay coordenadas")
            return jsonify({"error": "Coordenadas requeridas"}), 400
        
        # Generar ID único
        request_id = str(uuid.uuid4())[:8]
        
        # Guardar en memoria
        pending_requests[request_id] = {
            'location': location,
            'chat_id': chat_id,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"💾 Guardada solicitud {request_id}: {location.get('name', 'Sin nombre')}")
        
        # Crear URL de Google Maps
        try:
            coords = location['coords'].split(',')
            lat = coords[0].strip()
            lon = coords[1].strip()
            maps_url = f"https://www.google.com/maps?q={lat},{lon}"
        except Exception as e:
            print(f"⚠️ Error creando URL de maps: {e}")
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
        traceback.print_exc()
        return jsonify({"error": f"Error interno: {str(e)}"}), 500

@app.route('/approve/<request_id>', methods=['GET'])
def approve_route(request_id):
    """Ruta para aprobar desde enlace web"""
    print(f"🌐 Aprobando desde URL: {request_id}")
    
    try:
        if request_id in pending_requests:
            data = pending_requests[request_id]
            
            # Actualizar GitHub
            success = update_github_file(data['location'])
            
            if success:
                # Notificar
                send_telegram_message(
                    data['chat_id'], 
                    f"✅ *{data['location'].get('name', 'Ubicación')}* aprobada y agregada a GitHub!"
                )
                
                # Eliminar de pendientes
                del pending_requests[request_id]
                
                return f"""
                <html>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1 style="color: green;">✅ ¡Ubicación Aprobada!</h1>
                    <p>La ubicación ha sido agregada a la base de datos.</p>
                    <p><small>ID: {request_id}</small></p>
                    <a href="/">Volver al inicio</a>
                </body>
                </html>
                """
            else:
                return "❌ Error al actualizar GitHub", 500
        
        return "❌ Solicitud no encontrada o ya procesada", 404
        
    except Exception as e:
        print(f"❌ Error en approve_route: {str(e)}")
        return f"Error interno: {str(e)}", 500

# ========== FUNCIONES AUXILIARES ==========
def handle_text_approval(chat_id, message):
    """Manejar aprobación por texto"""
    print(f"📝 Aprobación por texto: {message}")
    
    try:
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
                        f"✅ *{data['location'].get('name', 'Ubicación')}* aprobada y agregada a GitHub!"
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
                            f"✅ *{data['location'].get('name', 'Ubicación')}* aprobada y agregada a GitHub!"
                        )
                        del pending_requests[req_id]
                    else:
                        send_telegram_message(chat_id, "❌ Error al actualizar GitHub")
                    break
            else:
                send_telegram_message(chat_id, "📭 No hay solicitudes pendientes")
    except Exception as e:
        print(f"❌ Error en handle_text_approval: {str(e)}")
        send_telegram_message(chat_id, f"❌ Error interno: {str(e)}")

def handle_text_rejection(chat_id, message):
    """Manejar rechazo por texto"""
    print(f"📝 Rechazo por texto: {message}")
    
    try:
        # Buscar ID en el mensaje usando regex
        id_match = re.search(r'❌ rechazar_(\w+)', message.lower())
        
        if id_match:
            request_id = id_match.group(1)
            if request_id in pending_requests:
                data = pending_requests[request_id]
                send_telegram_message(
                    chat_id, 
                    f"❌ *{data['location'].get('name', 'Ubicación')}* rechazada."
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
                        f"❌ *{data['location'].get('name', 'Ubicación')}* rechazada."
                    )
                    del pending_requests[req_id]
                    break
            else:
                send_telegram_message(chat_id, "📭 No hay solicitudes pendientes")
    except Exception as e:
        print(f"❌ Error en handle_text_rejection: {str(e)}")

def handle_button_approval(request_id, chat_id, message_id):
    """Manejar aprobación desde botón"""
    print(f"🔄 Aprobando desde botón: {request_id}")
    
    try:
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
                    f"*{data['location'].get('name', 'Ubicación')}* ha sido agregada a GitHub!"
                )
                
                # Enviar confirmación
                send_telegram_message(
                    chat_id,
                    f"✅ *{data['location'].get('name', 'Ubicación')}* aprobada y agregada a GitHub!"
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
    except Exception as e:
        print(f"❌ Error en handle_button_approval: {str(e)}")

def handle_button_rejection(request_id, chat_id, message_id):
    """Manejar rechazo desde botón"""
    print(f"🔄 Rechazando desde botón: {request_id}")
    
    try:
        if request_id in pending_requests:
            data = pending_requests[request_id]
            
            # Editar mensaje original
            edit_telegram_message(
                chat_id, 
                message_id,
                f"❌ *RECHAZADO*\n\n"
                f"*{data['location'].get('name', 'Ubicación')}* ha sido rechazada."
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
    except Exception as e:
        print(f"❌ Error en handle_button_rejection: {str(e)}")

def handle_copy_coords(request_id, callback_id):
    """Manejar copia de coordenadas"""
    print(f"📋 Copiando coordenadas: {request_id}")
    
    try:
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
    except Exception as e:
        print(f"❌ Error en handle_copy_coords: {str(e)}")

def show_pending_requests(chat_id):
    """Mostrar solicitudes pendientes"""
    print(f"📋 Mostrando pendientes para chat: {chat_id}")
    
    try:
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
    except Exception as e:
        print(f"❌ Error en show_pending_requests: {str(e)}")
        send_telegram_message(chat_id, "❌ Error mostrando solicitudes")

def update_github_file(location):
    """Actualizar archivo en GitHub"""
    print(f"🔄 Actualizando GitHub: {location.get('name', 'Sin nombre')}")
    
    try:
        # Verificar que tenemos el token
        if not GITHUB_TOKEN:
            print("❌ GitHub Token no configurado")
            return False
        
        # 1. Obtener archivo actual
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        print(f"📥 Obteniendo archivo: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Error obteniendo archivo: {response.status_code}")
            print(f"📄 Respuesta: {response.text}")
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
        try:
            coords = location['coords'].split(',')
            lat = float(coords[0].strip())
            lon = float(coords[1].strip())
        except Exception as e:
            print(f"❌ Error parseando coordenadas: {e}")
            lat = 0.0
            lon = 0.0
        
        # En el archivo app.py, busca la función update_github_file() y modifica el diccionario:
        current_json[key] = {
            "name": name,
            "lat": lat,
            "lon": lon,
            "municipio": location.get('municipio', 'Por determinar'),
            "departamento": location.get('departamento', 'Por determinar'),
            "type": location.get('type', 'colonia'),
            "added": datetime.now().isoformat(),
            "approved": True,
            "source": "user_submission",  # ESTA LÍNEA ES CRÍTICA
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
        }, timeout=30)
        
        print(f"📨 Respuesta GitHub: {update_response.status_code}")
        
        if update_response.status_code == 200:
            print("✅ GitHub actualizado exitosamente")
            return True
        else:
            print(f"❌ Error GitHub: {update_response.text}")
            return False
        
    except Exception as e:
        print(f"❌ Error en update_github_file: {str(e)}")
        traceback.print_exc()
        return False

def send_telegram_message(chat_id, text, reply_markup=None):
    """Enviar mensaje a Telegram"""
    try:
        if not TELEGRAM_TOKEN:
            print("❌ Telegram Token no configurado")
            return False
        
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
        response = requests.post(url, json=data, timeout=30)
        
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
        if not TELEGRAM_TOKEN:
            return False
            
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText"
        
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": new_text,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(url, json=data, timeout=30)
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Error editando mensaje: {str(e)}")
        return False

def answer_callback_query(callback_id, text=None, show_alert=True):
    """Responder a callback query"""
    try:
        if not TELEGRAM_TOKEN:
            return False
            
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

# ========== MANEJO DE ERRORES GLOBALES ==========
@app.errorhandler(404)
def not_found_error(error):
    print(f"🔍 404 Not Found: {request.path}")
    return jsonify({"error": "Endpoint no encontrado"}), 404

@app.errorhandler(500)
def internal_error(error):
    print(f"💥 500 Internal Server Error: {str(error)}")
    traceback.print_exc()
    return jsonify({"error": "Error interno del servidor"}), 500

@app.errorhandler(Exception)
def handle_exception(error):
    print(f"💥 Excepción no manejada: {str(error)}")
    traceback.print_exc()
    return jsonify({"error": "Error interno del servidor"}), 500

# ========== INICIALIZACIÓN ==========
if __name__ == '__main__':
    app_start_time = time.time()
    
    print("=" * 50)
    print("🚀 Iniciando Bot de Aprobación Honduras")
    print("=" * 50)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔧 Puerto: {PORT}")
    print(f"🤖 Telegram Token: {'✅ Configurado' if TELEGRAM_TOKEN else '❌ No configurado'}")
    print(f"🐙 GitHub Token: {'✅ Configurado' if GITHUB_TOKEN else '❌ No configurado'}")
    print(f"📁 GitHub Repo: {GITHUB_REPO}")
    print(f"📄 Archivo datos: {GITHUB_FILE}")
    print("=" * 50)
    
    # Verificar variables de entorno críticas
    if not TELEGRAM_TOKEN:
        print("⚠️ ADVERTENCIA: TELEGRAM_BOT_TOKEN no está configurado")
    
    if not GITHUB_TOKEN:
        print("⚠️ ADVERTENCIA: GITHUB_TOKEN no está configurado")
    
    app.run(host='0.0.0.0', port=PORT, debug=False)
