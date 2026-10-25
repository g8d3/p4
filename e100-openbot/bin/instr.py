import sys,os,json,time
sys.path.insert(0,os.path.expanduser("~/code/p4/e100-openbot")); import obctl
c=obctl.connect()
print(obctl.ev(c,"const t=[...document.querySelectorAll('textarea')].find(e=>e.value.startsWith('# Coco'));t.focus();t.setSelectionRange(0,t.value.length);return t.value.length"))
txt=open(os.path.expanduser("~/code/p4/e100-openbot/coco/persona.md")).read()
c.send(json.dumps({"id":9,"method":"Input.insertText","params":{"text":txt}}))
while json.loads(c.recv()).get("id")!=9: pass
time.sleep(1)
print(obctl.ev(c,"const t=[...document.querySelectorAll('textarea')].find(e=>e.value.startsWith('# Coco'));t.blur();return t.value.length+' '+t.value.slice(-200)"))
time.sleep(2)
