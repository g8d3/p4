import sys,os,json,time
sys.path.insert(0,os.path.expanduser("~/code/p4/e100-openbot")); import obctl
c=obctl.connect()
def fill(i,txt):
    obctl.ev(c,"const els=[...document.querySelectorAll('[role=dialog] input')];const e=els[%d];e.focus();e.select();return 1"%i)
    c.send(json.dumps({"id":9,"method":"Input.insertText","params":{"text":txt}}))
    while json.loads(c.recv()).get("id")!=9: pass
    time.sleep(0.3)
key=os.environ.get("ZAI_API_KEY","")
assert key, "no key"
for i,t in [(0,"zai"),(1,"Zhipu Z.ai"),(2,"https://api.z.ai/api/coding/paas/v4"),(3,key),(4,"glm-5.3-flash"),(5,"GLM-5.3 Flash (Zhipu)")]: fill(i,t)
print(obctl.ev(c,"return [...document.querySelectorAll('[role=dialog] input')].map((e,i)=>i==3?('key len '+e.value.length):e.value).join(' | ')"))
