import sys,os,json,time
sys.path.insert(0,os.path.expanduser("~/code/p4/e100-openbot")); import obctl
c=obctl.connect()
def ev(s): return obctl.ev(c,s)
def press(label):
    return ev(obctl.FIRE+"const t=%s;const els=[...document.querySelectorAll('button,a,[role=button],[role=menuitem],[role=tab],[role=option]')];"
      "const el=els.find(e=>((e.innerText||e.getAttribute('aria-label')||'').trim())===t);if(!el)return 'NF '+t;"
      "fire(el);el.focus();el.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',code:'Enter',bubbles:true}));return 'ok '+t;"%json.dumps(label))
def items(): return ev("return [...document.querySelectorAll('button,a,[role=button],[role=menuitem],[role=tab],[role=option],input,textarea')].map(e=>(e.innerText||e.getAttribute('aria-label')||e.placeholder||e.tagName).trim().slice(0,40)).filter(Boolean).join(' | ')")
for a in sys.argv[1:]:
    print(press(a)); time.sleep(2.5)
print(items()); print("---"); print(ev("return document.body.innerText.slice(0,1500)"))
