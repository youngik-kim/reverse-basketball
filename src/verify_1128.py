# -*- coding: utf-8 -*-
"""2026-11-28 개편 로컬 검증 — 합계 승리팀 표기 · 공동 순위 · 명단 드래그 · 전체화면 진입 · 작전판."""
import os, sys, json
from playwright.sync_api import sync_playwright

URL = os.environ.get('MP_URL') or 'http://127.0.0.1:8765/index.html'
OUT = '/workspace/screens/reverse-1128'
os.makedirs(OUT, exist_ok=True)
CODE = '2020'


def enter(page):
    page.goto(URL, wait_until='load')
    page.evaluate("localStorage.clear()")
    page.reload(wait_until='load')
    page.wait_for_timeout(300)
    page.fill('#gateCode', CODE)
    page.click('#gateBtn')
    page.wait_for_timeout(1600)


def shot(page, name):
    p = os.path.join(OUT, name)
    page.screenshot(path=p)
    return p


with sync_playwright() as pw:
    b = pw.chromium.launch(args=['--start-fullscreen'])
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    errs = []
    page.on('pageerror', lambda e: errs.append(str(e)))
    page.on('console', lambda m: errs.append('console:' + m.text) if m.type == 'error' else None)
    enter(page)

    # 1) 히어로 4버튼 한 줄
    info = page.evaluate("""() => {
      const bs = [...document.querySelectorAll('.duobtns .pairbtn')];
      return bs.map(b => ({t: b.innerText.trim(), top: Math.round(b.getBoundingClientRect().top),
        w: Math.round(b.getBoundingClientRect().width), sw: b.scrollWidth, cw: b.clientWidth,
        clipped: b.scrollWidth > b.clientWidth + 1}));
    }""")
    print('HERO', json.dumps(info, ensure_ascii=False))
    print('HERO_SHOT', shot(page, 'm1-hero.png'))

    # 2) 경기 진행 — 전체화면 자동
    page.locator('#resultCard [data-mp-go], [data-mp-go]').first.click()
    page.wait_for_timeout(1500)
    fs = page.evaluate("() => ({fs: document.fullscreenElement ? document.fullscreenElement.id : null, h: innerHeight, w: innerWidth})")
    print('FULLSCREEN', fs)
    print('PG_SHOT', shot(page, 'm2-pg-empty.png'))

    # 3) 점수 입력 — 합계/순위 표기
    scores = page.evaluate("""() => {
      const q = [...document.querySelectorAll('#pg .pgtbl tbody tr')];
      return q.length;
    }""")
    print('PG_ROWS', scores)

    # 첫 매치업 쿼터 칸에 점수 입력 (3파전: 쿼터행 × 매치업열)
    inputs = page.locator('#pg .sci')
    n = inputs.count()
    print('SCI', n)
    # 첫 매치업(열 0)의 1Q 누적 12:8, 2Q 20:15 / 둘째 매치업 10:10, 18:20  → 3파전
    vals = [12, 8, 20, 15, 10, 10, 18, 20, 14, 9, 25, 21, 9, 15, 16, 22]
    for i, v in enumerate(vals[:min(len(vals), n)]):
        inputs.nth(i).fill(str(v))
        inputs.nth(i).dispatch_event('input')
    page.wait_for_timeout(700)
    tot = page.evaluate("""() => [...document.querySelectorAll('#pg .pgtot')].map(td => td.innerText.replace(/\\n/g,' | '))""")
    print('TOTALS', json.dumps(tot, ensure_ascii=False))
    sums = page.evaluate("""() => [...document.querySelectorAll('#pg .pgs')].map(d => d.innerText.replace(/\\n/g,' | '))""")
    print('SUMS', json.dumps(sums, ensure_ascii=False))
    dm = page.evaluate("""() => [...document.querySelectorAll('#pg .totw')].map(e => ({txt: e.innerText.replace(/\\n/g,' '), cls: e.className,
        dot: e.querySelector('.dot') ? e.querySelector('.dot').className : null,
        over: e.scrollWidth > e.clientWidth + 1}))""")
    print('TOTW', json.dumps(dm, ensure_ascii=False))
    print('PG_SCORED', shot(page, 'm3-pg-scored.png'))

    # 4) 명단 드래그 — 이름 칸을 잡고 위로
    names = page.evaluate("""() => [...[...document.querySelectorAll('#pg .pgrows')][0].querySelectorAll('.pgrow')].map(r => r.getAttribute('data-row-name'))""")
    print('ROSTER_BEFORE', names)
    row = page.locator('#pg .pgrows').first.locator('.pgrow').nth(3)
    box = row.bounding_box()
    nm = row.locator('.pgnm').bounding_box()
    page.mouse.move(nm['x'] + nm['width'] / 2, nm['y'] + nm['height'] / 2)
    page.mouse.down()
    page.mouse.move(nm['x'] + nm['width'] / 2, nm['y'] + nm['height'] / 2 - 60, steps=8)
    page.mouse.move(nm['x'] + nm['width'] / 2, nm['y'] + nm['height'] / 2 - 170, steps=8)
    page.mouse.up()
    page.wait_for_timeout(700)
    names2 = page.evaluate("""() => [...[...document.querySelectorAll('#pg .pgrows')][0].querySelectorAll('.pgrow')].map(r => r.getAttribute('data-row-name'))""")
    print('ROSTER_AFTER', names2)
    print('DRAG_OK', names != names2)

    # 5) A4 인쇄 화면(인쇄 CSS) 확인용 스크린샷은 생략 — print 미디어는 별도 확인
    pm = page.evaluate("""() => { const el = document.querySelector('#pg .totw'); const cs = getComputedStyle(el); return {fs: cs.fontSize, disp: cs.display}; }""")
    print('TOTW_CSS', pm)

    # 경기 진행 닫고 작전판
    page.locator('#pg [data-pg="close"]').click()
    page.wait_for_timeout(500)
    page.locator('#tacBtn').click()
    page.wait_for_timeout(1200)
    st = page.evaluate("""() => {
      const el = document.querySelector('#tac');
      const toks = [...el.querySelectorAll('[data-tok]')];
      const ball = el.querySelector('[data-ball]');
      const cv = el.querySelector('#tacCv');
      return {open: !el.hidden, fs: document.fullscreenElement ? document.fullscreenElement.id : null,
        toks: toks.length, ball: !!ball, w: cv ? Math.round(cv.getBoundingClientRect().width) : 0,
        h: cv ? Math.round(cv.getBoundingClientRect().height) : 0,
        tokW: getComputedStyle(el.querySelector('.tactok')).width,
        labels: toks.slice(0, 6).map(t => t.innerText.trim()),
        mu: [...el.querySelectorAll('.tacmu')].map(b => b.innerText.replace(/\\n/g, ' ')),
        footOver: [...el.querySelectorAll('.tacfoot button')].map(b => b.scrollWidth > b.clientWidth + 1)};
    }""")
    print('TAC', json.dumps(st, ensure_ascii=False))
    print('TAC_SHOT', shot(page, 'm4-tac.png'))

    # 토큰 드래그
    tok = page.locator('#tac [data-tok]').first
    tb = tok.bounding_box()
    page.mouse.move(tb['x'] + tb['width'] / 2, tb['y'] + tb['height'] / 2)
    page.mouse.down()
    page.mouse.move(tb['x'] + tb['width'] / 2 + 60, tb['y'] + tb['height'] / 2 - 80, steps=10)
    page.mouse.up()
    page.wait_for_timeout(300)
    moved = page.evaluate("""() => { const t = document.querySelector('#tac [data-tok]'); return {l: t.style.left, tp: t.style.top}; }""")
    print('TOK_MOVED', moved)

    # 선 그리기
    cvb = page.locator('#tacCv').bounding_box()
    page.mouse.move(cvb['x'] + cvb['width'] * 0.2, cvb['y'] + cvb['height'] * 0.7)
    page.mouse.down()
    for i in range(12):
        page.mouse.move(cvb['x'] + cvb['width'] * (0.2 + i * 0.05), cvb['y'] + cvb['height'] * (0.7 - i * 0.03), steps=3)
    page.mouse.up()
    page.wait_for_timeout(300)
    strokes = page.evaluate("""() => ({n: document.querySelectorAll('#tacStrokes path').length,
        d: document.querySelector('#tacStrokes path') ? document.querySelector('#tacStrokes path').getAttribute('d').slice(0,40) : ''})""")
    print('STROKES', strokes)
    print('TAC_DRAWN', shot(page, 'm5-tac-drawn.png'))

    # 지우개 부분 지우기
    page.locator('#tac [data-tac-tool="erase"]').click()
    page.wait_for_timeout(200)
    mid = page.evaluate("""() => { const p = document.querySelector('#tacStrokes path'); const L = p.getTotalLength(); const pt = p.getPointAtLength(L/2);
        const r = document.querySelector('#tacCv').getBoundingClientRect(); const sv = p.ownerSVGElement.viewBox.baseVal;
        return {x: r.left + pt.x / sv.width * r.width, y: r.top + pt.y / sv.height * r.height}; }""")
    page.mouse.move(mid['x'], mid['y'])
    page.mouse.down()
    page.mouse.move(mid['x'] + 6, mid['y'] + 2, steps=3)
    page.mouse.up()
    page.wait_for_timeout(300)
    after = page.evaluate("""() => document.querySelectorAll('#tacStrokes path').length""")
    print('ERASE_PATHS', after)
    print('TAC_ERASED', shot(page, 'm6-tac-erased.png'))

    # 되돌리기
    page.locator('#tac [data-tac-act="undo"]').click()
    page.wait_for_timeout(300)
    print('UNDO_PATHS', page.evaluate("() => document.querySelectorAll('#tacStrokes path').length"))

    # 올코트
    page.locator('#tac [data-tac-court="full"]').click()
    page.wait_for_timeout(600)
    print('FULLCOURT', page.evaluate("""() => { const cv = document.querySelector('#tacCv'); const r = cv.getBoundingClientRect();
        return {w: Math.round(r.width), h: Math.round(r.height), ratio: +(r.height / r.width).toFixed(3), vb: cv.querySelector('svg').getAttribute('viewBox')}; }"""))
    print('TAC_FULL', shot(page, 'm7-tac-full.png'))

    # 초기화
    page.locator('#tac [data-tac-act="reset"]').click()
    page.wait_for_timeout(400)
    print('RESET', page.evaluate("""() => ({paths: document.querySelectorAll('#tacStrokes path').length,
        toks: document.querySelectorAll('#tac [data-tok]').length})"""))
    print('TAC_RESET', shot(page, 'm8-tac-reset.png'))

    # 닫기
    page.locator('#tac [data-tac="close"]').click()
    page.wait_for_timeout(500)
    print('CLOSED', page.evaluate("() => ({hidden: document.querySelector('#tac').hidden, fs: document.fullscreenElement ? document.fullscreenElement.id : null})"))

    print('ERRORS', json.dumps(errs[:10], ensure_ascii=False))
    ctx.close()

    # 태블릿
    ctx2 = b.new_context(viewport={'width': 1280, 'height': 800}, device_scale_factor=1)
    p2 = ctx2.new_page()
    errs2 = []
    p2.on('pageerror', lambda e: errs2.append(str(e)))
    enter(p2)
    p2.locator('#tacBtn').click()
    p2.wait_for_timeout(1000)
    t = p2.evaluate("""() => { const cv = document.querySelector('#tacCv'); const r = cv.getBoundingClientRect();
        return {w: Math.round(r.width), h: Math.round(r.height), tw: getComputedStyle(document.querySelector('.tactok')).width}; }""")
    print('TAB_TAC', t)
    p2.screenshot(path=os.path.join(OUT, 't10-tac-tablet.png'))
    p2.locator('#tac [data-tac="close"]').click()
    p2.wait_for_timeout(300)
    p2.locator('[data-mp-go]').first.click()
    p2.wait_for_timeout(1200)
    p2.screenshot(path=os.path.join(OUT, 't11-pg-tablet.png'))
    print('TAB_ERR', json.dumps(errs2[:6], ensure_ascii=False))
    ctx2.close()
    b.close()
print('DONE', sorted(os.listdir(OUT)))
