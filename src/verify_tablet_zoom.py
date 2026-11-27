# -*- coding: utf-8 -*-
"""태블릿 확대 모드 검증 — 해상도 × 배율(자동/125%/150%) 전수 검사 + 스크린샷.

    python3 src/verify_tablet_zoom.py            # 로컬 index.html
    MP_URL=... python3 src/verify_tablet_zoom.py # 배포 페이지

검사 항목(각 뷰포트 × 각 배율):
  1) 선수 이름 말줄임 0건        — scrollWidth > clientWidth, + 폰트 실측(캔버스) 폭
  2) 팀 머리글(● 화이트 5명 순서) 넘침·말줄임 0건
  3) 매치업 헤더(● 형광 | ● 화이트) 한 줄 유지·넘침 0건
  4) 점수표 가로 스크롤 0건 · 보드가 칸 밖으로 넘침 0건 · 페이지 세로 스크롤 0건
  5) 폰(390×844)은 확대 모드 미적용(zoom 1) — 기존 그대로
  6) 회전(가로↔세로) 후 다시 맞춤
"""
import functools, http.server, json, os, sys, socketserver, threading
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

VP = [(390, 844, 'phone'), (960, 600, 'tablet960'), (1024, 768, 'tablet1024'),
      (768, 1024, 'tablet-portrait'), (1280, 800, 'desktop')]
MODES = ('auto', '1.25', '1.5')
# 기기(태블릿) 폰트가 헤드리스보다 넓은 경우를 흉내 — 글자 폭을 약 7% 늘려 재검사
WIDE_FONT = """#pg .pgnm{letter-spacing:.07em !important}
#pg .pgth b{letter-spacing:.07em !important}
#pg .pgrc{letter-spacing:.07em !important}
#pg .pgtbl .mpair{letter-spacing:.03em !important}
#pg .pgasg,#pg .pgtn{letter-spacing:.06em !important}"""
res = []

def ok(name, cond, extra=''):
    res.append((name, bool(cond), extra))
    print(('PASS ' if cond else 'FAIL ') + name + ((' — ' + str(extra)) if extra else ''))

SNAP = """() => {
  const pg = document.querySelector('#pg');
  const body = document.querySelector('#pgBody');
  const z = parseFloat(pg.style.zoom || '1') || 1;
  const names = [...document.querySelectorAll('#pg .pgnm')].map(n => ({
    t: n.innerText.trim(), cw: n.clientWidth, sw: n.scrollWidth,
    tw: Math.round(mpTextW(n) * 10) / 10,
    bad: n.scrollWidth > n.clientWidth + 1 || mpTextW(n) > n.clientWidth + 1 }));
  const ths = [...document.querySelectorAll('#pg .pgth')].map(t => {
    const b = t.querySelector('b');
    return {t: t.innerText.trim().replace(/\\n/g, ' '), bad: t.scrollWidth > t.clientWidth + 1 || mpClamped(b, 0)};
  });
  const mps = [...document.querySelectorAll('#pg .pgtbl .mpair')].map(m => ({
    t: m.innerText.trim().replace(/\\n/g, ' '), cw: m.clientWidth,
    spare: Math.round(mpPairSpare(m) * 10) / 10, fs: getComputedStyle(m).fontSize,
    lines: Math.round(m.getBoundingClientRect().height / (parseFloat(getComputedStyle(m).fontSize) * 1.6) * 10) / 10,
    bad: mpPairSpare(m) < 0 || m.scrollWidth > m.clientWidth + 1 || m.scrollHeight > m.clientHeight + 1 }));
  const fits = [...document.querySelectorAll('#pg .pgfit')].map(el => {
    const p = el.parentNode;
    return {h: el.clientHeight, ph: p.clientHeight, over: p.clientHeight ? el.clientHeight > p.clientHeight + 1 : false};
  });
  const sheet = document.querySelector('#pgSettings .pgsetp');
  return {
    zoom: z, tab: pg.classList.contains('pg-tab'), cls: pg.className, vw: innerWidth, vh: innerHeight,
    badNames: names.filter(n => n.bad), badThs: ths.filter(t => t.bad), badMps: mps.filter(m => m.bad),
    mpair: mps, thr: ths.slice(0, 1), nameMinSlack: Math.min(...names.map(n => Math.round((n.cw - n.tw) * 10) / 10)),
    fits, colOver: fits.filter(f => f.over).length,
    tblH: [...document.querySelectorAll('#pg .pgtblwrap')].filter(e => e.scrollWidth > e.clientWidth + 1).length,
    bodyScroll: {sh: body.scrollHeight, ch: body.clientHeight, sw: body.scrollWidth, cw: body.clientWidth},
    pgScroll: {sh: pg.scrollHeight, ch: pg.clientHeight},
    sheet: sheet ? (r => ({x: Math.round(r.x), y: Math.round(r.y), right: Math.round(r.right), bottom: Math.round(r.bottom)}))(sheet.getBoundingClientRect()) : null,
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
    page.locator('#resultCard [data-mp-go]').first.click()
    page.wait_for_timeout(900)          # 폰트 로드 후 재맞춤(700ms)까지 기다림

def setmode(page, mode):
    page.locator('#pg [data-pg="set"]').click()
    page.wait_for_timeout(350)
    page.locator('#pg [data-pgzoom="%s"]' % mode).click()
    page.wait_for_timeout(400)
    page.locator('#pgSettings .pgx').click()
    page.wait_for_timeout(500)

with sync_playwright() as pw:
    b = pw.chromium.launch()
    for w, h, tag in VP:
        ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=1)
        page = ctx.new_page()
        errs = []
        page.on('pageerror', lambda e: errs.append(str(e)))
        page.on('console', lambda m: errs.append('console:' + m.text) if m.type == 'error' else None)
        enter(page)
        ok('%s: JS 오류 0건' % tag, not errs, errs[:2])
        for mode in MODES:
            if mode != 'auto':
                if tag == 'phone':
                    continue
                setmode(page, mode)
            d = page.evaluate(SNAP)
            lbl = '%s[%s]' % (tag, '자동' if mode == 'auto' else mode.replace('1.25', '125%').replace('1.5', '150%'))
            page.screenshot(path=os.path.join(SHOTS, 'reverse-tablet-%s-%s.png' % (tag, mode)))
            ok('%s: 선수 이름 말줄임 0' % lbl, not d['badNames'],
               [(x['t'], x['cw'], x['tw'], x['sw']) for x in d['badNames']] or d['nameMinSlack'])
            ok('%s: 팀 머리글(● 팀명 N명 순서) 넘침 0' % lbl, not d['badThs'], d['badThs'])
            ok('%s: 매치업 헤더 한 줄·넘침 0' % lbl, not d['badMps'],
               [(m['t'], m['cw'], m['spare'], m['fs'], m['lines']) for m in d['badMps']] or
               [(m['spare'], m['fs'], m['lines']) for m in d['mpair']])
            ok('%s: 점수표 가로 스크롤 0 · 보드 넘침 0 · 세로 스크롤 0' % lbl,
               d['tblH'] == 0 and d['colOver'] == 0 and d['bodyScroll']['sh'] <= d['bodyScroll']['ch'] + 1
               and d['pgScroll']['sh'] <= d['pgScroll']['ch'] + 1,
               {'tblH': d['tblH'], 'colOver': d['colOver'], 'body': d['bodyScroll'], 'pg': d['pgScroll']})
            if tag == 'phone':
                ok('폰: 확대 모드 미적용(zoom 1 · pg-tab 없음)', d['zoom'] == 1 and not d['tab'], d['zoom'])
            elif mode == 'auto':
                ok('%s: 자동 배율 적용 zoom>1' % tag, d['tab'] and d['zoom'] > 1, d['zoom'])
            print('    ', lbl, 'zoom %.2f' % d['zoom'],
                  'names[slack %.1f]' % d['nameMinSlack'],
                  'mpair', [(m['spare'], m['fs'], m['lines']) for m in d['mpair']],
                  'th', d['thr'])
        # 설정 시트 · 배율 버튼
        page.locator('#pg [data-pg="set"]').click()
        page.wait_for_timeout(350)
        ds = page.evaluate(SNAP)
        page.screenshot(path=os.path.join(SHOTS, 'reverse-tablet-%s-settings.png' % tag))
        ok('%s: 설정 시트가 화면 안' % tag,
           ds['sheet'] and ds['sheet']['x'] >= -1 and ds['sheet']['y'] >= -1
           and ds['sheet']['right'] <= w + 1 and ds['sheet']['bottom'] <= h + 1, ds['sheet'])
        if tag == 'phone':
            ok('폰: 확대(배율) 설정 숨김 — 폰에는 의미 없음', len(ds['zoomBtns']) == 0, ds['zoomBtns'])
        else:
            ok('%s: 배율 버튼 3개(자동/125/150)' % tag, len(ds['zoomBtns']) == 3, ds['zoomBtns'])
        page.locator('#pgSettings .pgx').click()
        page.wait_for_timeout(250)
        # 회전
        page.set_viewport_size({'width': h, 'height': w})
        page.wait_for_timeout(900)
        rot = page.evaluate(SNAP)
        page.screenshot(path=os.path.join(SHOTS, 'reverse-tablet-%s-rotated.png' % tag))
        if tag == 'phone':
            ok('phone: 회전(가로)해도 확대 모드 미적용', rot['zoom'] == 1 and not rot['tab'], {'zoom': rot['zoom'], 'cls': rot['cls']})
        else:
            ok('%s: 회전 후에도 이름·헤더 잘림 0 · 넘침 0' % tag,
               not rot['badNames'] and not rot['badThs'] and not rot['badMps'] and rot['colOver'] == 0,
               {'zoom': rot['zoom'], 'names': rot['badNames'][:2], 'mps': rot['badMps'][:1]})
        # 기기 폰트가 더 넓은 경우(±) — 글자 폭을 7% 늘린 뒤 다시 맞춰도 잘리지 않아야 합니다
        if tag != 'phone':
            page.set_viewport_size({'width': w, 'height': h})
            page.wait_for_timeout(500)
            page.add_style_tag(content=WIDE_FONT)
            page.evaluate("() => { mpZoomCache = {key:'', base:1, z:1}; mpApplyFit(); }")
            page.wait_for_timeout(500)
            wd = page.evaluate(SNAP)
            ok('%s: 넓은 폰트(글자 +7%%)에서도 이름·헤더 잘림 0' % tag,
               not wd['badNames'] and not wd['badThs'] and not wd['badMps'] and wd['colOver'] == 0,
               {'zoom': wd['zoom'], 'names': wd['badNames'][:2], 'mps': wd['badMps'][:1]})
            page.screenshot(path=os.path.join(SHOTS, 'reverse-tablet-%s-widefont.png' % tag))
        ctx.close()
    b.close()

bad = [r for r in res if not r[1]]
print('\n%d/%d PASS' % (len(res) - len(bad), len(res)))
if bad:
    for r in bad:
        print('  FAIL', r[0], r[2])
    sys.exit(1)
