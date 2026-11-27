# -*- coding: utf-8 -*-
"""경기진행패치 4건 + 테마 3단계 검증.

    python3 src/verify_patch4.py            # 로컬 index.html
    MP_URL=... python3 src/verify_patch4.py # 배포 페이지

검사: 기본 글씨 '크게', 휴식 횟수 0→1→2→3→0, 매치 프리뷰 초기화(정본 15명 복원),
      확정 주차 정본 프리뷰 우선 표시(테스트 정본 주차), 테마 어두운/중간/밝은 + PNG 반영,
      가로 좌우 비율 59:41·명단 잘림 0, JS 오류 0건.
"""
import functools, http.server, io, json, os, socketserver, sys, threading
from playwright.sync_api import sync_playwright

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get('MP_OUT') or os.path.join(SITE, '_verify_patch4')
os.makedirs(OUT, exist_ok=True)
CODE = os.environ.get('MP_CODE') or '2020'
DATA = json.loads(io.open(os.path.join(SITE, 'src', 'data.json'), encoding='utf-8').read())
CANON = DATA['preview']
CANON_NAMES = [n for t in CANON['teams'] for n in t['roster']]
ALLNAMES = set([p['name'] for p in DATA['members']] + [p['name'] for p in DATA['outsiders']]
               + [g['name'] for g in DATA['guests']] + list(DATA['absent']) + CANON_NAMES)

URL = os.environ.get('MP_URL')

httpd = None
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


def txt(page, sel):
    try:
        return page.inner_text(sel)
    except Exception:
        return ''


def enter(page):
    page.goto(URL, wait_until='load')
    page.evaluate("localStorage.clear()")
    page.reload(wait_until='load')
    page.wait_for_timeout(250)
    page.fill('#gateCode', CODE)
    page.click('#gateBtn')
    page.wait_for_timeout(1200)


def close_settings(page):
    if page.locator('#pgSettings').is_visible():
        page.keyboard.press('Escape')
        page.wait_for_timeout(200)


def open_progress(page):
    card = page.locator('#resultCard [data-mp-go]').first
    if card.count():
        card.click()
    else:
        page.locator('[data-mp-go]').first.click()
    page.wait_for_timeout(550)


if not os.environ.get('MP_URL'):
    html = io.open(os.path.join(SITE, 'index.html'), encoding='utf-8').read()
    ok('index.html 평문 이름 0건(정본 프리뷰 포함)', not any(n in html for n in ALLNAMES),
       [n for n in ALLNAMES if n in html][:3])
    ok('index.html 입장 코드 2020 평문 0건', CODE not in html)

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for tag, w, h in [('m', 390, 844), ('d', 1280, 800)]:
        ctx = browser.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2 if tag == 'm' else 1,
                                  accept_downloads=True)
        page = ctx.new_page()
        errs = []
        page.on('console', lambda m: errs.append('console.%s: %s' % (m.type, m.text)) if m.type == 'error' else None)
        page.on('pageerror', lambda e: errs.append('pageerror: %s' % e))
        enter(page)
        ok('%s: 입장' % tag, page.locator('#secResult').is_visible())

        # ---------- 경기 결과 위 중복 등록 버튼 제거 ----------
        ok('%s: 경기 결과 위 중복 등록 버튼 없음' % tag,
           page.locator('#mpRegBtn').count() == 0 and page.locator('#secResult .mpbar').count() == 0
           and '매치 프리뷰 등록하기' not in txt(page, '#secResult .shead'))
        hero = page.locator('#mpPreviewBtn')
        ok('%s: 상단 히어로 📝 매치 프리뷰 유지' % tag,
           hero.is_visible() and '매치 프리뷰' in hero.inner_text(), hero.inner_text().replace('\n', ' ') if hero.count() else '')
        ok('%s: 결과 카드가 섹션 제목 바로 아래' % tag, page.evaluate("""() => {
              const s = document.querySelector('#secResult .shead').getBoundingClientRect();
              const c = document.querySelector('#resultCard').getBoundingClientRect();
              return c.top - s.bottom < 26;
            }"""))

        # ---------- 매치 프리뷰 카드(정본 11/28) ----------
        card = txt(page, '#resultCard')
        ok('%s: 예정 카드 정본 프리뷰(11/28)' % tag, '2026-11-28' in card and '정본' in card, card[:70].replace('\n', ' '))
        page.screenshot(path='%s/%s_0_home.png' % (OUT, tag))

        # ---------- 1) 기본 글씨 크게 ----------
        open_progress(page)
        ok('%s: 경기 진행 열림' % tag, page.locator('#pg').is_visible())
        page.click('[data-pg="set"]')
        page.wait_for_timeout(250)
        fontbtn = txt(page, '#pgSettings [data-pg="font"]')
        ok('%s: 기본 글씨 크게' % tag, '크게' in fontbtn, fontbtn)
        ok('%s: 내부 scale=2(크게)' % tag, page.evaluate("() => PGS.scale") == 2, page.evaluate("() => PGS.scale"))
        page.click('#pgSettings [data-pg="font"]')
        page.wait_for_timeout(220)
        ok('%s: 크게 → 다음 단계 작게(순환)' % tag, '작게' in txt(page, '#pgSettings [data-pg="font"]'), txt(page, '#pgSettings [data-pg="font"]'))
        page.click('#pgSettings [data-pg="font"]')
        page.wait_for_timeout(180)
        page.click('#pgSettings [data-pg="font"]')
        page.wait_for_timeout(180)
        ok('%s: 다시 크게(기본값 유지)' % tag, '크게' in txt(page, '#pgSettings [data-pg="font"]'))
        page.screenshot(path='%s/%s_1_settings.png' % (OUT, tag))

        # ---------- 테마 3단계 ----------
        th = page.eval_on_selector_all('#pgSettings [data-pgtheme]', 'els => els.map(e => ({v: e.dataset.pgtheme, t: e.innerText.trim(), on: e.getAttribute("aria-pressed")}))')
        ok('%s: 테마 3단계(어두운·중간·밝은)' % tag,
           [x['v'] for x in th] == ['dark', 'mid', 'light'] and all(k in th[i]['t'] for i, k in enumerate(['어두운', '중간', '밝은'])), th)
        ok('%s: 기본 테마 = 어두운' % tag, [x['on'] for x in th][0] == 'true', th)
        themeres = {}
        for v, expect_bg in [('mid', 'rgb(220, 227, 236)'), ('light', 'rgb(241, 244, 248)'), ('dark', None)]:
            page.click('#pgSettings [data-pgtheme="%s"]' % v)
            page.wait_for_timeout(260)
            got = page.evaluate("() => { const pg = document.querySelector('#pg');"
                                " return {cls: pg.className, bg: getComputedStyle(pg).backgroundColor,"
                                " tx: getComputedStyle(pg).color, on: document.querySelector('#pgSettings [data-pgtheme=\"%s\"]').getAttribute('aria-pressed')}; }" % v)
            themeres[v] = got
            ok('%s: %s 테마 적용' % (tag, v), (('pg-' + v) in got['cls']) and got['on'] == 'true'
               and (expect_bg is None or got['bg'] == expect_bg), got)
            if v != 'dark':
                vars_ = page.evaluate("() => { const s = getComputedStyle(document.querySelector('#pg'));"
                                      " return [s.getPropertyValue('--pg-card').trim(), s.getPropertyValue('--pg-in').trim()]; }")
                want = ['#f9fafb', '#f8fafc'] if v == 'light' else ['#edf1f6', '#ffffff']
                ok('%s: %s 테마 카드·입력칸 %s' % (tag, v, '오프화이트' if v == 'light' else '소프트 그레이'), vars_ == want, vars_)
            page.screenshot(path='%s/%s_2_theme_%s.png' % (OUT, tag, v))

        # 중간 테마 상태로 돌아가 명단 잘 보이는지 확인
        page.click('#pgSettings [data-pgtheme="mid"]')
        page.wait_for_timeout(260)

        # ---------- 가로 비율 ----------
        ratio = page.evaluate("""() => {
            const l = document.querySelector('#pg .pgcol.pgl').getBoundingClientRect();
            const r = document.querySelector('#pg .pgcol.pgr').getBoundingClientRect();
            const rows = [...document.querySelectorAll('#pg .pgrow')].map(e => e.scrollWidth - e.clientWidth);
            const names = [...document.querySelectorAll('#pg .pgnm')].map(e => e.scrollWidth - e.clientWidth);
            return { l: Math.round(l.width), r: Math.round(r.width), pct: Math.round(l.width / (l.width + r.width) * 100),
                     rowOver: rows.filter(x => x > 1).length, nameOver: names.filter(x => x > 1).length,
                     nOver: document.querySelector('#pgBody').scrollWidth - document.querySelector('#pgBody').clientWidth };
        }""")
        if tag == 'd':
            ok('d: 가로 좌우 비율 점수표 59%% 내외(레프트 %d : 라이트 %d)' % (ratio['l'], ratio['r']), 57 <= ratio['pct'] <= 61, ratio)
            ok('d: 명단 3열 잘림 0', ratio['rowOver'] == 0 and ratio['nameOver'] == 0, ratio)
            ok('d: 가로 본문 가로 넘침 0', ratio['nOver'] <= 1, ratio['nOver'])
        else:
            ok('m: 세로 모드 본문 가로 넘침 0', ratio['nOver'] <= 1, ratio['nOver'])
        page.screenshot(path='%s/%s_3_board_mid.png' % (OUT, tag))

        # ---------- 2) 휴식 횟수 0→1→2→3→0 ----------
        close_settings(page)
        rc = page.locator('#pg .pgrc').first
        seq = []
        for _ in range(4):
            rc.click()
            page.wait_for_timeout(120)
            seq.append(txt(page, '#pg .pgrc'))
        ok('%s: 휴식 횟수 순환 1→2→3→0' % tag, seq == ['1회', '2회', '3회', '0회'], seq)
        page.click('[data-pg="set"]')
        page.wait_for_timeout(200)
        note = txt(page, '#pgSettings .pgnote')
        ok('%s: 안내 문구 0→1→2→3→0' % tag, '0→1→2→3→0' in note, note[:90])

        # ---------- 3) 매치 프리뷰 초기화(정본 복원) ----------
        # 기기에 엉뚱한 프리뷰를 등록해 둔 상태를 만듭니다 (11/28 · 3팀 × 3명)
        fake = {'v': 2, 'items': {'2026-11-28': {'v': 1, 'date': '2026-11-28', 'mode': 3,
                'teams': [{'team': '화이트', 'cap': '테스트A', 'roster': ['테스트A', '테스트B', '테스트C']},
                          {'team': '블랙', 'cap': '테스트D', 'roster': ['테스트D', '테스트E', '테스트F']},
                          {'team': '형광', 'cap': '테스트G', 'roster': ['테스트G', '테스트H', '테스트I']}],
                'savedAt': '2026-11-27T00:00:00Z'}}}
        page.evaluate("(o) => localStorage.setItem('reverse-match-preview-v1', JSON.stringify(o))", fake)
        close_settings(page)
        page.click('[data-pg="close"]')
        page.wait_for_timeout(200)
        open_progress(page)
        names_now = page.eval_on_selector_all('#pg .pgnm', 'els => els.map(e => e.innerText.trim())')
        ok('%s: 기기 등록 프리뷰(테스트 9명)로 진행 화면 열림' % tag,
           names_now[:1] == ['테스트A'] or any(n.startswith('테스트') for n in names_now), names_now[:4])
        page.click('[data-pg="set"]')
        page.wait_for_timeout(220)
        cbtn = page.locator('#pgSettings [data-pg="canon"]')
        ok('%s: ⚙️ 설정에 매치 프리뷰 초기화 버튼' % tag,
           cbtn.count() == 1 and '매치 프리뷰 초기화' in cbtn.inner_text() and '서버 정본 복원' in cbtn.inner_text(),
           cbtn.inner_text() if cbtn.count() else '')
        cbtn.click()
        page.wait_for_timeout(250)
        dlgtxt = txt(page, '#pgCanon .pgcf p')
        ok('%s: 확인 팝업 문구' % tag,
           '기기에 임시 저장된 매치 프리뷰를 지우고 서버 정본 기준으로 되돌릴까요?' in dlgtxt, dlgtxt)
        page.screenshot(path='%s/%s_4_canon_confirm.png' % (OUT, tag))
        page.click('#pgCanon [data-pg="canonok"]')
        page.wait_for_timeout(600)
        names_after = page.eval_on_selector_all('#pg .pgnm', 'els => els.map(e => e.innerText.replace(/👑/g, "").trim())')
        stored = page.evaluate("() => JSON.parse(localStorage.getItem('reverse-match-preview-v1') || '{}').items || {}")
        ok('%s: 정본 15명 복원' % tag, len(names_after) == 15 and set(names_after) == set(CANON_NAMES), names_after)
        ok('%s: 기기 등록분 삭제' % tag, '2026-11-28' not in stored, list(stored.keys()))
        ok('%s: 복원 안내 토스트' % tag, '정본' in txt(page, '#mpToastEl'), txt(page, '#mpToastEl'))
        page.screenshot(path='%s/%s_5_canon_restored.png' % (OUT, tag))

        # ---------- 4-예정) 예정 날짜는 기기 등록분 우선 ----------
        page.evaluate("(o) => localStorage.setItem('reverse-match-preview-v1', JSON.stringify(o))", fake)
        close_settings(page)
        page.click('[data-pg="close"]')
        page.wait_for_timeout(200)
        page.reload(wait_until='load')
        page.wait_for_timeout(1200)
        open_progress(page)
        names_expect = page.eval_on_selector_all('#pg .pgnm', 'els => els.map(e => e.innerText.replace(/👑/g, "").trim())')
        ok('%s: 예정 날짜(11/28)는 기기 등록분 우선' % tag,
           any(n.startswith('테스트') for n in names_expect), names_expect[:3])

        # ---------- PNG 사진 저장(테마 반영) ----------
        page.click('[data-pg="set"]')
        page.wait_for_timeout(200)
        page.click('#pgSettings [data-pgtheme="mid"]')
        page.wait_for_timeout(260)
        with page.expect_download() as dl:
            page.click('#pgSettings [data-pg="png"]')
        path = dl.value.path()
        png_mid = os.path.join(OUT, '%s_png_mid.png' % tag)
        dl.value.save_as(png_mid)
        ok('%s: 사진 저장(PNG) 파일' % tag, os.path.getsize(png_mid) > 20000, os.path.getsize(png_mid))

        # ---------- JS 오류 ----------
        ok('%s: JS 오류 0건' % tag, not errs, errs[:4])
        ctx.close()
    browser.close()

print('\n%d/%d PASS' % (sum(1 for r in results if r[1]), len(results)))
sys.exit(0 if all(r[1] for r in results) else 1)
