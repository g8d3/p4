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
    {"name": "Saludo formal", "text": "Estimados colegas, les doy la más cordial bienvenida a esta presentación.", "prompt": "Speak in a formal professional tone, neutral Spanish"},
    {"name": "Saludo casual", "text": "¡Qué tal! ¿Cómo va todo? Espero que estén teniendo un excelente día.", "prompt": "Speak casually and friendly, Latin American Spanish"},
    {"name": "Noticia", "text": "En las últimas horas, el mercado financiero ha experimentado un crecimiento significativo del tres por ciento.", "prompt": "Speak like a news anchor, clear and neutral Spanish"},
    {"name": "Poema", "text": "La luz que me ilumina, el sol que me abriga, el viento que me guía, la voz que me sigue.", "prompt": "Speak poetically and slowly, emotional Spanish"},
    {"name": "Instrucción técnica", "text": "Para instalar el paquete, ejecute el comando npm install seguido del nombre del módulo.", "prompt": "Speak clearly and technically, neutral Spanish"},
    {"name": "Acento inglés", "text": "Hello, welcome to this demonstration of the Xiaomi text to speech system.", "prompt": "Speak in natural American English"},
    {"name": "Acento inglés UK", "text": "Good morning everyone, today we're going to explore the capabilities of this API.", "prompt": "Speak in British English"},
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
