#!/usr/bin/env python3
"""Serves a single HTML page with noVNC + audio. wayvnc runs on 5901 separately."""
import asyncio, os
from aiohttp import web

VNC_WS_PORT = 5901
AUDIO_PATH = "/audio.mp3"  # served by ffmpeg on the same port? We'll proxy it.
HOST_IP = "192.168.0.93"

HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no">
<meta name="mobile-web-app-capable" content="yes">
<title>Display Virtual</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{background:#000;color:#eee;font-family:system-ui,sans-serif;height:100dvh;height:100vh;overflow:hidden;display:flex;flex-direction:column}
#top{background:rgba(26,26,46,.92);padding:4px 10px;display:flex;align-items:center;gap:6px;flex-shrink:0;z-index:10;font-size:12px}
#top h1{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;color:#e94560}
#indicator{display:flex;align-items:center;gap:4px;font-size:10px;color:#888}
.dot{width:6px;height:6px;border-radius:50%;background:#555}
.dot.on{background:#4caf50;animation:pulse 1.5s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
#screen{flex:1;display:flex;align-items:center;justify-content:center;background:#000;position:relative;overflow:hidden;min-height:0}
#screen canvas{max-width:100%;max-height:100%;object-fit:contain}
#subs{position:fixed;bottom:0;left:0;right:0;background:rgba(0,0,0,.75);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);border-top:1px solid rgba(233,69,96,.3);padding:8px 12px;font-size:13px;color:#ddd;white-space:pre-wrap;line-height:1.4;max-height:80px;overflow-y:auto;z-index:20;pointer-events:none}
</style>
</head>
<body>
<div id="top">
<h1>Display HEADLESS-1 <span style="font-weight:400;color:#666">720x1600</span></h1>
<div id="indicator"><span class="dot" id="vncDot"></span><span id="vncLabel">connecting</span></div>
</div>
<div id="screen"><canvas id="vnc"></canvas></div>
<div id="subs">Interactivo: mouse/teclado funcionan</div>
<audio id="audio" autoplay playsinline style="display:none"><source src="/audio" type="audio/mpeg"></audio>
<script src="https://cdn.jsdelivr.net/npm/@novnc/novnc@1.5.0/dist/rfb.min.js"></script>
<script>
(function(){
var rfb, dot=document.getElementById('vncDot'), lab=document.getElementById('vncLabel'), au=document.getElementById('audio');
au.addEventListener('play',function(){});
async function cn(){
try{
rfb=new RFB(document.getElementById('screen'),'ws://HOST_IP:VNC_WS',{wsProtocols:['binary']});
rfb.scaleViewport=true;rfb.resizeSession=false;
rfb.addEventListener('connect',function(){dot.className='dot on';lab.textContent='connected'});
rfb.addEventListener('disconnect',function(e){dot.className='dot';lab.textContent='disconnected: '+e.detail.reason;setTimeout(cn,5000)});
rfb.addEventListener('securityfailure',function(e){lab.textContent='auth fail: '+e.detail.reason;});
}catch(e){lab.textContent='error: '+e.message;setTimeout(cn,5000)}}
cn();
})();
</script>
</body>
</html>
""".replace("HOST_IP", HOST_IP).replace("VNC_WS", str(VNC_WS_PORT))

# Audio proxy: forward /audio to the ffmpeg audio stream
async def audio_proxy(request):
    resp = web.StreamResponse(
        status=200,
        headers={"Content-Type": "audio/mpeg", "Cache-Control": "no-cache", "Connection": "close"})
    await resp.prepare(request)
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-re", "-f", "pulse", "-i", "remote-audio.monitor",
        "-acodec", "libmp3lame", "-ab", "64k", "-f", "mp3", "-",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    try:
        while True:
            chunk = await asyncio.wait_for(proc.stdout.read(4096), timeout=2)
            if not chunk: break
            await resp.write(chunk)
    except: pass
    finally: proc.kill()
    return resp

async def index(request):
    return web.Response(text=HTML, content_type="text/html", charset="utf-8")

async def main():
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/audio", audio_proxy)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8083)
    await site.start()
    print(f"Server: http://0.0.0.0:8083", flush=True)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
