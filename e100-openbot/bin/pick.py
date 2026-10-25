import sys,os,json,time
sys.path.insert(0,os.path.expanduser("~/code/p4/e100-openbot")); import obctl
c=obctl.connect(); t=sys.argv[1]
r=obctl.ev(c,"const t=%s;const box=document.querySelector('[role=dialog],[data-radix-popper-content-wrapper]');const els=[...box.querySelectorAll('*')].filter(e=>e.innerText&&e.innerText.trim().split('\\n')[0].trim()===t&&e.offsetParent);const el=els[0];if(!el)return null;const r=el.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2,el.tagName,el.getAttribute('role')];"%json.dumps(t))
print(r)
obctl.ev(c,"const t=%s;const box=document.querySelector('[role=dialog],[data-radix-popper-content-wrapper]');const el=[...box.querySelectorAll('*')].filter(e=>e.innerText&&e.innerText.trim().split('\\n')[0].trim()===t&&e.offsetParent)[0];el.scrollIntoView({block:'center'});"%json.dumps(t))
r=obctl.ev(c,"const t=%s;const box=document.querySelector('[role=dialog],[data-radix-popper-content-wrapper]');const el=[...box.querySelectorAll('*')].filter(e=>e.innerText&&e.innerText.trim().split('\\n')[0].trim()===t&&e.offsetParent)[0];const r=el.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2];"%json.dumps(t))
for i,ty in enumerate(["mousePressed","mouseReleased"]):
    c.send(json.dumps({"id":100+i,"method":"Input.dispatchMouseEvent","params":{"type":ty,"x":r[0],"y":r[1],"button":"left","clickCount":1}}))
    while json.loads(c.recv()).get("id")!=100+i: pass
time.sleep(3)
print(obctl.ev(c,"return [...document.querySelectorAll('button')].map(b=>b.getAttribute('aria-label')||'').filter(x=>x.startsWith('Agent model')).join()"))
