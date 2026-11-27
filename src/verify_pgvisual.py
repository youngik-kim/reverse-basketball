# -*- coding: utf-8 -*-
"""경기 진행 화면 — 팀 색 구분(점·상단선·배지) · A4 인쇄 흑백 · 사진 저장 2장 검증.

    python3 src/verify_pgvisual.py            # 로컬 index.html
    MP_URL=... python3 src/verify_pgvisual.py # 배포 페이지

검사:
  1) 매치업 헤더 — 팀 색 점(●)·팀명 배지·2색 상단선, 글씨 크고 굵게 (어두운/중간/밝은 테마)
  2) 하단 팀 순위 카드 — 팀 색 상단선·순위 배지·굵은 팀명
  3) A4 인쇄(@media print) — 테마와 무관하게 흰 배경(#fff)·검정 글씨/테두리
  4) 📸 사진 저장 — 원본 테마 PNG + 잉크절약 흑백 PNG 2장 다운로드(이름·색 확인)
  5) JS 오류 0건
"""
import functools, http.server, io, json, os, socketserver, sys, threading
from playwright.sync_api import sync_playwright
from PIL import Image

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get('MP_OUT') or os.path.join(SITE, '_verify_pgvisual')
os.makedirs(OUT, exist_ok=True)
CODE = os.environ.get('MP_CODE') or '2020'
DATA = json.loads(io.open(os.path.join(SITE, 'src', 'data.json'), encoding='utf-8').read())
CANON = DATA['preview']
ALLNAMES = set([p['name'] for p in DATA['members']] + [p['name'] for p in DATA['outsiders']]
               + [g['name'] for g in DATA['guests']] + list(DATA['absent'])
               + [n for t in CANON['teams'] for n in t['roster']])
TEAMS = [t['team'] for t in CANON['teams']]
THEMES = [('dark', 'rgb(8, 11, 16)'), ('mid', 'rgb(220, 227, 236)'), ('light', 'rgb(241, 244, 248)')]

URL = os.environ.get('MP_URL')
if not URL:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    handler = functools.partial(Quiet, directory=SITE)
    httpd = socketserver.ThreadingTCPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    URL = 'http://127.0.0.1:%d/' % httpd.server_address[1]
print('target', URL)

results = []


def ok(name, cond, extra=''):
    results.append((name, bool(cond), extra))
    print(('PASS ' if cond else 'FAIL ') + name + ((' — ' + str(extra)) if extra else ''))


def enter(page):
    page.goto(URL, wait_until='load')
    page.evaluate("localStorage.clear()")
    page.reload(wait_until='load')
    page.wait_for_timeout(250)
    page.fill('#gateCode', CODE)
    page.click('#gateBtn')
    page.wait_for_timeout(1200)


def open_progress(page):
    page.locator('#resultCard [data-mp-go]').first.click()
    page.wait_for_timeout(650)


SNAP = """() => {
  const cs = el => el ? getComputedStyle(el) : null;
  const dots = [...document.querySelectorAll('#pg .pgtbl .mh .dot')].map(e => ({
    cls: e.className, bg: cs(e).backgroundColor, sh: cs(e).boxShadow,
    w: Math.round(e.getBoundingClientRect().width) }));
  const chips = [...document.querySelectorAll('#pg .pgtbl .mh .tm')].map(e => ({
    txt: e.innerText.trim(), ring: cs(e).boxShadow, fw: cs(e).fontWeight,
    fs: cs(e).fontSize }));
  const mpair = document.querySelector('#pg .pgtbl .mh .mpair');
  const mh = document.querySelector('#pg .pgtbl .mh');
  const top = mh ? getComputedStyle(mh, '::before') : null;
  const sum = [...document.querySelectorAll('#pg .pgs')].map(e => ({
    team: e.querySelector('.pgsn') ? e.querySelector('.pgsn').innerText.trim() : '',
    bt: cs(e).borderTopWidth, btc: cs(e).borderTopColor,
    nameFs: e.querySelector('.pgsn') ? cs(e.querySelector('.pgsn')).fontSize : '',
    nameFw: e.querySelector('.pgsn') ? cs(e.querySelector('.pgsn')).fontWeight : '',
    rankBg: e.querySelector('.pgsr,.pgsrank') ? cs(e.querySelector('.pgsr,.pgsrank')).backgroundColor : '',
    dotBg: e.querySelector('.dot') ? cs(e.querySelector('.dot')).backgroundColor : '' }));
  return { dots, chips, mpairFs: mpair ? cs(mpair).fontSize : '', mpairFw: mpair ? cs(mpair).fontWeight : '',
    topImg: top ? top.backgroundImage : '', topH: top ? top.height : '', sum,
    pgBg: cs(document.querySelector('#pg')).backgroundColor,
    pgColor: cs(document.querySelector('#pg')).color };
}"""


with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for tag, w, h in [('d', 1280, 800), ('m', 390, 844)]:
        ctx = browser.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2 if tag == 'm' else 1,
                                  accept_downloads=True)
        page = ctx.new_page()
        errs = []
        page.on('console', lambda m: errs.append('console.%s: %s' % (m.type, m.text)) if m.type == 'error' else None)
        page.on('pageerror', lambda e: errs.append('pageerror: %s' % e))
        downloads = []
        page.on('download', lambda d: downloads.append(d))
        enter(page)
        open_progress(page)
        ok('%s: 경기 진행 열림' % tag, page.locator('#pg').is_visible())
        page.click('[data-pg="set"]')
        page.wait_for_timeout(250)

        for theme, bg in THEMES:
            page.click('#pgSettings [data-pgtheme="%s"]' % theme)
            page.wait_for_timeout(320)
            page.keyboard.press('Escape')
            page.wait_for_timeout(250)
            snap = page.evaluate(SNAP)
            page.click('[data-pg="set"]')
            page.wait_for_timeout(220)
            ok('%s/%s: 매치업 팀 점 색 채워짐(투명 아님)' % (tag, theme),
               len(snap['dots']) >= 6 and all(d['bg'] not in ('rgba(0, 0, 0, 0)', 'transparent') for d in snap['dots']),
               snap['dots'][:3])
            ok('%s/%s: 매치업 팀명 배지 + 테두리 링' % (tag, theme),
               len(snap['chips']) >= 6 and all('rgb' in c['ring'] for c in snap['chips']),
               snap['chips'][:3])
            ok('%s/%s: 매치업 2색 상단선' % (tag, theme), 'gradient' in (snap['topImg'] or ''), snap['topImg'][:60])
            ok('%s/%s: 매치업 팀명 크고 굵게' % (tag, theme),
               float(snap['mpairFs'].replace('px', '')) >= 11.5 and int(snap['mpairFw']) >= 800 and snap['mpairFw'] == '900',
               (snap['mpairFs'], snap['mpairFw']))
            ok('%s/%s: 순위 카드 팀 색 상단선' % (tag, theme),
               len(snap['sum']) == 3 and all(float(s['bt'].replace('px', '')) >= 2.4
                                             and s['btc'] not in ('rgba(0, 0, 0, 0)', 'transparent')
                                             for s in snap['sum']), [(s['bt'], s['btc']) for s in snap['sum']])
            ok('%s/%s: 순위 카드 팀명 굵게·확대' % (tag, theme),
               all(s['nameFw'] == '900' and float(s['nameFs'].replace('px', '')) >= 10.5 for s in snap['sum']),
               [(s['team'], s['nameFs'], s['nameFw']) for s in snap['sum']])
            page.screenshot(path='%s/%s_theme_%s.png' % (OUT, tag, theme))

        # ---------- 쿼터 행 화살표 제거 · 합계/순위 카드 가운데 정렬 ----------
        lay = page.evaluate("""() => {
          const cs = el => getComputedStyle(el);
          const qh = [...document.querySelectorAll('#pg .pgtbl .qh')];
          const qrows = qh.filter(e => /Q$/.test((e.innerText || '').trim()));
          const sum = document.querySelector('#pg .pgsums .pgs');
          const tot = document.querySelector('#pg .pgtot');
          return { qArrows: document.querySelectorAll('#pg [data-qmove]').length,
                   mArrows: document.querySelectorAll('#pg [data-mmove]').length,
                   qhW: qrows.length ? Math.round(qrows[0].getBoundingClientRect().width) : 0,
                   zoom: parseFloat(document.querySelector('#pg .pgfit').style.zoom || '1') || 1,
                   sumJustify: cs(sum.querySelector('.pgs1')).justifyContent,
                   sumAlign: cs(sum).textAlign, totAlign: cs(tot).textAlign };
        }""")
        ok('%s: 쿼터 ▲▼ 화살표 제거(매치업 ◀▶ 유지)' % tag,
           lay['qArrows'] == 0 and lay['mArrows'] >= 6, lay)
        ok('%s: 쿼터 열 좁아짐(%dpx · zoom %.2f)' % (tag, lay['qhW'], lay['zoom']),
           0 < lay['qhW'] <= 34 * lay['zoom'] + 2, (lay['qhW'], lay['zoom']))
        ok('%s: 합계·순위 카드 가운데 정렬' % tag,
           lay['sumJustify'] == 'center' and lay['sumAlign'] == 'center' and lay['totAlign'] == 'center', lay)

        # ---------- A4 인쇄 — 테마와 무관하게 흰 배경 · 검정 글씨 ----------
        for theme, _bg in THEMES:
            page.click('#pgSettings [data-pgtheme="%s"]' % theme)
            page.wait_for_timeout(250)
            page.keyboard.press('Escape')
            page.wait_for_timeout(200)
            page.emulate_media(media='print')
            page.wait_for_timeout(250)
            pr = page.evaluate("""() => {
              const cs = el => el ? getComputedStyle(el) : null;
              const pg = document.querySelector('#pg');
              const cells = [...document.querySelectorAll('#pg .pgcell')].slice(0, 4).map(e => ({
                bg: cs(e).backgroundColor, bc: cs(e).borderTopColor, color: cs(e).color }));
              const texts = [...document.querySelectorAll('#pg .pgnm')].slice(0, 4).map(e => cs(e).color);
              const dots = [...document.querySelectorAll('#pg .dot')].slice(0, 4).map(e => ({
                bg: cs(e).backgroundColor, ol: cs(e).outlineColor, olw: cs(e).outlineWidth }));
              return { body: cs(document.body).backgroundColor, pg: cs(pg).backgroundColor,
                       pgc: cs(pg).color, txt: cs(document.querySelector('#pg .pgt')).color,
                       bar: cs(document.querySelector('#pg .pgbar')).backgroundColor,
                       cells, texts, dots,
                       pgs: cs(document.querySelector('#pg .pgs')).backgroundColor };
            }""")
            page.emulate_media(media='screen')
            page.wait_for_timeout(150)
            page.click('[data-pg="set"]')
            page.wait_for_timeout(200)
            white = lambda v: v in ('rgb(255, 255, 255)', 'rgba(0, 0, 0, 0)')
            black = lambda v: v in ('rgb(0, 0, 0)',)
            ok('%s/%s 인쇄: 배경 흰색' % (tag, theme),
               white(pr['body']) and pr['pg'] in ('rgb(255, 255, 255)', 'rgba(0, 0, 0, 0)') and white(pr['bar']),
               (pr['body'], pr['pg'], pr['bar']))
            ok('%s/%s 인쇄: 글씨·테두리 검정' % (tag, theme),
               black(pr['pgc']) and black(pr['txt']) and all(black(c['color']) and black(c['bc']) for c in pr['cells'])
               and all(black(t) for t in pr['texts']), (pr['pgc'], pr['txt'], pr['cells'][:2]))
            ok('%s/%s 인쇄: 팀 점도 검정 테두리' % (tag, theme),
               all(black(d['ol']) for d in pr['dots']), pr['dots'])

        # ---------- 📸 사진 저장 — 2장 ----------
        with page.expect_download(timeout=15000) as d1:
            page.click('#pgSettings [data-pg="png"]')
        f1 = os.path.join(OUT, '%s_png_original.png' % tag)
        d1.value.save_as(f1)
        for _ in range(30):
            if len(downloads) >= 2:
                break
            page.wait_for_timeout(150)
        ok('%s: 사진 저장 2장 다운로드' % tag, len(downloads) >= 2, [d.suggested_filename for d in downloads])
        names = [d.suggested_filename for d in downloads]
        ok('%s: 원본 파일 이름' % tag, any(n == '리버스_3파전_경기기록_%s.png' % CANON['date'] for n in names), names)
        ok('%s: 잉크절약 파일 이름' % tag,
           any(n == '리버스_3파전_경기기록_%s_잉크절약.png' % CANON['date'] for n in names), names)
        if len(downloads) >= 2:
            f2 = os.path.join(OUT, '%s_png_ink.png' % tag)
            downloads[1].save_as(f2)
            ok('%s: 두 PNG 파일 생성' % tag, os.path.getsize(f1) > 20000 and os.path.getsize(f2) > 20000,
               (os.path.getsize(f1), os.path.getsize(f2)))
            a = Image.open(f1).convert('RGB')
            b = Image.open(f2).convert('RGB')
            ok('%s: 잉크절약 PNG 배경 완전 흰색' % tag, b.getpixel((5, 5)) == (255, 255, 255), b.getpixel((5, 5)))
            ok('%s: 원본 PNG 는 테마 배경(흑백 아님)' % tag, a.getpixel((5, 5)) != (255, 255, 255), a.getpixel((5, 5)))
            ok('%s: 잉크절약 PNG 검정 글씨 존재' % tag,
               sum(1 for px in b.crop((0, 0, b.width, 260)).getdata() if px == (0, 0, 0)) > 200)

        # ---------- 2파전 — 상단 헤더 팀 칩·점 ----------
        fake = {'v': 2, 'items': {'2026-12-05': {'v': 1, 'date': '2026-12-05', 'mode': 2, 'id': '2026-12-05|2',
                'teams': [{'team': '블랙', 'cap': '', 'roster': ['테스트A', '테스트B', '테스트C', '테스트D', '테스트E']},
                          {'team': '화이트', 'cap': '', 'roster': ['테스트F', '테스트G', '테스트H', '테스트I', '테스트J']}],
                'savedAt': '2026-11-27T00:00:00Z'}}}
        page.evaluate("(o) => localStorage.setItem('reverse-match-preview-v1', JSON.stringify(o))", fake)
        page.reload(wait_until='load')
        page.wait_for_timeout(1300)
        page.click('#mpPreviewBtn')
        page.wait_for_timeout(400)
        page.click('[data-mptab=\"hist\"]')
        page.wait_for_timeout(300)
        page.click('[data-mphist=\"2026-12-05\"]')
        page.wait_for_timeout(300)
        page.click('[data-mphist-go=\"2026-12-05\"]')
        page.wait_for_timeout(700)
        g2 = page.evaluate("""() => {
          const cs = el => el ? getComputedStyle(el) : null;
          const box = document.querySelector('#pg .pggh2');
          return { vis: !!box,
                   chips: box ? [...box.querySelectorAll('.tm')].map(e => ({ t: e.innerText.trim(), ring: cs(e).boxShadow })) : [],
                   dots: box ? [...box.querySelectorAll('.dot')].map(e => ({ bg: cs(e).backgroundColor, w: Math.round(e.getBoundingClientRect().width) })) : [] };
        }""")
        ok('%s: 2파전 헤더 팀 점·칩' % tag,
           g2['vis'] and len(g2['chips']) == 2 and len(g2['dots']) == 2
           and all(d['bg'] not in ('rgba(0, 0, 0, 0)', 'transparent') and d['w'] >= 8 for d in g2['dots'])
           and all('rgb' in c['ring'] for c in g2['chips']), g2)
        page.screenshot(path='%s/%s_2man.png' % (OUT, tag))

        ok('%s: JS 오류 0건' % tag, not errs, errs[:4])
        ctx.close()
    browser.close()

print('\n%d/%d PASS' % (sum(1 for r in results if r[1]), len(results)))
sys.exit(0 if all(r[1] for r in results) else 1)
