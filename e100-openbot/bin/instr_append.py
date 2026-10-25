# Append text to the open agent side panel instructions textarea (starts with "# Coco"), if not already present.
# Usage: python3 bin/ui.py "<Agent name>"  (opens side panel), then: python3 bin/instr_append.py "text"
import sys,os,json,time
sys.path.insert(0,os.path.expanduser("~/code/p4/e100-openbot")); import obctl
c=obctl.connect(); add=sys.argv[1]
F="const t=[...document.querySelectorAll(\"textarea\")].find(e=>e.value.startsWith(\"# Coco\"));"
if obctl.ev(c,F+"return t.value.includes(%s)"%json.dumps(add)): print("already present"); sys.exit()
print(obctl.ev(c,F+"t.focus();t.setSelectionRange(t.value.length,t.value.length);return t.value.length"))
c.send(json.dumps({"id":9,"method":"Input.insertText","params":{"text":"\n\n"+add+"\n"}}))
while json.loads(c.recv()).get("id")!=9: pass
time.sleep(1)
print(obctl.ev(c,F+"t.blur();return t.value.length+\" \"+t.value.slice(-160)"))
time.sleep(2)
