import sys,os,json,time
sys.path.insert(0,os.path.expanduser("~/code/p4/e100-openbot")); import obctl
c=obctl.connect()
for t in ["keyDown","keyUp"]:
    c.send(json.dumps({"id":7,"method":"Input.dispatchKeyEvent","params":{"type":t,"key":"Escape","code":"Escape","windowsVirtualKeyCode":27}}))
    while json.loads(c.recv()).get("id")!=7: pass
time.sleep(1)
