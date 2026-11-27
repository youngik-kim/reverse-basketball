# -*- coding: utf-8 -*-
"""2파전 합계 표기 · 동률 공동순위 · A4 인쇄 · PNG 저장 검증."""
import os, json
from playwright.sync_api import sync_playwright

URL = 'http://127.0.0.1:8765/index.html'
OUT = '/workspace/screens/reverse-1128'
os.makedirs(OUT, exist_ok=True)

with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, accept_downloads=True)
    page = ctx.new_page()
    errs = []
    page.on('pageerror', lambda e: errs.append(str(e)))
    page.goto(URL, wait_until='load')
    page.evaluate("localStorage.clear()")
    page.reload(wait_until='load')
    page.wait_for_timeout(300)
    page.fill('#gateCode', '2020')
    page.click('#gateBtn')
    page.wait_for_timeout(1500)

    # ── 2파전 매치를 페이지에 직접 넣어 렌더 검증 (UI 우회) ──
    page.evaluate("""() => {
      const names = (t) => [...document.querySelectorAll('#pg .pgrow')]; // unused
      MPS = { v: 1, date: '2026-11-28', mode: 2, id: '2026-11-28|2',
        teams: [{ team: '블랙', roster: ['박광현','김준성','심호길','김현준','최정범'], cap: '박광현' },
                { team: '화이트', roster: ['변정훈','정승혁','유동훈','나윤','김영익'], cap: '유동훈' }] };
      mpOpenProgress();
    }""")
    page.wait_for_timeout(1200)
    print('MODE2', page.evaluate("""() => ({mode: document.querySelector('#pg').className,
        games: document.querySelectorAll('#pg .pgtbl.g2 tbody tr').length})"""))
    inputs = page.locator('#pg .sci')
    vals = [10, 8, 20, 16, 30, 24]
    for i, v in enumerate(vals):
        inputs.nth(i).fill(str(v)); inputs.nth(i).dispatch_event('input')
    page.wait_for_timeout(600)
    print('MODE2_TOT', page.evaluate("""() => [...document.querySelectorAll('#pg .pgtot')].map(t => t.innerText.replace(/\\n/g,' | '))"""))
    print('MODE2_TOTW', page.evaluate("""() => [...document.querySelectorAll('#pg .totw')].map(e => ({t: e.innerText.replace(/\\n/g,' '),
        over: e.scrollWidth > e.clientWidth + 1, w: Math.round(e.getBoundingClientRect().width), sw: e.scrollWidth}))"""))
    print('MODE2_SUM', page.evaluate("""() => [...document.querySelectorAll('#pg .pgs')].map(t => t.innerText.replace(/\\n/g,' | '))"""))
    page.screenshot(path=os.path.join(OUT, 'm9-mode2.png'))

    # ── 동률(공동 순위) — 3파전에서 두 팀이 같은 승률 ──
    page.evaluate("""() => { mpCloseProgress(); MPS = null; }""")
    page.wait_for_timeout(400)
    page.locator('[data-mp-go]').first.click()
    page.wait_for_timeout(1000)
    page.evaluate("""() => { document.querySelectorAll('#pg .sci').forEach(i => { i.value=''; }); }""")
    page.evaluate("""() => { PGS.scores = {}; mpSavePGS(); mpPaintProgress(true); }""")
    page.wait_for_timeout(300)
    # 매치업1: 형광 10:10 화이트, 매치업2: 화이트 20:10 블랙, 매치업3: 블랙 10:10 형광 → 모두 1승0무1패? 계산:
    # 형광: 1무(화이트) + 1무(블랙) = 0승 2무 / 화이트: 1무 + 1승 / 블랙: 1패 + 1무
    # 대신 두 팀 모두 1승1패가 되도록: 형광-화이트 10:5, 화이트-블랙 12:9, 블랙-형광 11:7
    page.evaluate("""() => {
      const s = PGS, mus = mpMatchups(MPS);
      const set = (mi, q, a, b2) => { const A = mus[mi][0], B = mus[mi][1];
        mpSetScore(s, A, B, q, null, A, a); mpSetScore(s, A, B, q, null, B, b2); };
      set(0, 1, 10, 5);   // 형광 vs 화이트 → 형광 승
      set(1, 1, 12, 9);   // 화이트 vs 블랙 → 화이트 승
      set(2, 1, 11, 7);   // 블랙 vs 형광 → 블랙 승
      mpSavePGS(); mpPaintProgress(true);
    }""")
    page.wait_for_timeout(600)
    print('TIE_SUM', page.evaluate("""() => [...document.querySelectorAll('#pg .pgs')].map(t => t.innerText.replace(/\\n/g,' | '))"""))
    print('TIE_TOT', page.evaluate("""() => [...document.querySelectorAll('#pg .pgtot')].map(t => t.innerText.replace(/\\n/g,' | '))"""))
    page.screenshot(path=os.path.join(OUT, 'm10-tie.png'))

    # ── A4 인쇄 미리보기 (print CSS) ──
    page.emulate_media(media='print')
    page.wait_for_timeout(400)
    page.screenshot(path=os.path.join(OUT, 'm11-print.png'), full_page=True)
    print('PRINT_TOTW', page.evaluate("""() => { const e = document.querySelector('#pg .totw'); if (!e) return null;
        const cs = getComputedStyle(e); return {fs: cs.fontSize, color: cs.color, disp: cs.display, txt: e.innerText.replace(/\\n/g,' ')}; }"""))
    page.emulate_media(media='screen')
    page.wait_for_timeout(300)

    # ── PNG 저장 ──
    page.locator('#pg [data-pg="set"]').click()
    page.wait_for_timeout(400)
    with page.expect_download(timeout=20000) as d1:
        page.locator('#pg [data-pg="png"]').click()
    dl = d1.value
    p1 = os.path.join(OUT, 'png-' + (dl.suggested_filename or 'shot.png'))
    dl.save_as(p1)
    print('PNG1', dl.suggested_filename, os.path.getsize(p1))
    page.wait_for_timeout(1500)
    print('DL_FILES', [f for f in os.listdir(OUT) if f.startswith('png-')])
    print('ERR', json.dumps(errs[:6], ensure_ascii=False))
    ctx.close()
    b.close()
print('DONE')
