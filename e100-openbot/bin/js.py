import sys,os
sys.path.insert(0,os.path.expanduser("~/code/p4/e100-openbot")); import obctl
c=obctl.connect(); print(obctl.ev(c,open(sys.argv[1]).read()))
