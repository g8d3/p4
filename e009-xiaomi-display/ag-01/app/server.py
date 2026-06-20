#!/usr/bin/env python3
import asyncio, base64, json, os, ssl, urllib.request
from aiohttp import web, MultipartReader

BASE_URL = os.environ.get("XIAOMI_BASE_URL", "https://token-plan-sgp.xiaomimimo.com/v1")
API_KEY = os.environ.get("XIAOMI_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

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

async def handle_tts(request):
    body = await request.json()
    text = body.get("text", "")
    voice = body.get("voice", "Mia")
    prompt = body.get("prompt", "")
    if not text:
        return web.json_response({"error": "text is required"}, status=400)
    user_msg = prompt if prompt else f"Di esto: {text}"
    result = await api_call({
        "model": "mimo-v2.5-tts", "messages": [
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": text},
        ], "modalities": ["audio"],
        "audio": {"voice": voice, "format": "wav"},
    })
    if not result["ok"]:
        return web.json_response(result["error"], status=result["status"])
    audio_data = result["data"]["choices"][0]["message"].get("audio", {}).get("data")
    if not audio_data:
        return web.json_response({"error": "no audio in response"}, status=500)
    return web.Response(body=base64.b64decode(audio_data), content_type="audio/wav")

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
    app.router.add_post("/tts", handle_tts)
    app.router.add_post("/asr", handle_asr)
    runner = web.AppRunner(app)
    await runner.setup()

    cert = "/tmp/server.crt"
    key = "/tmp/server.key"

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
