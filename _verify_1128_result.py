# -*- coding: utf-8 -*-
"""2026-11-28 9주차 결과 반영 — 로컬 검증 (암호화 게이트 + 화면 값)"""
import os, json, subprocess, sys, time
from playwright.sync_api import sync_playwright

ROOT = '/workspace/reverse-basketball-site'
PORT = 8771
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
    page.wait_for_timeout(1600)


fails = []
def check(name, ok, detail=''):
    print(('  OK  ' if ok else '  NG  ') + name + (('  ' + str(detail)) if detail else ''))
    if not ok:
        fails.append(name)

try:
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for w, h, tag, mob in ((390, 844, 'm', True), (1280, 800, 'd', False)):
            ctx = b.new_context(viewport={'width': w, 'height': h},
                                device_scale_factor=2 if mob else 1, is_mobile=mob, has_touch=mob)
            page = ctx.new_page()
            errs = []
            page.on('pageerror', lambda e: errs.append('pageerror ' + str(e)))
            page.on('console', lambda m: errs.append('console ' + m.text) if m.type == 'error' else None)
            enter(page)
            print('==', tag, 'unlocked', not page.locator('body.locked').count())

            res = page.locator('#resultCard').inner_text().replace('\n', ' | ')
            print(tag, 'RESULT:', res[:300])
            check(f'{tag} 결과카드 공동 우승', '공동 우승 형광·화이트·블랙' in res, res[:120])
            check(f'{tag} 팀장 3명 표기', '👑 박광현·유동훈·고건우' in res)
            check(f'{tag} 3팀 1위', res.count('1위') >= 3)
            check(f'{tag} 스코어 26:28', '26:28' in res and '46:64' in res and '38:40' in res)
            check(f'{tag} 프리뷰 비교', '실제 공동 1위 형광·화이트·블랙' in res and '순위 적중 1/3' in res, res[-160:])

            hero = page.locator('#heroStats').inner_text().replace('\n', ' | ')
            print(tag, 'HERO:', hero)
            check(f'{tag} 27경기', '27경기' in hero)
            check(f'{tag} 기간 11.28', '11.28' in page.locator('#periodLine').inner_text(), page.locator('#periodLine').inner_text())

            sel = page.evaluate("() => [...document.querySelectorAll('#weekSel option')].map(o => o.textContent)")
            print(tag, 'SEL:', json.dumps(sel[-2:], ensure_ascii=False))
            check(f'{tag} 선택목록 공동 1위', '공동 1위(형광·화이트·블랙)' in sel[-1], sel[-1])
            check(f'{tag} 11/21은 단독 우승', '형광 우승' in sel[-2], sel[-2])

            rank = page.evaluate("""() => ({
              count: document.querySelector('#rankCount').textContent,
              scope: document.querySelector('#rankScope').textContent,
              crit: document.querySelector('#critInner').textContent.replace(/\\s+/g,' ').slice(0,160),
              rows: [...document.querySelectorAll('#rankBody .rrow, #regularList .rrow, .rrow')].map(r => r.innerText.replace(/\\n/g,' ')),
            })""")
            print(tag, 'RANKCOUNT:', rank['count'], '|', rank['scope'])
            print(tag, 'CRIT:', rank['crit'])
            check(f'{tag} 정규17/외5/게스트19', '정규 17' in rank['count'] and '순위 외 5' in rank['count'] and '게스트 19' in rank['count'], rank['count'])
            check(f'{tag} 9주 누적', '9주 누적' in rank['scope'], rank['scope'])
            check(f'{tag} 9주 중 4주', '9주 중 4주 이상' in rank['crit'], rank['crit'])
            rows = rank['rows']
            regular = [r for r in rows][:25]
            check(f'{tag} 나윤 1위/변동훈 8위', any(r.startswith('1') and '나윤' in r for r in regular) and any(r.startswith('8') and '변동훈' in r for r in regular), rows[:3])
            check(f'{tag} 김영익 38.9%', any('김영익' in r and '38.9%' in r for r in rows), [r for r in rows if '김영익' in r][:1])
            check(f'{tag} 개근 2명', sum(1 for r in rows if '🔥' in r) == 2, [r for r in rows if '🔥' in r])

            # 주간 결과 전체 — 최신 카드
            wk = page.evaluate("""() => { const c = document.querySelectorAll('.wkcard')[0];
               return {t: c.querySelector('summary').innerText.replace(/\\n/g,' '),
                       body: c.innerText.replace(/\\n/g,' ').slice(0, 500)}; }""")
            print(tag, 'WEEK CARD:', wk['t'][:160])
            check(f'{tag} 주간카드 공동 우승', '공동 우승 형광·화이트·블랙' in wk['t'])
            check(f'{tag} 주간카드 팀장 3', '👑 박광현·유동훈·고건우' in wk['t'])
            check(f'{tag} 주간카드 1위 3개', wk['body'].count('1승 1패') >= 3, wk['body'][:200])

            # 개인 전적 카드 — 김영익
            page.locator('.rrow', has_text='김영익').first.click()
            page.wait_for_timeout(700)
            pc = page.locator('#mBody').inner_text().replace('\n', ' | ')
            print(tag, 'PERSON:', pc[:260])
            check(f'{tag} 김영익 9주 개근', '9주' in pc and '🔥' in pc and '7승 11패' in pc, pc[:160])
            page.keyboard.press('Escape')
            page.wait_for_timeout(400)

            # 게스트 — 최정범
            page.evaluate("() => { const q = document.querySelector('#searchInput, #q'); if (q) { q.value='최정범'; q.dispatchEvent(new Event('input')); } }")
            page.wait_for_timeout(500)
            gtxt = page.locator('#rankBody, #rankWrap, body').first.inner_text()
            check(f'{tag} 최정범 게스트 노출', '최정범' in gtxt)
            page.evaluate("() => { const q = document.querySelector('#searchInput, #q'); if (q) { q.value=''; q.dispatchEvent(new Event('input')); } }")
            page.wait_for_timeout(400)

            page.screenshot(path=f'{OUT}/{tag}-1-top.png')
            page.locator('.rrow', has_text='나윤').first.scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            page.screenshot(path=f'{OUT}/{tag}-2-rank.png')

            # 주요 변경점
            page.locator('#logBtn').click()
            page.wait_for_timeout(600)
            log = page.locator('#logModal').inner_text()
            check(f'{tag} 변경점 기록 항목', '2026-11-28 9주차 경기 결과 반영' in log and '3팀 공동 1위' in log)
            page.screenshot(path=f'{OUT}/{tag}-3-log.png')
            page.keyboard.press('Escape')
            page.wait_for_timeout(300)

            # 경기 진행 — 이력 프리뷰 → 🏀 경기 진행하기
            page.locator('#resultCard [data-pv-view]').first.click()
            page.wait_for_selector('#mpModal:not([hidden])')
            page.wait_for_timeout(900)
            pv = page.locator('#mpBody').inner_text().replace('\n', ' | ')
            print(tag, 'PVVIEW:', pv[:240])
            check(f'{tag} 프리뷰 이력 공동 우승', '공동 우승' in pv and '실제 1위' in pv, pv[:200])
            page.locator('[data-mphist-go]').first.click()
            page.wait_for_timeout(1600)
            pg = page.evaluate("""() => ({open: document.querySelector('#pg').classList.contains('open'),
                 teams: [...document.querySelectorAll('#pg .pgteam, #pg .pgrow')].length,
                 names: [...document.querySelectorAll('#pg .pgnm')].map(e => e.innerText.trim()).slice(0,20)})""")
            print(tag, 'PG:', json.dumps(pg, ensure_ascii=False)[:300])
            check(f'{tag} 경기진행 15명', pg['open'] and len([n for n in pg['names'] if n]) >= 15)
            page.screenshot(path=f'{OUT}/{tag}-4-pg.png')
            page.locator('#pg [data-pg="close"]').click()
            page.wait_for_timeout(400)

            check(f'{tag} JS 오류 없음', not errs, errs[:3])
            ctx.close()
        b.close()
finally:
    srv.terminate()

print('\nFAILS:', fails if fails else 'none')
sys.exit(1 if fails else 0)
