import sys,os,json,time
sys.path.insert(0,os.path.expanduser("~/code/p4/e100-openbot")); import obctl
c=obctl.connect(); sel=sys.argv[1]
r=obctl.ev(c,"const t=%s;const el=[...document.querySelectorAll('button,[role=button],a,[role=menuitem],[role=option],[role=tab]')].find(e=>((e.getAttribute('aria-label')||e.innerText||'').trim()).startsWith(t));if(!el)return null;const r=el.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2];"%json.dumps(sel))
print("at",r)
if r:
  for i,t in enumerate(["mousePressed","mouseReleased"]):
    c.send(json.dumps({"id":100+i,"method":"Input.dispatchMouseEvent","params":{"type":t,"x":r[0],"y":r[1],"button":"left","clickCount":1}}))
    while json.loads(c.recv()).get("id")!=100+i: pass
time.sleep(2.5)
print(obctl.ev(c,"return [...document.querySelectorAll('[role=dialog],[role=menu],[role=listbox],[data-radix-popper-content-wrapper]')].map(e=>e.innerText.slice(0,1500)).join('\\n####\\n')"))
