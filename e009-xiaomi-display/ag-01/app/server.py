#!/usr/bin/env python3
import asyncio, base64, json, os, ssl, subprocess, tempfile, urllib.request
from aiohttp import web

BASE_URL = os.environ.get("XIAOMI_BASE_URL", "https://token-plan-sgp.xiaomimimo.com/v1")
API_KEY = os.environ.get("XIAOMI_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

TTS_MODELS = ["mimo-v2.5-tts", "mimo-v2-tts", "mimo-v2.5-tts-voiceclone", "mimo-v2.5-tts-voicedesign"]
ASR_MODELS = ["mimo-v2.5-asr", "mimo-v2-omni"]
TTS_FORMATS = {"wav": "audio/wav", "mp3": "audio/mpeg", "pcm": "audio/L16", "pcm16": "audio/L16"}
TTS_VOICES = ["Mia", "Chloe", "Milo", "Dean", "mimo_default", "冰糖", "茉莉", "苏打", "白桃"]
EXAMPLES = [
    # Natural language style control (English)
    {"name": "😊 Happy news", "text": "Hey boss — guess what, guess what? I just got the results back and I actually passed! Not just passed, I got a distinction!", "prompt": "Bright, bouncy, slightly sing-song tone — like you're bursting with good news you can barely hold in. Fast pace, rising pitch at the end."},
    {"name": "😢 Melancholic", "text": "After all these years, when I walked down that street again, a part of my heart suddenly felt empty.", "prompt": "Melancholic, slow pace, with a hint of nostalgia and sadness. Soft voice, occasional sighs."},
    {"name": "😡 Angry", "text": "You are UN-BE-LIEVABLE! I am sooooo done with your constant lies. GET. OUT!", "prompt": "Angry and explosive, raising voice progressively, trembling with rage at the end."},
    {"name": "🤫 Whisper", "text": "Hey... come here... I have a secret to tell you. But you have to promise not to tell anyone.", "prompt": "Whispering, conspiratorial tone, very close to the microphone like sharing a secret. Slow and deliberate."},
    {"name": "😴 Lazy", "text": "Let me sleep for five more minutes... just five minutes... really, this is the last time.", "prompt": "Lazy, groggy, half-asleep tone. Mumbling, slow speech, trailing off at the end."},
    {"name": "📰 News anchor", "text": "Good evening. The Federal Reserve announced today a quarter-point rate cut, the first in over four years, citing cooling inflation.", "prompt": "Formal news anchor tone, clear and authoritative. Steady pace, professional delivery."},
    {"name": "📚 Poetic", "text": "The light that guides me, the sun that warms me, the wind that carries me, the voice that follows me.", "prompt": "Poetic, slow, with emotional depth. Each line with a slight pause, soft and reflective tone."},
    {"name": "🇬🇧 British calm", "text": "Good morning everyone, today we'll be exploring the capabilities of this system. Let's begin with an overview.", "prompt": "Calm, authoritative British English. Measured pace, clear enunciation."},

    # Audio tag control (tags embedded in text)
    {"name": "🏷️ Sighing", "text": "(Sighing)After all these years, when I walked down that street again, a part of my heart suddenly felt empty.", "prompt": ""},
    {"name": "🏷️ Lazy", "text": "(Lazy)Let me sleep for five more minutes... just five minutes, really, for the last time.", "prompt": ""},
    {"name": "🏷️ Magnetic", "text": "(Magnetic)The night is already deep, but the city is still breathing. I'm the one accompanying you tonight.", "prompt": ""},
    {"name": "🏷️ Happy + fast", "text": "(Happy, fast)Hey! Come on! We're going to be late! Everyone is waiting for me!", "prompt": ""},
    {"name": "🏷️ Nervous", "text": "(Nervous, takes a deep breath) Hoo... Calm down, calm down. It's just an interview... Everything will be fine...", "prompt": ""},
    {"name": "🏷️ Trembling + smile", "text": "If I had... (pauses for a moment) even for one more second... would it have been different? (forced smile) Ah, no use wondering now.", "prompt": ""},

    # Director mode
    {"name": "🎬 Cold director", "text": "Do you think that's enough to move me? How naive. I've spent my whole life burying my feelings.", "prompt": "Role: The cold, calculating head of a noble family. Deep, imposing voice.\nScene: In the shadows of the main hall, watching someone who tried to escape.\nGuidance: Extremely slow, every word carries weight. No pitch fluctuation, but bone-chilling oppression."},

    # Voice design (for voicedesign model)
    {"name": "🎨 ASMR female", "text": "Hello... take a deep breath... feel the air filling your lungs... and release it very slowly...", "prompt": "Young female, extreme close-up with a binaural, ear-to-ear ASMR feel. Audible breathing, subtle swallowing. She speaks very slowly, deeply relaxing.", "model": "mimo-v2.5-tts-voicedesign"},
    {"name": "🎨 Old narrator", "text": "Once upon a time, in a village far away, there lived a wise old man who knew all the secrets of the forest.", "prompt": "Elderly gentleman, slow and steady, slightly hoarse and weathered voice, like a grandfather telling stories.", "model": "mimo-v2.5-tts-voicedesign"},
    {"name": "🎨 British gent", "text": "Good evening, ladies and gentlemen. Tonight's performance promises to be rather exceptional, if I may say so myself.", "prompt": "British elderly gentleman, posh accent, warm and articulate. Slightly formal but welcoming.", "model": "mimo-v2.5-tts-voicedesign"},
    {"name": "🎨 Russian accent", "text": "Comrades, the plan is simple. We go in, we take what is ours, and we leave before they even know we were there.", "prompt": "Heavy Russian accent, gruff middle-aged male, blunt and matter-of-fact.", "model": "mimo-v2.5-tts-voicedesign"},

    # Singing
    {"name": "🎤 Singing", "text": "(singing)I had the time of my life, and I never felt this way before. Yes I swear, it's the truth, and I owe it all to you.", "prompt": "Singing melodically, like a pop ballad. Emotional and heartfelt."},

    # Chinese
    {"name": "🇨🇳 Happy (CN)", "text": "(Happy)今天真是一个好日子！阳光明媚，万里无云，心情特别好！", "prompt": ""},
    {"name": "🇨🇳 Sad (CN)", "text": "(Sighing)这么多年过去了，当我再次走过那条街，心里突然空了一块。", "prompt": ""},
    {"name": "🇨🇳 Northeast (CN)", "text": "(Northeastern dialect)哎呀妈呀，今天也太冷了吧！这风呼呼的，跟刀子似的！", "prompt": ""},
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
    user_msg = prompt if prompt else f"Say this: {text}"
    payload = {
        "model": model, "messages": [
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": text},
        ], "modalities": ["audio"],
        "audio": {"voice": voice, "format": fmt},
    }
    if body.get("dry_run"):
        return web.json_response(payload)
    result = await api_call(payload)
    if not result["ok"]:
        return web.json_response(result["error"], status=result["status"])
    msg = result["data"]["choices"][0]["message"]
    audio_data = msg.get("audio", {}).get("data")
    if not audio_data:
        return web.json_response({"error": "no audio in response"}, status=500)
    content_type = TTS_FORMATS.get(fmt, "audio/wav")
    return web.Response(body=base64.b64decode(audio_data), content_type=content_type)

SUPPORTED_ASR_FORMATS = {"wav", "mp3", "mpeg"}

async def handle_asr(request):
    reader = await request.multipart()
    part = await reader.next()
    if not part:
        return web.json_response({"error": "audio file required"}, status=400)
    data = await part.read()
    ext = (part.filename.rsplit(".", 1)[-1] if part.filename else "webm").lower()
    # Convert unsupported formats to wav via ffmpeg
    if ext not in SUPPORTED_ASR_FORMATS:
        inp = tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False)
        inp.write(data); inp.close()
        out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        out.close()
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y", "-i", inp.name, "-acodec", "pcm_s16le",
                "-ar", "16000", "-ac", "1", out.name,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            await asyncio.wait_for(proc.wait(), timeout=10)
            with open(out.name, "rb") as f:
                data = f.read()
            ext = "wav"
        except:
            pass
        finally:
            os.unlink(inp.name)
            os.unlink(out.name)
    b64 = base64.b64encode(data).decode()
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
