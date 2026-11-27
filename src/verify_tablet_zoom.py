# -*- coding: utf-8 -*-
"""태블릿 확대 모드 검증 — 4개 뷰포트 실측 + 스크린샷.

    python3 src/verify_tablet_zoom.py            # 로컬 index.html
    MP_URL=... python3 src/verify_tablet_zoom.py # 배포 페이지

검사:
  1) 폰(390x844) — 확대 모드 미적용(zoom 1) · 기존 레이아웃 그대로
  2) 태블릿/데스크톱 — 자동 배율 적용, 선수 이름 잘림 0, 스크롤 없음(한 화면)
  3) 설정 시트 — 배율 버튼(자동/125%/150%) 동작·기억(localStorage)
  4) 125% · 150% — 더 커지되 한 화면 유지(넘치면 낮춤)
  5) 회전(세로↔가로) 후에도 다시 맞춰짐
"""
import functools, http.server, json, os, socketserver, sys, threading
from playwright.sync_api import sync_playwright

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.environ.get('MP_SHOTS') or os.path.join(os.path.dirname(SITE), 'screens')
os.makedirs(SHOTS, exist_ok=True)
CODE = os.environ.get('MP_CODE') or '2020'
URL = os.environ.get('MP_URL')

if not URL:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    httpd = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=SITE))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    URL = 'http://127.0.0.1:%d/' % httpd.server_address[1]
print('target', URL)

VP = [(390, 844, 'phone'), (768, 1024, 'tablet-portrait'), (1024, 768, 'tablet-landscape'), (1280, 800, 'desktop')]
res = []

def ok(name, cond, extra=''):
    res.append((name, bool(cond), extra))
    print(('PASS ' if cond else 'FAIL ') + name + ((' — ' + str(extra)) if extra else ''))

SNAP = """() => {
  const pg = document.querySelector('#pg');
  const r = el => { if (!el) return null; const b = el.getBoundingClientRect();
    return {x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height),
            bottom: Math.round(b.bottom), right: Math.round(b.right)}; };
  const nms = [...document.querySelectorAll('#pg .pgnm')];
  const trunc = nms.filter(n => { const rg = document.createRange(); rg.selectNodeContents(n);
    return rg.getBoundingClientRect().width > n.clientWidth + 1; });
  const body = document.querySelector('#pgBody');
  const fits = [...document.querySelectorAll('#pg .pgfit')].map(e => e.getBoundingClientRect());
  const br = body.getBoundingClientRect();
  const sheet = document.querySelector('#pgSettings .pgsetp');
  const z = parseFloat(pg.style.zoom || '1');
  const fs = s => { const e = document.querySelector(s); return e ? Math.round(parseFloat(getComputedStyle(e).fontSize) * 100) / 100 : null; };
  return {
    zoom: z, tab: pg.classList.contains('pg-tab'), cls: pg.className, vw: innerWidth, vh: innerHeight,
    trunc: trunc.length, truncNames: trunc.map(n => n.innerText.trim()).slice(0, 4),
    fitsInside: fits.every(b => b.bottom <= br.bottom + 1.5 && b.top >= br.top - 1.5 && b.right <= br.right + 1.5),
    bodyOverflow: {sh: body.scrollHeight, ch: body.clientHeight},
    pgScroll: {sh: pg.scrollHeight, ch: pg.clientHeight},
    tblHScroll: [...document.querySelectorAll('#pg .pgtblwrap')].filter(e => e.scrollWidth > e.clientWidth + 1).length,
    eff: {science: Math.round(fs('#pg .sci') * z * 10) / 10, mpair: Math.round(fs('#pg .pgtbl .mpair') * z * 10) / 10,
          pgnm: Math.round(fs('#pg .pgnm') * z * 10) / 10, tot: Math.round(fs('#pg .pgtot .totv') * z * 10) / 10},
    sci: r(document.querySelector('#pg .sci')), mpair: r(document.querySelector('#pg .pgtbl .mpair')),
    tot: r(document.querySelector('#pg .pgtot')), sum: r(document.querySelector('#pg .pgsums')),
    roster: r(document.querySelector('#pg .pgrosters')), lastRow: r([...document.querySelectorAll('#pg .pgrow')].pop()),
    tbl: r(document.querySelector('#pg .pgtbl')), sheet: sheet ? r(sheet) : null,
    zoomBtns: [...document.querySelectorAll('#pg [data-pgzoom]')].filter(b => b.offsetParent !== null)
      .map(b => b.textContent + (b.getAttribute('aria-pressed') === 'true' ? '*' : ''))
  };
}"""

def enter(page):
    page.goto(URL, wait_until='load')
    page.evaluate("localStorage.clear()")
    page.reload(wait_until='load')
    page.wait_for_timeout(200)
    page.fill('#gateCode', CODE)
    page.click('#gateBtn')
    page.wait_for_timeout(1300)

with sync_playwright() as pw:
    b = pw.chromium.launch()
    for w, h, tag in VP:
        ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=1)
        page = ctx.new_page()
        errs = []
        page.on('pageerror', lambda e: errs.append(str(e)))
        page.on('console', lambda m: errs.append('console:' + m.text) if m.type == 'error' else None)
        enter(page)
        page.locator('#resultCard [data-mp-go]').first.click()
        page.wait_for_timeout(800)
        d = page.evaluate(SNAP)
        page.screenshot(path=os.path.join(SHOTS, 'reverse-tablet-%s.png' % tag))
        ok('%s: JS 오류 0건' % tag, not errs, errs[:2])
        ok('%s: 한 화면(보드가 #pgBody 안)' % tag, d['fitsInside'], d['bodyOverflow'])
        ok('%s: 선수 이름 잘림 0' % tag, d['trunc'] == 0, d['truncNames'])
        if tag == 'phone':
            ok('폰: 확대 모드 미적용(zoom 1 · pg-tab 없음)', d['zoom'] == 1 and not d['tab'], d['zoom'])
        else:
            ok('%s: 자동 확대 적용 zoom>1' % tag, d['tab'] and d['zoom'] > 1, d['zoom'])
        # 설정 시트
        page.locator('#pg [data-pg="set"]').click()
        page.wait_for_timeout(400)
        ds = page.evaluate(SNAP)
        page.screenshot(path=os.path.join(SHOTS, 'reverse-tablet-%s-settings.png' % tag))
        ok('%s: 설정 시트가 화면 안' % tag,
           ds['sheet'] and ds['sheet']['x'] >= -1 and ds['sheet']['y'] >= -1
           and ds['sheet']['right'] <= w + 1 and ds['sheet']['bottom'] <= h + 1, ds['sheet'])
        if tag == 'phone':
            ok('폰: 확대(배율) 설정 숨김 — 폰에는 의미 없음', len(ds['zoomBtns']) == 0, ds['zoomBtns'])
        else:
            ok('%s: 배율 버튼 3개(자동/125/150)' % tag, len(ds['zoomBtns']) == 3, ds['zoomBtns'])
        # 125% / 150%
        out = {}
        for lvl in (() if tag == 'phone' else ('1.25', '1.5')):
            page.locator('#pg [data-pgzoom="%s"]' % lvl).click()
            page.wait_for_timeout(500)
            page.locator('#pgSettings .pgx').click()
            page.wait_for_timeout(300)
            dm = page.evaluate(SNAP)
            page.screenshot(path=os.path.join(SHOTS, 'reverse-tablet-%s-%s.png' % (tag, lvl.replace('.', ''))))
            out[lvl] = dm
            ok('%s: %s 퍼센트 선택 반영' % (tag, lvl), abs(dm['zoom'] - (1 if tag == 'phone' else dm['zoom'])) < 1e-6 and dm['fitsInside'],
               {'zoom': dm['zoom'], 'fits': dm['fitsInside']})
            if tag != 'phone':
                ok('%s: %s 퍼센트 한 화면 유지' % (tag, lvl), dm['fitsInside'] and dm['pgScroll']['sh'] <= dm['pgScroll']['ch'] + 1,
                   dm['pgScroll'])
            page.locator('#pg [data-pg="set"]').click()
            page.wait_for_timeout(300)
        stored = page.evaluate("localStorage.getItem('reverse-pgzoom-v1')")
        # 자동 복귀
        if tag != 'phone':
            page.locator('#pg [data-pgzoom="auto"]').click()
            page.wait_for_timeout(400)
        back = page.evaluate(SNAP)
        ok('%s: 자동 복귀' % tag, abs(back['zoom'] - d['zoom']) < 1e-6, {'auto': d['zoom'], 'back': back['zoom'], 'stored': stored})
        # 회전
        page.locator('#pgSettings .pgx').click()
        page.wait_for_timeout(250)
        page.set_viewport_size({'width': h, 'height': w})
        page.wait_for_timeout(700)
        rot = page.evaluate(SNAP)
        page.screenshot(path=os.path.join(SHOTS, 'reverse-tablet-%s-rotated.png' % tag))
        if tag == 'phone':
            ok('phone: 회전(가로)해도 확대 모드 미적용 — 기존 동작 그대로', rot['zoom'] == 1 and not rot['tab'], {'zoom': rot['zoom'], 'cls': rot['cls']})
        else:
            ok('%s: 회전 후 다시 맞춤' % tag, rot['fitsInside'] and rot['trunc'] == 0, {'zoom': rot['zoom'], 'cls': rot['cls']})
        print('   ', tag, json.dumps({k: d[k] for k in ('zoom', 'eff', 'trunc', 'bodyOverflow', 'pgScroll')}, ensure_ascii=False))
        if out:
            print('   ', tag, '125/150 →', out['1.25']['zoom'], out['1.5']['zoom'], 'eff', out['1.5']['eff'])
        ctx.close()
    b.close()

bad = [r for r in res if not r[1]]
print('\n%d/%d PASS' % (len(res) - len(bad), len(res)))
if bad:
    for r in bad:
        print('  FAIL', r[0], r[2])
    sys.exit(1)
