#!/usr/bin/env python3
"""Unified server: VNC web + audio + subtitles on port 8080"""
import asyncio, os
from aiohttp import web, WSMsgType

VNC_HOST = "127.0.0.1"
VNC_PORT = 5901
AUDIO_SINK = "remote-audio.monitor"
SUBTITLES_LOG = os.path.expanduser("~/.local/share/e009-display/subtitles.log")

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
#top{background:rgba(26,26,46,.92);padding:4px 10px;display:flex;align-items:center;gap:6px;flex-shrink:0;z-index:10}
#top h1{font-size:12px;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#top h1 span{font-weight:400;color:#666;font-size:11px}
#indicator{display:flex;align-items:center;gap:4px;font-size:10px;color:#888;flex-shrink:0}
#indicator .dot{width:6px;height:6px;border-radius:50%;background:#555}
#indicator .dot.live{background:#4caf50;animation:pulse 1.5s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
#screen{flex:1;display:flex;align-items:center;justify-content:center;background:#000;position:relative;overflow:hidden;min-height:0}
#screen canvas{max-width:100%;max-height:100%;object-fit:contain}
#subs{position:fixed;bottom:0;left:0;right:0;background:rgba(0,0,0,.75);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);border-top:1px solid rgba(233,69,96,.3);padding:8px 12px;font-size:13px;color:#ddd;white-space:pre-wrap;line-height:1.4;max-height:90px;overflow-y:auto;z-index:20;pointer-events:none}
</style>
</head>
<body>
<div id="top">
<h1>Display Virtual <span>720x1600</span></h1>
<div id="indicator"><span class="dot" id="audioDot"></span><span id="audioLabel">sin audio</span></div>
</div>
<div id="screen"><canvas id="vnc"></canvas></div>
<div id="subs">Esperando...</div>
<audio id="audio" autoplay playsinline style="display:none"><source src="/audio" type="audio/mpeg"></audio>
<script>
if(!crypto.randomUUID){crypto.randomUUID=function(){return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,function(c){var r=Math.random()*16|0,v=c=='x'?r:r&3|8;return v.toString(16)})}}
</script>
<script src="https://cdn.jsdelivr.net/npm/@novnc/novnc@1.5.0/dist/rfb.min.js"></script>
<script>
(function(){
var rfb,st=document.getElementById('subs'),ad=document.getElementById('audioDot'),al=document.getElementById('audioLabel'),au=document.getElementById('audio');
au.addEventListener('play',function(){ad.className='dot live';al.textContent='audio'});
au.addEventListener('pause',function(){ad.className='dot';al.textContent='sin audio'});
async function cn(){try{
rfb=new RFB(document.getElementById('screen'),'ws://'+location.host+'/vnc',{wsProtocols:['binary']});
rfb.scaleViewport=true;rfb.resizeSession=false;
}catch(e){setTimeout(cn,3000)}}
async function sl(){try{
var r=await fetch('/subtitles'),t=await r.text();
st.textContent=t.trim().split('\\n').filter(Boolean).slice(-3).join('\\n');
}catch(e){}setTimeout(sl,2000)}
cn();sl();
})();
</script>
</body></html>"""

async def vnc_proxy(request):
    ws = web.WebSocketResponse(max_msg_size=0)
    await ws.prepare(request)
    try:
        vnc_r, vnc_w = await asyncio.wait_for(
            asyncio.open_connection(VNC_HOST, VNC_PORT), timeout=3)
    except:
        return ws

    async def vnc_to_ws():
        try:
            while True:
                data = await asyncio.wait_for(vnc_r.read(65536), timeout=300)
                if not data:
                    break
                await ws.send_bytes(data)
        except:
            pass

    async def ws_to_vnc():
        try:
            async for msg in ws:
                if msg.type == WSMsgType.BINARY:
                    vnc_w.write(msg.data)
                    await vnc_w.drain()
                elif msg.type == web.WSMsgType.TEXT:
                    pass  # ignore text frames
                elif msg.type == WSMsgType.ERROR or msg.type == WSMsgType.CLOSE:
                    break
        except:
            pass
        finally:
            vnc_w.close()

    await asyncio.gather(vnc_to_ws(), ws_to_vnc())
    return ws

async def audio_stream(request):
    resp = web.StreamResponse(
        status=200, headers={
            "Content-Type": "audio/mpeg",
            "Cache-Control": "no-cache",
            "Connection": "close",
        })
    await resp.prepare(request)
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-re", "-f", "pulse", "-i", AUDIO_SINK,
        "-acodec", "libmp3lame", "-ab", "64k", "-f", "mp3", "-",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    try:
        while True:
            chunk = await asyncio.wait_for(proc.stdout.read(4096), timeout=2)
            if not chunk:
                break
            await resp.write(chunk)
    except (asyncio.TimeoutError, ConnectionResetError, BrokenPipeError):
        pass
    finally:
        proc.kill()
    return resp

async def subtitles(request):
    try:
        with open(SUBTITLES_LOG) as f: text = f.read().strip() or "Esperando..."
    except: text = "Esperando..."
    return web.Response(text=text, content_type="text/plain", charset="utf-8")

async def index(request):
    return web.Response(text=HTML, content_type="text/html", charset="utf-8")

async def start():
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/vnc", vnc_proxy)
    app.router.add_get("/audio", audio_stream)
    app.router.add_get("/subtitles", subtitles)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print(f"Servidor: http://0.0.0.0:8080", flush=True)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(start())
