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
/* noVNC handles scaling via scaleViewport=true */
#subs{position:fixed;bottom:0;left:0;right:0;background:rgba(0,0,0,.75);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);border-top:1px solid rgba(233,69,96,.3);padding:8px 12px;font-size:13px;color:#ddd;white-space:pre-wrap;line-height:1.4;max-height:80px;overflow-y:auto;z-index:20;pointer-events:none}
</style>
</head>
<body>
<div id="top">
<h1>Display HEADLESS-1 <span style="font-weight:400;color:#666">720x1280</span></h1>
<div id="indicator"><span class="dot" id="vncDot"></span><span id="vncLabel">connecting</span></div>
</div>
<div id="screen"><canvas id="vnc"></canvas></div>
<input id="kbd" autofocus style="position:fixed;top:-100px;left:0;width:1px;height:1px;opacity:0" inputmode="text" autocomplete="off">
<div id="subs">Tap screen to focus, keyboard will appear</div>
<audio id="audio" autoplay playsinline style="display:none"><source src="/audio" type="audio/mpeg"></audio>
<script type="module">
if(!crypto.randomUUID){crypto.randomUUID=function(){return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,function(c){var r=Math.random()*16|0,v=c=='x'?r:r&3|8;return v.toString(16)})}}
import RFB from 'https://cdn.jsdelivr.net/npm/@novnc/novnc@1.7.0/core/rfb.js';
var dot=document.getElementById('vncDot'), lab=document.getElementById('vncLabel'), au=document.getElementById('audio'), kbd=document.getElementById('kbd');
au.addEventListener('play',function(){});
function scaleAll(){
  var c=document.querySelector('#screen div:last-child');
  if(!c)return;
  canv=c.querySelector('canvas');
  if(!canv||canv.width<=300)return;
  var vw=window.innerWidth,vh=window.innerHeight-50;
  var sx=vw/canv.width,sy=vh/canv.height;
  var s=Math.min(sx,sy);
  c.style.transform='scale('+s+')';
  c.style.transformOrigin='top left';
  c.style.width=canv.width+'px';
  c.style.height=canv.height+'px';
  c.style.overflow='hidden';
  c.style.position='absolute';
  c.style.left='0';
  c.style.top='0';
}
// Keyboard forwarding: capture input and send to RFB
function forwardKey(ev){
  if(!rfb)return;
  var key=ev.key;
  if(key==='Unidentified')return;
  ev.preventDefault();
  rfb.sendKey(ev.keyCode, key, true);
  rfb.sendKey(ev.keyCode, key, false);
  kbd.value='';
}
kbd.addEventListener('keydown', forwardKey);
// Auto-focus on connect
var rfb,scaler,canv,canvRect;
// Touchpad: tap=click, drag=move cursor (relative)
var tp={active:false,startX:0,startY:0,startTime:0,curX:360,curY:640};
var sc=document.getElementById('screen');
sc.addEventListener('click',function(){kbd.focus();});
sc.addEventListener('touchstart',function(ev){
  ev.preventDefault();
  var t=ev.changedTouches[0];
  tp.startX=t.clientX; tp.startY=t.clientY; tp.startTime=Date.now();
  tp.active=true;
},{passive:false,capture:true});
sc.addEventListener('touchmove',function(ev){
  ev.preventDefault();
  if(!tp.active||!canv)return;
  var t=ev.changedTouches[0];
  var dx=t.clientX-tp.startX, dy=t.clientY-tp.startY;
  canvRect=canv.getBoundingClientRect();
  var sx=canv.width/canvRect.width, sy=canv.height/canvRect.height;
  tp.curX=Math.max(0,Math.min(canv.width-1,tp.curX+dx*sx*1.5));
  tp.curY=Math.max(0,Math.min(canv.height-1,tp.curY+dy*sy*1.5));
  rfb.sendPointer(Math.round(tp.curX),Math.round(tp.curY),0);
  tp.startX=t.clientX; tp.startY=t.clientY;
},{passive:false,capture:true});
sc.addEventListener('touchend',function(ev){
  ev.preventDefault();
  if(!tp.active||!canv)return;
  var elapsed=Date.now()-tp.startTime;
  var t=ev.changedTouches[0];
  var dist=Math.hypot(t.clientX-tp.startX,t.clientY-tp.startY);
  if(elapsed<300&&dist<15){
    // tap = click at touch position
    canvRect=canv.getBoundingClientRect();
    var rx=(t.clientX-canvRect.left)/canvRect.width*canv.width;
    var ry=(t.clientY-canvRect.top)/canvRect.height*canv.height;
    tp.curX=Math.max(0,Math.min(canv.width-1,rx));
    tp.curY=Math.max(0,Math.min(canv.height-1,ry));
    rfb.sendPointer(Math.round(tp.curX),Math.round(tp.curY),1);
    setTimeout(function(){rfb.sendPointer(Math.round(tp.curX),Math.round(tp.curY),0);},80);
  }
  tp.active=false;
  setTimeout(function(){kbd.focus();},50);
},{passive:false,capture:true});
async function cn(){
try{
rfb=new RFB(document.getElementById('screen'),'ws://HOST_IP:VNC_WS');
rfb.resizeSession=false;
rfb.addEventListener('connect',function(){
  dot.className='dot on';lab.textContent='connected';
  kbd.focus();
  if(scaler)clearInterval(scaler);
  scaler=setInterval(function(){scaleAll();},200);
  setTimeout(function(){clearInterval(scaler);scaleAll();},1500);
});
rfb.addEventListener('disconnect',function(e){dot.className='dot';lab.textContent='disconnected: '+e.detail.reason;clearInterval(scaler);setTimeout(cn,5000)});
rfb.addEventListener('securityfailure',function(e){lab.textContent='auth fail: '+e.detail.reason;});
window.addEventListener('resize',scaleAll);
}catch(e){lab.textContent='error: '+e.message;setTimeout(cn,5000)}}
cn();
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
    import subprocess, json
    default_sink = subprocess.run(["pactl", "get-default-sink"], capture_output=True, text=True).stdout.strip()
    monitor = f"{default_sink}.monitor"
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-re", "-f", "pulse", "-i", monitor,
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
