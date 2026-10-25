#!/usr/bin/env python3
"""Minimal CDP controller for the OpenBot desktop app (headless, no screenshots).

Usage:
  python3 obctl.py text            # print visible text of the app
  python3 obctl.py eval "<js-fn-body>"
  python3 obctl.py click "<exact-or-regex button text>"

Requires: app launched with --remote-debugging-port=9222 --remote-allow-origins=*
"""
import json
import sys
import time
import urllib.request
from websocket import create_connection

PORT = 9222


def connect():
    targets = json.load(urllib.request.urlopen(
        f"http://localhost:{PORT}/json/list", timeout=10))
    pages = [t for t in targets if t.get("type") == "page"]
    page = next((t for t in pages if t["url"].endswith("/index.html")), pages[0])
    return create_connection(page["webSocketDebuggerUrl"], timeout=15)


def ev(c, fnbody):
    expr = "(function(){ %s })()" % fnbody
    c.send(json.dumps({"id": 7, "method": "Runtime.evaluate",
                       "params": {"expression": expr,
                                 "returnByValue": True}}))
    while True:
        m = json.loads(c.recv())
        if m.get("id") == 7:
            r = m["result"]["result"]
            return r.get("value", r)


FIRE = ("const fire=(el)=>{const r=el.getBoundingClientRect(),"
        "x=r.x+r.width/2,y=r.y+r.height/2;"
        "['pointerover','pointerenter','pointerdown','mousedown',"
        "'pointerup','mouseup','click'].forEach(t=>el.dispatchEvent("
        "new MouseEvent(t,{bubbles:true,cancelable:true,clientX:x,"
        "clientY:y,button:0})));};")

FOCUS_ENTER = ("el.focus();el.dispatchEvent(new KeyboardEvent('keydown',"
               "{key:'Enter',code:'Enter',bubbles:true,cancelable:true}));")


def cmd_text(c):
    print(ev(c, "return document.body.innerText.slice(0,3000);"))


def cmd_eval(c, body):
    print(ev(c, body))


def cmd_click(c, text):
    print(ev(c, FIRE + (
        "const t=%s;"
        "const els=[...document.querySelectorAll('button,a,[role=button]')];"
        "const el=els.find(e=>(e.innerText||'').trim()===t)||"
        "els.find(e=>new RegExp(t,'i').test((e.innerText||'').trim()));"
        "if(!el) return 'NOTFOUND:'+t; fire(el); return 'clicked:'+t;"
    ) % json.dumps(text)))


if __name__ == "__main__":
    c = connect()
    try:
        if sys.argv[1] == "text":
            cmd_text(c)
        elif sys.argv[1] == "eval":
            cmd_eval(c, sys.argv[2])
        elif sys.argv[1] == "click":
            cmd_click(c, sys.argv[2])
            time.sleep(3)
            cmd_text(c)
        else:
            sys.exit("unknown cmd: text | eval | click")
    finally:
        c.close()
