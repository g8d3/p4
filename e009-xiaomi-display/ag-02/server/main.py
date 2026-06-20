import asyncio, os
from aiohttp import web, WSMsgType

SUBTITLE = ""
DISPLAY_NUM = int(os.environ.get("DISPLAY_NUM", "1"))

async def index(request):
    with open("server/static/index.html") as f:
        return web.Response(text=f.read(), content_type="text/html")

async def get_subtitle(request):
    return web.Response(text=SUBTITLE, content_type="text/plain", charset="utf-8")

async def set_subtitle(request):
    global SUBTITLE
    SUBTITLE = (await request.text()).strip()
    return web.Response(text="ok")

async def vnc_ws(request):
    ws = web.WebSocketResponse(max_msg_size=0)
    await ws.prepare(request)
    try:
        r, w = await asyncio.open_connection("localhost", 5900 + DISPLAY_NUM)
    except OSError:
        return ws

    async def relay(src, dst):
        try:
            while True:
                d = await src.read(65536)
                if not d: break
                await dst.send_bytes(d)
        except (ConnectionResetError, asyncio.CancelledError):
            pass

    async def relay_ws():
        try:
            async for m in ws:
                if m.type == WSMsgType.BINARY:
                    w.write(m.data)
                    await w.drain()
                elif m.type == WSMsgType.ERROR: break
        except (ConnectionResetError, asyncio.CancelledError):
            pass
        finally:
            w.close()

    await asyncio.gather(relay(r, ws), relay_ws())
    return ws

async def audio_stream(request):
    resp = web.StreamResponse(headers={
        "Content-Type": "audio/mpeg", "Cache-Control": "no-cache",
    })
    await resp.prepare(request)
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-f", "pulse", "-i", "default", "-f", "mp3", "-",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        while True:
            c = await proc.stdout.read(4096)
            if not c: break
            await resp.write(c)
    except (asyncio.CancelledError, ConnectionResetError):
        proc.kill()

app = web.Application()
app.router.add_static("/novnc", "server/static/novnc", show_index=False)
app.router.add_get("/", index)
app.router.add_get("/subtitle", get_subtitle)
app.router.add_post("/subtitle", set_subtitle)
app.router.add_get("/vnc", vnc_ws)
app.router.add_get("/audio", audio_stream)

if __name__ == "__main__":
    web.run_app(app, port=8080)
