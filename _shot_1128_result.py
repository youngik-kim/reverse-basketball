# -*- coding: utf-8 -*-
"""2026-11-28 반영 화면 캡처 (모바일·데스크톱)"""
import os, subprocess, sys, time
from playwright.sync_api import sync_playwright

ROOT = '/workspace/reverse-basketball-site'
PORT = 8772
OUT = '/workspace/screens/reverse-1128-result'
os.makedirs(OUT, exist_ok=True)
srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'],
                       cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
URL = f'http://127.0.0.1:{PORT}/index.html'


def enter(page):
    page.goto(URL, wait_until='load')
    page.evaluate("localStorage.clear()")
    page.reload(wait_until='load')
    page.wait_for_timeout(300)
    page.fill('#gateCode', '2020')
    page.click('#gateBtn')
    page.wait_for_timeout(1800)


try:
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for w, h, tag, mob in ((390, 844, 'm', True), (1280, 900, 'd', False)):
            ctx = b.new_context(viewport={'width': w, 'height': h},
                                device_scale_factor=2 if mob else 1, is_mobile=mob, has_touch=mob)
            page = ctx.new_page()
            enter(page)
            page.evaluate("window.scrollTo(0,0)")
            page.wait_for_timeout(500)
            page.screenshot(path=f'{OUT}/{tag}-top.png')
            page.screenshot(path=f'{OUT}/{tag}-full.png', full_page=True)
            # 결과 카드
            page.locator('#secResult').scroll_into_view_if_needed()
            page.wait_for_timeout(400)
            page.screenshot(path=f'{OUT}/{tag}-result.png')
            # 순위 상단
            page.locator('#secRank').scroll_into_view_if_needed()
            page.wait_for_timeout(400)
            page.screenshot(path=f'{OUT}/{tag}-rank.png')
            # 주간 카드
            page.locator('#secWeeks').scroll_into_view_if_needed()
            page.wait_for_timeout(400)
            page.screenshot(path=f'{OUT}/{tag}-weeks.png')
            ctx.close()
        b.close()
finally:
    srv.terminate()
print('done')
