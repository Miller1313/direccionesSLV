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

# Configuración
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
GITHUB_REPO = os.getenv('GITHUB_REPO', 'Miller1313/direccionesSLV')
GITHUB_FILE = 'locations.json'
PORT = int(os.getenv('PORT', 10000))

# Almacenamiento en memoria
pending_requests = {}
app_start_time = time.time()

# Configuración de países SIMPLIFICADA
COUNTRIES = {
    'HN': {'name': 'Honduras', 'emoji': '🇭🇳', 'code': 'hn'},
    'SV': {'name': 'El Salvador', 'emoji': '🇸🇻', 'code': 'sv'},
    'CR': {'name': 'Costa Rica', 'emoji': '🇨🇷', 'code': 'cr'},
    'PA': {'name': 'Panamá', 'emoji': '🇵🇦', 'code': 'pa'}
}

# ========== MIDDLEWARE ==========
@app.before_request
def log_request_info():
    print(f"\n{'='*60}")
    print(f"📨 [{datetime.now().strftime('%H:%M:%S')}] {request.method} {request.path}")
    if request.is_json:
        try:
            data = request.get_json()
            # Mostrar solo datos relevantes para no saturar logs
            print(f"📦 Data recibida")
            if 'location' in data:
                loc = data['location']
                print(f"   País: {loc.get('pais', 'HN')}")
                print(f"   Nombre: {loc.get('name', 'Sin nombre')}")
                print(f"   Coords: {loc.get('coords', 'Sin coords')}")
        except:
            pass
    print('='*60)

# ========== RUTAS PRINCIPALES ==========
@app.route('/')
def home():
    """Página de inicio del servidor"""
    try:
        total_locations = 0
        try:
            # Intentar contar ubicaciones del archivo
            url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{GITHUB_FILE}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for country in COUNTRIES:
                    total_locations += len(data.get(country, {}))
        except:
            pass
        
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>📍 Sistema Centroamérica</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ 
                    font-family: 'Segoe UI', system-ui, sans-serif;
                    background: #1a1a1a; 
                    color: white; 
                    margin: 0; 
                    padding: 20px;
                    text-align: center;
                }}
                .container {{ 
                    max-width: 800px; 
                    margin: 0 auto; 
                    background: #262626; 
                    padding: 30px; 
                    border-radius: 15px; 
                    border: 2px solid #34675C; 
                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                }}
                h1 {{ 
                    color: #70c4f4; 
                    font-size: 28px;
                    margin-bottom: 10px;
                }}
                .subtitle {{
                    color: #98FFD9;
                    font-size: 16px;
                    margin-bottom: 30px;
                    opacity: 0.9;
                }}
                .status {{
                    background: #4CAF50;
                    color: white;
                    padding: 12px 25px;
                    border-radius: 25px;
                    display: inline-block;
                    margin: 20px 0;
                    font-weight: bold;
                    font-size: 16px;
                }}
                .countries-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: 15px;
                    margin: 30px 0;
                }}
                .country-card {{
                    background: #2d2d2d;
                    padding: 20px;
                    border-radius: 12px;
                    border-top: 4px solid;
                    transition: transform 0.3s;
                }}
                .country-card:hover {{
                    transform: translateY(-5px);
                }}
                .country-card.hn {{ border-color: #0E4BEF; }}
                .country-card.sv {{ border-color: #0E4BEF; }}
                .country-card.cr {{ border-color: #002B7F; }}
                .country-card.pa {{ border-color: #005293; }}
                .country-emoji {{
                    font-size: 40px;
                    margin-bottom: 10px;
                }}
                .country-name {{
                    font-weight: bold;
                    margin-bottom: 5px;
                    color: #98FFD9;
                }}
                .stats {{
                    background: rgba(255,255,255,0.05);
                    padding: 20px;
                    border-radius: 10px;
                    margin: 25px 0;
                    text-align: left;
                }}
                .endpoints {{
                    background: #2d2d2d;
                    padding: 20px;
                    border-radius: 10px;
                    margin: 20px 0;
                    text-align: left;
                    border-left: 4px solid #70c4f4;
                }}
                code {{
                    background: #1a1a1a;
                    padding: 3px 8px;
                    border-radius: 4px;
                    color: #98FFD9;
                    font-family: 'Courier New', monospace;
                }}
                .config-item {{
                    margin: 8px 0;
                    padding: 8px 0;
                    border-bottom: 1px solid rgba(255,255,255,0.1);
                }}
                @media (max-width: 600px) {{
                    .container {{ padding: 20px; }}
                    .countries-grid {{ grid-template-columns: 1fr; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📍 Sistema de Direcciones Centroamérica</h1>
                <p class="subtitle">Gestión de ubicaciones para Honduras, El Salvador, Costa Rica y Panamá</p>
                
                <div class="status">✅ SERVIDOR OPERATIVO</div>
                
                <div class="countries-grid">
                    <div class="country-card hn">
                        <div class="country-emoji">🇭🇳</div>
                        <div class="country-name">Honduras</div>
                        <div>Departamentos y municipios</div>
                    </div>
                    <div class="country-card sv">
                        <div class="country-emoji">🇸🇻</div>
                        <div class="country-name">El Salvador</div>
                        <div>Departamentos y municipios</div>
                    </div>
                    <div class="country-card cr">
                        <div class="country-emoji">🇨🇷</div>
                        <div class="country-name">Costa Rica</div>
                        <div>Provincias y cantones</div>
                    </div>
                    <div class="country-card pa">
                        <div class="country-emoji">🇵🇦</div>
                        <div class="country-name">Panamá</div>
                        <div>Provincias y distritos</div>
                    </div>
                </div>
                
                <div class="stats">
                    <strong>📊 Estadísticas:</strong><br>
                    <div class="config-item">• Ubicaciones totales: <code>{total_locations}</code></div>
                    <div class="config-item">• Solicitudes pendientes: <code>{len(pending_requests)}</code></div>
                    <div class="config-item">• Tiempo activo: <code>{int(time.time() - app_start_time)} segundos</code></div>
                    <div class="config-item">• Puerto: <code>{PORT}</code></div>
                </div>
                
                <div class="endpoints">
                    <strong>📡 Endpoints disponibles:</strong><br><br>
                    <div class="config-item"><code>GET /</code> - Esta página (status)</div>
                    <div class="config-item"><code>POST /webhook</code> - Webhook para Telegram</div>
                    <div class="config-item"><code>POST /send-notification</code> - Enviar solicitudes</div>
                    <div class="config-item"><code>GET /health</code> - Estado del servidor</div>
                    <div class="config-item"><code>GET /approve/&lt;id&gt;</code> - Aprobar desde navegador</div>
                </div>
                
                <div class="stats">
                    <strong>🔧 Configuración:</strong><br>
                    <div class="config-item">• Telegram Token: <code>{"✅ CONFIGURADO" if TELEGRAM_TOKEN else "❌ NO CONFIGURADO"}</code></div>
                    <div class="config-item">• GitHub Token: <code>{"✅ CONFIGURADO" if GITHUB_TOKEN else "❌ NO CONFIGURADO"}</code></div>
                    <div class="config-item">• Repositorio: <code>{GITHUB_REPO}</code></div>
                    <div class="config-item">• Archivo datos: <code>{GITHUB_FILE}</code></div>
                </div>
                
                <p style="margin-top: 30px; color: #B7B8B6; font-size: 14px;">
                    🕒 Última actualización: {datetime.now().strftime("%H:%M:%S")}
                </p>
            </div>
        </body>
        </html>
        '''
        return html
    except Exception as e:
        print(f"❌ Error en página de inicio: {str(e)}")
        return f"Error interno: {str(e)}", 500

@app.route('/health')
def health_check():
    """Endpoint de salud para monitoreo"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "pending_requests": len(pending_requests),
        "countries_supported": list(COUNTRIES.keys()),
        "config": {
            "telegram_configured": bool(TELEGRAM_TOKEN),
            "github_configured": bool(GITHUB_TOKEN),
            "github_repo": GITHUB_REPO,
            "port": PORT
        }
    })

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    """Webhook para recibir mensajes de Telegram"""
    print("📥 Webhook de Telegram recibido")
    
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Manejar mensajes de texto
        if 'message' in data:
            message = data['message'].get('text', '')
            chat_id = data['message']['chat']['id']
            
            print(f"📱 Mensaje de {chat_id}: {message[:50]}...")
            
            if message == '/start':
                response_text = (
                    "🤖 *Sistema de Aprobación Centroamérica*\n\n"
                    "Recibo solicitudes de nuevas ubicaciones para:\n"
                    "🇭🇳 Honduras\n🇸🇻 El Salvador\n🇨🇷 Costa Rica\n🇵🇦 Panamá\n\n"
                    "*Comandos disponibles:*\n"
                    "/start - Mostrar este mensaje\n"
                    "/lista - Ver solicitudes pendientes\n"
                    "/paises - Ver países soportados\n"
                    "/ayuda - Mostrar ayuda"
                )
                send_telegram_message(chat_id, response_text)
            
            elif message == '/lista' or message == '/list':
                show_pending_requests(chat_id)
            
            elif message == '/paises' or message == '/countries':
                paises_text = "\n".join([f"{c['emoji']} *{c['name']}*" for c in COUNTRIES.values()])
                send_telegram_message(chat_id, f"*🌎 Países soportados:*\n\n{paises_text}")
            
            elif message == '/ayuda' or message == '/help':
                send_telegram_message(chat_id,
                    "📋 *Ayuda del Sistema*\n\n"
                    "*Cómo funciona:*\n"
                    "1. Los usuarios agregan ubicaciones desde la web\n"
                    "2. Llegan aquí como solicitudes pendientes\n"
                    "3. Usa los botones para aprobar/rechazar\n\n"
                    "*Comandos:*\n"
                    "/lista - Ver solicitudes\n"
                    "/paises - Países disponibles"
                )
            
            # Manejar aprobación por texto (backup)
            elif 'aprobar' in message.lower() or 'approve' in message.lower():
                handle_text_command(chat_id, message, 'approve')
            
            # Manejar rechazo por texto (backup)
            elif 'rechazar' in message.lower() or 'reject' in message.lower():
                handle_text_command(chat_id, message, 'reject')
        
        # Manejar botones inline
        elif 'callback_query' in data:
            callback = data['callback_query']
            chat_id = callback['message']['chat']['id']
            message_id = callback['message']['message_id']
            callback_data = callback['data']
            
            print(f"🔄 Callback recibido: {callback_data}")
            
            # Responder inmediatamente al callback
            answer_callback_query(callback['id'])
            
            # Procesar acciones según el callback_data
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
        return jsonify({"error": "Error interno del servidor"}), 500

@app.route('/send-notification', methods=['POST'])
def send_notification():
    """Endpoint para recibir solicitudes del frontend"""
    print("🔔 Recibiendo solicitud del frontend...")
    
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type debe ser application/json"}), 400
        
        data = request.json
        
        location = data.get('location')
        chat_id = data.get('telegram_chat_id')
        
        if not location:
            return jsonify({"error": "Datos de ubicación requeridos"}), 400
        
        if not chat_id:
            return jsonify({"error": "chat_id requerido"}), 400
        
        # Validar coordenadas
        if 'coords' not in location:
            return jsonify({"error": "Coordenadas requeridas"}), 400
        
        # Validar país
        pais = location.get('pais', 'HN')
        if pais not in COUNTRIES:
            return jsonify({"error": f"País no soportado: {pais}"}), 400
        
        # Generar ID único
        request_id = str(uuid.uuid4())[:8]
        
        # Guardar en memoria
        pending_requests[request_id] = {
            'location': location,
            'chat_id': chat_id,
            'timestamp': datetime.now().isoformat(),
            'pais': pais
        }
        
        print(f"💾 Guardada solicitud {request_id} para {pais}")
        
        # Crear URL de Google Maps
        try:
            coords = location['coords'].split(',')
            lat = coords[0].strip()
            lon = coords[1].strip()
            maps_url = f"https://www.google.com/maps?q={lat},{lon}"
        except Exception as e:
            print(f"⚠️ Error creando URL de maps: {e}")
            maps_url = f"https://www.google.com/maps/search/{location.get('name', '')}"
        
        # Obtener información del país
        country = COUNTRIES[pais]
        
        # Crear mensaje para Telegram
        message = f"""{country['emoji']} *NUEVA SOLICITUD - {country['name'].upper()}*

*📌 Nombre:* {location.get('name', 'Sin nombre')}
*📍 Coordenadas:* `{location.get('coords', 'No especificadas')}`
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
                    {"text": "🗺️ Ver en Maps", "url": maps_url},
                    {"text": "📋 Copiar coords", "callback_data": f"copy_{request_id}"}
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
                "message": f"Solicitud enviada para {country['name']}"
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
    """Ruta para aprobar desde enlace web (fallback)"""
    print(f"🌐 Aprobando desde URL: {request_id}")
    
    try:
        if request_id in pending_requests:
            data = pending_requests[request_id]
            pais = data['pais']
            country = COUNTRIES.get(pais, {})
            
            # Actualizar GitHub
            success = update_github_file(data['location'])
            
            if success:
                # Notificar por Telegram
                send_telegram_message(
                    data['chat_id'], 
                    f"✅ *{data['location'].get('name', 'Ubicación')}* aprobada en {country.get('name', 'el país')}!"
                )
                
                # Eliminar de pendientes
                del pending_requests[request_id]
                
                # Página de éxito
                return f"""
                <html>
                <head>
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body {{ 
                            font-family: Arial, sans-serif; 
                            text-align: center; 
                            padding: 50px 20px;
                            background: #1a1a1a;
                            color: white;
                        }}
                        .container {{ 
                            max-width: 500px;
                            margin: 0 auto;
                            background: #262626;
                            padding: 30px;
                            border-radius: 15px;
                            border: 2px solid #4CAF50;
                        }}
                        h1 {{ color: #4CAF50; }}
                        .emoji {{ font-size: 60px; margin: 20px 0; }}
                        .btn {{
                            display: inline-block;
                            background: #34675C;
                            color: white;
                            padding: 12px 25px;
                            border-radius: 25px;
                            text-decoration: none;
                            margin-top: 20px;
                            font-weight: bold;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="emoji">✅</div>
                        <h1>¡Ubicación Aprobada!</h1>
                        <p>La ubicación ha sido agregada exitosamente a la base de datos.</p>
                        <p><strong>País:</strong> {country.get('name', 'N/A')}</p>
                        <p><strong>Nombre:</strong> {data['location'].get('name', 'Sin nombre')}</p>
                        <p><small>ID: {request_id}</small></p>
                        <a href="/" class="btn">Volver al inicio</a>
                    </div>
                </body>
                </html>
                """
            else:
                return "❌ Error al actualizar GitHub", 500
        
        return """
        <html>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1 style="color: #f44336;">❌ Solicitud no encontrada</h1>
            <p>La solicitud no existe o ya fue procesada.</p>
            <a href="/">Volver al inicio</a>
        </body>
        </html>
        """, 404
        
    except Exception as e:
        print(f"❌ Error en approve_route: {str(e)}")
        return f"Error interno: {str(e)}", 500

# ========== FUNCIONES AUXILIARES ==========
def handle_text_command(chat_id, message, action):
    """Manejar comandos de texto (aprobación/rechazo)"""
    print(f"📝 Comando de texto: {action} - {message[:50]}...")
    
    try:
        # Buscar ID en el mensaje
        request_id = None
        for req_id in pending_requests.keys():
            if req_id in message:
                request_id = req_id
                break
        
        if request_id and request_id in pending_requests:
            data = pending_requests[request_id]
            
            if action == 'approve':
                success = update_github_file(data['location'])
                if success:
                    send_telegram_message(
                        chat_id, 
                        f"✅ *{data['location'].get('name', 'Ubicación')}* aprobada exitosamente."
                    )
                    del pending_requests[request_id]
                else:
                    send_telegram_message(chat_id, "❌ Error al actualizar GitHub")
            else:  # reject
                send_telegram_message(
                    chat_id, 
                    f"❌ *{data['location'].get('name', 'Ubicación')}* rechazada."
                )
                del pending_requests[request_id]
        else:
            send_telegram_message(chat_id, "📭 No se encontró la solicitud")
            
    except Exception as e:
        print(f"❌ Error en handle_text_command: {str(e)}")
        send_telegram_message(chat_id, "❌ Error procesando el comando")

def handle_button_approval(request_id, chat_id, message_id):
    """Manejar aprobación desde botón inline"""
    print(f"🔄 Aprobando desde botón: {request_id}")
    
    try:
        if request_id in pending_requests:
            data = pending_requests[request_id]
            pais = data['pais']
            country = COUNTRIES.get(pais, {})
            
            # Actualizar GitHub
            success = update_github_file(data['location'])
            
            if success:
                # Editar mensaje original
                edit_telegram_message(
                    chat_id, 
                    message_id,
                    f"✅ *APROBADO - {country.get('emoji', '')} {country.get('name', '')}*\n\n"
                    f"*{data['location'].get('name', 'Ubicación')}* ha sido agregada exitosamente."
                )
                
                # Eliminar de pendientes
                del pending_requests[request_id]
                print(f"✅ Solicitud {request_id} aprobada")
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
    """Manejar rechazo desde botón inline"""
    print(f"🔄 Rechazando desde botón: {request_id}")
    
    try:
        if request_id in pending_requests:
            data = pending_requests[request_id]
            pais = data['pais']
            country = COUNTRIES.get(pais, {})
            
            # Editar mensaje original
            edit_telegram_message(
                chat_id, 
                message_id,
                f"❌ *RECHAZADO - {country.get('emoji', '')} {country.get('name', '')}*\n\n"
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
            
            answer_callback_query(
                callback_id, 
                f"📍 Coordenadas copiadas al portapapeles:\n`{coords}`",
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
    """Mostrar solicitudes pendientes al usuario"""
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
            pais = data.get('pais', 'HN')
            country = COUNTRIES.get(pais, {})
            
            message += f"{country.get('emoji', '📍')} *{loc.get('name', 'Sin nombre')}*\n"
            message += f"   🆔: `{req_id}`\n"
            message += f"   📍: `{loc.get('coords', '')}`\n"
            message += f"   🕒: {data['timestamp'][11:16]}\n\n"
        
        send_telegram_message(chat_id, message)
    except Exception as e:
        print(f"❌ Error en show_pending_requests: {str(e)}")
        send_telegram_message(chat_id, "❌ Error mostrando solicitudes")

def update_github_file(location):
    """Actualizar archivo en GitHub - VERSIÓN SIMPLIFICADA"""
    print(f"🔄 Actualizando GitHub: {location.get('name', 'Sin nombre')}")
    
    try:
        if not GITHUB_TOKEN:
            print("❌ GitHub Token no configurado")
            return False
        
        pais = location.get('pais', 'HN')
        country = COUNTRIES.get(pais, {})
        
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        print(f"📥 Obteniendo archivo: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Error obteniendo archivo: {response.status_code}")
            return False
        
        file_data = response.json()
        
        # Decodificar contenido
        current_content = base64.b64decode(file_data['content']).decode('utf-8')
        current_json = json.loads(current_content) if current_content.strip() else {}
        
        # Inicializar estructura por países si no existe
        for country_code in COUNTRIES:
            if country_code not in current_json:
                current_json[country_code] = {}
        
        if pais not in current_json:
            current_json[pais] = {}
        
        print(f"📄 País: {pais} | Entradas: {len(current_json[pais])}")
        
        # Crear clave única basada en nombre
        name = location.get('name', 'Ubicación sin nombre')
        key = name.lower()\
            .replace(' ', '_')\
            .replace('ñ', 'n')\
            .replace('á', 'a')\
            .replace('é', 'e')\
            .replace('í', 'i')\
            .replace('ó', 'o')\
            .replace('ú', 'u')\
            .replace('.', '')\
            .replace(',', '')\
            .replace("'", '')\
            .replace('"', '')\
            .strip('_')
        
        # Si la clave ya existe, agregar sufijo
        original_key = key
        counter = 1
        while key in current_json[pais]:
            key = f"{original_key}_{counter}"
            counter += 1
        
        print(f"🔑 Clave generada: {key}")
        
        # Parsear coordenadas
        try:
            coords = location['coords'].split(',')
            lat = float(coords[0].strip())
            lon = float(coords[1].strip())
        except Exception as e:
            print(f"❌ Error parseando coordenadas: {e}")
            lat = 0.0
            lon = 0.0
        
        # **ESTRUCTURA SIMPLIFICADA - SOLO DATOS BÁSICOS**
        current_json[pais][key] = {
            "name": name,
            "lat": lat,
            "lon": lon,
            "pais": pais,
            "type": location.get('type', 'colonia'),
            "added": datetime.now().isoformat(),
            "approved": True,
            "source": "user_submission",
            "detected_automatically": True,
            "full_address": location.get('detected', 'No detectado automáticamente')
        }
        
        # **ELIMINADO: Campos específicos por país**
        # Solo mantenemos la estructura básica
        
        # Subir cambios
        new_content = json.dumps(current_json, indent=2, ensure_ascii=False)
        new_content_b64 = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')
        
        print(f"📤 Subiendo cambios a GitHub...")
        
        update_response = requests.put(url, headers=headers, json={
            "message": f"📍 Agregar en {country.get('name', pais)}: {name}",
            "content": new_content_b64,
            "sha": file_data['sha']
        }, timeout=30)
        
        print(f"📨 Respuesta GitHub: {update_response.status_code}")
        
        if update_response.status_code == 200:
            print("✅ GitHub actualizado exitosamente")
            return True
        else:
            print(f"❌ Error GitHub: {update_response.text[:200]}")
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
            print(f"❌ Error Telegram: {response.text[:200]}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Error en send_telegram_message: {str(e)}")
        return False

def edit_telegram_message(chat_id, message_id, new_text):
    """Editar mensaje existente en Telegram"""
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

def answer_callback_query(callback_id, text=None, show_alert=False):
    """Responder a callback query de Telegram"""
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
    print(f"💥 500 Internal Server Error")
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
    
    print("=" * 60)
    print("🚀 Sistema de Direcciones Centroamérica")
    print("=" * 60)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌎 Países: {', '.join([f'{c["emoji"]} {c["name"]}' for c in COUNTRIES.values()])}")
    print(f"🔧 Puerto: {PORT}")
    print(f"🤖 Telegram Token: {'✅ CONFIGURADO' if TELEGRAM_TOKEN else '❌ NO CONFIGURADO'}")
    print(f"🐙 GitHub Token: {'✅ CONFIGURADO' if GITHUB_TOKEN else '❌ NO CONFIGURADO'}")
    print(f"📁 Repositorio: {GITHUB_REPO}")
    print(f"📄 Archivo datos: {GITHUB_FILE}")
    print("=" * 60)
    
    # Verificar variables críticas
    if not TELEGRAM_TOKEN:
        print("⚠️ ADVERTENCIA: TELEGRAM_BOT_TOKEN no está configurado")
        print("⚠️ El bot de Telegram no funcionará correctamente")
    
    if not GITHUB_TOKEN:
        print("⚠️ ADVERTENCIA: GITHUB_TOKEN no está configurado")
        print("⚠️ No se podrán guardar ubicaciones en GitHub")
    
    # Iniciar servidor
    app.run(host='0.0.0.0', port=PORT, debug=False)