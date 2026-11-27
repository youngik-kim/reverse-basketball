# -*- coding: utf-8 -*-
"""경기 진행 화면 '화면 꽉 채우기 + 글씨 크기 3단계' 검증.

    python3 src/verify_tablet_full.py            # 로컬 index.html
    MP_URL=... MP_SHOTS=... python3 src/verify_tablet_full.py   # 배포 페이지

검사 항목(각 뷰포트):
  1) 화면 꽉 채우기 — 보드(점수표·명단) 하단이 화면 끝에서 24px 안쪽, 페이지/본문 스크롤 0
  2) 글씨 크기 작게 < 보통 < 크게 가 실제 px 로 뚜렷이 다름(단계 비 1.3배 이상)
  3) 선수 이름·팀 머리글(● 팀명 N명 순서)·매치업 헤더(● 형광 | ● 화이트) 잘림/넘침 0
  4) 점수 입력칸·합계 칸이 칸을 넘지 않음, 점수표 가로 스크롤 0
  5) ⚙️ 설정 시트 — '글씨 크기' 3버튼(작게·보통·크게)이 있고 '확대'는 없음, 기본값 보통
  6) A4 인쇄(print 미디어)에서도 보드가 페이지 안
"""
import functools, http.server, os, sys, socketserver, threading
from playwright.sync_api import sync_playwright

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(SITE)
SHOTS = os.environ.get('MP_SHOTS') or os.path.join(ROOT, 'screens', 'reverse-tablet-full-2026-11-27')
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
print('shots ', SHOTS)

VP = [(1280, 800, 'tablet1280'), (1024, 768, 'tablet1024'), (960, 600, 'tablet960'),
      (768, 1024, 'portrait768'), (800, 1280, 'portrait800'),
      (390, 844, 'phone390'), (430, 932, 'phone430')]
LEVELS = [(0, 'small'), (1, 'medium'), (2, 'large')]
BOTTOM_GAP_MAX = 24

res = []

def ok(name, cond, extra=''):
    res.append((name, bool(cond), extra))
    print(('PASS ' if cond else 'FAIL ') + name + ((' — ' + str(extra)) if extra else ''))

SNAP = """() => {
  const pg = document.querySelector('#pg');
  const body = document.querySelector('#pgBody');
  const px = v => Math.round(v * 10) / 10;
  const fs = sel => { const e = document.querySelector(sel); return e ? px(parseFloat(getComputedStyle(e).fontSize)) : 0; };
  const names = [...document.querySelectorAll('#pg .pgnm')].map(n => ({
    t: n.innerText.trim(), cw: n.clientWidth, sw: n.scrollWidth,
    tw: px(mpTextW(n)), fs: px(parseFloat(getComputedStyle(n).fontSize)),
    bad: n.scrollWidth > n.clientWidth + 1 || mpTextW(n) > n.clientWidth + 1 }));
  const ths = [...document.querySelectorAll('#pg .pgth')].map(t => {
    const b = t.querySelector('b');
    return { t: t.innerText.trim().replace(/\\n/g, ' '), sw: t.scrollWidth, cw: t.clientWidth,
             bad: t.scrollWidth > t.clientWidth + 1 || (b && b.scrollWidth > b.clientWidth + 1) };
  });
  const mps = [...document.querySelectorAll('#pg .pgtbl .mpair')].map(m => ({
    t: m.innerText.trim().replace(/\\n/g, ' '), cw: m.clientWidth, sw: m.scrollWidth,
    sh: m.scrollHeight, ch: m.clientHeight, fs: px(parseFloat(getComputedStyle(m).fontSize)),
    bad: m.scrollWidth > m.clientWidth + 1 || m.scrollHeight > m.clientHeight + 1 }));
  const pcols = [...document.querySelectorAll('#pg .pgcol')];
  const fits = [...document.querySelectorAll('#pg .pgfit')];
  const boardBottom = Math.max.apply(null, fits.map(f => f.getBoundingClientRect().bottom));
  const sumCards = [...document.querySelectorAll('#pg .pgs')].map(s => ({sw: s.scrollWidth, cw: s.clientWidth,
    sh: s.scrollHeight, ch: s.clientHeight}));
  const tbls = [...document.querySelectorAll('#pg .pgtblwrap')].map(w => ({sw: w.scrollWidth, cw: w.clientWidth,
    sh: w.scrollHeight, ch: w.clientHeight}));
  const sci = [...document.querySelectorAll('#pg .sci')].map(i => ({cw: i.clientWidth, sw: i.scrollWidth}));
  const rowH = (() => { const r = document.querySelector('#pg .pgrow'); return r ? px(r.getBoundingClientRect().height) : 0; })();
  const cellH = (() => { const c = document.querySelector('#pg .pgtbl .pgcell'); return c ? px(c.getBoundingClientRect().height) : 0; })();
  const sheet = document.querySelector('#pgSettings .pgsetp');
  return {
    cls: pg.className, vw: innerWidth, vh: innerHeight,
    pgScroll: {sh: pg.scrollHeight, ch: pg.clientHeight, sw: pg.scrollWidth, cw: pg.clientWidth},
    bodyScroll: {sh: body.scrollHeight, ch: body.clientHeight, sw: body.scrollWidth, cw: body.clientWidth},
    boardBottom: px(boardBottom), bottomGap: px(pg.getBoundingClientRect().bottom - boardBottom),
    badNames: names.filter(n => n.bad), badThs: ths.filter(t => t.bad), badMps: mps.filter(m => m.bad),
    nameFs: names.length ? Math.max.apply(null, names.map(n => n.fs)) : 0,
    minNameSlack: names.length ? Math.min.apply(null, names.map(n => Math.round((n.cw - n.tw) * 10) / 10)) : 0,
    scoreFs: fs('#pg .sci'), teamFs: fs('#pg .pgth b'), mpairFs: fs('#pg .pgtbl .mpair'),
    metaFs: fs('#pg .pgrc') || fs('#pg .cum'), rowH: rowH, cellH: cellH,
    over: {tbl: tbls.filter(t => t.sw > t.cw + 1 || t.sh > t.ch + 1).length,
           sum: sumCards.filter(s => s.sw > s.cw + 1 || s.sh > s.ch + 1).length,
           sci: sci.filter(s => s.sw > s.cw + 1).length,
           fit: fits.filter(f => f.scrollHeight > f.clientHeight + 1).length,
           col: pcols.filter(c => c.scrollHeight > c.clientHeight + 1).length},
    zoom: pg.style.zoom || '', tab: pg.classList.contains('pg-tab'), full: pg.classList.contains('pg-full'),
    nameAlign: (() => { const n = document.querySelector('#pg .pgnm'); return n ? getComputedStyle(n).textAlign : ''; })(),
    thJustify: (() => { const t = document.querySelector('#pg .pgth'); return t ? getComputedStyle(t).justifyContent : ''; })(),
    sheet: sheet ? (r => ({x: Math.round(r.x), y: Math.round(r.y), right: Math.round(r.right),
                           bottom: Math.round(r.bottom)}))(sheet.getBoundingClientRect()) : null,
    fsBtns: [...document.querySelectorAll('#pg [data-pgfs]')].filter(b => b.offsetParent !== null).map(b => b.textContent),
    fsPressed: [...document.querySelectorAll('#pg [data-pgfs][aria-pressed="true"]')].map(b => b.textContent),
    zoomRow: [...document.querySelectorAll('#pg .pgsl')].map(e => e.textContent).filter(t => t.indexOf('확대') >= 0).length
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
    page.wait_for_timeout(1400)

def open_sheet(page):
    page.locator('#pg [data-pg="set"]').click()
    page.wait_for_timeout(300)

def set_level(page, lv):
    open_sheet(page)
    page.locator('#pg [data-pgfs="%d"]' % lv).click()
    page.wait_for_timeout(350)
    page.locator('#pgSettings .pgx').click()
    page.wait_for_timeout(650)

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
        # 기본값 = 보통
        open_sheet(page)
        d0 = page.evaluate(SNAP)
        ok('%s: 기본 글씨 크기 = 보통' % tag, d0['fsPressed'] == ['보통'], d0['fsPressed'])
        ok('%s: 설정 시트 — 글씨 크기 3버튼 · 확대 없음' % tag,
           d0['fsBtns'] == ['작게', '보통', '크게'] and d0['zoomRow'] == 0,
           {'btns': d0['fsBtns'], 'zoomRow': d0['zoomRow']})
        ok('%s: 설정 시트가 화면 안' % tag,
           d0['sheet'] and d0['sheet']['x'] >= -1 and d0['sheet']['y'] >= -1
           and d0['sheet']['right'] <= w + 1 and d0['sheet']['bottom'] <= h + 1, d0['sheet'])
        page.screenshot(path=os.path.join(SHOTS, '%s-settings.png' % tag))
        page.locator('#pgSettings .pgx').click()
        page.wait_for_timeout(300)
        got = {}
        for lv, lab in LEVELS:
            set_level(page, lv)
            d = page.evaluate(SNAP)
            got[lab] = d
            name = '%s.png' % lab if (w, h) == (1280, 800) else '%s-%s.png' % (tag, lab)
            page.screenshot(path=os.path.join(SHOTS, name))
            ok('%s[%s]: 보드가 화면 끝까지 참 (하단 여백 %.0fpx, 스크롤 0)' % (tag, lab, d['bottomGap']),
               -1 <= d['bottomGap'] <= BOTTOM_GAP_MAX
               and d['pgScroll']['sh'] <= d['pgScroll']['ch'] + 1
               and d['bodyScroll']['sh'] <= d['bodyScroll']['ch'] + 1,
               {'gap': d['bottomGap'], 'pg': d['pgScroll'], 'body': d['bodyScroll']})
            ok('%s[%s]: 이름·팀머리글·매치업 헤더 잘림 0' % (tag, lab),
               not d['badNames'] and not d['badThs'] and not d['badMps'],
               {'names': [(x['t'], x['cw'], x['tw']) for x in d['badNames']][:2],
                'ths': d['badThs'][:1], 'mps': d['badMps'][:1], 'nameFs': d['nameFs']})
            ok('%s[%s]: 점수표·합계·입력칸 넘침 0' % (tag, lab),
               d['over']['tbl'] == 0 and d['over']['sum'] == 0 and d['over']['sci'] == 0
               and d['over']['fit'] == 0 and d['over']['col'] == 0, d['over'])
            ok('%s[%s]: 이름 가운데 정렬 · 팀머리글 가운데' % (tag, lab),
               d['nameAlign'] == 'center' and d['thJustify'] == 'center',
               (d['nameAlign'], d['thJustify']))
            print('     %s[%s] vw%d name %.1f score %.1f team %.1f mpair %.1f meta %.1f rowH %.0f cellH %.0f gap %.0f'
                  % (tag, lab, d['vw'], d['nameFs'], d['scoreFs'], d['teamFs'], d['mpairFs'], d['metaFs'],
                     d['rowH'], d['cellH'], d['bottomGap']))
        s, m, l = got['small'], got['medium'], got['large']
        ok('%s: 글씨 크기 단계 뚜렷이 다름 (작게 %.1f < 보통 %.1f < 크게 %.1f, %.2f배)'
           % (tag, s['nameFs'], m['nameFs'], l['nameFs'], l['nameFs'] / max(1e-6, s['nameFs'])),
           s['nameFs'] < m['nameFs'] < l['nameFs'] and l['nameFs'] / max(1e-6, s['nameFs']) >= 1.3,
           {'small': s['nameFs'], 'medium': m['nameFs'], 'large': l['nameFs']})
        ok('%s: 점수 숫자도 단계별로 커짐 (%.1f < %.1f < %.1f)'
           % (tag, s['scoreFs'], m['scoreFs'], l['scoreFs']),
           s['scoreFs'] < m['scoreFs'] < l['scoreFs'] and l['scoreFs'] / max(1e-6, s['scoreFs']) >= 1.25,
           {'small': s['scoreFs'], 'medium': m['scoreFs'], 'large': l['scoreFs']})
        # 점수 3자리 입력 후에도 넘치지 않는지 (보통)
        set_level(page, 1)
        ins = page.locator('#pg .sci')
        ins.nth(0).fill('100'); ins.nth(1).fill('088'); ins.nth(2).fill('77')
        page.wait_for_timeout(800)
        dq = page.evaluate(SNAP)
        page.screenshot(path=os.path.join(SHOTS, '%s-scored.png' % tag))
        ok('%s: 점수 입력(3자리) 후에도 잘림·넘침 0' % tag,
           not dq['badNames'] and not dq['badThs'] and not dq['badMps'] and dq['over']['sci'] == 0
           and dq['over']['tbl'] == 0 and dq['over']['fit'] == 0 and dq['bottomGap'] <= BOTTOM_GAP_MAX,
           {'sci': dq['over']['sci'], 'names': dq['badNames'][:1], 'gap': dq['bottomGap']})
        # 회전
        page.set_viewport_size({'width': h, 'height': w})
        page.wait_for_timeout(1200)
        dr = page.evaluate(SNAP)
        page.screenshot(path=os.path.join(SHOTS, '%s-rotated.png' % tag))
        ok('%s: 회전(%dx%d) 후에도 꽉 참·잘림 0' % (tag, h, w),
           -1 <= dr['bottomGap'] <= BOTTOM_GAP_MAX and not dr['badNames'] and not dr['badThs']
           and not dr['badMps'] and dr['over']['fit'] == 0,
           {'gap': dr['bottomGap'], 'cls': dr['cls']})
        # A4 인쇄
        page.set_viewport_size({'width': w, 'height': h})
        page.wait_for_timeout(600)
        page.emulate_media(media='print')
        page.wait_for_timeout(400)
        dp = page.evaluate("""() => {
          const pg = document.querySelector('#pg');
          const t = document.querySelector('#pg .pgtbl');
          return {disp: getComputedStyle(pg).display,
                  tblW: t ? Math.round(t.getBoundingClientRect().width) : 0,
                  docW: document.documentElement.clientWidth,
                  h: Math.round(document.documentElement.scrollHeight)};
        }""")
        page.screenshot(path=os.path.join(SHOTS, '%s-print.png' % tag), full_page=True)
        page.emulate_media(media='screen')
        ok('%s: 인쇄에서도 보드가 페이지 폭 안' % tag,
           dp['tblW'] > 0 and dp['tblW'] <= dp['docW'] + 2, dp)
        ctx.close()
    b.close()

bad = [r for r in res if not r[1]]
print('\n%d/%d PASS' % (len(res) - len(bad), len(res)))
if bad:
    for r in bad:
        print('  FAIL', r[0], r[2])
    sys.exit(1)
