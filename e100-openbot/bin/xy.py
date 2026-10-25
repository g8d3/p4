import sys,os,json,time
sys.path.insert(0,os.path.expanduser("~/code/p4/e100-openbot")); import obctl
c=obctl.connect(); x,y=float(sys.argv[1]),float(sys.argv[2])
for i,ty in enumerate(["mousePressed","mouseReleased"]):
    c.send(json.dumps({"id":100+i,"method":"Input.dispatchMouseEvent","params":{"type":ty,"x":x,"y":y,"button":"left","clickCount":1}}))
    while json.loads(c.recv()).get("id")!=100+i: pass
time.sleep(2)
