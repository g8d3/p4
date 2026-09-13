"""Real browser verification of the e062 fleet board: console errors,
rendered content, and UI-vs-API data correctness (phone + desktop)."""
import json, sys, urllib.request
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:8322'
api = json.load(urllib.request.urlopen(BASE + '/api/board', timeout=15))
errors = []

def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + ((' — ' + str(extra)) if extra and not cond else ''))
    if not cond:
        errors.append(name)

with sync_playwright() as pw:
    b = pw.chromium.launch()
    # ---------- phone ----------
    pg = b.new_page(viewport={'width': 390, 'height': 844})
    cerr = []
    pg.on('console', lambda m: cerr.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: cerr.append(str(e)))
    pg.goto(BASE + '/', wait_until='networkidle')
    pg.wait_for_timeout(2500)

    check('no console errors (phone)', len(cerr) == 0, cerr[:3])
    nwidgets = pg.evaluate('window._widgets.length')
    check('3 default widgets rendered', nwidgets == 3, nwidgets)
    ncards = pg.locator('#cards .card').count()
    check('6 project cards rendered', ncards == 6, ncards)
    # waiting math: UI badge total vs API notes+pending
    api_wait = len(api.get('notes', [])) + len([p for p in api.get('proposals', []) if p['status'] == 'pending'])
    wtxt = pg.locator('#waiting').inner_text() if pg.locator('#waiting').count() else ''
    import re
    m = re.search(r'(\d+)', wtxt)
    ui_wait = int(m.group(1)) if m else 0
    check('thumbbar waiting count == notes+pending', ui_wait == api_wait, f'ui={ui_wait} api={api_wait} txt={wtxt!r}')
    # session short-ids visible
    body = pg.locator('body').inner_text()
    ses_ids = [r.get('session') for r in api.get('runs', []) if r.get('session')]
    shown = [s for s in ses_ids if s.split(',')[0] in body]
    check('run session ids visible in UI', len(shown) > 0, f'{len(shown)}/{len(ses_ids)}')
    # money gate from API visible?
    pend = [p for p in api.get('proposals', []) if p['status'] == 'pending']
    if pend:
        check('pending gate action visible', pend[0]['action'][:20] in body, pend[0]['action'][:40])
    # projects root: expand first project -> relation tabs + nested table
    pg.locator('#wc-0 tr.prow').first.click()
    pg.wait_for_timeout(700)
    check('project expands meaningfully', pg.locator('#wc-0 table.ntable').count() > 0)
    # a group WITH relations shows tabs; expand e062 (has gates) explicitly
    pg.evaluate("wProjToggle(0, 0)")
    pg.wait_for_timeout(400)
    # sessions root: expand first session -> talk box
    pg.locator('#wc-1 tr').nth(1).click()
    pg.wait_for_timeout(700)
    check('session expands with talk box', pg.locator('#wc-1 .act-reply input').count() > 0)
    # waiting badge tap -> filters
    pg.locator('#waiting').click()
    pg.wait_for_timeout(800)
    fval = pg.locator('#widgets input[aria-label="filter"]').first.input_value()
    check('waiting tap sets is:waiting filter', 'is:waiting' in fval, fval)
    pg.screenshot(path='/tmp/ui-phone.png')
    # ---------- desktop ----------
    pg2 = b.new_page(viewport={'width': 1280, 'height': 900})
    cerr2 = []
    pg2.on('console', lambda m: cerr2.append(m.text) if m.type == 'error' else None)
    pg2.on('pageerror', lambda e: cerr.append(str(e)))
    pg2.goto(BASE + '/', wait_until='networkidle')
    pg2.wait_for_timeout(2000)
    check('no console errors (desktop)', len(cerr2) == 0, cerr2[:3])
    check('root tables render', pg2.locator('#widgets table.rtable').count() >= 3, pg2.locator('#widgets table.rtable').count())
    check('no vertical scroll traps', pg2.evaluate("getComputedStyle(document.querySelector('#wc-0')).overflowY") in ('visible', ''), pg2.evaluate("getComputedStyle(document.querySelector('#wc-0')).overflowY"))
    pg2.screenshot(path='/tmp/ui-desktop.png', full_page=False)
    b.close()

# restore: leave the owner's saved views clean (tests must not pollute)
try:
    urllib.request.urlopen(urllib.request.Request(
        BASE + '/api/prefs', data=json.dumps({'widgets': ''}).encode(),
        headers={'Content-Type': 'application/json'}), timeout=10)
except Exception as e:
    print('WARN restore failed:', e)
print('RESULT:', 'ALL PASS' if not errors else f'{len(errors)} FAILURES: {errors}')
sys.exit(1 if errors else 0)
