# -*- coding: utf-8 -*-
import os, json
from playwright.sync_api import sync_playwright

URL = 'http://127.0.0.1:8765/index.html'
OUT = '/workspace/screens/reverse-1128'
os.makedirs(OUT, exist_ok=True)


def enter(page):
    page.goto(URL, wait_until='load')
    page.evaluate("localStorage.clear()")
    page.reload(wait_until='load')
    page.wait_for_timeout(300)
    page.fill('#gateCode', '2020')
    page.click('#gateBtn')
    page.wait_for_timeout(1500)


with sync_playwright() as pw:
    b = pw.chromium.launch()
    for w, h, tag, mob in ((390, 844, 'm', True), (844, 390, 'ml', True), (1280, 800, 't', False), (820, 1180, 'tp', False)):
        ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2 if mob else 1, is_mobile=mob, has_touch=mob)
        page = ctx.new_page()
        errs = []
        page.on('pageerror', lambda e: errs.append(str(e)))
        enter(page)
        page.locator('#tacBtn').click()
        page.wait_for_timeout(1000)
        info = page.evaluate("""() => { const st = document.querySelector('#tacStage');
          const cv = document.querySelector('#tacCv'), pn = document.querySelector('.tacpanel');
          const r = cv.getBoundingClientRect(), s = st.getBoundingClientRect();
          const body = document.body;
          return {row: st.classList.contains('row'), cw: Math.round(r.width), ch: Math.round(r.height),
            pw: Math.round(pn.getBoundingClientRect().width), ph: Math.round(pn.getBoundingClientRect().height),
            stage: [Math.round(s.width), Math.round(s.height)],
            overflowY: document.querySelector('#tac').scrollHeight > document.querySelector('#tac').clientHeight,
            tok: getComputedStyle(document.querySelector('.tactok')).width,
            footClip: [...document.querySelectorAll('.tacfoot button')].filter(b2 => b2.scrollWidth > b2.clientWidth + 1).length,
            panelClip: [...document.querySelectorAll('.tacpblock li')].filter(li => li.scrollWidth > li.clientWidth + 1).length}; }""")
        print(tag, json.dumps(info, ensure_ascii=False))
        page.screenshot(path=os.path.join(OUT, 'tac-%s.png' % tag))
        print('  err', errs[:3])
        ctx.close()
    b.close()
print('DONE')
