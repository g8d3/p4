import sys,os,json,time
sys.path.insert(0,os.path.expanduser("~/code/p4/e100-openbot")); import obctl
c=obctl.connect(); t=sys.argv[1]
r=obctl.ev(c,"const el=[...document.querySelectorAll('[role=option]')].find(e=>e.innerText.trim()===%s);if(!el)return null;el.scrollIntoView({block:'center'});const r=el.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]"%json.dumps(t))
print(r); time.sleep(0.5)
r=obctl.ev(c,"const el=[...document.querySelectorAll('[role=option]')].find(e=>e.innerText.trim()===%s);const r=el.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]"%json.dumps(t))
for i,ty in enumerate(["mousePressed","mouseReleased"]):
    c.send(json.dumps({"id":100+i,"method":"Input.dispatchMouseEvent","params":{"type":ty,"x":r[0],"y":r[1],"button":"left","clickCount":1}}))
    while json.loads(c.recv()).get("id")!=100+i: pass
time.sleep(2)
