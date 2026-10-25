import sys,os,json,time
sys.path.insert(0,os.path.expanduser("~/code/p4/e100-openbot")); import obctl
k=os.environ["OPENCODE_GO_API_KEY"]; c=obctl.connect()
print(obctl.ev(c,("const d=document.querySelector('[role=dialog]')||document;const i=[...d.querySelectorAll('input')].filter(x=>x.offsetParent).pop();"
 "i.focus();const s=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;s.call(i,%s);i.dispatchEvent(new Event('input',{bubbles:true}));return 'len '+i.value.length;")%json.dumps(k)))
print(obctl.ev(c,obctl.FIRE+"const b=[...document.querySelectorAll('button')].find(e=>e.innerText.trim()==='Save key');fire(b);return 'saved-click';"))
time.sleep(6)
t=obctl.ev(c,"return document.body.innerText"); print(t.replace(k,"<KEY>")[-900:])
