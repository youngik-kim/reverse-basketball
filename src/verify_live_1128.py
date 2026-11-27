# -*- coding: utf-8 -*-
"""배포본(라이브) 검증 — 2026-11-28 개편 5종 + 🏀 작전판."""
import os, json, re
from playwright.sync_api import sync_playwright

BASE = 'https://youngik-kim.github.io/reverse-basketball/'
URL = BASE + '?v=1128a'
OUT = '/workspace/screens/reverse-1128-live'
os.makedirs(OUT, exist_ok=True)


def enter(page):
    page.goto(URL, wait_until='load')
    page.evaluate("localStorage.clear()")
    page.goto(URL, wait_until='load')
    page.wait_for_timeout(400)
    page.fill('#gateCode', '2020')
    page.click('#gateBtn')
    page.wait_for_timeout(1800)


with sync_playwright() as pw:
    b = pw.chromium.launch()
    for w, h, tag, mob in ((390, 844, 'm', True), (1280, 800, 't', False)):
        ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2 if mob else 1,
                            is_mobile=mob, has_touch=mob)
        page = ctx.new_page()
        errs = []
        page.on('pageerror', lambda e: errs.append(str(e)))
        page.on('console', lambda m: errs.append('c:' + m.text) if m.type == 'error' else None)
        enter(page)
        print('==', tag, 'loaded', page.title())

        hero = page.evaluate("""() => { const bs = [...document.querySelectorAll('.duobtns .pairbtn')];
          return {n: bs.length, tops: [...new Set(bs.map(b => Math.round(b.getBoundingClientRect().top)))],
            clip: bs.filter(b => b.scrollWidth > b.clientWidth + 1).map(b => b.innerText),
            labels: bs.map(b => b.querySelector('.pbtxt').textContent)}; }""")
        print(tag, 'HERO', json.dumps(hero, ensure_ascii=False))
        page.screenshot(path=os.path.join(OUT, '%s-1-hero.png' % tag))

        # 경기 진행 — 전체화면 자동
        page.locator('[data-mp-go]').first.click()
        page.wait_for_timeout(1600)
        print(tag, 'FS', page.evaluate("() => ({el: document.fullscreenElement ? document.fullscreenElement.id : null, iw: innerWidth, ih: innerHeight})"))

        # 점수 입력 → 합계 승리팀 · 순위
        inputs = page.locator('#pg .sci')
        vals = [12, 8, 20, 15, 10, 10, 18, 20, 14, 9, 25, 21, 9, 15, 16, 22]
        for i, v in enumerate(vals[:inputs.count()]):
            inputs.nth(i).fill(str(v))
            inputs.nth(i).dispatch_event('input')
        page.wait_for_timeout(800)
        print(tag, 'TOT', json.dumps(page.evaluate("() => [...document.querySelectorAll('#pg .pgtot')].map(t => t.innerText.replace(/\\n/g,' | '))"), ensure_ascii=False))
        print(tag, 'SUM', json.dumps(page.evaluate("() => [...document.querySelectorAll('#pg .pgs')].map(t => t.innerText.replace(/\\n/g,' | '))"), ensure_ascii=False))
        print(tag, 'TOTW_OVER', page.evaluate("() => [...document.querySelectorAll('#pg .totw')].filter(e => e.scrollWidth > e.clientWidth + 1).length"))
        page.screenshot(path=os.path.join(OUT, '%s-2-pg.png' % tag))

        # 명단 드래그 (이름 칸)
        before = page.evaluate("() => [...[...document.querySelectorAll('#pg .pgrows')][0].querySelectorAll('.pgrow')].map(r => r.getAttribute('data-row-name'))")
        nm = page.locator('#pg .pgrows').first.locator('.pgrow').nth(3).locator('.pgnm').bounding_box()
        page.mouse.move(nm['x'] + nm['width'] / 2, nm['y'] + nm['height'] / 2)
        page.mouse.down()
        page.mouse.move(nm['x'] + nm['width'] / 2, nm['y'] + nm['height'] / 2 - 60, steps=8)
        page.mouse.move(nm['x'] + nm['width'] / 2, nm['y'] + nm['height'] / 2 - 170, steps=8)
        page.mouse.up()
        page.wait_for_timeout(700)
        after = page.evaluate("() => [...[...document.querySelectorAll('#pg .pgrows')][0].querySelectorAll('.pgrow')].map(r => r.getAttribute('data-row-name'))")
        print(tag, 'DRAG', before != after, before, '->', after)
        page.screenshot(path=os.path.join(OUT, '%s-3-drag.png' % tag))

        # 작전판
        page.locator('#pg [data-pg="close"]').click()
        page.wait_for_timeout(500)
        page.locator('#tacBtn').click()
        page.wait_for_timeout(1400)
        tac = page.evaluate("""() => { const el = document.querySelector('#tac'), cv = document.querySelector('#tacCv');
          const toks = [...el.querySelectorAll('[data-tok]')];
          return {open: !el.hidden, fs: document.fullscreenElement ? document.fullscreenElement.id : null,
            tok: toks.length, ball: !!el.querySelector('[data-ball]'),
            cw: Math.round(cv.getBoundingClientRect().width), ch: Math.round(cv.getBoundingClientRect().height),
            row: document.querySelector('#tacStage').classList.contains('row'),
            panel: !!el.querySelector('.tacpanel'), foot: [...el.querySelectorAll('.tacfoot button')].length,
            chips: [...el.querySelectorAll('.tacmu')].map(c => c.innerText.replace(/\\n/g, ' '))}; }""")
        print(tag, 'TAC', json.dumps(tac, ensure_ascii=False))
        page.screenshot(path=os.path.join(OUT, '%s-4-tac.png' % tag))

        # 선 긋기 + 지우개 + 되돌리기
        cvb = page.locator('#tacCv').bounding_box()
        page.mouse.move(cvb['x'] + cvb['width'] * 0.2, cvb['y'] + cvb['height'] * 0.65)
        page.mouse.down()
        for i in range(10):
            page.mouse.move(cvb['x'] + cvb['width'] * (0.2 + i * 0.06), cvb['y'] + cvb['height'] * (0.65 - i * 0.035), steps=2)
        page.mouse.up()
        page.wait_for_timeout(300)
        page.screenshot(path=os.path.join(OUT, '%s-5-tac-drawn.png' % tag))
        page.locator('#tac [data-tac-tool="erase"]').click()
        mid = page.evaluate("""() => { const p = document.querySelector('#tacStrokes path'); if (!p) return null; const L = p.getTotalLength(); const pt = p.getPointAtLength(L / 2);
          const r = document.querySelector('#tacCv').getBoundingClientRect(); const sv = p.ownerSVGElement.viewBox.baseVal;
          return {x: r.left + pt.x / sv.width * r.width, y: r.top + pt.y / sv.height * r.height}; }""")
        if mid:
            page.mouse.move(mid['x'], mid['y']); page.mouse.down(); page.mouse.move(mid['x'] + 8, mid['y'] + 3, steps=3); page.mouse.up()
        page.wait_for_timeout(300)
        print(tag, 'PATHS', page.evaluate("() => ({after_erase: document.querySelectorAll('#tacStrokes path').length})"))
        page.locator('#tac [data-tac-act="undo"]').click(); page.wait_for_timeout(300)
        print(tag, 'AFTER_UNDO', page.evaluate("() => document.querySelectorAll('#tacStrokes path').length"))
        page.locator('#tac [data-tac-court="full"]').click(); page.wait_for_timeout(700)
        page.screenshot(path=os.path.join(OUT, '%s-6-tac-full.png' % tag))
        page.locator('#tac [data-tac-court="half"]').click(); page.wait_for_timeout(500)
        page.locator('#tac [data-tac-act="reset"]').click(); page.wait_for_timeout(400)
        page.locator('#tac [data-tac="close"]').click(); page.wait_for_timeout(400)
        print(tag, 'CLOSED', page.evaluate("() => ({hidden: document.querySelector('#tac').hidden, fs: document.fullscreenElement ? document.fullscreenElement.id : null})"))

        # 주요 변경점
        page.locator('#logBtn').click()
        page.wait_for_timeout(500)
        logtxt = page.evaluate("() => { const m = document.querySelector('#logModal'); return m ? m.innerText.slice(0, 260) : null; }")
        print(tag, 'LOG', (logtxt or '').replace('\n', ' / ')[:240])
        page.screenshot(path=os.path.join(OUT, '%s-7-log.png' % tag))
        print(tag, 'ERR', json.dumps(errs[:5], ensure_ascii=False))
        ctx.close()
    b.close()
print('DONE', sorted(os.listdir(OUT)))
