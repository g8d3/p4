import sys,os,json,time
sys.path.insert(0,os.path.expanduser("~/code/p4/e100-openbot")); import obctl
c=obctl.connect(); msg=sys.argv[1]
print(obctl.ev(c,"const e=document.querySelector('[contenteditable=true]')||[...document.querySelectorAll('textarea,input')].find(x=>/Message/.test(x.placeholder||x.getAttribute('aria-label')||''));e.focus();return e.tagName;"))
c.send(json.dumps({"id":50,"method":"Input.insertText","params":{"text":msg}}))
while json.loads(c.recv()).get("id")!=50: pass
time.sleep(1)
print(obctl.ev(c,obctl.FIRE+"const b=[...document.querySelectorAll('button')].find(e=>e.getAttribute('aria-label')==='Send message');fire(b);return 'sent';"))
time.sleep(45)
print(obctl.ev(c,"return document.querySelector('main')?document.querySelector('main').innerText.slice(-700):document.body.innerText.slice(-900)"))
