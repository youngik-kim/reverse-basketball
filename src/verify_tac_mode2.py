# -*- coding: utf-8 -*-
"""2파전 매치에서 작전판 팀 조합이 MPS 를 따라가는지."""
import os, json, sys
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8765/index.html'
OUT = '/workspace/screens/reverse-1128-live'
os.makedirs(OUT, exist_ok=True)
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
    p = ctx.new_page()
    errs = []
    p.on('pageerror', lambda e: errs.append(str(e)))
    p.goto(URL, wait_until='load')
    p.evaluate("localStorage.clear()")
    p.goto(URL, wait_until='load')
    p.wait_for_timeout(400)
    p.fill('#gateCode', '2020')
    p.click('#gateBtn')
    p.wait_for_timeout(1500)
    p.evaluate("""() => { MPS = { v:1, date:'2026-11-28', mode:2, id:'2026-11-28|2',
      teams:[{team:'블랙', roster:['박광현','김준성','심호길','김현준','최정범','조성현'], cap:'박광현'},
             {team:'화이트', roster:['변정훈','정승혁','유동훈','나윤','김영익'], cap:'유동훈'}] }; }""")
    p.locator('#tacBtn').click()
    p.wait_for_timeout(1200)
    print(json.dumps(p.evaluate("""() => { const el=document.querySelector('#tac');
      return {chips:[...el.querySelectorAll('.tacmu')].map(c=>c.innerText.replace(/\\n/g,' ')),
              toks:[...el.querySelectorAll('[data-tok]')].map(t=>t.className.replace('tactok ','')),
              names:[...el.querySelectorAll('.tacpblock li')].map(li=>li.innerText.replace(/\\n/g,' ')),
              open:!el.hidden, fs: document.fullscreenElement?document.fullscreenElement.id:null}; }"""), ensure_ascii=False))
    p.screenshot(path=os.path.join(OUT, 'm-10-tac-mode2.png'))
    print('ERR', errs[:3])
    b.close()
