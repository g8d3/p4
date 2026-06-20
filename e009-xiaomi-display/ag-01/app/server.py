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
    audio_cfg = {"format": fmt}
    if "voicedesign" not in model and "voiceclone" not in model:
        audio_cfg["voice"] = voice
    payload = {
        "model": model, "messages": [
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": text},
        ], "modalities": ["audio"],
        "audio": audio_cfg,
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

# Only these formats are accepted by the Xiaomi ASR API
SUPPORTED_MIME = {"wav": "audio/wav", "mp3": "audio/mpeg", "mpeg": "audio/mpeg"}

async def convert_to_wav(data, ext):
    if len(data) < 500:
        print(f"convert_to_wav: data too small ({len(data)}b), returning empty wav", flush=True)
        # Return a minimal valid WAV (0.1s of silence)
        import struct, io
        buf = io.BytesIO()
        sr = 16000; bits = 16; channels = 1; duration_samples = int(sr * 0.1)
        data_size = duration_samples * channels * (bits // 8)
        buf.write(b'RIFF')
        buf.write(struct.pack('<I', 36 + data_size))
        buf.write(b'WAVE')
        buf.write(b'fmt ')
        buf.write(struct.pack('<I', 16))
        buf.write(struct.pack('<H', 1))
        buf.write(struct.pack('<H', channels))
        buf.write(struct.pack('<I', sr))
        buf.write(struct.pack('<I', sr * channels * (bits // 8)))
        buf.write(struct.pack('<H', channels * (bits // 8)))
        buf.write(struct.pack('<H', bits))
        buf.write(b'data')
        buf.write(struct.pack('<I', data_size))
        buf.write(b'\x00' * data_size)
        return buf.getvalue(), "wav"
    # Use piping through stdin/stdout instead of temp files
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-i", "pipe:0", "-f", "wav", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1", "pipe:1",
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out_data, stderr = await asyncio.wait_for(proc.communicate(data), timeout=20)
        if proc.returncode == 0 and len(out_data) > 100:
            return out_data, "wav"
        err = stderr.decode()[:500] if stderr else ""
        print(f"ffmpeg FAILED ({ext}): rc={proc.returncode} out={len(out_data)} err={err}", flush=True)
        # Save failing data for analysis
        with open(f"/tmp/failed_chunk_{ext}.webm", "wb") as f:
            f.write(data)
    except Exception as e:
        print(f"ffmpeg pipe EXCEPTION ({ext}): {e}", flush=True)
    return data, ext

async def handle_asr(request):
    reader = await request.multipart()
    part = await reader.next()
    if not part:
        return web.json_response({"error": "audio file required"}, status=400)
    data = await part.read()
    ext = (part.filename.rsplit(".", 1)[-1] if part.filename else "webm").lower()
    print(f"ASR received: {ext} {len(data)}b", flush=True)

    # Skip empty/tiny chunks
    if len(data) < 300:
        return web.json_response({"text": ""})

    # Convert unsupported formats to supported ones (wav)
    if ext not in SUPPORTED_MIME:
        data, ext = await convert_to_wav(data, ext)
    if ext not in SUPPORTED_MIME:
        print(f"ASR cannot convert {ext} ({len(data)}b), rejecting", flush=True)
        return web.json_response({"error": f"cannot convert {ext} to supported format"}, status=400)
    mime = SUPPORTED_MIME[ext]
    b64 = base64.b64encode(data).decode()
    data_url = f"data:{mime};base64,{b64}"
    # Validate data URL format
    if not data_url.startswith("data:audio/"):
        print(f"BAD data_url: {data_url[:80]}...", flush=True)
        return web.json_response({"error": f"invalid data_url format for {ext}"}, status=500)
    result = await api_call({
        "model": "mimo-v2.5-asr",
        "messages": [{"role": "user", "content": [
            {"type": "input_audio", "input_audio": {"data": data_url, "format": ext}}
        ]}],
    })
    if not result["ok"]:
        print(f"ASR error: ext={ext} mime={mime}", flush=True)
        return web.json_response(result["error"], status=result["status"])
    return web.json_response({"text": result["data"]["choices"][0]["message"]["content"]})

async def handle_tts_clone(request):
    reader = await request.multipart()
    parts = {}
    filenames = {}
    while True:
        part = await reader.next()
        if not part: break
        parts[part.name] = await part.read()
        if part.filename:
            filenames[part.name] = part.filename
    text = parts.get("text", b"").decode()
    if not text:
        return web.json_response({"error": "text required"}, status=400)
    model = parts.get("model", b"mimo-v2.5-tts-voiceclone").decode()
    fmt = parts.get("format", b"wav").decode()
    prompt = parts.get("prompt", b"").decode()
    sample = parts.get("sample")
    if not sample:
        return web.json_response({"error": "sample audio required"}, status=400)
    # Detect format and convert if needed
    sample_name = filenames.get("sample", "")
    sample_ext = sample_name.rsplit(".", 1)[-1].lower() if sample_name else "wav"
    if sample_ext not in ("wav", "mp3", "mpeg"):
        # Convert via ffmpeg pipe
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-i", "pipe:0", "-f", "wav", "-acodec", "pcm_s16le",
                "-ar", "24000", "-ac", "1", "pipe:1",
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            sample, _ = await asyncio.wait_for(proc.communicate(sample), timeout=15)
            if proc.returncode == 0 and len(sample) > 100:
                sample_ext = "wav"
        except:
            pass
    b64 = base64.b64encode(sample).decode()
    mime = "audio/wav" if sample_ext == "wav" else "audio/mpeg"
    ext = sample_ext
    messages = [{"role": "user", "content": prompt or ""}]
    if not prompt:
        messages = []
    messages.append({"role": "assistant", "content": text})
    payload = {
        "model": model, "messages": messages,
        "modalities": ["audio"],
        "audio": {"format": fmt, "voice": f"data:{mime};base64,{b64}"},
    }
    result = await api_call(payload)
    if not result["ok"]:
        return web.json_response(result["error"], status=result["status"])
    msg = result["data"]["choices"][0]["message"]
    audio_data = msg.get("audio", {}).get("data")
    if not audio_data:
        return web.json_response({"error": "no audio"}, status=500)
    content_type = TTS_FORMATS.get(fmt, "audio/wav")
    return web.Response(body=base64.b64decode(audio_data), content_type=content_type)

async def index(request):
    path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    with open(path) as f:
        return web.Response(text=f.read(), content_type="text/html", charset="utf-8")

async def main():
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/models", handle_models)
    app.router.add_post("/tts", handle_tts)
    app.router.add_post("/tts-clone", handle_tts_clone)
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
