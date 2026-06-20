#!/usr/bin/env python3
import asyncio, base64, json, os, ssl, urllib.request
from aiohttp import web

BASE_URL = os.environ.get("XIAOMI_BASE_URL", "https://token-plan-sgp.xiaomimimo.com/v1")
API_KEY = os.environ.get("XIAOMI_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

TTS_MODELS = ["mimo-v2.5-tts", "mimo-v2-tts", "mimo-v2.5-tts-voiceclone", "mimo-v2.5-tts-voicedesign"]
ASR_MODELS = ["mimo-v2.5-asr", "mimo-v2-omni"]
TTS_FORMATS = {"wav": "audio/wav", "mp3": "audio/mpeg", "pcm": "audio/L16", "pcm16": "audio/L16"}
TTS_VOICES = ["Mia", "Chloe", "Milo", "Dean", "mimo_default", "冰糖", "茉莉", "苏打", "白桃"]
EXAMPLES = [
    # Natural language style control
    {"name": "😊 Alegre", "text": "¡Adivina qué, adivina qué! Acabo de recibir los resultados y aprobé. No solo aprobé, ¡saqué matrícula de honor!", "prompt": "Bright, bouncy, slightly sing-song tone — like you're bursting with good news you can barely hold in. Fast pace, rising pitch at the end."},
    {"name": "😢 Triste", "text": "Después de todos estos años, cuando volví a caminar por esa calle, sentí un vacío en el pecho.", "prompt": "Melancholic, slow pace, with a hint of nostalgia and sadness. Soft voice, occasional sighs."},
    {"name": "😡 Enojado", "text": "¡Eres increíble! ¡Ya estoy harta de tus mentiras constantes! ¡FUERA DE AQUÍ!", "prompt": "Angry and explosive, raising voice progressively, trembling with rage at the end."},
    {"name": "🤫 Susurro", "text": "Oye... ven aquí... tengo un secreto que contarte. Pero tienes que prometer que no se lo dirás a nadie.", "prompt": "Whispering, conspiratorial tone, very close to the microphone like sharing a secret. Slow and deliberate."},
    {"name": "😴 Perezoso", "text": "Déjame dormir cinco minutos más... solo cinco minutos... en serio, es la última vez.", "prompt": "Lazy, groggy, half-asleep tone. Mumbling, slow speech, trailing off at the end."},
    {"name": "📰 Noticiero", "text": "En las últimas horas, el mercado financiero global ha experimentado un crecimiento significativo del tres por ciento, según reportes de las principales bolsas de valores.", "prompt": "Formal news anchor tone, clear and authoritative, neutral Spanish. Steady pace, professional delivery."},
    {"name": "📚 Poema", "text": "La luz que me ilumina, el sol que me abriga, el viento que me guía, la voz que me sigue.", "prompt": "Poetic, slow, with emotional depth. Each line with a slight pause, soft and reflective tone."},

    # Audio tag control (tags embedded in text)
    {"name": "🏷️ Suspiro", "text": "(Sighing)Después de todos estos años, cuando volví a caminar por esa calle, sentí un vacío en el pecho.", "prompt": ""},
    {"name": "🏷️ Perezoso", "text": "(Lazy)Déjame dormir cinco minutos más... solo cinco minutos, en serio, la última vez.", "prompt": ""},
    {"name": "🏷️ Magnético", "text": "(Magnetic)La noche ya está profunda, pero la ciudad todavía respira. Soy el que te acompaña esta noche.", "prompt": ""},
    {"name": "🏷️ Alegre + rápido", "text": "(Happy, fast)¡Hey! ¡Vamos! ¡Que se hace tarde! ¡Todos me están esperando!", "prompt": ""},
    {"name": "🏷️ Norteño", "text": "(Northeastern dialect)¡Ay madre, hace un frío hoy! Ese viento, mija, corta como navaja.", "prompt": ""},
    {"name": "🏷️ Cantones", "text": "(Cantonese)Esto está realmente increíble. Una vez que lo pruebas, no lo olvidas.", "prompt": ""},
    {"name": "🏷️ Asustado", "text": "(Nervous, takes a deep breath) Hoo... Calma, calma. Es solo una entrevista... todo va a salir bien...", "prompt": ""},
    {"name": "🏷️ Temblor + risa", "text": "Si tan solo... (pauses for a moment) si tan solo hubiera persistido un segundo más, ¿habría sido diferente? (forced smile) Bah, ya no hay 'qué hubiera pasado'.", "prompt": ""},

    # Director mode - elaborate character + scene + guidance
    {"name": "🎬 Directora fría", "text": "¿Crees que solo con eso puedes conmoverme? Qué ingenuo. Llevo toda una vida enterrando mis sentimientos.", "prompt": "Role: La actual cabeza de la noble familia Cen. Una mujer fría, calculadora, de voz grave e imponente.\nScene: En las sombras del salón principal, observa a alguien que intentó escapar con ella.\nGuidance: Voz extremadamente lenta, cada palabra pesa. Sin fluctuaciones de tono, pero con una opresión que hiela los huesos. Pausas largas e incómodas entre frases."},

    # Voice design examples (for voicedesign model)
    {"name": "🎨 ASMR femenino", "text": "Hola... respira profundo... siente cómo el aire llena tus pulmones... y suelta muy despacio...", "prompt": "Voz femenina joven, primerísimo plano, estilo ASMR. Se escucha la respiración, trago saliva, labios. Habla muy lento, relajante.", "model": "mimo-v2.5-tts-voicedesign"},
    {"name": "🎨 Anciano narrador", "text": "Érase una vez, en un pueblo muy lejano, un viejo sabio que conocía todos los secretos del bosque.", "prompt": "Un señor mayor, voz lenta y pausada, ligeramente ronca y curtida, como un abuelo contando historias.", "model": "mimo-v2.5-tts-voicedesign"},
    {"name": "🎨 Inglés británico", "text": "Good evening, ladies and gentlemen. Tonight's performance promises to be rather exceptional, if I may say so myself.", "prompt": "British elderly gentleman, posh accent, warm and articulate. Slightly formal but welcoming.", "model": "mimo-v2.5-tts-voicedesign"},

    # English examples
    {"name": "🇺🇸 English excited", "text": "Hey boss — guess what, guess what? I just got the results back and I actually passed! Not just passed, I got a distinction!", "prompt": "Bright, bouncy, slightly sing-song tone. Fast pace, rising pitch at the end."},
    {"name": "🇬🇧 English calm", "text": "Good morning everyone, today we'll be exploring the capabilities of this system. Let's begin with an overview.", "prompt": "Calm, authoritative British English. Measured pace, clear enunciation."},

    # Singing
    {"name": "🎤 Canto", "text": "(singing)Perdona si no supe amarte como debía, si mi orgullo pudo más que mi amor. Pero ahora entiendo que te necesito aquí, a mi lado, mi sol.", "prompt": "Singing melodically, like a pop ballad. Emotional and heartfelt."},
]

async def api_call(data):
    loop = asyncio.get_running_loop()
    def _call():
        req = urllib.request.Request(
            f"{BASE_URL}/chat/completions",
            data=json.dumps(data).encode(), headers=HEADERS)
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            return {"ok": True, "data": json.loads(resp.read())}
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            try: err = json.loads(body)
            except: err = {"message": body}
            return {"ok": False, "status": e.code, "error": err}
    return await loop.run_in_executor(None, _call)

async def handle_models(request):
    return web.json_response({"tts_models": TTS_MODELS, "asr_models": ASR_MODELS,
                              "voices": TTS_VOICES, "formats": list(TTS_FORMATS.keys()),
                              "examples": EXAMPLES})

async def handle_tts(request):
    body = await request.json()
    text = body.get("text", "")
    voice = body.get("voice", "Mia")
    model = body.get("model", "mimo-v2.5-tts")
    fmt = body.get("format", "wav")
    prompt = body.get("prompt", "")
    if not text:
        return web.json_response({"error": "text is required"}, status=400)
    user_msg = prompt if prompt else f"Di esto: {text}"
    result = await api_call({
        "model": model, "messages": [
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": text},
        ], "modalities": ["audio"],
        "audio": {"voice": voice, "format": fmt},
    })
    if not result["ok"]:
        return web.json_response(result["error"], status=result["status"])
    msg = result["data"]["choices"][0]["message"]
    audio_data = msg.get("audio", {}).get("data")
    if not audio_data:
        return web.json_response({"error": "no audio in response"}, status=500)
    content_type = TTS_FORMATS.get(fmt, "audio/wav")
    return web.Response(body=base64.b64decode(audio_data), content_type=content_type)

async def handle_asr(request):
    reader = await request.multipart()
    part = await reader.next()
    if not part:
        return web.json_response({"error": "audio file required"}, status=400)
    data = await part.read()
    b64 = base64.b64encode(data).decode()
    ext = (part.filename.rsplit(".", 1)[-1] if part.filename else "webm").lower()
    if ext not in ("wav","mp3","webm","ogg","opus","aac","flac"): ext = "wav"
    result = await api_call({
        "model": "mimo-v2.5-asr",
        "messages": [{"role": "user", "content": [
            {"type": "input_audio", "input_audio": {"data": f"data:audio/{ext};base64,{b64}", "format": ext}}
        ]}],
    })
    if not result["ok"]:
        return web.json_response(result["error"], status=result["status"])
    return web.json_response({"text": result["data"]["choices"][0]["message"]["content"]})

async def index(request):
    path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    with open(path) as f:
        return web.Response(text=f.read(), content_type="text/html", charset="utf-8")

async def main():
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/models", handle_models)
    app.router.add_post("/tts", handle_tts)
    app.router.add_post("/asr", handle_asr)
    runner = web.AppRunner(app)
    await runner.setup()
    cert, key = "/tmp/server.crt", "/tmp/server.key"
    if os.path.exists(cert) and os.path.exists(key):
        ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ctx.load_cert_chain(cert, key)
        site = web.TCPSite(runner, "0.0.0.0", 8081, ssl_context=ctx)
        await site.start()
        print("Xiaomi API app: https://0.0.0.0:8081", flush=True)
    else:
        site = web.TCPSite(runner, "0.0.0.0", 8081)
        await site.start()
        print("Xiaomi API app: http://0.0.0.0:8081", flush=True)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
