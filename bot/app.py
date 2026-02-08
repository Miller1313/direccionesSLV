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

# Configuración de países
COUNTRIES_CONFIG = {
    'HN': {
        'name': 'Honduras',
        'emoji': '🇭🇳',
        'levels': ['departamento', 'municipio'],
        'bounds': {'min_lat': 12.0, 'max_lat': 17.0, 'min_lon': -89.5, 'max_lon': -83.0}
    },
    'SV': {
        'name': 'El Salvador',
        'emoji': '🇸🇻',
        'levels': ['departamento', 'municipio'],
        'bounds': {'min_lat': 13.0, 'max_lat': 14.5, 'min_lon': -90.0, 'max_lon': -87.5}
    },
    'CR': {
        'name': 'Costa Rica',
        'emoji': '🇨🇷',
        'levels': ['provincia', 'canton', 'distrito'],
        'bounds': {'min_lat': 8.0, 'max_lat': 11.5, 'min_lon': -86.0, 'max_lon': -82.5}
    },
    'PA': {
        'name': 'Panamá',
        'emoji': '🇵🇦',
        'levels': ['provincia', 'distrito', 'corregimiento'],
        'bounds': {'min_lat': 7.0, 'max_lat': 10.0, 'min_lon': -83.0, 'max_lon': -77.0}
    }
}

# ========== MIDDLEWARE ==========
@app.before_request
def log_request_info():
    print(f"\n{'='*50}")
    print(f"📨 [{datetime.now().strftime('%H:%M:%S')}] {request.method} {request.path}")
    if request.is_json:
        try:
            data = request.get_json()
            print(f"📦 JSON Data: {json.dumps(data, indent=2)}")
        except:
            pass
    print('='*50)

# ========== RUTAS ==========
@app.route('/')
def home():
    html_content = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🤖 Sistema de Aprobación Centroamérica</title>
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                text-align: center; 
                padding: 50px; 
                background: #1a1a1a; 
                color: white; 
            }}
            .container {{ 
                max-width: 900px; 
                margin: 0 auto; 
                background: #262626; 
                padding: 30px; 
                border-radius: 15px; 
                border: 2px solid #34675C; 
            }}
            h1 {{ color: #70c4f4; }}
            .countries-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            .country-card {{
                background: #2d2d2d;
                padding: 20px;
                border-radius: 10px;
                border-left: 4px solid;
                text-align: center;
            }}
            .country-card.hn {{ border-color: #0E4BEF; }}
            .country-card.sv {{ border-color: #0E4BEF; }}
            .country-card.cr {{ border-color: #002B7F; }}
            .country-card.pa {{ border-color: #005293; }}
            .country-emoji {{ font-size: 40px; margin-bottom: 10px; }}
            .status {{ 
                background: #4CAF50; 
                color: white; 
                padding: 10px 20px; 
                border-radius: 20px; 
                display: inline-block; 
                margin: 20px 0; 
            }}
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
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Sistema de Aprobación Centroamérica</h1>
            
            <div class="status">
                ✅ SERVIDOR OPERATIVO
            </div>
            
            <p>Sistema para gestión de ubicaciones en Centroamérica</p>
            
            <div class="countries-grid">
                <div class="country-card hn">
                    <div class="country-emoji">🇭🇳</div>
                    <h3>Honduras</h3>
                    <p>Departamentos y municipios</p>
                </div>
                <div class="country-card sv">
                    <div class="country-emoji">🇸🇻</div>
                    <h3>El Salvador</h3>
                    <p>Departamentos y municipios</p>
                </div>
                <div class="country-card cr">
                    <div class="country-emoji">🇨🇷</div>
                    <h3>Costa Rica</h3>
                    <p>Provincias y cantones</p>
                </div>
                <div class="country-card pa">
                    <div class="country-emoji">🇵🇦</div>
                    <h3>Panamá</h3>
                    <p>Provincias y distritos</p>
                </div>
            </div>
            
            <div class="endpoint">
                <strong>📡 Endpoints disponibles:</strong><br><br>
                <code>GET /</code> - Esta página<br>
                <code>POST /webhook</code> - Webhook Telegram<br>
                <code>POST /send-notification</code> - Enviar solicitudes<br>
                <code>GET /health</code> - Estado del servidor
            </div>
            
            <div class="endpoint">
                <strong>🔧 Configuración:</strong><br><br>
                <div>• Telegram Token: <code>{"✅" if TELEGRAM_TOKEN else "❌"}</code></div>
                <div>• GitHub Token: <code>{"✅" if GITHUB_TOKEN else "❌"}</code></div>
                <div>• Puerto: <code>{PORT}</code></div>
                <div>• Solicitudes pendientes: <code>{len(pending_requests)}</code></div>
            </div>
        </div>
    </body>
    </html>
    '''
    return html_content

@app.route('/health')
def health_check():
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "pending_requests": len(pending_requests),
        "countries": list(COUNTRIES_CONFIG.keys()),
        "config": {
            "telegram_token_configured": bool(TELEGRAM_TOKEN),
            "github_token_configured": bool(GITHUB_TOKEN)
        }
    })

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Manejar mensajes de texto
        if 'message' in data:
            message = data['message'].get('text', '')
            chat_id = data['message']['chat']['id']
            
            if message == '/start':
                send_telegram_message(chat_id, 
                    "🤖 *Sistema de Aprobación Centroamérica*\n\n"
                    "Recibo solicitudes de nuevas ubicaciones para:\n"
                    "🇭🇳 Honduras\n🇸🇻 El Salvador\n🇨🇷 Costa Rica\n🇵🇦 Panamá\n\n"
                    "*Comandos:*\n"
                    "/lista - Ver solicitudes pendientes\n"
                    "/paises - Ver países soportados")
            
            elif message == '/lista':
                show_pending_requests(chat_id)
            
            elif message == '/paises':
                countries_text = "\n".join([f"{c['emoji']} {c['name']}" for c in COUNTRIES_CONFIG.values()])
                send_telegram_message(chat_id, 
                    f"*🌎 Países soportados:*\n\n{countries_text}")
        
        # Manejar botones inline
        elif 'callback_query' in data:
            callback = data['callback_query']
            chat_id = callback['message']['chat']['id']
            message_id = callback['message']['message_id']
            callback_data = callback['data']
            
            answer_callback_query(callback['id'])
            
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
    try:
        data = request.json
        
        location = data.get('location')
        chat_id = data.get('telegram_chat_id')
        
        if not location or not chat_id:
            return jsonify({"error": "Datos incompletos"}), 400
        
        # Verificar país
        pais = location.get('pais', 'HN')
        if pais not in COUNTRIES_CONFIG:
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
        
        print(f"💾 Solicitud {request_id} para {pais}: {location.get('name', 'Sin nombre')}")
        
        # Crear mensaje según país
        country = COUNTRIES_CONFIG[pais]
        coords = location.get('coords', '').split(',')
        
        if len(coords) == 2:
            lat, lon = coords[0].strip(), coords[1].strip()
            maps_url = f"https://www.google.com/maps?q={lat},{lon}"
        else:
            maps_url = f"https://www.google.com/maps/search/{location.get('name', '')}"
        
        # Construir mensaje
        message = f"""{country['emoji']} *NUEVA SOLICITUD - {country['name'].upper()}*

*📌 Nombre:* {location.get('name', 'Sin nombre')}
*📍 Coordenadas:* `{location.get('coords', 'No especificadas')}`"""

        # Campos según país
        if pais in ['HN', 'SV']:
            message += f"""
*🏙️ Municipio:* {location.get('municipio', 'No especificado')}
*🏛️ Departamento:* {location.get('departamento', 'No especificado')}"""
        elif pais == 'CR':
            message += f"""
*🏙️ Cantón:* {location.get('canton', 'No especificado')}
*🏛️ Provincia:* {location.get('provincia', 'No especificado')}
*📍 Distrito:* {location.get('distrito', 'No especificado')}"""
        elif pais == 'PA':
            message += f"""
*🏙️ Distrito:* {location.get('distrito', 'No especificado')}
*🏛️ Provincia:* {location.get('provincia', 'No especificado')}
*📍 Corregimiento:* {location.get('corregimiento', 'No especificado')}"""

        message += f"""
*📋 Tipo:* {location.get('type', 'colonia')}

*🆔 ID:* `{request_id}`"""
        
        # Crear teclado
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
        success = send_telegram_message(chat_id, message, keyboard)
        
        if success:
            return jsonify({
                "success": True, 
                "request_id": request_id,
                "message": f"Solicitud enviada para {country['name']}"
            })
        else:
            return jsonify({"error": "No se pudo enviar a Telegram"}), 500
            
    except Exception as e:
        print(f"❌ Error en send_notification: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"Error interno: {str(e)}"}), 500

# ========== FUNCIONES AUXILIARES ==========
def update_github_file(location):
    try:
        if not GITHUB_TOKEN:
            print("❌ GitHub Token no configurado")
            return False
        
        pais = location.get('pais', 'HN')
        
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Error obteniendo archivo: {response.status_code}")
            return False
        
        file_data = response.json()
        current_content = base64.b64decode(file_data['content']).decode('utf-8')
        current_json = json.loads(current_content) if current_content.strip() else {}
        
        # Inicializar estructura por países
        for country_code in COUNTRIES_CONFIG:
            if country_code not in current_json:
                current_json[country_code] = {}
        
        if pais not in current_json:
            current_json[pais] = {}
        
        # Crear clave única
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
            .strip('_')
        
        original_key = key
        counter = 1
        while key in current_json[pais]:
            key = f"{original_key}_{counter}"
            counter += 1
        
        # Parsear coordenadas
        try:
            coords = location['coords'].split(',')
            lat = float(coords[0].strip())
            lon = float(coords[1].strip())
        except:
            lat = 0.0
            lon = 0.0
        
        # Crear entrada según país
        nueva_entrada = {
            "name": name,
            "lat": lat,
            "lon": lon,
            "pais": pais,
            "type": location.get('type', 'colonia'),
            "added": datetime.now().isoformat(),
            "approved": True,
            "source": "user_submission",
            "detected_automatically": True,
            "full_address": location.get('detected', '')
        }
        
        # Campos específicos por país
        if pais in ['HN', 'SV']:
            nueva_entrada.update({
                "municipio": location.get('municipio', 'Por determinar'),
                "departamento": location.get('departamento', 'Por determinar')
            })
        elif pais == 'CR':
            nueva_entrada.update({
                "canton": location.get('canton', 'Por determinar'),
                "provincia": location.get('provincia', 'Por determinar'),
                "distrito": location.get('distrito', 'Por determinar')
            })
        elif pais == 'PA':
            nueva_entrada.update({
                "distrito": location.get('distrito', 'Por determinar'),
                "provincia": location.get('provincia', 'Por determinar'),
                "corregimiento": location.get('corregimiento', 'Por determinar')
            })
        
        current_json[pais][key] = nueva_entrada
        
        # Subir cambios
        new_content = json.dumps(current_json, indent=2, ensure_ascii=False)
        new_content_b64 = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')
        
        update_response = requests.put(url, headers=headers, json={
            "message": f"📍 Agregar en {COUNTRIES_CONFIG[pais]['name']}: {name}",
            "content": new_content_b64,
            "sha": file_data['sha']
        }, timeout=30)
        
        if update_response.status_code == 200:
            print(f"✅ {pais} actualizado: {name}")
            return True
        else:
            print(f"❌ Error GitHub: {update_response.text}")
            return False
        
    except Exception as e:
        print(f"❌ Error en update_github_file: {str(e)}")
        traceback.print_exc()
        return False

def handle_button_approval(request_id, chat_id, message_id):
    if request_id in pending_requests:
        data = pending_requests[request_id]
        pais = data['pais']
        country = COUNTRIES_CONFIG.get(pais, {})
        
        success = update_github_file(data['location'])
        
        if success:
            edit_telegram_message(
                chat_id, 
                message_id,
                f"✅ *APROBADO - {country.get('emoji', '')} {country.get('name', '')}*\n\n"
                f"*{data['location'].get('name', 'Ubicación')}* ha sido agregada."
            )
            
            send_telegram_message(
                chat_id,
                f"✅ *{data['location'].get('name', 'Ubicación')}* aprobada en {country.get('name', 'el país')}."
            )
            
            del pending_requests[request_id]
        else:
            edit_telegram_message(
                chat_id, 
                message_id,
                "❌ Error al actualizar GitHub"
            )
    else:
        edit_telegram_message(
            chat_id, 
            message_id,
            "❌ Solicitud no encontrada"
        )

def handle_button_rejection(request_id, chat_id, message_id):
    if request_id in pending_requests:
        data = pending_requests[request_id]
        pais = data['pais']
        country = COUNTRIES_CONFIG.get(pais, {})
        
        edit_telegram_message(
            chat_id, 
            message_id,
            f"❌ *RECHAZADO - {country.get('emoji', '')} {country.get('name', '')}*\n\n"
            f"*{data['location'].get('name', 'Ubicación')}* ha sido rechazada."
        )
        
        del pending_requests[request_id]

def show_pending_requests(chat_id):
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
        country = COUNTRIES_CONFIG.get(pais, {})
        
        message += f"{country.get('emoji', '📍')} *{loc.get('name', 'Sin nombre')}*\n"
        message += f"   🆔: `{req_id}`\n"
        message += f"   📍: `{loc.get('coords', '')}`\n"
        message += f"   🏙️: {loc.get('municipio', loc.get('canton', 'N/A'))}\n\n"
    
    send_telegram_message(chat_id, message)

def send_telegram_message(chat_id, text, reply_markup=None):
    try:
        if not TELEGRAM_TOKEN:
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
        
        response = requests.post(url, json=data, timeout=30)
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Error en send_telegram_message: {str(e)}")
        return False

def edit_telegram_message(chat_id, message_id, new_text):
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

def handle_copy_coords(request_id, callback_id):
    if request_id in pending_requests:
        data = pending_requests[request_id]
        coords = data['location'].get('coords', '')
        
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

# ========== ERROR HANDLERS ==========
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Endpoint no encontrado"}), 404

@app.errorhandler(500)
def internal_error(error):
    traceback.print_exc()
    return jsonify({"error": "Error interno del servidor"}), 500

# ========== INICIALIZACIÓN ==========
if __name__ == '__main__':
    app_start_time = time.time()
    
    print("=" * 50)
    print("🚀 Sistema de Aprobación Centroamérica")
    print("=" * 50)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌎 Países soportados: {', '.join(COUNTRIES_CONFIG.keys())}")
    print(f"🔧 Puerto: {PORT}")
    print(f"🤖 Telegram: {'✅' if TELEGRAM_TOKEN else '❌'}")
    print(f"🐙 GitHub: {'✅' if GITHUB_TOKEN else '❌'}")
    print("=" * 50)
    
    if not TELEGRAM_TOKEN:
        print("⚠️ ADVERTENCIA: TELEGRAM_BOT_TOKEN no configurado")
    
    if not GITHUB_TOKEN:
        print("⚠️ ADVERTENCIA: GITHUB_TOKEN no configurado")
    
    app.run(host='0.0.0.0', port=PORT, debug=False)