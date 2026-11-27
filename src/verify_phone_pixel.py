# -*- coding: utf-8 -*-
"""폰 화면 픽셀 동일성 — 배포 전 index.html(HEAD)과 현재 index.html 을 같은 브라우저로 비교."""
import functools, http.server, os, socketserver, subprocess, threading
from playwright.sync_api import sync_playwright
from PIL import Image, ImageChops

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OLD = '/tmp/oldsite'
os.makedirs(OLD, exist_ok=True)
open(os.path.join(OLD, 'index.html'), 'wb').write(subprocess.check_output(['git', 'show', 'HEAD:index.html'], cwd=SITE))
if not os.path.exists(os.path.join(OLD, 'assets')):
    os.symlink(os.path.join(SITE, 'assets'), os.path.join(OLD, 'assets'))

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def serve(d):
    h = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=d))
    threading.Thread(target=h.serve_forever, daemon=True).start()
    return 'http://127.0.0.1:%d/' % h.server_address[1]

URLS = [('old', serve(OLD)), ('new', serve(SITE))]
shots = {}
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for tag, url in URLS:
        for vw, vh, vtag in ((390, 844, 'phone'), (430, 932, 'phone430')):
            ctx = b.new_context(viewport={'width': vw, 'height': vh}, device_scale_factor=1)
            page = ctx.new_page()
            page.goto(url, wait_until='load')
            page.evaluate("localStorage.clear()"); page.reload(wait_until='load'); page.wait_for_timeout(250)
            page.fill('#gateCode', '2020'); page.click('#gateBtn'); page.wait_for_timeout(1400)
            page.locator('#resultCard [data-mp-go]').first.click(); page.wait_for_timeout(900)
            p1 = '/tmp/%s-%s-board.png' % (tag, vtag)
            page.screenshot(path=p1)
            page.locator('#pg [data-pg="set"]').click(); page.wait_for_timeout(400)
            p2 = '/tmp/%s-%s-sheet.png' % (tag, vtag)
            page.screenshot(path=p2)
            shots[(tag, vtag)] = (p1, p2)
            ctx.close()
    b.close()

for vtag in ('phone', 'phone430'):
    for kind, i in (('board', 0), ('sheet', 1)):
        a = Image.open(shots[('old', vtag)][i]).convert('RGB')
        c = Image.open(shots[('new', vtag)][i]).convert('RGB')
        d = ImageChops.difference(a, c)
        print(vtag, kind, 'size', a.size, 'diff bbox', d.getbbox())
