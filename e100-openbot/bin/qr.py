import sys,os,json,time,base64
sys.path.insert(0,os.path.expanduser("~/code/p4/e100-openbot")); import obctl
c=obctl.connect()
print(obctl.ev(c,obctl.FIRE+"const b=[...document.querySelectorAll('button')].find(e=>/^(Generate new code|Generate QR code)$/.test(e.innerText.trim()));fire(b);return 'gen';"))
print("generated_at", time.strftime("%H:%M:%S")); time.sleep(5)
FIND=("const lab=[...document.querySelectorAll('*')].find(e=>e.children.length==0&&/Choose Scan QR code/.test(e.textContent));lab.scrollIntoView({block:'center'});"
 "const ly=lab.getBoundingClientRect().y;const cands=[...document.querySelectorAll('svg,canvas,img')].filter(e=>{const r=e.getBoundingClientRect();return r.width>100&&Math.abs(r.width-r.height)<8});"
 "cands.sort((a,b)=>Math.abs(a.getBoundingClientRect().y-ly)-Math.abs(b.getBoundingClientRect().y-ly));const r=cands[0].getBoundingClientRect();return [r.x,r.y,r.width,r.height,cands.length,cands[0].tagName];")
obctl.ev(c,FIND); time.sleep(1); r=obctl.ev(c,FIND); print(r)
p=16
c.send(json.dumps({"id":60,"method":"Page.captureScreenshot","params":{"format":"png","clip":{"x":r[0]-p,"y":r[1]-p,"width":r[2]+2*p,"height":r[3]+2*p,"scale":2}}}))
while True:
    m=json.loads(c.recv())
    if m.get("id")==60: break
open("/tmp/openbot_qr.png","wb").write(base64.b64decode(m["result"]["data"]))
t=obctl.ev(c,"const t=document.body.innerText;const i=t.indexOf('2.1');return t.slice(i,i+300)")
import re; print(re.sub(r"[A-Za-z0-9_\-]{24,}","<TOKEN>",t))
