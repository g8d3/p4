import sys,os,json,time
sys.path.insert(0,os.path.expanduser("~/code/p4/e100-openbot")); import obctl
c=obctl.connect(); t=sys.argv[1]; scope=sys.argv[2] if len(sys.argv)>2 else 'body'
r=obctl.ev(c,"const els=[...document.querySelectorAll(%s+' *')].filter(e=>e.offsetParent&&(e.innerText||'').includes(%s));els.sort((a,b)=>a.innerText.length-b.innerText.length);const el=els[0];if(!el)return null;el.scrollIntoView({block:'center'});const r=el.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2];"%(json.dumps(scope),json.dumps(t)))
print("at",r)
if r:
  for i,ty in enumerate(["mousePressed","mouseReleased"]):
    c.send(json.dumps({"id":100+i,"method":"Input.dispatchMouseEvent","params":{"type":ty,"x":r[0],"y":r[1],"button":"left","clickCount":1}}))
    while json.loads(c.recv()).get("id")!=100+i: pass
time.sleep(2.5)
