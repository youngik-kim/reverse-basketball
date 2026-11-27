# -*- coding: utf-8 -*-
"""실제 태블릿 해상도 몇 가지에서 자동 배율/수납 확인 (배포 페이지)."""
import json, os, sys
from playwright.sync_api import sync_playwright

URL = os.environ.get('MP_URL')
if not URL:
    sys.exit('MP_URL 필요')
CODE = '2020'
VP = [(1280, 800, 'galaxy-tab-1280x800'), (1180, 820, 'ipad-air-1180x820'),
      (1366, 1024, 'ipad-pro-1366x1024'), (800, 1280, 'tab-a-portrait-800x1280'),
      (960, 600, 'tab-small-960x600')]

SNAP = """() => {
  const pg = document.querySelector('#pg'), body = document.querySelector('#pgBody');
  const br = body.getBoundingClientRect();
  const fits = [...document.querySelectorAll('#pg .pgfit')].map(e => e.getBoundingClientRect());
  const trunc = [...document.querySelectorAll('#pg .pgnm')].filter(n =>
    n.scrollWidth > n.clientWidth + 1 || mpTextW(n) > n.clientWidth + 1).length;
  const badMp = [...document.querySelectorAll('#pg .pgtbl .mpair')].filter(m => mpPairSpare(m) < 0).length;
  const z = parseFloat(pg.style.zoom || '1');
  const f = s => { const e = document.querySelector(s); return e ? Math.round(parseFloat(getComputedStyle(e).fontSize) * z) : null; };
  return {zoom: z, cls: pg.className, trunc, badMp,
    inside: fits.every(b => b.top >= br.top - 1.5 && b.bottom <= br.bottom + 1.5 && b.right <= br.right + 1.5),
    sciPx: f('#pg .sci'), namePx: f('#pg .pgrow .pgnm'), teamPx: f('#pg .pgtbl .mpair')};
}"""

with sync_playwright() as pw:
    b = pw.chromium.launch()
    for w, h, tag in VP:
        ctx = b.new_context(viewport={'width': w, 'height': h})
        page = ctx.new_page()
        page.goto(URL, wait_until='load')
        page.evaluate("localStorage.clear()"); page.reload(wait_until='load'); page.wait_for_timeout(300)
        page.fill('#gateCode', CODE); page.click('#gateBtn'); page.wait_for_timeout(1600)
        page.locator('#resultCard [data-mp-go]').first.click(); page.wait_for_timeout(900)
        print(tag, json.dumps(page.evaluate(SNAP), ensure_ascii=False))
        page.screenshot(path='/workspace/screens/reverse-tablet-%s.png' % tag)
        ctx.close()
    b.close()
