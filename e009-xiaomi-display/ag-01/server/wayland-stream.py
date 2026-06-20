#!/usr/bin/env python3
"""Stream a Wayland output via MJPEG over HTTP. One URL."""
import asyncio, subprocess, os, signal
from aiohttp import web

OUTPUT = os.environ.get("STREAM_OUTPUT", "HEADLESS-1")
FPS = int(os.environ.get("STREAM_FPS", "10"))

# Pool of JPEG bytes, updated by a background capture loop
latest_frame = None

async def capture_loop():
    global latest_frame
    while True:
        try:
            proc = await asyncio.create_subprocess_exec(
                "grim", "-o", OUTPUT, "-",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            png_bytes, _ = await asyncio.wait_for(proc.communicate(), timeout=3)
            if proc.returncode == 0 and len(png_bytes) > 100:
                # Convert to JPEG for streaming efficiency
                try:
                    proc2 = await asyncio.create_subprocess_exec(
                        "ffmpeg", "-i", "pipe:0", "-f", "mjpeg", "-q:v", "5", "pipe:1",
                        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.DEVNULL)
                    jpeg_bytes, _ = await asyncio.wait_for(
                        proc2.communicate(png_bytes), timeout=5)
                    if proc2.returncode == 0 and len(jpeg_bytes) > 100:
                        latest_frame = jpeg_bytes
                except:
                    pass
        except:
            pass
        await asyncio.sleep(1.0 / FPS)

async def stream_mjpeg(request):
    resp = web.StreamResponse(
        status=200,
        headers={
            "Content-Type": "multipart/x-mixed-replace; boundary=frame",
            "Cache-Control": "no-cache",
            "Connection": "close",
            "Access-Control-Allow-Origin": "*",
        })
    await resp.prepare(request)
    try:
        while True:
            if latest_frame:
                chunk = b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                chunk += str(len(latest_frame)).encode()
                chunk += b"\r\n\r\n" + latest_frame + b"\r\n"
                await resp.write(chunk)
            await asyncio.sleep(1.0 / FPS)
    except (ConnectionResetError, BrokenPipeError):
        pass
    return resp

async def index(request):
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Display {OUTPUT}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#000;display:flex;align-items:center;justify-content:center;height:100dvh;height:100vh}}
img{{max-width:100%;max-height:100%;object-fit:contain;image-rendering:auto}}
</style>
</head>
<body>
<img src="/stream" alt="Stream">
</body>
</html>"""
    return web.Response(text=html, content_type="text/html", charset="utf-8")

async def main():
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/stream", stream_mjpeg)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8082)
    await site.start()
    print(f"Stream: http://0.0.0.0:8082  (capturing {OUTPUT} @ {FPS}fps)", flush=True)
    await capture_loop()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
