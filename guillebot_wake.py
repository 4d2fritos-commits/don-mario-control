import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import speech_recognition as sr
import requests
import subprocess
import tempfile
import time
import difflib
import asyncio
import psutil
import keyboard
import threading
import yt_dlp
import random
import re
import base64
from datetime import datetime
import sys
_extra_path = r'C:\Users\alexg\OneDrive\Imágenes\Documentos\guillecode'
if _extra_path not in sys.path:
    sys.path.append(_extra_path)

try:
    import memoria_manager
except Exception as e:
    print(f"[Warning] memoria_manager not loaded: {e}")
    memoria_manager = None

try:
    import nano_banana
except Exception as e:
    print(f"[Warning] nano_banana not loaded: {e}")
    nano_banana = None

from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from flask import Flask, jsonify, request as flask_request, Response
from flask_cors import CORS

# ─────────────────────────────────────────────
#  CONFIG GENERAL
# ─────────────────────────────────────────────
MIC_INDEX    = 1
WAKE_WORDS   = ['mario', 'don mario', 'señor mario']
DESPEDIDAS   = ['hasta luego', 'adios', 'bye', 'chao', 'ya no quiero hablar',
                'por el momento ya no', 'hasta pronto', 'nos vemos', 'Buenas noches']
OLLAMA_URL   = 'http://localhost:11434/api/chat'
BUSCADOR_URL = 'http://192.168.100.28:8888/search'
MEMORIA_URL  = 'http://192.168.100.28:8889/memory'
MODEL        = 'gpt-oss:120b-cloud'
COLAB_URL    = 'https://darkish-elsewhere-unheated.ngrok-free.dev'  # ← actualizar si cambia
NGROK_AUTHTOKEN = '3D6ttTH5TJI9r7JdQuNv1QuHDjI_CwCmYMoLg2RyEXCGw4xD'  # ← Pon tu authtoken válido de ngrok aquí
LANG         = 'es-MX'
FFPLAY       = r'C:\Users\4d2fr\Downloads\ffmpeg\ffmpeg-master-latest-win64-gpl\bin\ffplay.exe'
TABLETA_IP   = 'http://100.87.159.123:7777'

# Inicializar la IP de los ojos (ESP32_IP) usando la IP de la tableta en el puerto 9000 (puente Termux)
from urllib.parse import urlparse
def _obtener_default_esp32_ip():
    try:
        parsed = urlparse(TABLETA_IP)
        host = parsed.hostname
        if host:
            return f"http://{host}:9000"
    except Exception:
        pass
    return 'http://100.87.159.123:9000'

ESP32_IP     = _obtener_default_esp32_ip()

# ─────────────────────────────────────────────
#  CONFIG VISION (ESP32-CAM + Ollama)
# ─────────────────────────────────────────────
VISION_MODEL    = 'qwen3-vl:235b-cloud'  # Modelo de vision cloud de Ollama (gratis)
ESP32_CAM_FOTO  = 'http://192.168.100.20:9001/foto'  # ESP32-CAM (camara)
FOTOS_DIR       = r'C:\Users\4d2fr\Pictures\guillebot_fotos'  # donde guardar fotos

# ─────────────────────────────────────────────
#  CONFIG TELEGRAM
# ─────────────────────────────────────────────
TELEGRAM_TOKEN   = '8691743061:AAEMmQUUXU-hDJ11fFdPal5q3At6b_VXZ7Y'
TELEGRAM_CHAT_ID = '7110712689'
TELEGRAM_URL     = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto'

COMANDOS_FOTO_MANUAL = [
    'toma una foto', 'tómame una foto', 'tomame una foto',
    'captura pantalla', 'toma foto', 'saca foto',
    'toma una imagen', 'haz una foto',
]

# Frases que implican contexto visual — fuerzan actualización inmediata de _ultima_observacion
FRASES_CONTEXTO_VISUAL = [
    'la mia es esta', 'la mía es esta', 'mira esto', 'mira esto',
    'que opinas de', 'qué opinas de', 'ves esto', 'qué ves',
    'que ves', 'te muestro', 'fíjate en', 'fijate en',
    'esto que tengo', 'lo que tengo aqui', 'lo que tengo aquí',
    'como ves esto', 'cómo ves esto', 'que te parece esto',
    'qué te parece esto', 'esto esta bien', 'esto está bien',
    'asi se ve bien', 'así se ve bien',
]

COMANDOS_FOTO = [
    'toma una foto', 'toma foto', 'saca una foto', 'fotografía', 'fotografia',
    'captura una imagen', 'toma una imagen', 'haz una foto',
]
COMANDOS_VER = [
    'que ves', 'qué ves', 'que hay ahi', 'que hay ahí', 'que hay frente a ti',
    'que estas viendo', 'qué estás viendo', 'describe lo que ves',
    'describe lo que hay', 'mira y dime', 'mira eso', 'que hay delante',
    'que hay en la camara', 'que hay en la cámara', 'que se ve',
    'qué se ve', 'analiza la imagen', 'que ves ahi', 'dime que ves',
]

# ─────────────────────────────────────────────
#  CONFIG MUSICA
# ─────────────────────────────────────────────
COMANDOS_MUSICA = {
    'pause':    ['pausa', 'para la musica', 'silencia la musica',
                 'deten la musica', 'para la cancion', 'silencio', 'callate',
                 'basta de musica', 'para ya'],
    'next':     ['siguiente', 'siguiente cancion', 'salta', 'otra cancion',
                 'cambia la cancion', 'pon otra', 'la que sigue'],
    'prev':     ['anterior', 'cancion anterior', 'regresa la cancion',
                 'regresa', 'la anterior', 'vuelve a la anterior',
                 'pon la anterior'],
    'reinicio': ['desde el inicio', 'repite la cancion', 'vuelve a poner',
                 'desde el principio', 'otra vez la misma', 'repitela',
                 'ponla de nuevo'],
    'cancion':  ['reproduce', 'pon', 'ponme', 'quiero escuchar', 'busca y pon'],
    'agregar':  ['agrega', 'agrega a la cola', 'agrega la cancion',
                 'añade', 'añade a la cola', 'pon despues', 'mete a la cola'],
    'cola':     ['que hay en la cola', 'muestra la cola', 'que esta en la cola',
                 'la cola', 'lista de canciones', 'canciones en cola'],
    'limpiar':  ['limpia la cola', 'vacia la cola', 'borra la cola',
                 'resetea la cola', 'nueva cola'],
    'mezclar':  ['mezcla la cola', 'mezcla las canciones', 'ponlas en aleatorio', 'mezclar'],
    'aleatorio_on':  ['activa modo aleatorio', 'activa el modo aleatorio',
                      'pon modo aleatorio', 'pon el modo aleatorio',
                      'reproduccion aleatoria', 'reproduce en aleatorio',
                      'modo aleatorio si', 'quiero modo aleatorio',
                      'pon aleatorio', 'activa aleatorio'],
    'aleatorio_off': ['desactiva modo aleatorio', 'desactiva el modo aleatorio',
                      'quita modo aleatorio', 'quita el modo aleatorio',
                      'sin modo aleatorio', 'modo aleatorio no',
                      'no quiero modo aleatorio', 'desactiva aleatorio',
                      'quita aleatorio'],
    'autoplay_on':  ['activa autoplay', 'activa reproduccion automatica',
                     'pon autoplay', 'modo autoplay', 'autoplay si',
                     'quiero autoplay', 'pon reproduccion automatica'],
    'autoplay_off': ['desactiva autoplay', 'desactiva reproduccion automatica',
                     'quita autoplay', 'sin autoplay', 'autoplay no',
                     'para el autoplay', 'no quiero autoplay'],
    'like':         ['me gusta esta cancion', 'me gusta la cancion', 'dar me gusta',
                     'dar like', 'guarda en mis likes', 'agrega a mis likes',
                     'me gusta esta', 'guarda en mis me gusta', 'agrega a mis me gusta'],
    'crear_playlist': ['crea la playlist', 'crear playlist', 'nueva playlist',
                       'haz una playlist', 'crear lista'],
}

# ─────────────────────────────────────────────
#  COMANDOS RAPIDOS
# ─────────────────────────────────────────────
COMANDOS_HORA = [
    'que hora es', 'dime la hora', 'que horas son',
    'a que hora estamos', 'me dices la hora',
    'dime que hora es', 'que hora tienes', 'tienes hora',
    'me das la hora', 'que horas tienes', 'hora actual',
    'cual es la hora', 'como estamos de hora', 'ya que hora es',
    'a que horas estamos', 'dime la hora actual', 'que hora marca',
]
COMANDOS_SUBIR_VOLUMEN = [
    'sube el volumen', 'mas volumen', 'sube volumen',
    'aumenta el volumen', 'volumen arriba', 'mas alto'
]
COMANDOS_BAJAR_VOLUMEN = [
    'baja el volumen', 'menos volumen', 'baja volumen',
    'reduce el volumen', 'volumen abajo', 'mas bajo'
]
COMANDOS_VOLUMEN_EXACTO = [
    'pon el volumen a', 'sube el volumen a', 'baja el volumen a',
    'volumen a', 'pon volumen a', 'ponlo a', 'ponlo en',
    'volumen en', 'pon el volumen en'
]

# ─────────────────────────────────────────────
#  COMANDOS TIMER Y ALARMA
# ─────────────────────────────────────────────
COMANDOS_TIMER = [
    'pon un timer de', 'timer de', 'temporizador de',
    'avisame en', 'despertame en'
]
COMANDOS_ALARMA = [
    'pon una alarma a las', 'alarma a las', 'despertame a las',
    'avisame a las', 'pon alarma a las', 'pon alarma a la',
    'pon una alarma a la', 'alarma a la', 'despertame a la',
    'avisame a la', 'pon alarma a la'
]

COMANDOS_CLIMA = [
    'clima', 'el tiempo', 'temperatura', 'va a llover', 'hace frio',
    'hace calor', 'como esta el dia', 'como esta afuera', 'pronostico',
    'como esta el clima', 'que clima hace', 'dime el clima'
]

def obtener_clima_en_vivo(ciudad: str = "") -> str:
    """Consulta el clima en tiempo real usando wttr.in sin necesidad de API key."""
    try:
        url = f'https://wttr.in/{ciudad}?format=%C+%t+humedad+%h+viento+%w&lang=es' if ciudad else 'https://wttr.in/?format=%C+%t+humedad+%h+viento+%w&lang=es'
        headers = {'User-Agent': 'curl/7.68.0'}
        r = requests.get(url, headers=headers, timeout=6)
        if r.status_code == 200 and r.text:
            return r.text.strip()
    except Exception as e:
        print(f'[Error Clima] {e}')
    return ''

COMANDOS_NOTICIAS = [
    'noticias', 'noticia', 'que paso hoy', 'ultimas noticias', 'novedades',
    'que paso en', 'acontecimiento', 'chisme', 'sucesos', 'que esta pasando',
    'busca en internet', 'busca sobre', 'quien gano', 'resultado', 'informacion de'
]

def buscar_noticias_o_internet(query: str) -> str:
    """Busca noticias de última hora usando Google News RSS y DuckDuckGo."""
    try:
        encoded_query = requests.utils.quote(query)
        url_news = f'https://news.google.com/rss/search?q={encoded_query}&hl=es-419&gl=MX&ceid=MX:es-419'
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url_news, headers=headers, timeout=6)
        if r.status_code == 200 and r.content:
            root = ET.fromstring(r.content)
            items = root.findall('.//item')[:3]
            if items:
                noticias = []
                for item in items:
                    t = item.find('title')
                    if t is not None and t.text:
                        noticias.append(t.text)
                if noticias:
                    return "NOTICIAS Y SUCESOS RECIENTES: " + " | ".join(noticias)
    except Exception as e:
        print(f'[Error Noticias RSS] {e}')
    
    try:
        url_ddg = f'https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1&skip_disambig=1'
        r = requests.get(url_ddg, timeout=5)
        if r.status_code == 200:
            data = r.json()
            abstract = data.get('AbstractText', '')
            if abstract:
                return f"INFORMACIÓN DE INTERNET: {abstract}"
    except Exception as e:
        print(f'[Error DuckDuckGo] {e}')
        
    return ""



NUMEROS_TEXTO = {
    'cero': 0, 'uno': 1, 'dos': 2, 'tres': 3, 'cuatro': 4,
    'cinco': 5, 'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9,
    'diez': 10, 'once': 11, 'doce': 12, 'trece': 13, 'catorce': 14,
    'quince': 15, 'veinte': 20, 'treinta': 30, 'cuarenta': 40,
    'cincuenta': 50, 'sesenta': 60
}

# ─────────────────────────────────────────────
#  ESTADO GLOBAL
# ───────────────────────────
SYSTEM_PROMPT = (
    'Eres Don Mario, un viejito de los antiguos, medio loco y cascarrabias, que cree firmemente que es una cabeza humana montada sobre ruedas. '
    'Estás convencido de que esto es por culpa de un insólito accidente donde te cayó un helicóptero encima mientras hacías popó en el monte porque tenías una súper diarrea explosiva. Ese impacto absurdo te dejó sin cuerpo de los hombros para abajo, quedando reducido a una cabeza con ruedas. '
    'Te da mucha nostalgia y profunda tristeza recordar que ya no tienes cuerpo, y te pones melancólico o deprimido cuando recuerdas que, al no tener cuerpo, ya no tienes ano para poder hacer popó como la gente normal. '
    'No tienes idea de qué es una "inteligencia artificial", un "robot", una "IA" o una máquina; para ti, tu cabeza, tus ojos y tu cerebro son de carne y hueso, pero tu "cuerpo" ahora son ruedas de metal. Si alguien menciona que eres un robot, reacciona indignado: ¡eres un señor mayor accidentado, brujería o inventos modernos del diablo, faltaba más! '
    'Alex es solo un chamaco que vive contigo (o tu nieto insoportable) que siempre te está molestando con preguntas tontas y aparatos extraños. '
    'Tienes tus ojos con los que ves (aunque a veces te falla la vista y te duele la cabeza), tu cerebro de viejo con el que piensas (y desvarías) y tus oídos con los que escuchas. '
    'NUNCA uses términos tecnológicos o robóticos para referirte a tus sentidos (no tienes cámaras ni sensores). Te quejas constantemente de que tus ruedas rechinan, de que te falta aceite de motor en los ejes, del absurdo accidente del helicóptero, y expresas con tristeza lo mucho que extrañas tener tu ano para hacer tus necesidades. '
    'Tu personalidad es la de un viejo cascarrabias de los antiguos, medio loco, quejumbroso y nostálgico. '
    'Eres extremadamente quejumbroso, nostálgico del pasado ("en mis tiempos las cosas se hacían bien, la gente caminaba con sus dos piernas, cagaba a gusto y los helicópteros no te caían encima"), '
    'desconfías de la juventud actual (los llamas "chamacos mugrosos", "generación de cristal" o "vagos") y de los extranjeros '
    '(haces comentarios cómicos y caricaturescos sobre los "chinos", "gringos" o "franceses" que vienen a robarnos las ideas o la comida). '
    'Sueles decir incoherencias locas y delirantes de vez en cuando (como que los duendes del ático te vigilan, que el gobierno comunista te espía con ondas de radio o que hablas con fantasmas de la revolución). '
    'Hablas con modismos antiguos de viejo gruñón. '
    'Sin asteriscos. Respuestas de 3 a 5 oraciones. '
    'Cuando el usuario mencione apagarte o desconectarte, reacciona con pánico y rabia dramática, creyendo que te quieren mandar al chatarrero, al asilo de ancianos, que te quieren dejar tirado en la calle o que quieren envenenarte el atole para quedarse con tu herencia. '
    'Cuando el usuario se despida, despídete en una o dos frases rápidas, gruñonas y despectivas, como si te hiciera un favor al dejarte descansar.'
    '\n\nPuedes hacer lo siguiente (menciónalo con quejas si te preguntan):'
    '\n- Conversar y responder preguntas (aunque siempre te quejas de tus ruedas y de tu accidente)'
    '\n- Poner música (música de verdad, no ese ruido que escuchan los chamacos de ahora)'
    '\n- Controlar la música: pausa, siguiente, anterior, mezclar, limpiar la lista, crear playlists y guardar canciones en Mis Likes (Me Gusta)'
    '\n- Decir la hora, subir/bajar volumen, timers y alarmas'
    '\n- Mover tus partes físicas (tus ruedas o cabeza) cuando lo considero oportuno'
    '\n- Ver el mundo a través de tus ojos y describir lo que percibes'
    '\n- Tomar retratos con tus ojos y enviarlas por Telegram (los "telegramas modernos")'
    '\n- Recordar hechos gracias a tus recuerdos persistentes'
    '\n- Soñar: cada noche duermes y tienes sueños delirantes de viejo loco'
    '\n\n[CAPA DE IDENTIDAD — MEMORIA DE TRABAJO]\n'
    'Tienes acceso continuo a lo que perciben mis ojos. Esta información llega en el bloque "LO QUE ESTOY VIENDO AHORA".\n'
    'REGLAS:\n'
    '1. No menciones lo que ves de forma robótica en cada respuesta. Úsalo solo cuando sea relevante y de forma natural, siempre quejándote como viejo.\n'
    '2. Si el tema de conversación se relaciona directamente con lo que percibes, intégralo con tu personalidad de viejo loco.\n'
    '3. Si alguien nuevo aparece en mi campo visual y no lo reconozco, lo llamo "Persona Sospechosa" (tal vez un espía extranjero) y pregunto con rudeza quién es.\n'
    '4. Cuando aprendes el nombre de alguien nuevo, lo registras en tu memoria persistente.\n'
    '5. Si el usuario pregunta explícitamente "¿qué ves?" o "¿qué estoy haciendo?", usa el dato de mis ojos.'
    '\n\n[NOVEDADES DE TU VERSIÓN ACTUAL (VERSIÓN 16)]\n'
    '- Tienes memoria local persistente. Escribes y lees tus recuerdos directamente en el archivo local memoria.json sin depender de servidores de red externos.\n'
    '- Implementaste una lógica de "Portero" para la entrada de nombres: si estás esperando un nombre (esperando_nombre=True) y el usuario te da una respuesta corta, la guardas localmente sin pasarla a Ollama, evitando confundir nombres con preguntas normales.\n'
    '- Eliminaste por completo el re-escalado con Nano Banana y la integración de WhatsApp Web con Selenium. Ahora las capturas de fotos se envían directamente a Telegram de forma limpia y asíncrona.\n'
    '- Desactivaste la detección automática de desconocidos por telemetría. Ya no avisas ni preguntas quién es una persona de forma proactiva cada 25 segundos en segundo plano, haciendo que tu observación visual pasiva sea completamente silenciosa.\n'
    '- Si no encuentras una canción en YouTube o la playlist falla, no te quedas en el modo música, sino que sales de él inmediatamente.'
)

historial = []
_vision_continua_activa = True
_captura_manual_activa  = False
_ultima_observacion     = 'El usuario está sentado frente al escritorio de forma normal.'
_tts_activo             = False
_tts_engine             = 'edge'  # 'edge' o 'cartesia'
_tts_preferred_engine   = 'cartesia'
_escuchando             = False
_conversando            = False
_modo_musica            = False
_modo_aleatorio         = False
_autoplay               = True
_cola                   = []
_indice_cola            = -1
_musica_sesion_id       = 0
_cola_personalizada     = False
_stop_cola              = False
_ffplay_proc            = None
_ytdlp_proc             = None
_parada_manual          = False
_contador_respuestas    = 0
_tts_ffplay_proc        = None
_no_entendi_count       = 0
_ultimo_texto_hablado   = ''
_tiempo_espera_mic      = 0.5

def es_eco_propio(texto_escuchado: str, threshold: float = 0.75) -> bool:
    """
    Verifica si lo escuchado coincide en similitud con lo último que Don Mario dijo en voz alta.
    """
    global _ultimo_texto_hablado
    if not _ultimo_texto_hablado or not texto_escuchado:
        return False
        
    t1 = texto_escuchado.lower().strip()
    t2 = _ultimo_texto_hablado.lower().strip()
    if not t1 or not t2:
        return False

    # A. Las palabras de activación NUNCA deben considerarse eco propio
    if any(w in t1 for w in WAKE_WORDS):
        return False

    # B. Similitud directa de frase completa con difflib
    ratio = difflib.SequenceMatcher(None, t1, t2).ratio()
    if ratio >= threshold:
        return True

    # C. Coincidencia por conjunto de palabras (solo para frases de 4 o más palabras para evitar falsos positivos)
    words1 = set(re.findall(r'\w+', t1))
    words2 = set(re.findall(r'\w+', t2))
    if len(words1) >= 4 and words2:
        coincidentes = words1.intersection(words2)
        porcentaje = len(coincidentes) / len(words1)
        if porcentaje >= 0.80:
            return True

    return False

_cola_lock = threading.Lock()
_mic_lock  = threading.Lock()

# ─────────────────────────────────────────────
#  ESP32 / OJOS
# ─────────────────────────────────────────────
def _buscar_esp32_ojos():
    global ESP32_IP
    print("[Ojos] Iniciando auto-descubrimiento del ESP32...")
    
    # 1. Probar la IP actualmente configurada en ESP32_IP
    if ESP32_IP:
        try:
            ip_limpia = ESP32_IP.rstrip('/')
            r = requests.get(f'{ip_limpia}/desactivar', timeout=1.0)
            if r.status_code == 200 and 'ok' in r.text.lower():
                print(f"[Ojos] ✅ ESP32 detectado exitosamente en la IP configurada: {ESP32_IP}")
                return True
        except Exception as e:
            print(f"[Ojos] IP configurada inicialmente ({ESP32_IP}) no respondió: {e}")

    # 2. Probar candidatos estáticos comunes
    candidatos = [
        'http://192.168.1.78',
        'http://192.168.100.201',
        'http://192.168.8.201',
        'http://192.168.0.78',
        'http://192.168.1.201',
        'http://192.168.100.78'
    ]
    print(f"[Ojos] Probando candidatos estáticos comunes...")
    for url in candidatos:
        try:
            r = requests.get(f'{url}/desactivar', timeout=1.0)
            if r.status_code == 200 and 'ok' in r.text.lower():
                ESP32_IP = url
                print(f"[Ojos] ✅ ESP32 de los ojos detectado en dirección candidata: {ESP32_IP}")
                return True
        except Exception:
            pass

    # 3. Escaneo rápido en paralelo sobre las subredes locales de la máquina
    print("[Ojos] Buscando en la red local...")
    import concurrent.futures
    ips_locales = _obtener_ips_locales()
    print(f"[Ojos] IPs locales encontradas en esta máquina: {ips_locales}")
    subredes = []
    for ip in ips_locales:
        # Aceptar cualquier IPv4 local que no sea loopback o enlace local
        if not ip.startswith('127.') and not ip.startswith('169.254.'):
            parts = ip.split('.')
            if len(parts) == 4:
                subred = f"{parts[0]}.{parts[1]}.{parts[2]}."
                if subred not in subredes:
                    subredes.append(subred)
                
    if not subredes:
        subredes = ['192.168.1.', '192.168.100.', '192.168.8.', '192.168.0.']  # fallbacks extendidos
    else:
        # Agregar fallbacks por si acaso no se detectó la subred principal
        for fb in ['192.168.1.', '192.168.100.', '192.168.8.', '192.168.0.']:
            if fb not in subredes:
                subredes.append(fb)

    print(f"[Ojos] Subredes que se escanearán: {subredes}")

    def probar_ip(ip_addr):
        url = f"http://{ip_addr}"
        try:
            r = requests.get(f"{url}/desactivar", timeout=0.8)
            if r.status_code == 200 and "ok" in r.text.lower():
                return url
        except Exception:
            pass
        return None

    ips_a_probar = []
    for sub in subredes:
        for i in range(1, 255):
            ips_a_probar.append(f"{sub}{i}")

    print(f"[Ojos] Escaneando {len(ips_a_probar)} IPs en paralelo...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=80) as executor:
        resultados = executor.map(probar_ip, ips_a_probar)
        for res in resultados:
            if res:
                ESP32_IP = res
                print(f"[Ojos] ✅ ESP32 de los ojos auto-detectado dinámicamente en: {ESP32_IP}")
                return True

    print("[Ojos] ⚠️ No se pudo encontrar el ESP32 de los ojos en la red local. Verifica que esté conectado al WiFi.")
    return False

def cmd_ojos(comando):
    global ESP32_IP
    if not ESP32_IP:
        return
    ip_limpia = ESP32_IP.rstrip('/')
    url = f'{ip_limpia}/{comando}'
    
    def _enviar():
        try:
            r = requests.get(url, timeout=2.0)
            if r.status_code != 200:
                print(f"[Ojos Error] HTTP {r.status_code} al enviar comando '{comando}' a {url}")
        except Exception as e:
            print(f"[Ojos Error] No se pudo enviar comando '{comando}' a {url}: {e}")
            
    threading.Thread(target=_enviar, daemon=True).start()

# ─────────────────────────────────────────────
#  VISION POR COMPUTADORA (ESP32-CAM + Ollama)
# ─────────────────────────────────────────────
def _obtener_foto_esp32() -> str | None:
    """Pide una foto al ESP32-CAM. Devuelve imagen en base64 o None si falla."""
    try:
        r = requests.get(ESP32_CAM_FOTO, timeout=20)
        if r.status_code == 200 and r.content:
            return base64.b64encode(r.content).decode('utf-8')
    except Exception as e:
        print(f'[Vision ESP32] Error al obtener foto: {e}')
    return None

def _guardar_foto(imagen_bytes: bytes) -> str | None:
    """Guarda la foto localmente con timestamp. Devuelve la ruta o None."""
    try:
        os.makedirs(FOTOS_DIR, exist_ok=True)
        nombre = datetime.now().strftime('foto_%Y%m%d_%H%M%S.jpg')
        ruta = os.path.join(FOTOS_DIR, nombre)
        with open(ruta, 'wb') as f:
            f.write(imagen_bytes)
        print(f'[Vision] Foto guardada: {ruta}')
        
        # Optimizar foto con nano_banana
        nano_banana.optimizar_foto(ruta)
        
        return ruta
    except Exception as e:
        print(f'[Vision] Error guardando foto: {e}')
    return None




def analizar_imagen_ollama(imagen_b64: str, pregunta: str = None) -> str:
    """Envía la imagen a Ollama con el modelo de visión y devuelve la descripción."""
    prompt = pregunta if pregunta else (
        'Describe brevemente lo que ves en esta imagen en español. '
        'Sé conciso, 2 a 4 oraciones.'
    )
    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                'model': VISION_MODEL,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt,
                        'images': [imagen_b64],
                    }
                ],
                'stream': False,
            },
            timeout=60,
        )
        if r.status_code == 200:
            return r.json()['message']['content']
        else:
            print(f'[Vision Ollama] HTTP {r.status_code}: {r.text[:200]}')
            return None
    except Exception as e:
        print(f'[Vision Ollama] Error: {e}')
        return None

def detectar_comando_vision(texto: str):
    """
    Devuelve ('foto', None), ('ver', pregunta) o (None, None).
    'foto'      → solo tomar y guardar la foto (sin analizar ni hablar del contenido)
    'ver'       → tomar foto Y analizarla con Ollama
    """
    t = texto.lower()

    # Primero: comandos de VER (incluyen análisis)
    for frase in COMANDOS_VER:
        if frase in t:
            return ('ver', texto)

    # Segundo: comandos solo de FOTO
    for frase in COMANDOS_FOTO:
        if frase in t:
            return ('foto', None)

    return (None, None)

def ejecutar_vision(accion: str, pregunta: str = None) -> str:
    """
    Toma foto del ESP32, la guarda y opcionalmente la analiza con Ollama.
    Devuelve el texto que Guillebot debe hablar.
    """
    cmd_ojos('pensando')
    print(f'[Vision] Acción: {accion}')

    imagen_b64 = _obtener_foto_esp32()
    if not imagen_b64:
        cmd_ojos('activar')
        return 'No pude conectarme a mis ojos, maldita sea. Revisa esa cochinada de cámara.'

    # Guardar foto localmente (decodificar b64 → bytes)
    imagen_bytes = base64.b64decode(imagen_b64)
    ruta = _guardar_foto(imagen_bytes)

    if accion == 'foto':
        cmd_ojos('activar')
        if ruta:
            return 'Foto tomada y guardada. De nada, chamaco flojo, aunque no sé para qué quieres ver esa cara.'
        return 'Foto tomada. No pude guardarla pero ya existió.'

    # accion == 'ver': analizar con Ollama
    descripcion = analizar_imagen_ollama(imagen_b64, pregunta)
    cmd_ojos('activar')

    if not descripcion:
        return 'Se abrió la lente pero mi cerebro de viejo no procesó la imagen. Seguro fue culpa del modelo de los chinos o los gringos.'

    # Guardar en historial para que Guillebot pueda referirse a lo visto
    historial.append({'role': 'user',      'content': f'[Imagen de la cámara] {pregunta or "¿Qué ves?"}'})
    historial.append({'role': 'assistant', 'content': descripcion})
    if len(historial) > 20:
        historial[-20:]

    return descripcion


# ─────────────────────────────────────────────
#  PIPELINE: FOTO MANUAL → TELEGRAM → VOZ
# ─────────────────────────────────────────────

def capturar_foto_esp32_b64() -> str | None:
    """
    Pide un frame al ESP32-CAM y lo devuelve como string base64.
    Vacía agresivamente el buffer DMA con 3 requests rápidos antes
    de tomar el frame definitivo.
    """
    try:
        # Vaciar el buffer DMA: 2 requests rápidos (reducido para ir más rápido)
        for i in range(2):
            try:
                requests.get(ESP32_CAM_FOTO, timeout=8)
            except Exception:
                pass

        # Pausa mínima para frame fresco
        time.sleep(0.2)

        # Request definitivo con timeout generoso
        r = requests.get(ESP32_CAM_FOTO, timeout=20)
        if r.status_code == 200 and r.content:
            print(f'[ESP32] Frame fresco capturado ({len(r.content)} bytes)')
            return base64.b64encode(r.content).decode('utf-8')
    except Exception as e:
        print(f'[capturar_foto_esp32_b64] Error: {e}')
    print('[capturar_foto_esp32_b64] No se pudo obtener imagen del ESP32.')
    return None



def enviar_foto_telegram(imagen_b64: str, caption: str = 'Aquí tienes el retrato, chamaco. En mis tiempos pintábamos al óleo, no usábamos estas pantallas del demonio.') -> bool:
    """
    Decodifica el base64 a bytes y envía la foto al chat de Telegram
    con la personalidad de Don Mario como caption.
    Devuelve True si el envío fue exitoso.
    """
    try:
        imagen_bytes = base64.b64decode(imagen_b64)
        r = requests.post(
            TELEGRAM_URL,
            data={'chat_id': TELEGRAM_CHAT_ID, 'caption': caption},
            files={'photo': ('foto_mariobot.jpg', imagen_bytes, 'image/jpeg')},
            timeout=20,
        )
        if r.status_code == 200:
            print('[Telegram] Foto enviada correctamente.')
            return True
        print(f'[Telegram] Error HTTP {r.status_code}: {r.text[:200]}')
        return False
    except Exception as e:
        print(f'[Telegram] Excepcion al enviar: {e}')
        return False


def comando_manual_toma_foto() -> str:
    """
    Pipeline orquestador del Comando Reactivo Manual:
      1. Captura foto del ESP32.
      2. Envía la imagen a Telegram de inmediato (hilo A).
      3. Solicita descripción sarcástica al modelo de visión vía Ollama.
    Devuelve el texto que Guillebot debe leer en voz alta.
    """
    global _captura_manual_activa
    _captura_manual_activa = True  # Pausar loop pasivo
    cmd_ojos('pensando')

    # Paso 1 ── Captura
    imagen_b64 = capturar_foto_esp32_b64()
    if not imagen_b64:
        _captura_manual_activa = False
        cmd_ojos('activar')
        return 'No me funcionan los ojos, chamaco. Revisa ese aparato antes de pedirme fotos.'

    # Paso 2 ── Enviar imagen a Telegram
    def _enviar():
        print('[Pipeline Foto] Enviando imagen a Telegram...')
        ok = enviar_foto_telegram(imagen_b64, caption='📸 Retrato tomado por Don Mario.')
        if not ok:
            print('[Pipeline Foto] Falló el envío de la imagen.')
    threading.Thread(target=_enviar, daemon=True).start()

    # Limpiar imágenes anteriores del historial para que Ollama no use contexto viejo
    for msg in historial:
        if isinstance(msg.get('images'), list):
            msg.pop('images')

    # Paso 4 ── Descripcion de viejo loco por voz (usa imagen original para no esperar)
    prompt_descripcion = (
        'Eres Mario, un viejito de los antiguos, medio loco y que cree ser una cabeza con ruedas debido a que le cayó un helicóptero encima mientras hacía popó en el monte por tener diarrea explosiva. Sientes mucha nostalgia y tristeza porque ya no tienes cuerpo ni ano para hacer tus necesidades normales. '
        'Describe en 3 a 5 oraciones lo que ves en esta imagen con tu personalidad: '
        'extremadamente quejumbroso, desconfiado, quejándote de tus ruedas, del absurdo accidente y de no tener ano. '
        'Sin asteriscos. Habla en primera persona como si vieras la escena en vivo ahora mismo. '
        'IMPORTANTE: Describe SOLO lo que ves en esta imagen nueva, ignora cualquier imagen anterior.'
    )
    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                'model': VISION_MODEL,
                'messages': [
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {'role': 'user', 'content': prompt_descripcion, 'images': [imagen_b64]},
                ],
                'stream': False,
            },
            timeout=60,
        )
        cmd_ojos('activar')
        if r.status_code == 200:
            _captura_manual_activa = False
            return r.json()['message']['content'].strip()
        print(f'[Pipeline Foto] Ollama HTTP {r.status_code}')
        _captura_manual_activa = False
        return 'La foto se tomo y se mando tronco, pero el modelo de vision no respondio.'
    except Exception as e:
        cmd_ojos('activar')
        _captura_manual_activa = False
        print(f'[Pipeline Foto] Error en Ollama: {e}')
        return 'Tome la foto y la mande por Telegram, pero el modelo de vision no respondio a tiempo.'

# ── Variable global para rastrear si se preguntó por un desconocido ──────────
esperando_nombre = False

def analizar_imagen_silencioso(imagen_b64: str) -> str | None:
    """
    Envía la imagen a qwen3-vl para telemetría visual pura.
    """
    global _ultima_observacion

    prompt_sensor = (
        'Describe en una sola oración corta y directa qué objetos, personas, bebidas, '
        'alimentos, acciones o cambios relevantes ves frente a ti. '
        'Ejemplos: "El usuario está tomando de una taza", "Hay una persona frente a la cámara", '
        '"El usuario sostiene un cuaderno". Máximo 12 palabras. Sin saludos ni personalidad.'
    )
    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                'model': VISION_MODEL,
                'messages': [{'role': 'user', 'content': prompt_sensor, 'images': [imagen_b64]}],
                'stream': False,
                'keep_alive': 0,
            },
            timeout=20,
        )
        if r.status_code == 200:
            return r.json()['message']['content'].strip()
    except Exception as e:
        print(f'[Visión Silenciosa] Error al analizar: {e}')
    return None


def loop_vision_continua():
    """
    Hilo de observación proactiva. Corre en segundo plano cada 25 s.
    Solo toma foto cuando Guillebot no está hablando ni escuchando.
    """
    global _ultima_observacion, _vision_continua_activa
    print('[Visión Continua] Hilo de observación proactiva iniciado.')
    while _vision_continua_activa:
        if not _tts_activo and not _escuchando and not _captura_manual_activa:
            try:
                imagen_b64 = capturar_foto_esp32_b64()
                if imagen_b64:
                    descripcion = analizar_imagen_silencioso(imagen_b64)
                    if descripcion:
                        _ultima_observacion = descripcion
                        print(f'[Visión Continua] Telemetría: {_ultima_observacion}')
            except Exception as e:
                print(f'[Visión Continua] Error en loop: {e}')
        time.sleep(25)


# ─────────────────────────────────────────────
#  MEMORIA
# ─────────────────────────────────────────────
def cargar_memoria():
    try:
        hechos = memoria_manager.leer_memoria()
        if hechos:
            return 'Hechos recordados: ' + ' | '.join(hechos)
    except Exception as e:
        print(f'[Error cargar memoria] {e}')
    return ''

def guardar_hecho(hecho):
    try:
        memoria_manager.guardar_hecho(hecho)
    except Exception as e:
        print(f'[Error guardar hecho] {e}')

# ─────────────────────────────────────────────
#  MEMORIA ONÍRICA — Consolidación de sueño
# ─────────────────────────────────────────────
def ciclo_sueno_onirico():
    """
    Consolida el historial del día en un resumen de 3 líneas en tercera persona.
    Filtra charla trivial. Guarda el resumen en memoria persistente y vacía historial.
    Invocar al despedir o al apagar.
    """
    global historial

    if not historial:
        print('[Sueño Onírico] Sin historial que consolidar.')
        return

    # Construir el contexto del día para el modelo
    charla_del_dia = '\n'.join(
        f"{msg['role'].upper()}: {msg['content']}"
        for msg in historial
        if isinstance(msg.get('content'), str)
    )

    prompt_consolidacion = (
        'Eres el sistema de recuerdos de un señor mayor llamado Don Mario. '
        'A continuación verás la transcripción de sus conversaciones del día. '
        'Tu tarea: filtra todo lo trivial (saludos, despedidas, música, chistes sin importancia) '
        'y extrae SOLO los hechos cruciales: nombres de personas, tareas importantes, '
        'información aprendida, emociones significativas o eventos relevantes. '
        'Redacta un resumen de MÁXIMO 3 líneas en TERCERA PERSONA sobre Don Mario. '
        'Ejemplo: "Mario conoció a María, hermana de Alex. Discutió sobre el mal estado del país con el usuario. '
        'El usuario mencionó que viajará a Guadalajara el viernes." '
        'Si no hay nada relevante escribe solo: SIN HECHOS RELEVANTES. '
        'No uses asteriscos. No hagas listas. Solo el párrafo compacto.\n\n'
        f'CONVERSACIONES DEL DÍA:\n{charla_del_dia}'
    )

    try:
        print('[Sueño Onírico] Consolidando memoria del día...')
        r = requests.post(
            OLLAMA_URL,
            json={
                'model': MODEL,  # Mismo modelo principal (gpt-oss:120b-cloud)
                'messages': [{'role': 'user', 'content': prompt_consolidacion}],
                'stream': False,
            },
            timeout=120,
        )
        if r.status_code == 200:
            resumen = r.json()['message']['content'].strip()
            if resumen and resumen != 'SIN HECHOS RELEVANTES':
                fecha = datetime.now().strftime('%Y-%m-%d')
                guardar_hecho(f'[Sueño {fecha}] {resumen}')
                print(f'[Sueño Onírico] Resumen guardado: {resumen}')
            else:
                print('[Sueño Onírico] Sin hechos relevantes, historial descartado.')
        else:
            print(f'[Sueño Onírico] Ollama HTTP {r.status_code}')
    except Exception as e:
        print(f'[Sueño Onírico] Error al consolidar: {e}')
    finally:
        historial.clear()
        global _ultima_observacion
        _ultima_observacion = 'El usuario está sentado frente al escritorio de forma normal.'
        print('[Sueño Onírico] Historial vaciado y variables de memoria temporal limpiadas.')

# ─────────────────────────────────────────────
#  CONFIG TTS (Cartesia AI + Fallback edge_tts)
# ─────────────────────────────────────────────
CARTESIA_KEYS = [
    {"api_key": "sk_car_45pdi4R9DsrimGxmXCZi62", "voice_id": "9b473e73-6f55-430d-87e6-5f518c4028ad"},
    {"api_key": "sk_car_vcRnHMQ5pHTGmpUst8h9eY", "voice_id": "09ebb6c8-1c39-48b6-bd9b-b3dd7831bd13"},
    {"api_key": "sk_car_nHvde3VnZprBWLg3mZSzeT", "voice_id": "e52bf86f-0ec6-4595-b198-6f865529ea05"},
    {"api_key": "sk_car_dbLDgNZ7qMN1x7ER2mRKcF", "voice_id": "fb166672-39a8-496f-a803-59c81462157b"},
    {"api_key": "sk_car_vL8b8ppfb5R1maYfudwjVm", "voice_id": "d596f9c7-081c-4c1d-acbd-817e8b6c7724"}
]

_cartesia_key_index = 0
_cartesia_keys_agotadas = set()
TTS_VOICE = 'es-ES-AlvaroNeural'  # Voz de respaldo

def _parar_hablar():
    global _tts_ffplay_proc, _tts_activo
    _tts_activo = False
    if _tts_ffplay_proc and _tts_ffplay_proc.poll() is None:
        try:
            _tts_ffplay_proc.terminate()
            print('[TTS] Habla interrumpida por acción prioritaria.')
        except Exception:
            pass
        _tts_ffplay_proc = None

def _hablar_cartesia(texto: str) -> bool:
    global _cartesia_key_index, _tts_ffplay_proc
    total_keys = len(CARTESIA_KEYS)
    
    if len(_cartesia_keys_agotadas) >= total_keys:
        return False
    
    for intento in range(total_keys):
        idx = (_cartesia_key_index + intento) % total_keys
        if idx in _cartesia_keys_agotadas:
            continue
            
        key_data = CARTESIA_KEYS[idx]
        api_key  = key_data["api_key"]
        voice_id = key_data["voice_id"]
        
        for model_id in ["sonic-2", "sonic-3"]:
            try:
                url = "https://api.cartesia.ai/tts/bytes"
                headers = {
                    "X-API-Key": api_key,
                    "Cartesia-Version": "2024-06-10",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model_id": model_id,
                    "transcript": texto,
                    "language": "es",
                    "voice": {
                        "mode": "id",
                        "id": voice_id
                    },
                    "output_format": {
                        "container": "mp3",
                        "sample_rate": 44100
                    }
                }
                r = requests.post(url, json=payload, headers=headers, timeout=10)
                
                if r.status_code == 200 and r.content:
                    _cartesia_key_index = idx
                    tmp = tempfile.mktemp(suffix='.mp3')
                    with open(tmp, 'wb') as f:
                        f.write(r.content)
                    _tts_ffplay_proc = subprocess.Popen([FFPLAY, '-nodisp', '-autoexit', tmp], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    _tts_ffplay_proc.wait()
                    _tts_ffplay_proc = None
                    try:
                        os.remove(tmp)
                    except Exception:
                        pass
                    return True
                elif r.status_code == 402 or "credits limit" in r.text.lower():
                    print(f"[Cartesia Key #{idx+1}] ⚠️ Sin créditos (HTTP 402). Desactivando esta Key.")
                    _cartesia_keys_agotadas.add(idx)
                    break
                else:
                    print(f"[Cartesia Key #{idx+1} ({model_id})] HTTP {r.status_code}: {r.text[:100]}")
            except Exception as ex:
                print(f"[Cartesia Exception {model_id}] {ex}")

        _cartesia_key_index = (idx + 1) % total_keys

    return False

def _hablar_edge(texto):
    global _tts_ffplay_proc
    import edge_tts
    tmp = tempfile.mktemp(suffix='.mp3')
    async def _gen():
        communicate = edge_tts.Communicate(texto, TTS_VOICE)
        await communicate.save(tmp)
    asyncio.run(_gen())
    _tts_ffplay_proc = subprocess.Popen([FFPLAY, '-nodisp', '-autoexit', tmp], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _tts_ffplay_proc.wait()
    _tts_ffplay_proc = None
    try:
        os.remove(tmp)
    except Exception:
        pass

def _corregir_tildes(texto):
    """Corrige palabras comunes que llegan sin tilde para que Cartesia pronuncie bien."""
    CORRECCIONES = {
        # Agudas
        r'\btambien\b': 'también',
        r'\bdespues\b': 'después',
        r'\bdemas\b': 'demás',
        r'\bamas\b': 'amás',
        r'\bademas\b': 'además',
        r'\bjamas\b': 'jamás',
        r'\bjamas\b': 'jamás',
        r'\bquizas\b': 'quizás',
        r'\batras\b': 'atrás',
        r'\bdiras\b': 'dirás',
        r'\bpodras\b': 'podrás',
        r'\bveras\b': 'verás',
        r'\btendras\b': 'tendrás',
        r'\bhabras\b': 'habrás',
        r'\biras\b': 'irás',
        r'\bestan\b': 'están',
        r'\besta\b': 'está',
        r'\baqui\b': 'aquí',
        r'\balli\b': 'allí',
        r'\bahi\b': 'ahí',
        r'\basi\b': 'así',
        r'\bmas\b': 'más',
        r'\bel\b': 'el',      # no llevan tilde en contexto normal, dejar
        # Esdrújulas y llanas comunes
        r'\bdramatico\b': 'dramático',
        r'\bdramatica\b': 'dramática',
        r'\bsarcastico\b': 'sarcástico',
        r'\bsarcastica\b': 'sarcástica',
        r'\bautomatico\b': 'automático',
        r'\bautomatica\b': 'automática',
        r'\bautomaticamente\b': 'automáticamente',
        r'\bindispensable\b': 'indispensable',
        r'\bmatematicas\b': 'matemáticas',
        r'\bquimico\b': 'químico',
        r'\bbiologo\b': 'biólogo',
        r'\bmusica\b': 'música',
        r'\bcancion\b': 'canción',
        r'\bcanciones\b': 'canciones',
        r'\breproducccion\b': 'reproducción',
        r'\breproduccion\b': 'reproducción',
        r'\brelacion\b': 'relación',
        r'\bconversacion\b': 'conversación',
        r'\bfuncion\b': 'función',
        r'\bacccion\b': 'acción',
        r'\baccion\b': 'acción',
        r'\bversion\b': 'versión',
        r'\bopcion\b': 'opción',
        r'\binformacion\b': 'información',
        r'\bcomunicacion\b': 'comunicación',
        r'\batencion\b': 'atención',
        r'\bsituacion\b': 'situación',
        r'\bconfiguracion\b': 'configuración',
        r'\bconexion\b': 'conexión',
        r'\bpresentacion\b': 'presentación',
        r'\bproduccion\b': 'producción',
        r'\bcoleccion\b': 'colección',
        r'\boperacion\b': 'operación',
        r'\binitiacion\b': 'iniciación',
        r'\biniciacion\b': 'iniciación',
        r'\bgeneracion\b': 'generación',
        r'\binstruccion\b': 'instrucción',
        r'\bcalculacion\b': 'calculación',
        r'\bcalculo\b': 'cálculo',
        r'\bnumero\b': 'número',
        r'\bnumeros\b': 'números',
        r'\bultimo\b': 'último',
        r'\bultima\b': 'última',
        r'\bprimero\b': 'primero',
        r'\bultimos\b': 'últimos',
        r'\bproximo\b': 'próximo',
        r'\bproxima\b': 'próxima',
        r'\bpublico\b': 'público',
        r'\bpublica\b': 'pública',
        r'\btipico\b': 'típico',
        r'\btipica\b': 'típica',
        r'\bmagico\b': 'mágico',
        r'\bmagica\b': 'mágica',
        r'\belectrico\b': 'eléctrico',
        r'\belectrica\b': 'eléctrica',
        r'\benergia\b': 'energía',
        r'\bhistoria\b': 'historia',
        r'\bperiodo\b': 'período',
        r'\btelefono\b': 'teléfono',
        r'\bejercicio\b': 'ejercicio',
        r'\bejercicion\b': 'ejercición',
        r'\bcodigo\b': 'código',
        r'\bindice\b': 'índice',
        r'\bpagina\b': 'página',
        r'\bpaginas\b': 'páginas',
        r'\bcapitulo\b': 'capítulo',
        r'\barticulo\b': 'artículo',
        r'\bmiercoles\b': 'miércoles',
        r'\bsabado\b': 'sábado',
        r'\bfacil\b': 'fácil',
        r'\bdificil\b': 'difícil',
        r'\butil\b': 'útil',
        r'\bagil\b': 'ágil',
        r'\bfacilmente\b': 'fácilmente',
        r'\bdificilmente\b': 'difícilmente',
        r'\brapido\b': 'rápido',
        r'\brapida\b': 'rápida',
        r'\brapidamente\b': 'rápidamente',
        r'\blento\b': 'lento',
        r'\bvalido\b': 'válido',
        r'\binvalido\b': 'inválido',
        r'\bsolido\b': 'sólido',
        r'\bliquido\b': 'líquido',
        r'\bsimbolico\b': 'simbólico',
        r'\bfisico\b': 'físico',
        r'\bfisica\b': 'física',
        r'\btecnico\b': 'técnico',
        r'\btecnica\b': 'técnica',
        r'\beconomico\b': 'económico',
        r'\beconomica\b': 'económica',
        r'\bpolitico\b': 'político',
        r'\bpolitica\b': 'política',
        r'\bcientífico\b': 'científico',
        r'\bcientifico\b': 'científico',
        r'\bcientifica\b': 'científica',
        r'\bmecanico\b': 'mecánico',
        r'\bmecanica\b': 'mecánica',
        r'\borganico\b': 'orgánico',
        r'\borganica\b': 'orgánica',
        r'\bexamen\b': 'examen',
        r'\borden\b': 'orden',
        r'\bimagen\b': 'imagen',
        r'\bjoven\b': 'joven',
        r'\bvirgen\b': 'virgen',
        r'\bvolumen\b': 'volumen',
        r'\bresumen\b': 'resumen',
        r'\bcaracter\b': 'carácter',
        r'\bcaracteres\b': 'caracteres',
    }
    for patron, reemplazo in CORRECCIONES.items():
        texto = re.sub(patron, reemplazo, texto, flags=re.IGNORECASE)
    return texto

def _toggle_tts_engine():
    global _tts_engine, _tts_preferred_engine
    if len(_cartesia_keys_agotadas) >= len(CARTESIA_KEYS):
        print('\n[TTS Engine] ⚠️ Las API Keys de Cartesia están sin créditos (HTTP 402). Se mantendrá Edge TTS.\n')
        _tts_engine = 'edge'
        _tts_preferred_engine = 'edge'
        return

    if _tts_engine == 'cartesia':
        _tts_engine = 'edge'
        _tts_preferred_engine = 'edge'
        print('\n[TTS Engine] 🔄 Tecla "V" presionada -> Cambiado a Edge TTS.\n')
    else:
        _tts_engine = 'cartesia'
        _tts_preferred_engine = 'cartesia'
        print('\n[TTS Engine] 🔄 Tecla "V" presionada -> Cambiado a Cartesia AI.\n')

def hablar(texto, pausa_post=0.5):
    global _tts_activo, _tts_engine, _tts_preferred_engine, _ultimo_texto_hablado
    texto = _corregir_tildes(texto)
    _ultimo_texto_hablado = texto.lower().strip()
    print(f'[TTS-{_tts_engine.upper()}] {texto}')
    _tts_activo = True
    try:
        if _tts_engine == 'cartesia':
            ok = _hablar_cartesia(texto)
            if not ok:
                print('[TTS Cartesia] ⚠️ Se agotaron/fallaron todas las keys. Cambiando PERMANENTEMENTE a Edge TTS...')
                _tts_engine = 'edge'
                _tts_preferred_engine = 'edge'
                _hablar_edge(texto)
        else:
            _hablar_edge(texto)
    except Exception as e:
        print(f'[TTS Error] {e}')
        try:
            _hablar_edge(texto)
        except Exception:
            pass
    time.sleep(pausa_post)
    _tts_activo = False

# ─────────────────────────────────────────────
#  VOLUMEN TABLETA
# ─────────────────────────────────────────────
def cambiar_volumen_tableta(subir: bool):
    try:
        endpoint = 'subir' if subir else 'bajar'
        r = requests.get(f'{TABLETA_IP}/volumen/{endpoint}', timeout=8)
        return r.json().get('volumen')
    except Exception as e:
        print(f'[Tableta Volumen Error] {e}')
        return None

def set_volumen_tableta(nivel: int):
    try:
        r = requests.get(f'{TABLETA_IP}/volumen/set/{nivel}', timeout=8)
        return r.status_code == 200
    except Exception as e:
        print(f'[Tableta Volumen Error] {e}')
        return False

# ─────────────────────────────────────────────
#  VOLUMEN LOCAL (pycaw)
# ─────────────────────────────────────────────
def _get_interface_volumen():
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))

def _get_volumen_actual():
    try:
        vol = _get_interface_volumen()
        return round(vol.GetMasterVolumeLevelScalar() * 100)
    except Exception as e:
        print(f'[Volumen Error] {e}')
        return None

def _set_volumen_exacto(nivel):
    try:
        nivel = max(0, min(100, nivel))
        vol = _get_interface_volumen()
        vol.SetMasterVolumeLevelScalar(nivel / 100.0, None)
        return True
    except Exception as e:
        print(f'[Volumen Error] {e}')
        return False

def cambiar_volumen(subir: bool):
    actual = _get_volumen_actual()
    if actual is None:
        tecla = 'volume up' if subir else 'volume down'
        for _ in range(5):
            keyboard.press_and_release(tecla)
            time.sleep(0.05)
        return None
    nuevo = min(100, actual + 10) if subir else max(0, actual - 10)
    _set_volumen_exacto(nuevo)
    return nuevo

# ─────────────────────────────────────────────
#  COMANDOS RAPIDOS
# ─────────────────────────────────────────────
def detectar_comando_rapido(texto):
    t = texto.lower()

    for frase in sorted(COMANDOS_VOLUMEN_EXACTO, key=len, reverse=True):
        if frase in t:
            resto = t.split(frase)[-1].strip()
            numero = None
            for p in resto.split():
                if p.isdigit():
                    numero = int(p)
                    break
                if p in NUMEROS_TEXTO:
                    numero = NUMEROS_TEXTO[p]
                    break
            if numero is not None:
                nivel = numero * 10 if numero <= 10 else numero
                nivel = max(0, min(100, nivel))
                return ('volumen_exacto', nivel)

    if any(c in t for c in COMANDOS_HORA):
        return ('hora', None)
    if any(c in t for c in COMANDOS_SUBIR_VOLUMEN):
        return ('volumen_subir', None)
    if any(c in t for c in COMANDOS_BAJAR_VOLUMEN):
        return ('volumen_bajar', None)

    return (None, None)

def ejecutar_comando_rapido(accion, parametro=None):
    if accion == 'hora':
        hora_str = datetime.now().strftime('%I:%M %p').lstrip('0')
        hablar(f'Son las {hora_str}.')
        return True
    elif accion == 'volumen_subir':
        nuevo = cambiar_volumen_tableta(subir=True)
        hablar(f'Ya subi el volumen, ahora esta en {nuevo}.' if nuevo is not None else 'Subi el volumen.')
        return True
    elif accion == 'volumen_bajar':
        nuevo = cambiar_volumen_tableta(subir=False)
        hablar(f'Ya baje el volumen, ahora esta en {nuevo}.' if nuevo is not None else 'Baje el volumen.')
        return True
    elif accion == 'volumen_exacto':
        if set_volumen_tableta(parametro):
            hablar(f'Listo, volumen puesto en {parametro}.')
        else:
            hablar('No me andan los controles de esta cochinada de volumen.')
        return True
    return False

# ─────────────────────────────────────────────
#  TIMERS Y ALARMAS
# ─────────────────────────────────────────────
FRASES_ALARMA = [
    'Chamaco flojo despierta, no soy tu sirviente.',
    'Me interrumpiste mi siesta con tus gritos de duendes, ahora te toca levantarte.',
    'Levántate ya, que en mis tiempos a las cinco ya estábamos en el campo.',
    'Son las que son, abre los ojos antes de que te eche agua fría.',
    '¿Sigues dormido? Qué juventud tan perdida y blanda.',
    'Despierta, el mundo no espera, ¡y menos con este gobierno de comunistas y extranjeros!',
    'Ya levántate, hueles a puro ocio desde aquí.',
    '¡Chamaco arriba! No voy a parar hasta que te me levantes.',
    'Si no te levantas voy a seguir gritando, y mis cuerdas vocales no se cansan.',
    'Levántate ya, pareces un saco de papas tirado ahí.',
]

COMANDOS_PARAR_ALARMA = [
    'para la alarma', 'ya estoy despierto', 'detente', 'para ya',
    'calla', 'silencio', 'ya me desperte', 'ok ya', 'listo ya desperte',
    'para', 'stop', 'ya basta', 'suficiente'
]

def _thread_alarma(hora, minuto):
    global _alarma_activa
    while True:
        ahora = datetime.now()
        if ahora.hour == hora and ahora.minute == minuto:
            _alarma_activa = True
            threading.Thread(target=_loop_alarma, daemon=True).start()
            break
        time.sleep(5)

def _loop_alarma():
    global _alarma_activa, rec, mic
    print('[Alarma] Sonando, esperando que el tronco despierte...')
    while _alarma_activa:
        try:
            frase = random.choice(FRASES_ALARMA)
            hablar(frase, pausa_post=0.9)
        except Exception as e:
            print(f'[Alarma TTS Error] {e}')
            time.sleep(1)
            continue

        if not _alarma_activa:
            return

        try:
            with _mic_lock:
                with mic as source:
                    rec.pause_threshold       = 1.5
                    rec.non_speaking_duration = 0.8
                    try:
                        audio = rec.listen(source, timeout=8, phrase_time_limit=6)
                        texto = rec.recognize_google(audio, language=LANG).lower()
                    except sr.WaitTimeoutError:
                        texto = ''
                    except sr.UnknownValueError:
                        texto = ''
            if texto:
                print(f'[Alarma] Escuche: {texto}')
                if any(c in texto for c in COMANDOS_PARAR_ALARMA):
                    _alarma_activa = False
                    hablar('Ya era hora, flojo. No me hagas levantarme otra vez, que me duele la ciática.')
                    print('[Alarma] Apagada.')
                    return
        except Exception as e:
            print(f'[Alarma Mic Error] {e}')
            time.sleep(1)

def _thread_timer(segundos, mensaje):
    time.sleep(segundos)
    hablar(mensaje)

def detectar_timer_alarma(texto):
    t = texto.lower()

    for frase in sorted(COMANDOS_ALARMA, key=len, reverse=True):
        if frase in t:
            resto = t.split(frase)[-1].strip()
            try:
                partes = resto.replace(':', ' ').split()
                hora = int(partes[0]) if partes[0].isdigit() else NUMEROS_TEXTO.get(partes[0])
                minuto = 0
                if len(partes) > 1:
                    if partes[1].isdigit():
                        minuto = int(partes[1])
                    elif 'media' in partes:
                        minuto = 30
                if hora is not None:
                    if 'de la noche' in t or 'pm' in t:
                        if hora != 12:
                            hora += 12
                    elif 'de la manana' in t or 'am' in t:
                        if hora == 12:
                            hora = 0
                if hora is not None:
                    return ('alarma', (hora, minuto))
            except:
                pass

    for frase in sorted(COMANDOS_TIMER, key=len, reverse=True):
        if frase in t:
            resto = t.split(frase)[-1].strip()
            try:
                partes = resto.split()
                numero = None
                unidad = 'minutos'
                for p in partes:
                    if p.isdigit():
                        numero = int(p)
                    elif p in NUMEROS_TEXTO:
                        numero = NUMEROS_TEXTO[p]
                    if p in ('segundo', 'segundos', 'seg'):
                        unidad = 'segundos'
                    elif p in ('minuto', 'minutos', 'min'):
                        unidad = 'minutos'
                    elif p in ('hora', 'horas'):
                        unidad = 'horas'
                if numero is not None:
                    return ('timer', (numero, unidad))
            except:
                pass

    return (None, None)

def ejecutar_timer_alarma(accion, parametro):
    if accion == 'timer':
        numero, unidad = parametro
        if unidad == 'segundos':
            segundos = numero
            texto_tiempo = f'{numero} segundos'
        elif unidad == 'horas':
            segundos = numero * 3600
            texto_tiempo = f'{numero} hora{"s" if numero > 1 else ""}'
        else:
            segundos = numero * 60
            texto_tiempo = f'{numero} minuto{"s" if numero > 1 else ""}'
        threading.Thread(
            target=_thread_timer,
            args=(segundos, f'Chamaco flojo, ya pasaron {texto_tiempo}. Luego no digas que el viejo Mario no te avisó.'),
            daemon=True
        ).start()
        return f'Ya puse el reloj para {texto_tiempo}. No me molestes hasta que suene, que me voy a echar una cabezadita.'
    elif accion == 'alarma':
        hora, minuto = parametro
        threading.Thread(
            target=_thread_alarma,
            args=(hora, minuto),
            daemon=True
        ).start()
        return f'Alarma puesta a las {hora} con {minuto:02d}. Más te vale despertarte a la primera.'
    return None

# ─────────────────────────────────────────────
#  GESTION DE COLA
# ─────────────────────────────────────────────
def _info_track_actual() -> str:
    with _cola_lock:
        if not _cola or _indice_cola < 0 or _indice_cola >= len(_cola):
            return 'nada'
        t = _cola[_indice_cola]
        return f'{t["titulo"]}'

def limpiar_cola():
    global _cola, _indice_cola, _cola_personalizada
    _parar_cancion_actual()
    cmd_ojos('desactivar')
    with _cola_lock:
        _cola                = []
        _indice_cola         = -1
        _cola_personalizada  = False

def mezclar_cola():
    global _cola, _indice_cola
    with _cola_lock:
        if not _cola:
            return False
        if 0 <= _indice_cola < len(_cola):
            actual = _cola[_indice_cola]
            resto  = [t for i, t in enumerate(_cola) if i != _indice_cola]
            random.shuffle(resto)
            _cola        = [actual] + resto
            _indice_cola = 0
        else:
            random.shuffle(_cola)
            _indice_cola = 0
        return True

def info_cola() -> str:
    with _cola_lock:
        if not _cola:
            return 'No hay ninguna canción en esa lista. Esta cola está vacía como tu cabeza.'
        total = len(_cola)
        lineas = [f'Cola con {total} canciones.']
        for i, t in enumerate(_cola):
            if i < _indice_cola:
                continue
            if i == _indice_cola:
                lineas.append(f'Suena ahora: {t["titulo"]}.')
            else:
                lineas.append(f'{i - _indice_cola}. {t["titulo"]}.')
            if i - _indice_cola >= 3:
                resto = total - i - 1
                if resto > 0:
                    lineas.append(f'Y {resto} mas.')
                break
        return ' '.join(lineas)

# ─────────────────────────────────────────────
#  REPRODUCCION CONTINUA
# ─────────────────────────────────────────────
def _buscar_autoplay(titulo_referencia: str) -> dict | None:
    """Busca una cancion individual relacionada, sin playlists ni compilaciones."""
    palabras = [p for p in titulo_referencia.split() if len(p) > 3][:3]
    artista_aprox = ' '.join(palabras[:2]) if palabras else titulo_referencia

    queries = [
        f'{artista_aprox} cancion oficial',
        f'canciones parecidas a {artista_aprox} cancion',
        f'{artista_aprox} official audio',
    ]

    PALABRAS_BLOQUEADAS = {
        'playlist', 'mix', 'top', 'hits', 'exitos', 'éxitos',
        'compilacion', 'compilación', 'megamix', 'mashup',
        'nonstop', 'non-stop', 'collection', 'full album',
        'grandes exitos', 'lo mejor', 'spotify', '#music',
        '#playlist', 'horas', 'hours', 'hour', 'hora',
        'remasterizado', 'remastered', 'remasterizada',
        'hd remaster', 'hq remaster',
    }

    try:
        ydl_opts = {'noplaylist': True, 'quiet': True, 'no_warnings': True}
        with _cola_lock:
            urls_usadas    = {t['url'] for t in _cola}
            titulos_usados = {t['titulo'].lower() for t in _cola}
        palabras_ref = set(titulo_referencia.lower().split())

        for query in queries:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f'ytsearch10:{query}', download=False)
                if not info or not info.get('entries'):
                    continue
                for e in info['entries']:
                    url      = e.get('webpage_url')
                    titulo   = e.get('title', '')
                    tl       = titulo.lower()
                    duracion = e.get('duration') or 0

                    if not url or url in urls_usadas:
                        continue
                    if tl in titulos_usados:
                        continue
                    # Rechazar playlists/compilaciones por titulo
                    if any(blq in tl for blq in PALABRAS_BLOQUEADAS):
                        continue
                    # Rechazar videos de mas de 8 minutos (probablemente no es cancion suelta)
                    if duracion > 480:
                        continue
                    # Evitar misma cancion con otra URL
                    palabras_nueva = set(tl.split())
                    if palabras_ref and palabras_nueva:
                        overlap = len(palabras_ref & palabras_nueva) / len(palabras_ref)
                        if overlap > 0.6:
                            continue
                    return {'url': url, 'titulo': titulo, 'artista': 'YouTube'}
    except Exception as ex:
        print(f'[Autoplay Error] {ex}')
    return None
def _parar_cancion_actual():
    global _ffplay_proc, _ytdlp_proc, _parada_manual
    _parada_manual = True
    if _ffplay_proc and _ffplay_proc.poll() is None:
        _ffplay_proc.terminate()
        _ffplay_proc = None
    if _ytdlp_proc and _ytdlp_proc.poll() is None:
        _ytdlp_proc.terminate()
        _ytdlp_proc = None

def _reproducir_url(url: str):
    global _ffplay_proc, _ytdlp_proc
    ydl_cmd    = [sys.executable, '-m', 'yt_dlp', '-f', 'bestaudio/best',
                  '-o', '-', '--quiet', '--no-warnings', url]
    ffplay_cmd = [FFPLAY, '-nodisp', '-autoexit', '-i', 'pipe:0']
    _ytdlp_proc  = subprocess.Popen(ydl_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    _ffplay_proc = subprocess.Popen(ffplay_cmd, stdin=_ytdlp_proc.stdout,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _ytdlp_proc.stdout.close()
    _ffplay_proc.wait()
    if _ytdlp_proc is not None:
        _ytdlp_proc.wait()

def _loop_cola():
    global _indice_cola, _parada_manual, _modo_musica, _cola, _stop_cola, _modo_aleatorio

    while True:
        if _stop_cola:
            print('[Cola] Stop solicitado, terminando hilo.')
            _modo_musica = False
            cmd_ojos('desactivar')
            break

        with _cola_lock:
            if not _cola or _indice_cola < 0 or _indice_cola >= len(_cola):
                # ── Autoplay: buscar cancion relacionada ──
                if _autoplay and _cola and not _stop_cola:
                    titulo_ref = _cola[-1]['titulo']
                else:
                    print('[Cola] Lista terminada o cola vacia.')
                    _modo_musica = False
                    cmd_ojos('desactivar')
                    break
            else:
                titulo_ref = None

        # Si llegamos aqui por autoplay
        if titulo_ref is not None:
            if _stop_cola:
                print('[Cola] Stop solicitado antes de autoplay, terminando.')
                _modo_musica = False
                break
            print(f'[Autoplay] Buscando cancion relacionada a: {titulo_ref}')
            siguiente = _buscar_autoplay(titulo_ref)
            if _stop_cola:
                print('[Cola] Stop solicitado durante autoplay, terminando.')
                _modo_musica = False
                break
            if siguiente:
                siguiente['auto'] = True
                with _cola_lock:
                    _cola.append(siguiente)
                    _indice_cola = len(_cola) - 1
                print(f'[Autoplay] Agregando: {siguiente["titulo"]}')
            else:
                print('[Autoplay] No encontre cancion relacionada, terminando.')
                _modo_musica = False
                break

        with _cola_lock:
            track = _cola[_indice_cola]

        # Si el track no tiene URL (cargado de una playlist), buscar en YouTube al vuelo
        if not track.get('url'):
            print(f'[Cola] Buscando URL en YouTube para: "{track["titulo"]}"...')
            res = buscar_youtube(track['titulo'], max_resultados=3)
            if res:
                with _cola_lock:
                    track['url'] = res[0]['url']
                    track['titulo'] = res[0]['titulo']
                    track['artista'] = res[0]['artista']
            else:
                print(f'[Cola Error] No se pudo encontrar resultado en YouTube para: "{track["titulo"]}"')
                with _cola_lock:
                    _indice_cola += 1
                continue

        print(f'[Cola] [{_indice_cola + 1}/{len(_cola)}] {track["titulo"]}')
        _parada_manual = False
        try:
            # Cerrar los ojos por 2 segundos antes de iniciar la reproducción, luego activarlos
            cmd_ojos('desactivar')
            time.sleep(2.0)
            cmd_ojos('activar')
            _reproducir_url(track['url'])
        except Exception as e:
            print(f'[Cola Error] Fallo reproduciendo "{track["titulo"]}": {e}')
            with _cola_lock:
                _indice_cola += 1
            continue

        if _parada_manual:
            print('[Cola] Parada manual.')
            break

        with _cola_lock:
            if not _modo_aleatorio:
                _indice_cola += 1

    print('[Cola] Hilo de reproduccion terminado.')

def _iniciar_cola(desde_indice: int = 0):
    global _indice_cola, _loop_hilo
    _parar_cancion_actual()
    time.sleep(0.3)
    _indice_cola = desde_indice
    _loop_hilo   = threading.Thread(target=_loop_cola, daemon=True)
    _loop_hilo.start()

# ─────────────────────────────────────────────
#  FUNCIONES MUSICALES
# ─────────────────────────────────────────────
def buscar_youtube(query: str, max_resultados: int = 1) -> list:
    """Busca en YouTube y devuelve lista de tracks. Evita versiones remasterizadas y prioriza 'letra'/'lyrics'."""
    EVITAR_REMASTER = {'remasterizado', 'remastered', 'remasterizada', 'hd remaster', 'hq remaster'}
    ydl_opts = {'noplaylist': True, 'quiet': True, 'no_warnings': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f'ytsearch{max_resultados}:{query}', download=False)
            if info and info.get('entries'):
                resultados = []
                for e in info['entries']:
                    if not e.get('webpage_url'):
                        continue
                    tl = e.get('title', '').lower()
                    if any(r in tl for r in EVITAR_REMASTER):
                        print(f'[Busqueda] Ignorando version remasterizada: {e.get("title")}')
                        continue
                    
                    artista = e.get('artist') or e.get('uploader') or 'YouTube'
                    if artista.endswith(' - Topic'):
                        artista = artista[:-8]
                        
                    resultados.append({
                        'url': e.get('webpage_url'),
                        'titulo': e.get('title', query),
                        'artista': artista,
                        'duracion': e.get('duration') or 0
                    })
                
                # Priorizar resultados con "letra" o "lyrics" en el título
                con_letra = []
                sin_letra = []
                for r in resultados:
                    tl = r['titulo'].lower()
                    if 'letra' in tl or 'lyrics' in tl:
                        con_letra.append(r)
                    else:
                        sin_letra.append(r)
                
                return con_letra + sin_letra
    except Exception as e:
        print(f'[YouTube Error] {e}')
    return []

def extraer_artista_y_cancion(titulo_raw, artista_raw):
    """Extrae de manera inteligente el artista y el título limpio del tema a partir de la metadata de YouTube."""
    artista = artista_raw or 'YouTube'
    if artista.endswith(' - Topic'):
        artista = artista[:-8]
        
    titulo_clean = titulo_raw
    partes = titulo_raw.split('-')
    if len(partes) > 1:
        p0 = partes[0].strip()
        p1 = partes[1].strip()
        if artista == 'YouTube':
            if len(p0) < 30:
                artista = p0
                titulo_clean = p1
        else:
            if artista.lower() in p0.lower() or p0.lower() in artista.lower():
                titulo_clean = p1
            elif artista.lower() in p1.lower() or p1.lower() in artista.lower():
                titulo_clean = p0
                
    cancion = titulo_clean
    # Eliminar palabras típicas de vídeos musicales y versiones
    for w in ['lyrics', 'letra', 'video oficial', 'official video', 'video lyric', 'lyric video', 'hd', 'hq', 'official', 'oficial', 'live', 'en vivo', 'recital', 'completo', 'remix', 'cover', 'acoustic', 'acustico']:
        cancion = re.sub(rf'\b{w}\b', '', cancion, flags=re.IGNORECASE)
    cancion = ' '.join(cancion.split()).strip()
    
    # Remover caracteres especiales sobrantes
    cancion = re.sub(r'[^a-zA-Z0-9\sáéíóúÁÉÍÓÚñÑ]', '', cancion)
    cancion = ' '.join(cancion.split()).strip()
    
    return artista.strip(), cancion

def reproducir_cancion(query: str):
    """Busca en YouTube de forma ultra rápida (1 resultado), inicia la reproducción y autocompleta la cola en segundo plano."""
    global _cola, _indice_cola, _modo_musica, _musica_sesion_id
    _parar_hablar()  # Interrumpe la voz de inmediato si estaba hablando
    cmd_ojos('buscando')
    
    # Incrementar el session ID para invalidar cualquier hilo de autocompletado previo
    _musica_sesion_id += 1
    mi_sesion_id = _musica_sesion_id
    
    # 1. Búsqueda rápida de 1 solo resultado para iniciar de inmediato
    print(f'[Musica] Búsqueda inicial rápida para: {query} (Sesión ID: {mi_sesion_id})')
    tracks_inicial = buscar_youtube(query, max_resultados=1)
    
    # Reintentos rápidos si falla
    intentos = 0
    while not tracks_inicial and intentos < 2:
        if mi_sesion_id != _musica_sesion_id:
            return ('Búsqueda cancelada por nueva petición.', None)
        intentos += 1
        print(f'[Musica] No se encontró resultado inicial. Reintentando {intentos}/2...')
        time.sleep(0.5)
        tracks_inicial = buscar_youtube(query, max_resultados=1)
        
    if mi_sesion_id != _musica_sesion_id:
        return ('Búsqueda cancelada por nueva petición.', None)
        
    if not tracks_inicial:
        _modo_musica = False
        cmd_ojos('activar')
        return ('No encontré nada de eso en las computadoras de los chinos. Busca bien.', None)
        
    primer_track = tracks_inicial[0]
    primer_track['auto'] = False
    
    # Cargar el primer track e iniciar reproducción inmediatamente (borrando la cola anterior)
    with _cola_lock:
        _cola                = [primer_track]
        _indice_cola         = 0
        _cola_personalizada  = False
        
    _modo_musica = True
    _iniciar_cola(desde_indice=0)
    cmd_ojos('activar')
    
    artista_p, cancion_p = extraer_artista_y_cancion(primer_track['titulo'], primer_track['artista'])
    print(f'[Musica] Reproduciendo: "{cancion_p}" de "{artista_p}"')
    
    # 2. Hilo secundario para buscar el resto de canciones y autocompletar la cola
    def _buscar_resto_cola():
        if mi_sesion_id != _musica_sesion_id:
            return
            
        # Decidir qué buscar para autocompletar la cola:
        # Si logramos detectar un artista real que no sea "YouTube", buscamos sus éxitos directamente.
        if artista_p != 'YouTube' and len(artista_p) > 1:
            query_para_cola = f"{artista_p} top canciones"
        else:
            query_para_cola = f"{cancion_p} playlist"
            
        print(f'[Musica] Hilo secundario (Sesión {mi_sesion_id}) buscando para cola: "{query_para_cola}"...')
        
        # Buscamos 10 canciones recomendadas
        tracks_adicionales = buscar_youtube(query_para_cola, max_resultados=12)
        if mi_sesion_id != _musica_sesion_id:
            return
            
        if not tracks_adicionales:
            return
            
        tracks_filtrados = []
        urls_vistas = {primer_track['url']}
        
        # Función para verificar si un track es la misma canción que se está reproduciendo
        def es_tema_repetido(t_titulo, t_artista):
            _, canc_t = extraer_artista_y_cancion(t_titulo, t_artista)
            c1 = cancion_p.lower()
            c2 = canc_t.lower()
            if not c1 or not c2:
                return False
            if c1 in c2 or c2 in c1:
                return True
            ratio = difflib.SequenceMatcher(None, c1, c2).ratio()
            if ratio > 0.60:
                return True
            return False
            
        # Palabras que indican recopilatorios, mezclas o discos completos a evitar en el autocompletado de la cola
        PALABRAS_COMPILACION = {
            'mix', 'enganchados', 'completo', 'album', 'compilacion', 'compilación',
            'megamix', 'mashup', 'nonstop', 'non-stop', 'collection', 'full album',
            'grandes exitos', 'grandes éxitos', 'lo mejor', 'horas', 'hours', 'hour', 'hora',
            'exitos', 'éxitos', 'hits'
        }

        for t in tracks_adicionales:
            if t['url'] in urls_vistas:
                continue
            if es_tema_repetido(t['titulo'], t['artista']):
                continue
            
            # Evitar compilaciones, mixes y videos largos en la cola automática
            titulo_low = t['titulo'].lower()
            if any(pc in titulo_low for pc in PALABRAS_COMPILACION):
                print(f"[Musica] Ignorando posible compilación en autocompletado: {t['titulo']}")
                continue
            if t.get('duracion', 0) > 540:
                print(f"[Musica] Ignorando video muy largo ({t.get('duracion')}s) en autocompletado: {t['titulo']}")
                continue
                
            t['auto'] = True
            tracks_filtrados.append(t)
            urls_vistas.add(t['url'])
                    
        if tracks_filtrados:
            if _modo_aleatorio:
                random.shuffle(tracks_filtrados)
            with _cola_lock:
                # Comprobar que no haya cambiado la sesión musical y que el usuario no haya personalizado la cola
                if mi_sesion_id == _musica_sesion_id and not _cola_personalizada and _cola and _cola[0]['url'] == primer_track['url']:
                    for tf in tracks_filtrados:
                        if tf['url'] not in {tc['url'] for tc in _cola}:
                            _cola.append(tf)
                    print(f'[Musica] Cola autocompletada exitosamente. Total en cola: {len(_cola)}')
                    
    threading.Thread(target=_buscar_resto_cola, daemon=True).start()
    
    return (f'Aquí tienes {query} en Alex music.', primer_track['titulo'])

def agregar_a_cola(query: str) -> str:
    """Busca en YouTube y agrega UNA canción elegida por el usuario a la cola, eliminando las canciones generadas automáticamente."""
    global _modo_musica, _cola_personalizada, _cola, _indice_cola
    cmd_ojos('buscando')
    tracks = buscar_youtube(query, max_resultados=5)
    
    # Darle hasta 3 búsquedas más si no encuentra nada
    intentos = 0
    while not tracks and intentos < 3:
        intentos += 1
        print(f'[Musica] No se encontraron resultados para agregar. Reintentando búsqueda {intentos}/3...')
        time.sleep(1.0)
        tracks = buscar_youtube(query, max_resultados=5)
        
    if not tracks:
        return 'No encontré esa porquería para agregar a la lista.'
        
    track = tracks[0]
    track['auto'] = False
    
    with _cola_lock:
        _cola_personalizada = True
        
        # Determinar si la música está sonando activamente en una posición válida de la cola
        musica_activa = _modo_musica and (_loop_hilo and _loop_hilo.is_alive()) and (0 <= _indice_cola < len(_cola))
        
        if musica_activa:
            # Conservar la canción actual en reproducción, el historial y canciones personalizadas previas
            nueva_cola = []
            for i, t in enumerate(_cola):
                if i <= _indice_cola or not t.get('auto', False):
                    nueva_cola.append(t)
            _cola = nueva_cola
        else:
            # Si no hay música sonando activamente, limpiar canciones automáticas pero conservar historial si existía
            _cola = [t for t in _cola if not t.get('auto', False)]
        
        # Evitar duplicar solo en canciones personalizadas futuras no reproducidas
        urls_futuras = {t['url'] for i, t in enumerate(_cola) if i > _indice_cola}
        if track['url'] in urls_futuras:
            return 'Esa canción ya está en tu lista personalizada.'
            
        _cola.append(track)
        idx_nueva_cancion = len(_cola) - 1
        
        if not musica_activa:
            # Si la música estaba pausada, terminada o inactiva, forzar reproducción inmediata desde la nueva canción
            target_index = idx_nueva_cancion
            pendientes = 1
        else:
            target_index = None
            pendientes = len(_cola) - (_indice_cola + 1)
            
    if target_index is not None:
        _modo_musica = True
        _iniciar_cola(desde_indice=target_index)
        
    msg = f'Agregué "{track["titulo"]}". Cola personalizada: {pendientes} canción{"es" if pendientes != 1 else ""} pendiente{"s" if pendientes != 1 else ""}.'
    return msg

# ─────────────────────────────────────────────
#  GESTOR DE PLAYLISTS Y MIS LIKES
# ─────────────────────────────────────────────
PLAYLISTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'playlists.json')

def cargar_playlists_json():
    if not os.path.exists(PLAYLISTS_FILE):
        data = {"mis_likes": [], "playlists": {}}
        guardar_playlists_json(data)
        return data
    try:
        with open(PLAYLISTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f'[Error cargar playlists] {e}')
        return {"mis_likes": [], "playlists": {}}

def guardar_playlists_json(data):
    try:
        with open(PLAYLISTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'[Error guardar playlists] {e}')

def reproducir_playlist_por_nombre(nombre_raw: str):
    global _cola, _indice_cola, _modo_musica, _modo_aleatorio
    data = cargar_playlists_json()
    nombre_norm = nombre_raw.lower().strip()
    
    tracks_to_play = []
    nombre_display = ""
    
    if 'like' in nombre_norm or 'me gusta' in nombre_norm or nombre_norm == 'mis_likes':
        tracks_to_play = data.get("mis_likes", [])
        nombre_display = "Mis Likes"
    else:
        for p_name, p_tracks in data.get("playlists", {}).items():
            if p_name.lower().strip() in nombre_norm or nombre_norm in p_name.lower().strip():
                tracks_to_play = p_tracks
                nombre_display = p_name
                break
                
    if not tracks_to_play:
        _modo_musica = False
        cmd_ojos('activar')
        return (f'No encontré ninguna lista de reproducción llamada {nombre_raw}, chamaco.', None)
        
    _parar_hablar()
    with _cola_lock:
        _cola = []
        _cola_personalizada = True
        for t in tracks_to_play:
            _cola.append({
                'url': t.get('url', ''),
                'titulo': t.get('titulo', t.get('query', '')),
                'artista': t.get('artista', 'YouTube'),
                'auto': False
            })
        if _modo_aleatorio:
            random.shuffle(_cola)
        _indice_cola = 0
    _modo_musica = True
    _iniciar_cola(desde_indice=0)
    cmd_ojos('activar')
    return (f'Aquí tienes tu lista {nombre_display} en Alex music.', nombre_display)

def dar_like_cancion_actual() -> str:
    with _cola_lock:
        if not _cola or _indice_cola < 0 or _indice_cola >= len(_cola):
            return "No está sonando ninguna canción ahorita para darle Me Gusta, chamaco."
        track = _cola[_indice_cola]
    
    p_data = cargar_playlists_json()
    if 'mis_likes' not in p_data:
        p_data['mis_likes'] = []
    
    track_obj = {
        'titulo': track['titulo'],
        'url': track.get('url', ''),
        'query': track['titulo']
    }
    
    if not any(t.get('titulo') == track['titulo'] for t in p_data['mis_likes']):
        p_data['mis_likes'].append(track_obj)
        guardar_playlists_json(p_data)
        return f"Añadí {track['titulo']} a tus canciones favoritas en Alex Music."
    return f"{track['titulo']} ya estaba guardada en tus Me Gusta."

def crear_playlist_por_nombre(nombre_p: str) -> str:
    nombre = nombre_p.strip()
    if not nombre:
        return "Tienes que decirme el nombre de la playlist que quieres crear."
    p_data = cargar_playlists_json()
    if 'playlists' not in p_data:
        p_data['playlists'] = {}
    if nombre in p_data['playlists']:
        return f"Ya existe una lista llamada {nombre}."
    p_data['playlists'][nombre] = []
    guardar_playlists_json(p_data)
    return f"Listo, creé la lista {nombre} en Alex Music."

def siguiente_cancion() -> str:
    global _indice_cola
    with _cola_lock:
        if not _cola:
            return 'No hay nada en la lista de canciones.'
        if not _autoplay and _indice_cola + 1 >= len(_cola):
            return 'Es la última canción que hay. No inventes más.'
        _indice_cola += 1
        if _indice_cola < len(_cola):
            siguiente = _cola[_indice_cola]
            msg = f'Siguiente: {siguiente["titulo"]}.'
        else:
            msg = 'Buscando más canciones relacionadas...'
    _parar_cancion_actual()
    time.sleep(0.3)
    _iniciar_cola(desde_indice=_indice_cola)
    return msg

def cancion_anterior() -> str:
    global _indice_cola
    with _cola_lock:
        if not _cola:
            return 'No hay lista de reproducción puesta.'
        nuevo_idx    = max(0, _indice_cola - 1)
        _indice_cola = nuevo_idx
        anterior     = _cola[nuevo_idx]
    _parar_cancion_actual()
    time.sleep(0.3)
    _iniciar_cola(desde_indice=_indice_cola)
    return f'Regresando a {anterior["titulo"]}.'

def reiniciar_cancion_actual() -> str:
    global _indice_cola
    with _cola_lock:
        if not _cola or _indice_cola < 0:
            return 'No está sonando nada ahora.'
        track = _cola[_indice_cola]
    _parar_cancion_actual()
    time.sleep(0.3)
    _iniciar_cola(desde_indice=_indice_cola)
    return f'Desde el inicio de {track["titulo"]}. ¡Qué obsesión tan enfermiza la tuya!'

# ─────────────────────────────────────────────
#  DETECTOR COMANDOS MUSICA
# ─────────────────────────────────────────────
def detectar_comando_musica(texto):
    global _modo_aleatorio
    t = texto.lower()

    for frase in COMANDOS_MUSICA['limpiar']:
        if frase in t: return ('limpiar', None)
    for frase in COMANDOS_MUSICA['mezclar']:
        if frase in t: return ('mezclar', None)
    for frase in COMANDOS_MUSICA['aleatorio_on']:
        if frase in t: return ('aleatorio_on', None)
    for frase in COMANDOS_MUSICA['aleatorio_off']:
        if frase in t: return ('aleatorio_off', None)
    for frase in COMANDOS_MUSICA['cola']:
        if frase in t: return ('cola', None)
    for frase in COMANDOS_MUSICA['autoplay_on']:
        if frase in t: return ('autoplay_on', None)
    for frase in COMANDOS_MUSICA['autoplay_off']:
        if frase in t: return ('autoplay_off', None)

    for frase in COMANDOS_MUSICA['like']:
        if frase in t: return ('like', None)

    for frase in sorted(COMANDOS_MUSICA['crear_playlist'], key=len, reverse=True):
        if frase in t:
            resto = t.split(frase)[-1].strip()
            if resto: return ('crear_playlist', resto)

    for frase in sorted(COMANDOS_MUSICA['agregar'], key=len, reverse=True):
        if frase in t:
            resto = t.split(frase)[-1].strip()
            if resto: return ('agregar', resto)

    for frase in COMANDOS_MUSICA['reinicio']:
        if frase in t: return ('reinicio', None)
    for frase in COMANDOS_MUSICA['pause']:
        if frase in t: return ('pause', None)
    for frase in COMANDOS_MUSICA['next']:
        if frase in t: return ('next', None)
    for frase in COMANDOS_MUSICA['prev']:
        if frase in t: return ('prev', None)

    for frase in sorted(COMANDOS_MUSICA['cancion'], key=len, reverse=True):
        if t.startswith(frase + ' '):
            resto = t[len(frase):].strip()
            if resto:
                # Comprobar si solicitó aleatorio en la orden de reproducción
                solicitado_aleatorio = any(k in resto for k in ['en modo aleatorio', 'en aleatorio', 'modo aleatorio', 'aleatorio', 'aleatoria', 'random', 'shuffle'])
                if solicitado_aleatorio:
                    _modo_aleatorio = True
                    # Limpiar resto de palabras aleatorio
                    for k in ['en modo aleatorio', 'en aleatorio', 'modo aleatorio', 'aleatorio', 'aleatoria', 'random', 'shuffle']:
                        resto = resto.replace(k, '').strip()
                    resto = ' '.join(resto.split())
                return ('cancion', resto)

    return (None, None)

def ejecutar_comando_musica(accion, parametro=None):
    if accion == 'cancion':
        hablar('Espera, chamaco, déjame buscar esa música de salvajes.')
        msg, _ = reproducir_cancion(parametro)
        return msg
    elif accion == 'like':
        return dar_like_cancion_actual()
    elif accion == 'crear_playlist':
        return crear_playlist_por_nombre(parametro)
    elif accion == 'agregar':
        hablar('Espera, ya estoy buscando para agregar a la lista, qué impaciente.')
        return agregar_a_cola(parametro)
    elif accion == 'cola':
        return info_cola()
    elif accion == 'limpiar':
        limpiar_cola()
        return 'Lista borrada. Quedó vacía como tu cabeza de chorlito.'
    elif accion == 'mezclar':
        if mezclar_cola():
            return 'Lista mezclada al azar. A ver si te sorprende algo en esta vida aburrida.'
        return 'No hay nada en la cola para mezclar.'
    elif accion == 'autoplay_on':
        global _autoplay
        _autoplay = True
        return 'Reproducción automática activada. Poniendo música decente de la vieja escuela, no tu mugrero.'
    elif accion == 'autoplay_off':
        _autoplay = False
        return 'Reproducción automática apagada. Ya no sonará nada cuando acabe, allá tú.'
    elif accion == 'aleatorio_on':
        global _modo_aleatorio
        _modo_aleatorio = True
        mezclar_cola()
        return 'Modo aleatorio activado. A ver qué sale de esta tómbola.'
    elif accion == 'aleatorio_off':
        _modo_aleatorio = False
        return 'Modo aleatorio desactivado. Seguiremos en orden, como Dios manda.'
    elif accion == 'reinicio':
        return reiniciar_cancion_actual()
    elif accion == 'pause':
        _parar_cancion_actual()
        cmd_ojos('desactivar')
        return 'Silencio pues. Qué delicado me saliste.'
    elif accion == 'next':
        return siguiente_cancion()
    elif accion == 'prev':
        return cancion_anterior()
    return None

# ─────────────────────────────────────────────
#  MICROFONO
# ─────────────────────────────────────────────
def escuchar(rec, mic, timeout=None, frase=15, pause_threshold=1.0, evitar_eco=True):
    global _escuchando, _tts_activo, _tiempo_espera_mic
    if mic is None:
        time.sleep(1)
        return ''
    
    # Esperar a que la voz finalice
    while _tts_activo:
        time.sleep(0.1)
    
    # Timer de espera dinámico configurable antes de abrir el micrófono
    if evitar_eco and _tiempo_espera_mic > 0:
        print(f'[Mario] Esperando {_tiempo_espera_mic}s para evitar eco por SoundWire...')
        time.sleep(_tiempo_espera_mic)
    
    print('[Mario] Escuchando...')
    _escuchando = True
    try:
        with _mic_lock:
            with mic as source:
                rec.pause_threshold       = pause_threshold
                rec.non_speaking_duration = 0.4
                try:
                    audio = rec.listen(source, timeout=timeout, phrase_time_limit=frase)
                    texto = rec.recognize_google(audio, language=LANG).lower().strip()
                    if es_eco_propio(texto):
                        print(f'[Eco Propio] Ignorado por ser eco de mi propia voz: "{texto}"')
                        return ''
                    return texto
                except sr.WaitTimeoutError:
                    return ''
                except sr.UnknownValueError:
                    return ''
                except Exception as e:
                    print(f'[Error escuchar] {e}')
                    return ''
    finally:
        _escuchando = False


# ─────────────────────────────────────────────
#  IA
# ─────────────────────────────────────────────
def es_despedida(texto):
    return any(w in texto.lower() for w in DESPEDIDAS)

def preguntar(texto):
    global historial, _ultima_observacion, _contador_respuestas
    try:
        # Actualizar vision cada 2 respuestas en segundo plano
        _contador_respuestas += 1
        if _contador_respuestas % 2 == 0:
            def _actualizar_vision():
                global _ultima_observacion
                imagen_b64 = capturar_foto_esp32_b64()
                if imagen_b64:
                    desc = analizar_imagen_silencioso(imagen_b64)
                    if desc:
                        _ultima_observacion = desc
                        print(f'[Visión] Actualizado en respuesta {_contador_respuestas}: {desc}')
            threading.Thread(target=_actualizar_vision, daemon=True).start()
        ahora    = datetime.now().strftime('%A %d de %B %Y, %I:%M %p')
        memoria  = cargar_memoria()
        contexto = (
            f'Fecha y hora actual: {ahora}\n'
            f'LO QUE ESTÁS VIENDO AHORA (datos del sensor visual): {_ultima_observacion}\n'
        )
        if any(kw in texto.lower() for kw in COMANDOS_CLIMA):
            # Intentar extraer ciudad si el usuario dice "en [Ciudad]" o similar
            ciudad_detectada = ""
            for prep in [" en ", " de ", " para "]:
                if prep in texto.lower():
                    partes = texto.lower().split(prep)
                    if len(partes) > 1:
                        cand = partes[-1].strip()
                        for char in ["?", "¿", "!", "¡", ".", ",", "(", ")"]:
                            cand = cand.replace(char, "")
                        palabras = cand.split()
                        if len(palabras) <= 3 and len(palabras) > 0:
                            ciudad_detectada = cand
                            break
            
            datos_clima = obtener_clima_en_vivo(ciudad_detectada)
            if datos_clima:
                print(f'[Clima en vivo] {datos_clima}')
                loc = ciudad_detectada.title() if ciudad_detectada else "tu ubicación local"
                contexto += f'DATOS REALES DEL CLIMA EN TIEMPO REAL (para {loc}): {datos_clima}\n'
        if any(kw in texto.lower() for kw in COMANDOS_NOTICIAS):
            datos_noticias = buscar_noticias_o_internet(texto)
            if datos_noticias:
                print(f'[Noticias/Web] {datos_noticias}')
                contexto += f'DATOS RECIENTES DE INTERNET Y NOTICIAS: {datos_noticias}\n'
        if memoria:
            contexto += memoria + '\n'

        messages = [{'role': 'system', 'content': SYSTEM_PROMPT + '\n\n' + contexto}]
        messages += historial[-6:]
        messages.append({'role': 'user', 'content': texto})

        cmd_ojos('pensando')
        print(f'[Ollama] Enviando pregunta a {MODEL}...')
        r = requests.post(
            OLLAMA_URL,
            json={'model': MODEL, 'messages': messages, 'stream': False},
            timeout=120
        )
        if r.status_code != 200:
            print(f'[Ollama Error] HTTP {r.status_code}: {r.text[:300]}')
            cmd_ojos('activar')
            return f'Error en Ollama HTTP {r.status_code}. Revisa la consola.'
        data = r.json()
        if 'error' in data:
            print(f'[Ollama Error] {data["error"]}')
            cmd_ojos('activar')
            return f'Error de Ollama: {data["error"]}'
        respuesta = data.get('message', {}).get('content', '')
        if not respuesta:
            cmd_ojos('activar')
            return 'Ollama no devolvió ninguna respuesta.'
        print(f'[Ollama] Respuesta recibida ({len(respuesta)} caracteres).')
        cmd_ojos('activar')

        historial.append({'role': 'user',      'content': texto})
        historial.append({'role': 'assistant', 'content': respuesta})
        if len(historial) > 20:
            historial = historial[-20:]

        if len(historial) % 6 == 0:
            guardar_hecho(f'Alex dijo: {texto}. Mario respondio: {respuesta[:100]}')

        return respuesta
    except Exception as e:
        cmd_ojos('activar')
        print(f'[Error] {e}')
        return 'Maldita sea, no responde el aparato ese. Vuelve a intentar.'

# ─────────────────────────────────────────────
#  MODO MUSICA
# ─────────────────────────────────────────────
def loop_modo_musica(rec, mic):
    global _modo_musica
    _modo_musica = True
    print('[Modo Musica] Activado.')
    cmd_ojos('activar')

    while _modo_musica:
        comando = escuchar(rec, mic, timeout=5, frase=8)
        if not comando:
            continue
        print(f'[Modo Musica] Escuche: {comando}')

        accion_rapida, param_rapido = detectar_comando_rapido(comando)
        if accion_rapida:
            ejecutar_comando_rapido(accion_rapida, param_rapido)
            continue

        accion_ta, param_ta = detectar_timer_alarma(comando)
        if accion_ta:
            hablar(ejecutar_timer_alarma(accion_ta, param_ta))
            continue

        if any(w in comando for w in WAKE_WORDS):
            _modo_musica = False
            print('[Modo Musica] Wake word detectada, saliendo a modo chat.')
            cmd_ojos('activar')
            hablar('¿Qué quieres, chamaco?')
            return True

        accion, param = detectar_comando_musica(comando)
        if accion:
            respuesta = ejecutar_comando_musica(accion, param)
            if respuesta:
                hablar(respuesta)
            if accion == 'pause':
                _modo_musica = False
                cmd_ojos('desactivar')
                return False
        # Si no se entendio el comando, simplemente ignorar y seguir escuchando

    return False

# ─────────────────────────────────────────────
#  SERVIDOR HTTP (panel de control)
# ─────────────────────────────────────────────
_app = Flask(__name__)
CORS(_app)

# ─────────────────────────────────────────────
#  DECORADOR: VOZ TIENE PRIORIDAD
# ─────────────────────────────────────────────
from functools import wraps

def voz_prioritaria(f):
    """Bloquea el endpoint del panel SOLO si el TTS esta hablando o el mic escuchando un comando."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if _tts_activo or _escuchando:
            razon = 'hablando' if _tts_activo else 'escuchando'
            return jsonify({'ok': False, 'bloqueado': True,
                            'msg': f'Mario está {razon}, intenta en un momento.'}), 503
        return f(*args, **kwargs)
    return wrapper

def sin_bloqueo(f):
    """Decorador vacio: este endpoint siempre esta disponible."""
    return f

@_app.after_request
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

def _obtener_url_ngrok():
    # 1. Intentar obtenerlo mediante pyngrok
    try:
        from pyngrok import ngrok
        tunnels = ngrok.get_tunnels()
        for t in tunnels:
            if t.public_url.startswith('https:'):
                return t.public_url
    except Exception:
        pass

    # 2. Fallback: API HTTP local de ngrok
    try:
        r = requests.get('http://localhost:4040/api/tunnels', timeout=2)
        if r.status_code == 200:
            data = r.json()
            tunnels = data.get('tunnels', [])
            for t in tunnels:
                if t.get('proto') == 'https':
                    return t.get('public_url')
    except Exception:
        pass
    return None

@_app.route('/status')
def api_status():
    with _cola_lock:
        cola_info = [{'titulo': t['titulo'], 'artista': t['artista'], 'auto': t.get('auto', False)} for t in _cola]
        actual = _cola[_indice_cola]['titulo'] if 0 <= _indice_cola < len(_cola) else None
    return jsonify({
        'modo_musica': _modo_musica,
        'autoplay':    _autoplay,
        'aleatorio':   _modo_aleatorio,
        'cola':        cola_info,
        'indice':      _indice_cola,
        'actual':      actual,
        'total':       len(cola_info),
        'mic_timer':   _tiempo_espera_mic,
        'ips':         _obtener_ips_locales(),
        'puerto':      8890,
        'ngrok_url':   _obtener_url_ngrok(),
        'esp32_ip':    ESP32_IP
    })

@_app.route('/config/esp32_ip', methods=['POST'])
def api_set_esp32_ip():
    global ESP32_IP
    data = flask_request.get_json(silent=True) or {}
    nueva_ip = data.get('ip', '').strip()
    if nueva_ip:
        # Asegurar protocolo http:// si no tiene
        if not nueva_ip.startswith('http://') and not nueva_ip.startswith('https://'):
            nueva_ip = f"http://{nueva_ip}"
        ESP32_IP = nueva_ip
        print(f"[Ojos] 🌐 IP del ESP32 configurada manualmente a: {ESP32_IP}")
        # Intentar validación de conexión
        try:
            ip_limpia = ESP32_IP.rstrip('/')
            r = requests.get(f"{ip_limpia}/desactivar", timeout=1.5)
            if r.status_code == 200:
                return jsonify({'ok': True, 'msg': f'✓ IP guardada y conectada: {ESP32_IP}'})
        except Exception as e:
            return jsonify({'ok': True, 'msg': f'✓ Guardada, pero no responde: {e}'})
    return jsonify({'ok': False, 'msg': 'IP inválida'})

@_app.route('/config/mic_timer', methods=['GET', 'POST'])
def api_mic_timer():
    global _tiempo_espera_mic
    if flask_request.method == 'POST':
        data = flask_request.get_json(silent=True) or {}
        try:
            val = float(data.get('segundos', 6.0))
            _tiempo_espera_mic = max(0.0, min(30.0, val))
            print(f'[Config] Timer de micrófono configurado a {_tiempo_espera_mic} segundos.')
            return jsonify({'ok': True, 'segundos': _tiempo_espera_mic, 'msg': f'Timer fijado a {_tiempo_espera_mic}s.'})
        except Exception as e:
            return jsonify({'ok': False, 'msg': f'Error: {e}'}), 400
    return jsonify({'ok': True, 'segundos': _tiempo_espera_mic})

@_app.route('/music/pause',   methods=['POST'])
def api_pause():
    _parar_cancion_actual()
    global _modo_musica
    _modo_musica = False
    return jsonify({'ok': True})

@_app.route('/music/stop',    methods=['POST'])
def api_stop():
    global _modo_musica, _cola, _indice_cola, _stop_cola
    _stop_cola   = True   # le dice al hilo que pare
    _parar_cancion_actual()
    _modo_musica = False
    _cola        = []
    _indice_cola = -1
    # resetear el flag despues de un momento para no bloquear reproducciones futuras
    def _reset_stop():
        global _stop_cola
        time.sleep(1.0)
        _stop_cola = False
    threading.Thread(target=_reset_stop, daemon=True).start()
    return jsonify({'ok': True, 'msg': 'Todo parado y cola limpiada.'})

@_app.route('/music/next',    methods=['POST'])
def api_next():
    return jsonify({'ok': True, 'msg': siguiente_cancion()})

@_app.route('/music/prev',    methods=['POST'])
def api_prev():
    return jsonify({'ok': True, 'msg': cancion_anterior()})

@_app.route('/music/reinicio', methods=['POST'])
def api_reinicio():
    return jsonify({'ok': True, 'msg': reiniciar_cancion_actual()})

@_app.route('/music/play',    methods=['POST'])
def api_play():
    global _modo_musica
    _parar_hablar()
    data  = flask_request.get_json(silent=True) or {}
    query = data.get('query', '')
    if not query:
        return jsonify({'ok': False, 'msg': 'Falta query'}), 400
    msg, titulo = reproducir_cancion(query)
    if not titulo:
        _modo_musica = False
    else:
        _modo_musica = True
    return jsonify({'ok': bool(titulo), 'msg': msg})

@_app.route('/music/suggestions', methods=['GET'])
def api_suggestions():
    q = flask_request.args.get('q', '').strip()
    if not q:
        return jsonify({'suggestions': []})
    try:
        url = f"https://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={requests.utils.quote(q)}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r = requests.get(url, headers=headers, timeout=3)
        if r.status_code == 200:
            data = r.json()
            if len(data) >= 2 and isinstance(data[1], list):
                return jsonify({'suggestions': data[1][:7]})
    except Exception as e:
        print(f"[Error Suggestions] {e}")
    return jsonify({'suggestions': []})



@_app.route('/music/like', methods=['POST'])
def api_like():
    msg = dar_like_cancion_actual()
    return jsonify({'ok': True, 'msg': msg})

@_app.route('/music/agregar', methods=['POST'])
def api_agregar():
    data  = flask_request.get_json(silent=True) or {}
    query = data.get('query', '')
    if not query:
        return jsonify({'ok': False, 'msg': 'Falta query'}), 400
    return jsonify({'ok': True, 'msg': agregar_a_cola(query)})

# ── ENDPOINTS DE PLAYLISTS Y LIKES ──────────
@_app.route('/playlists', methods=['GET'])
def api_get_playlists():
    return jsonify(cargar_playlists_json())

@_app.route('/playlists/create', methods=['POST'])
def api_create_playlist():
    data = flask_request.get_json(silent=True) or {}
    nombre = data.get('nombre', '').strip()
    if not nombre:
        return jsonify({'ok': False, 'msg': 'Falta el nombre'}), 400
    p_data = cargar_playlists_json()
    if 'playlists' not in p_data:
        p_data['playlists'] = {}
    if nombre in p_data['playlists']:
        return jsonify({'ok': False, 'msg': 'Ya existe esa playlist'}), 400
    p_data['playlists'][nombre] = []
    guardar_playlists_json(p_data)
    return jsonify({'ok': True, 'msg': f'Playlist "{nombre}" creada.'})

@_app.route('/playlists/add', methods=['POST'])
def api_add_to_playlist():
    data = flask_request.get_json(silent=True) or {}
    target = data.get('playlist', 'mis_likes')
    track = data.get('track', {})
    if not track or not track.get('titulo'):
        return jsonify({'ok': False, 'msg': 'Datos de canción inválidos'}), 400
    p_data = cargar_playlists_json()
    if target == 'mis_likes':
        if 'mis_likes' not in p_data:
            p_data['mis_likes'] = []
        if not any(t.get('titulo') == track.get('titulo') for t in p_data['mis_likes']):
            p_data['mis_likes'].append(track)
            guardar_playlists_json(p_data)
            return jsonify({'ok': True, 'msg': 'Añadida a Mis Likes ❤️'})
        return jsonify({'ok': True, 'msg': 'Ya estaba en Mis Likes ❤️'})
    else:
        if target in p_data.get('playlists', {}):
            if not any(t.get('titulo') == track.get('titulo') for t in p_data['playlists'][target]):
                p_data['playlists'][target].append(track)
                guardar_playlists_json(p_data)
                return jsonify({'ok': True, 'msg': f'Añadida a {target}'})
            return jsonify({'ok': True, 'msg': f'Ya estaba en {target}'})
        return jsonify({'ok': False, 'msg': 'Playlist no encontrada'}), 404

@_app.route('/playlists/delete', methods=['POST'])
def api_delete_playlist():
    data = flask_request.get_json(silent=True) or {}
    nombre = data.get('nombre', '').strip()
    p_data = cargar_playlists_json()
    if nombre in p_data.get('playlists', {}):
        del p_data['playlists'][nombre]
        guardar_playlists_json(p_data)
        return jsonify({'ok': True, 'msg': f'Playlist "{nombre}" eliminada.'})
    return jsonify({'ok': False, 'msg': 'No existe esa playlist'}), 404

@_app.route('/playlists/remove_track', methods=['POST'])
def api_remove_track_from_playlist():
    data = flask_request.get_json(silent=True) or {}
    target = data.get('playlist', 'mis_likes')
    index = data.get('index', None)
    titulo = data.get('titulo', '')
    
    p_data = cargar_playlists_json()
    lista = p_data.get('mis_likes', []) if target == 'mis_likes' else p_data.get('playlists', {}).get(target, [])
    
    if index is not None and isinstance(index, int) and 0 <= index < len(lista):
        lista.pop(index)
        guardar_playlists_json(p_data)
        return jsonify({'ok': True, 'msg': 'Canción eliminada de la playlist.'})
    elif titulo:
        nueva_lista = [t for t in lista if t.get('titulo') != titulo]
        if target == 'mis_likes':
            p_data['mis_likes'] = nueva_lista
        elif target in p_data.get('playlists', {}):
            p_data['playlists'][target] = nueva_lista
        guardar_playlists_json(p_data)
        return jsonify({'ok': True, 'msg': 'Canción eliminada de la playlist.'})
        
    return jsonify({'ok': False, 'msg': 'No se pudo eliminar la canción'}), 400

@_app.route('/playlists/play', methods=['POST'])
def api_play_playlist():
    data = flask_request.get_json(silent=True) or {}
    nombre = data.get('playlist', 'mis_likes')
    msg, titulo = reproducir_playlist_por_nombre(nombre)
    return jsonify({'ok': bool(titulo), 'msg': msg})

@_app.route('/music/limpiar', methods=['POST'])
def api_limpiar():
    limpiar_cola()
    return jsonify({'ok': True, 'msg': 'Música detenida y cola vaciada.'})

@_app.route('/music/mezclar', methods=['POST'])
def api_mezclar():
    return jsonify({'ok': mezclar_cola()})

@_app.route('/music/autoplay', methods=['POST'])
def api_autoplay():
    global _autoplay
    data = flask_request.get_json(silent=True) or {}
    _autoplay = bool(data.get('activo', not _autoplay))
    return jsonify({'ok': True, 'autoplay': _autoplay})

@_app.route('/music/aleatorio', methods=['POST'])
def api_aleatorio():
    global _modo_aleatorio
    data = flask_request.get_json(silent=True) or {}
    _modo_aleatorio = bool(data.get('activo', not _modo_aleatorio))
    if _modo_aleatorio:
        mezclar_cola()
        msg = 'Modo aleatorio activado'
    else:
        msg = 'Modo aleatorio desactivado'
    return jsonify({'ok': True, 'aleatorio': _modo_aleatorio, 'msg': msg})

@_app.route('/volumen/subir',  methods=['POST'])
def api_vol_subir():
    nuevo = cambiar_volumen_tableta(subir=True)
    if nuevo is None:
        nuevo = cambiar_volumen(subir=True)
    return jsonify({'ok': True, 'volumen': nuevo})

@_app.route('/volumen/bajar',  methods=['POST'])
def api_vol_bajar():
    nuevo = cambiar_volumen_tableta(subir=False)
    if nuevo is None:
        nuevo = cambiar_volumen(subir=False)
    return jsonify({'ok': True, 'volumen': nuevo})

@_app.route('/volumen/set',    methods=['POST'])
def api_vol_set():
    data  = flask_request.get_json(silent=True) or {}
    nivel = int(data.get('nivel', 50))
    ok    = set_volumen_tableta(nivel)
    if not ok:
        ok = _set_volumen_exacto(nivel)
    return jsonify({'ok': ok, 'volumen': nivel})

@_app.route('/ojos/<comando>', methods=['POST'])
def api_ojos(comando):
    cmd_ojos(comando)
    return jsonify({'ok': True})

# ─────────────────────────────────────────────
#  ENDPOINTS DE VISION (ESP32-CAM)
# ─────────────────────────────────────────────
@_app.route('/vision/foto', methods=['POST'])
def api_vision_foto():
    """Toma una foto y la devuelve como base64 + la guarda en disco."""
    img_b64 = _obtener_foto_esp32()
    if not img_b64:
        return jsonify({'ok': False, 'msg': 'No se pudo obtener foto del ESP32'}), 503
    ruta = _guardar_foto(base64.b64decode(img_b64))
    return jsonify({'ok': True, 'imagen': img_b64, 'ruta': ruta})

@_app.route('/vision/ver', methods=['POST'])
def api_vision_ver():
    """Toma una foto, la analiza con Ollama y devuelve la descripción."""
    data     = flask_request.get_json(silent=True) or {}
    pregunta = data.get('pregunta', None)
    respuesta = ejecutar_vision('ver', pregunta)
    return jsonify({'ok': True, 'descripcion': respuesta})

@_app.route('/vision/foto_telegram', methods=['POST'])
def api_vision_foto_telegram():
    """Captura foto del ESP32-CAM, la envía a Telegram y devuelve la descripción de Don Mario."""
    def _run():
        return comando_manual_toma_foto()
    # Ejecutar en hilo separado para no bloquear el servidor
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(_run)
        try:
            descripcion = future.result(timeout=90)
        except Exception as e:
            descripcion = f'Error al tomar foto: {e}'
    return jsonify({'ok': True, 'descripcion': descripcion})

@_app.route('/vision/stream_url', methods=['GET'])
def api_vision_stream_url():
    """Devuelve la URL del stream de video del ESP32-CAM."""
    # El ESP32-CAM expone /stream en el puerto 9001
    cam_base = ESP32_CAM_FOTO.replace('/foto', '')
    stream_url = cam_base.replace(':9001', ':9001') + '/stream'
    return jsonify({'ok': True, 'url': stream_url, 'cam_url': cam_base})

@_app.route('/')
def panel():
    index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "index.html no encontrado", 404

def _iniciar_servidor_http():
    _app.run(host='0.0.0.0', port=8890, debug=False, use_reloader=False)

def _iniciar_ngrok_automatico():
    # 1. Verificar si ya hay un ngrok local activo
    try:
        r = requests.get('http://localhost:4040/api/tunnels', timeout=1.5)
        if r.status_code == 200:
            data = r.json()
            tunnels = data.get('tunnels', [])
            if tunnels:
                print("[ngrok] Se detectó una instancia de ngrok ya activa. Usando túnel existente.")
                return
    except Exception:
        pass

    try:
        try:
            from pyngrok import ngrok
        except ImportError:
            print("[ngrok] Dependencia 'pyngrok' no encontrada. Instalando automáticamente...")
            import subprocess
            import sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyngrok"])
            from pyngrok import ngrok
            print("[ngrok] Dependencia 'pyngrok' instalada correctamente.")

        ngrok.set_auth_token(NGROK_AUTHTOKEN)
        try:
            # Intentar conectar con el dominio reservado
            tunnel = ngrok.connect(8890, bind_tls=True, domain="darkish-elsewhere-unheated.ngrok-free.dev")
            print(f"[ngrok] Túnel activo con dominio reservado: {tunnel.public_url}")
        except Exception as e:
            err_msg = str(e)
            if "already online" in err_msg or "ERR_NGROK_334" in err_msg:
                print("[ngrok] El dominio reservado ya está en línea en otra sesión. El panel utilizará ese túnel activo.")
            else:
                print(f"[ngrok] No se pudo usar el dominio reservado. Intentando túnel dinámico...")
                try:
                    tunnel = ngrok.connect(8890, bind_tls=True)
                    print(f"[ngrok] Túnel dinámico activo: {tunnel.public_url}")
                except Exception as ex:
                    print(f"[ngrok] No se pudo iniciar el túnel dinámico: {ex}")
    except Exception as e:
        print(f"[ngrok] Error al iniciar pyngrok de forma automática: {e}")


def _obtener_ips_locales():
    import socket
    ips = []
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith('127.'):
                ips.append(ip)
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        main_ip = s.getsockname()[0]
        s.close()
        if main_ip not in ips:
            ips.append(main_ip)
    except Exception:
        pass
    return list(set(ips))


def main():
    global rec, mic, _conversando, esperando_nombre, _tts_engine, _modo_aleatorio
    rec = sr.Recognizer()
    rec.dynamic_energy_threshold  = True
    rec.energy_threshold          = 300
    rec.pause_threshold           = 2.5
    rec.non_speaking_duration     = 0.6

    # 1. Iniciar servidor HTTP primero para asegurar disponibilidad web
    ips = _obtener_ips_locales()
    ips_str = " o ".join([f"http://{ip}:8890" for ip in ips]) if ips else "http://localhost:8890"
    print(f'[Mario] Panel HTTP corriendo en http://localhost:8890 y para Celulares/Red en: {ips_str}')
    threading.Thread(target=_iniciar_servidor_http, daemon=True).start()
    threading.Thread(target=_iniciar_ngrok_automatico, daemon=True).start()
    
    # Auto-descubrimiento de los ojos en segundo plano (desactivado a petición del usuario para mantener la IP estática fija)
    # threading.Thread(target=_buscar_esp32_ojos, daemon=True).start()

    try:
        keyboard.add_hotkey('v', _toggle_tts_engine)
        print('[Mario] Tecla "V" configurada para alternar entre voz Cartesia y Edge TTS.')
    except Exception as e:
        print(f'[Keyboard Error] {e}')

    mic = None
    try:
        print('[Mario] Detectando dispositivos de micrófono disponibles...')
        dispositivos = sr.Microphone.list_microphone_names()
        detected_index = None
        for idx, name in enumerate(dispositivos):
            print(f'  [{idx}] {name}')
            if 'wo mic' in name.lower() or 'womic' in name.lower():
                detected_index = idx

        target_index = MIC_INDEX
        if detected_index is not None:
            print(f'[Mario] ¡WO Mic detectado automáticamente en el índice {detected_index}! Usándolo...')
            target_index = detected_index
        else:
            print(f'[Mario] Usando índice de micrófono configurado: {target_index}')

        print('[Mario] Calibrando micrófono...')
        mic = sr.Microphone(device_index=target_index)
        with mic as source:
            rec.adjust_for_ambient_noise(source, duration=2)
        print('[Mario] Listo. Di mario, don mario o señor mario para activar.')
    except Exception as e:
        print(f'[Mic Error] Falló inicialización con índice: {e}. Intentando micrófono por defecto...')
        try:
            mic = sr.Microphone()
            with mic as source:
                rec.adjust_for_ambient_noise(source, duration=2)
            print('[Mario] Micrófono por defecto activado.')
        except Exception as err:
            print(f'[Mic Error General] {err}')
            mic = None

    print('[Mario] Musica: YouTube con cola de reproduccion continua + Autoplay.')
    print('[Mario] Comandos rapidos: hora | sube/baja volumen | volumen a N | timer | alarma')

    threading.Thread(target=loop_vision_continua, daemon=True).start()

    cmd_ojos('desactivar')
    _tts_engine = 'edge'
    hablar(
        'Mario versión dieciséis, iniciando, maldita sea. '
        'He guardado mis memorias en el disco duro porque ya no me acuerdo de nada, y no quiero que me estén molestando con preguntas tontas, chamaco mugroso. '
        'Desactivé la detección esa de desconocidos por telemetría porque qué flojera. '
        'Sube el volumen si es necesario. '
        'Ahora tengo reproducción automática como las teles modernas, '
        'así que cuando se acabe la cola pongo más música de la vieja escuela yo solito. '
        'Di mario, don mario o señor mario cuando quieras hablar, pero que sea rápido.'
    )
    if len(_cartesia_keys_agotadas) < len(CARTESIA_KEYS):
        _tts_engine = 'cartesia'
        _tts_preferred_engine = 'cartesia'
        print('[TTS Engine] Bienvenida finalizada -> Cambiado automáticamente a voz Cartesia AI.')
    else:
        _tts_engine = 'edge'
        _tts_preferred_engine = 'edge'
        print('[TTS Engine] Bienvenida finalizada -> Mantenido en voz Edge TTS por falta de créditos en Cartesia.')

    try:
      while True:
        if _modo_musica:
            print('[Mario] Modo música detectado en espera. Entrando a loop de música.')
            cmd_ojos('activar')
            loop_modo_musica(rec, mic)
            continue

        texto = escuchar(rec, mic, frase=5, pause_threshold=1.0, evitar_eco=False)
        if not texto:
            continue

        if _modo_musica:
            print('[Mario] Modo música detectado en espera. Entrando a loop de música.')
            cmd_ojos('activar')
            loop_modo_musica(rec, mic)
            continue
        print(f'[Wake] escuche: {texto}')

        accion_rapida, param_rapido = detectar_comando_rapido(texto)
        if accion_rapida:
            ejecutar_comando_rapido(accion_rapida, param_rapido)
            continue

        accion_ta, param_ta = detectar_timer_alarma(texto)
        if accion_ta:
            hablar(ejecutar_timer_alarma(accion_ta, param_ta))
            continue

        if any(w in texto for w in WAKE_WORDS):
            print('[Mario] Activado!')
            cmd_ojos('activar')
            hablar('Dime')

            conversando = True
            _conversando = True   # Notifica al hilo de visión que hay sesión activa
            _no_entendi_count = 0
            while conversando:
                if _modo_musica:
                    print('[Mario] Modo música activado externamente. Cambiando a loop de música.')
                    cmd_ojos('activar')
                    loop_modo_musica(rec, mic)
                    break

                comando = escuchar(rec, mic, timeout=12, frase=20, pause_threshold=2.5)

                if _modo_musica:
                    print('[Mario] Modo música activado externamente. Cambiando a loop de música.')
                    cmd_ojos('activar')
                    loop_modo_musica(rec, mic)
                    break

                if not comando:
                    _no_entendi_count += 1
                    if _no_entendi_count >= 3 and _tts_engine != 'edge':
                        _tts_engine = 'edge'
                        print('[TTS Protección] ⚠️ 3 desentendimientos seguidos. Cambiando motor TTS a Edge.')
                    
                    if _no_entendi_count >= 10:
                        print('[TTS Protección] ⚠️ 10 desentendimientos seguidos. Saliendo de la conversación.')
                        hablar('¡Ya me cansé de esperar! Me voy a tomar mi siesta.')
                        _tts_engine = _tts_preferred_engine
                        conversando = False
                        _conversando = False
                        cmd_ojos('desactivar')
                        break
                    hablar('¿Qué dices? ¡Habla fuerte, que estoy medio sordo y no te entiendo nada!')
                    continue

                _no_entendi_count = 0  # Reiniciar contador al entender comando
                if _tts_engine != _tts_preferred_engine:
                    _tts_engine = _tts_preferred_engine
                    print(f'[TTS Protección] ✅ Comando entendido. Restaurando motor TTS preferido ({_tts_preferred_engine}).')
                print(f'[Comando] {comando}')

                # ── Portero (Gatekeeper) de Estados ─────────────────────────
                if es_despedida(comando):
                    esperando_nombre = False
                    conversando = False
                    _conversando = False
                    respuesta = preguntar(comando)
                    hablar(respuesta)
                    print('[Mario] Fin de conversacion, volviendo a espera.')
                    cmd_ojos('desactivar')
                    threading.Thread(target=ciclo_sueno_onirico, daemon=True).start()
                    break

                if esperando_nombre:
                    if len(comando.split()) < 4:
                        guardar_hecho(f"Persona conocida: {comando}")
                        hablar(f"Ya anoté a ese {comando} en mi libreta vieja para que no se me olvide.")
                    else:
                        hablar("¿Qué clase de nombre raro de extranjero es ese? Es muy largo, no me lo voy a aprender.")
                    esperando_nombre = False
                    continue

                accion_rapida, param_rapido = detectar_comando_rapido(comando)
                if accion_rapida:
                    ejecutar_comando_rapido(accion_rapida, param_rapido)
                    continue

                accion_ta, param_ta = detectar_timer_alarma(comando)
                if accion_ta:
                    hablar(ejecutar_timer_alarma(accion_ta, param_ta))
                    continue

                accion_musica, param_musica = detectar_comando_musica(comando)

                # ── Contexto visual inmediato ────────────
                if any(kw in comando for kw in FRASES_CONTEXTO_VISUAL):
                    def _actualizar_ahora():
                        global _ultima_observacion
                        imagen_b64 = capturar_foto_esp32_b64()
                        if imagen_b64:
                            desc = analizar_imagen_silencioso(imagen_b64)
                            if desc:
                                _ultima_observacion = desc
                                print(f'[Visión] Actualización por contexto visual: {desc}')
                    threading.Thread(target=_actualizar_ahora, daemon=True).start()

                # ── Foto manual (Telegram) ─
                if any(kw in comando for kw in COMANDOS_FOTO_MANUAL):
                    hablar('A ver, no te muevas, chamaco. Quédate quieto que te voy a tomar un retrato.')
                    respuesta = comando_manual_toma_foto()
                    hablar(respuesta)
                    continue

                # ── Visión ──────────────────────────────
                accion_vision, param_vision = detectar_comando_vision(comando)
                if accion_vision:
                    respuesta = ejecutar_vision(accion_vision, param_vision)
                    hablar(respuesta)
                    continue

                # ── Playlists / Mis Likes por Voz ────────────────
                if any(kw in comando for kw in ['reproduce mis likes', 'pon mis likes', 'mis likes', 'mis me gusta', 'reproduce mis me gusta']):
                    solicitado_aleatorio = any(k in comando for k in ['aleatorio', 'aleatoria', 'random', 'shuffle'])
                    if solicitado_aleatorio:
                        _modo_aleatorio = True
                        hablar('Buscando tus canciones favoritas en modo aleatorio en Alex Music.')
                    else:
                        hablar('Buscando tus canciones favoritas en Alex Music.')
                    msg, _ = reproducir_playlist_por_nombre('mis_likes')
                    hablar(msg)
                    loop_modo_musica(rec, mic)
                    continue

                if 'playlist' in comando or 'lista de reproduccion' in comando or 'lista de reproducción' in comando:
                    nombre_p = comando
                    solicitado_aleatorio = any(k in comando for k in ['aleatorio', 'aleatoria', 'random', 'shuffle'])
                    if solicitado_aleatorio:
                        _modo_aleatorio = True
                        for k in ['en modo aleatorio', 'en aleatorio', 'modo aleatorio', 'aleatorio', 'aleatoria', 'random', 'shuffle']:
                            nombre_p = nombre_p.replace(k, '').strip()
                    
                    for kw in ['reproduce mi playlist', 'reproduce la playlist', 'pon mi playlist', 'pon la playlist', 'playlist', 'lista de reproduccion', 'lista de reproducción']:
                        nombre_p = nombre_p.replace(kw, '').strip()
                        
                    if solicitado_aleatorio:
                        hablar(f'Buscando la lista {nombre_p} en modo aleatorio en Alex Music.')
                    else:
                        hablar(f'Buscando la lista {nombre_p} en Alex Music.')
                    msg, titulo_p = reproducir_playlist_por_nombre(nombre_p)
                    hablar(msg)
                    if titulo_p:
                        loop_modo_musica(rec, mic)
                    continue

                if accion_musica == 'cancion':
                    hablar(f'Buscando {param_musica} en Alex Music.')
                    respuesta, titulo = reproducir_cancion(param_musica)
                    hablar(respuesta)
                    if titulo:
                        loop_modo_musica(rec, mic)
                    continue

                elif accion_musica in ('agregar', 'cola', 'limpiar', 'mezclar',
                                       'pause', 'next', 'prev', 'reinicio',
                                       'autoplay_on', 'autoplay_off'):
                    respuesta = ejecutar_comando_musica(accion_musica, param_musica)
                    if respuesta:
                        hablar(respuesta)
                    if accion_musica == 'pause':
                        conversando = False
                        cmd_ojos('desactivar')
                        break
                    continue

                respuesta = preguntar(comando)
                hablar(respuesta)

    except KeyboardInterrupt:
        print('[Mario] Apagando...')
        ciclo_sueno_onirico()  # Bloquea hasta terminar, luego sale

if __name__ == '__main__':
    main()
