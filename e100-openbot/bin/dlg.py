import sys,os
sys.path.insert(0,os.path.expanduser("~/code/p4/e100-openbot")); import obctl
c=obctl.connect()
print(obctl.ev(c,"const d=[...document.querySelectorAll('[role=dialog],[role=menu],[data-radix-popper-content-wrapper]')];return d.map(x=>x.innerText.slice(0,2500)+' || '+[...x.querySelectorAll('button,input,textarea,[role=combobox],[role=option],[role=menuitem],[role=switch]')].map(e=>(e.tagName+':'+(e.getAttribute('aria-label')||e.placeholder||e.innerText||e.id)).slice(0,50)).join(' | ')).join('\\n#####\\n')"))
