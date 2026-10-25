import sys,os,json,time
sys.path.insert(0,os.path.expanduser("~/code/p4/e100-openbot")); import obctl
c=obctl.connect()
print(obctl.ev(c,"const el=[...document.querySelectorAll('[role=menuitem],[role=option]')].find(e=>e.innerText.trim()===%s);if(!el)return 'NF';el.focus();return 'f'"%json.dumps(sys.argv[1])))
for t in ["keyDown","keyUp"]:
    c.send(json.dumps({"id":7,"method":"Input.dispatchKeyEvent","params":{"type":t,"key":"Enter","code":"Enter","windowsVirtualKeyCode":13}}))
    while json.loads(c.recv()).get("id")!=7: pass
time.sleep(2.5)
