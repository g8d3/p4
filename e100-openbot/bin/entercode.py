import json,re,os,glob,sys,time
sys.path.insert(0,os.path.expanduser("~/code/p4/e100-openbot"))
import obctl
inbox=os.path.expanduser("~/code/p4/e092-echolike/correo/inbox")
f=max(glob.glob(inbox+"/*.json"),key=os.path.getmtime)
d=json.load(open(f)); t=d.get("text") or json.dumps(d)
code=re.findall(r"\b([A-Z0-9]{4}-?[A-Z0-9]{4})\b",t)[0].replace("-","")
c=obctl.connect()
js=("const i=document.querySelector('input');i.focus();const s=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;"
    "s.call(i,%s);i.dispatchEvent(new Event('input',{bubbles:true}));return i.value.length;")%json.dumps(code)
print("typed len",obctl.ev(c,js)); time.sleep(6)
print(obctl.ev(c,"return document.body.innerText.slice(0,600)"))
