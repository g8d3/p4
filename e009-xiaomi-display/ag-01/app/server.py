#!/usr/bin/env python3
import asyncio, base64, json, os, urllib.request
from aiohttp import web, MultipartReader

BASE_URL = os.environ.get("XIAOMI_BASE_URL", "https://token-plan-sgp.xiaomimimo.com/v1")
API_KEY = os.environ.get("XIAOMI_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

async def api_call(data):
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(data).encode(),
        headers=HEADERS,
    )
    resp = await asyncio.get_event_loop().run_in_executor(
        None, lambda: urllib.request.urlopen(req, timeout=30)
    )
    return json.loads(resp.read())

async def handle_tts(request):
    body = await request.json()
    text = body.get("text", "")
    voice = body.get("voice", "Mia")
    prompt = body.get("prompt", "")
    if not text:
        return web.Response(status=400, text="text is required")
    user_msg = prompt if prompt else f"Di esto: {text}"
    messages = [
        {"role": "user", "content": user_msg},
        {"role": "assistant", "content": text},
    ]
    result = await api_call({
        "model": "mimo-v2.5-tts",
        "messages": messages,
        "modalities": ["audio"],
        "audio": {"voice": voice, "format": "wav"},
    })
    audio_data = result["choices"][0]["message"].get("audio", {}).get("data")
    if not audio_data:
        return web.Response(status=500, text="no audio in response")
    audio_bytes = base64.b64decode(audio_data)
    return web.Response(body=audio_bytes, content_type="audio/wav",
                        headers={"Content-Disposition": "inline"})

async def handle_asr(request):
    reader = await request.multipart()
    part = await reader.next()
    if not part:
        return web.Response(status=400, text="audio file required")
    data = await part.read()
    b64 = base64.b64encode(data).decode()
    ext = part.filename.rsplit(".", 1)[-1] if part.filename else "webm"
    data_url = f"data:audio/{ext};base64,{b64}"
    result = await api_call({
        "model": "mimo-v2.5-asr",
        "messages": [{"role": "user", "content": [
            {"type": "input_audio", "input_audio": {"data": data_url, "format": ext}}
        ]}],
    })
    text = result["choices"][0]["message"]["content"]
    return web.json_response({"text": text})

async def index(request):
    path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    with open(path) as f:
        return web.Response(text=f.read(), content_type="text/html", charset="utf-8")

async def main():
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_post("/tts", handle_tts)
    app.router.add_post("/asr", handle_asr)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8081)
    await site.start()
    print("Xiaomi API app: http://0.0.0.0:8081", flush=True)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
