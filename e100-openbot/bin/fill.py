import sys,os,json,time
sys.path.insert(0,os.path.expanduser("~/code/p4/e100-openbot")); import obctl
c=obctl.connect(); idx=int(sys.argv[1]); txt=sys.argv[2]
print(obctl.ev(c,"const els=[...document.querySelectorAll('main input,main textarea,[role=dialog] input,[role=dialog] textarea')].filter(e=>e.offsetParent);const e=els[%d];e.focus();e.select&&e.select();return els.map(x=>x.tagName+':'+(x.placeholder||x.getAttribute('aria-label')||x.name)).join(' | ')"%idx))
c.send(json.dumps({"id":9,"method":"Input.insertText","params":{"text":txt}}))
while json.loads(c.recv()).get("id")!=9: pass
