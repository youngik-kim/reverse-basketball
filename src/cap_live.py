# -*- coding: utf-8 -*-
"""배포본 최종 스크린샷 — MP_URL(라이브) 기준."""
import os
from playwright.sync_api import sync_playwright

URL = os.environ.get('MP_URL') or 'https://youngik-kim.github.io/reverse-basketball/?v=tablet2'
OUT = '/workspace/screens/reverse-tablet-fix-2026-11-27'
os.makedirs(OUT, exist_ok=True)
CODE = '2020'

with sync_playwright() as pw:
    b = pw.chromium.launch()
    for w, h, tag in ((1280, 800, '1280x800'), (1024, 768, '1024x768'), (960, 600, '960x600'), (768, 1024, '768x1024')):
        ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=1)
        page = ctx.new_page()
        page.goto(URL, wait_until='load')
        page.evaluate("localStorage.clear()"); page.reload(wait_until='load'); page.wait_for_timeout(200)
        page.fill('#gateCode', CODE); page.click('#gateBtn'); page.wait_for_timeout(1500)
        page.locator('#resultCard [data-mp-go]').first.click(); page.wait_for_timeout(1400)
        for mode in ('auto', '1.25', '1.5'):
            if mode != 'auto':
                page.locator('#pg [data-pg="set"]').click(); page.wait_for_timeout(350)
                page.locator('#pg [data-pgzoom="%s"]' % mode).click(); page.wait_for_timeout(450)
                page.locator('#pgSettings .pgx').click(); page.wait_for_timeout(450)
            page.screenshot(path=os.path.join(OUT, 'live-%s-%s.png' % (tag, mode.replace('.', ''))))
            z = page.evaluate("() => document.querySelector('#pg').style.zoom")
            print(tag, mode, 'zoom', z)
        page.locator('#pg .sci').nth(0).fill('100')
        page.locator('#pg .sci').nth(1).fill('88')
        page.wait_for_timeout(500)
        page.screenshot(path=os.path.join(OUT, 'live-%s-scored.png' % tag))
        page.locator('#pg [data-pg="set"]').click(); page.wait_for_timeout(350)
        page.screenshot(path=os.path.join(OUT, 'live-%s-settings.png' % tag))
        page.locator('#pg [data-pgzoom="1.5"]').click(); page.wait_for_timeout(500)
        page.screenshot(path=os.path.join(OUT, 'live-%s-toast.png' % tag))
        ctx.close()
    b.close()
print(sorted(os.listdir(OUT)))
