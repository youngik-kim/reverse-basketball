# -*- coding: utf-8 -*-
"""매치 프리뷰 등록·편집 창 하단 — 🧩 초기화(서버 정본) + 🏀 경기 진행하기 검증.

    python3 src/verify_mpreset.py            # 로컬 index.html
    MP_URL=... python3 src/verify_mpreset.py # 배포 페이지

검사:
  1) 등록·편집 창 하단 버튼(🏀 경기 진행하기 · 🧩 매치 프리뷰 초기화 (서버 정본)) 노출
  2) 정본 있는 날짜(2026-11-28) — 확인 팝업 → 기기 등록분 삭제 + 편집창·메인 프리뷰 정본 15명 복원
  3) 인원 미달이면 🏀 경기 진행하기가 안내만 하고 진행 화면을 열지 않음
  4) 인원이 유효하면 저장 후 경기 진행 화면으로 이동
  5) 정본 없는 날짜 — ⚙️ 설정 시트: 기기 등록분 삭제 + 0명으로 비움
  6) 정본 없는 날짜 — 등록·편집 창: 기기 등록분 삭제 + 편집창 0명
  7) JS 오류 0건
"""
import functools, http.server, io, json, os, socketserver, sys, threading
from playwright.sync_api import sync_playwright

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get('MP_OUT') or os.path.join(SITE, '_verify_mpreset')
os.makedirs(OUT, exist_ok=True)
CODE = os.environ.get('MP_CODE') or '2020'
DATA = json.loads(io.open(os.path.join(SITE, 'src', 'data.json'), encoding='utf-8').read())
CANON = DATA['preview']
CANON_DATE = CANON['date']
CANON_NAMES = [n for t in CANON['teams'] for n in t['roster']]
ALLNAMES = set([p['name'] for p in DATA['members']] + [p['name'] for p in DATA['outsiders']]
               + [g['name'] for g in DATA['guests']] + list(DATA['absent']) + CANON_NAMES)
KEY = 'reverse-match-preview-v1'
ASK = '기기에 임시 저장된 매치 프리뷰를 지우고 서버 정본 기준으로 되돌릴까요?'

# 기기(localStorage)에 들어 있는 것처럼 꾸민 등록분 — 정본이 없는 날짜
FAKE_DATE = '2026-12-05'
FAKE = {'v': 2, 'items': {
    CANON_DATE: {'v': 1, 'date': CANON_DATE, 'mode': 3, 'id': CANON_DATE + '|3',
                 'teams': [{'team': '화이트', 'cap': '테스트A', 'roster': ['테스트A', '테스트B', '테스트C']},
                           {'team': '블랙', 'cap': '테스트D', 'roster': ['테스트D', '테스트E', '테스트F']},
                           {'team': '형광', 'cap': '테스트G', 'roster': ['테스트G', '테스트H', '테스트I']}],
                 'savedAt': '2026-11-27T00:00:00Z'},
    FAKE_DATE: {'v': 1, 'date': FAKE_DATE, 'mode': 3, 'id': FAKE_DATE + '|3',
                'teams': [{'team': '화이트', 'cap': '테스트A', 'roster': ['테스트A', '테스트B', '테스트C']},
                          {'team': '블랙', 'cap': '테스트D', 'roster': ['테스트D', '테스트E', '테스트F']},
                          {'team': '형광', 'cap': '테스트G', 'roster': ['테스트G', '테스트H', '테스트I']}],
                'savedAt': '2026-11-27T00:00:00Z'}}}

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


def seed(page):
    page.evaluate("(o) => localStorage.setItem('%s', JSON.stringify(o))" % KEY, FAKE)
    page.reload(wait_until='load')
    page.wait_for_timeout(1300)


def open_editor(page):
    page.click('#mpPreviewBtn')
    page.wait_for_timeout(450)


def editor_names(page):
    return [n.replace('👑', '').strip() for n in
            page.eval_on_selector_all('#mpBody .mpeNm', 'els => els.map(e => e.innerText)')]


def stored(page):
    return page.evaluate("() => (JSON.parse(localStorage.getItem('%s') || '{}').items) || {}" % KEY)


def hist_edit(page, date):
    page.click('[data-mptab="hist"]')
    page.wait_for_timeout(250)
    page.click('[data-mphist="%s"]' % date)
    page.wait_for_timeout(300)
    page.click('[data-mphist-edit="%s"]' % date)
    page.wait_for_timeout(400)


if not os.environ.get('MP_URL'):
    html = io.open(os.path.join(SITE, 'index.html'), encoding='utf-8').read()
    ok('index.html 평문 이름 0건(정본 프리뷰 포함)', not any(n in html for n in ALLNAMES),
       [n for n in ALLNAMES if n in html][:3])
    ok('index.html 입장 코드 2020 평문 0건', CODE not in html)

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for tag, w, h in [('m', 390, 844), ('d', 1280, 800)]:
        ctx = browser.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2 if tag == 'm' else 1)
        page = ctx.new_page()
        errs = []
        page.on('console', lambda m: errs.append('console.%s: %s' % (m.type, m.text)) if m.type == 'error' else None)
        page.on('pageerror', lambda e: errs.append('pageerror: %s' % e))
        enter(page)
        ok('%s: 입장' % tag, page.locator('#secResult').is_visible())

        # ---------- 1) 편집창 하단 버튼 ----------
        open_editor(page)
        btns = page.eval_on_selector_all('#mpBody .mpeBtns button',
                                         'els => els.map(e => ({id: e.id, cls: e.className, t: e.innerText.trim()}))')
        texts = [b['t'] for b in btns]
        ok('%s: 하단 [🏀 경기 진행하기]' % tag, any(b['id'] == 'mpSaveGo' and '경기 진행하기' in b['t'] for b in btns), texts)
        ok('%s: 하단 [🧩 매치 프리뷰 초기화 (서버 정본)]' % tag,
           any(b['id'] == 'mpCanonReset' and b['t'] == '🧩 매치 프리뷰 초기화 (서버 정본)' for b in btns), texts)
        ok('%s: 기존 [📝 매치 프리뷰 등록 완료]·[취소] 유지' % tag,
           any('매치 프리뷰 등록 완료' in t for t in texts) and any(t == '취소' for t in texts), texts)
        note = txt(page, '#mpBody .mpenote')
        ok('%s: 기기 임시 저장 안내 문구' % tag,
           '현재 기기(브라우저)에만 임시 저장' in note and '서버나 다른 팀원 화면에는 반영되지 않습니다' in note, note)
        nb = page.evaluate("""() => {
          const n = document.querySelector('#mpBody .mpenote');
          const b = document.querySelector('#mpBody .mpeSave');
          return { above: n.getBoundingClientRect().bottom <= b.getBoundingClientRect().top + 1,
                   visible: n.getBoundingClientRect().height > 0 };
        }""")
        ok('%s: 안내 문구가 [매치 프리뷰 등록 완료] 바로 위' % tag, nb['above'] and nb['visible'], nb)
        page.screenshot(path='%s/%s_1_editor_footer.png' % (OUT, tag))

        # ---------- 2) 정본 있는 날짜 — 편집창 초기화 ----------
        page.click('#mpModal .x')
        page.wait_for_timeout(200)
        seed(page)
        open_editor(page)
        before = editor_names(page)
        ok('%s: 기기 등록분(테스트 9명) 편집창' % tag, any(n.startswith('테스트') for n in before), before[:3])
        page.click('#mpCanonReset')
        page.wait_for_timeout(250)
        ok('%s: 🧩 확인 팝업 열림' % tag, page.locator('#mpCanonEd').is_visible())
        dlg = txt(page, '#mpCanonEd .mpcfbox p')
        ok('%s: 확인 팝업 문구' % tag, ASK in dlg, dlg)
        page.screenshot(path='%s/%s_2_canon_confirm.png' % (OUT, tag))
        page.click('#mpCanonEd .mpcfb [data-mpcanon="cancel"]')
        page.wait_for_timeout(200)
        ok('%s: 취소 — 팝업 닫힘·편집창 그대로' % tag,
           not page.locator('#mpCanonEd').is_visible() and any(n.startswith('테스트') for n in editor_names(page)))
        page.click('#mpCanonReset')
        page.wait_for_timeout(200)
        page.click('#mpCanonEd [data-mpcanon="ok"]')
        page.wait_for_timeout(600)
        after = editor_names(page)
        ok('%s: 편집창이 정본 15명으로 복원' % tag, len(after) == 15 and set(after) == set(CANON_NAMES), after)
        ok('%s: 기기 등록분 삭제' % tag, CANON_DATE not in stored(page), list(stored(page).keys()))
        ok('%s: 팝업 닫힘' % tag, not page.locator('#mpCanonEd').is_visible())
        ok('%s: 복원 안내 토스트' % tag, '정본' in txt(page, '#mpToastEl') and '15명' in txt(page, '#mpToastEl'),
           txt(page, '#mpToastEl'))
        page.screenshot(path='%s/%s_3_canon_editor.png' % (OUT, tag))
        page.click('#mpModal .x')
        page.wait_for_timeout(300)
        card = txt(page, '#resultCard')
        ok('%s: 메인 프리뷰 정본 복원' % tag, '정본' in card and '15명' in card, card[:80].replace('\n', ' '))

        # ---------- 4) 유효하면 저장 후 경기 진행 ----------
        seed(page)
        open_editor(page)
        hist_edit(page, FAKE_DATE)
        ok('%s: 기기 등록분(12/05) 편집창' % tag, len(editor_names(page)) == 9, editor_names(page))
        page.click('#mpSaveGo')
        page.wait_for_timeout(700)
        names_pg = [n.replace('👑', '').strip() for n in
                    page.eval_on_selector_all('#pg .pgnm', 'els => els.map(e => e.innerText)')]
        ok('%s: 🏀 경기 진행하기 — 진행 화면 열림' % tag,
           page.locator('#pg').is_visible() and page.locator('#mpModal').is_hidden())
        ok('%s: 진행 명단 = 구성 인원(9명)' % tag, len(names_pg) == 9 and any(n.startswith('테스트') for n in names_pg),
           names_pg[:4])
        ok('%s: 저장 후 진행 안내 토스트' % tag, '경기 진행' in txt(page, '#mpToastEl'), txt(page, '#mpToastEl'))
        page.screenshot(path='%s/%s_5_go_progress.png' % (OUT, tag))

        # ---------- 5) 정본 없는 날짜 — ⚙️ 설정 시트 초기화 ----------
        page.click('[data-pg="set"]')
        page.wait_for_timeout(250)
        sbtn = page.locator('#pgSettings [data-pg="canon"]')
        ok('%s: ⚙️ 설정 초기화 버튼 유지' % tag, sbtn.count() == 1 and '서버 정본 복원' in sbtn.inner_text(),
           sbtn.inner_text() if sbtn.count() else '')
        sbtn.click()
        page.wait_for_timeout(250)
        ok('%s: ⚙️ 설정 확인 팝업' % tag, page.locator('#pgCanon').is_visible() and ASK in txt(page, '#pgCanon .pgcf'))
        page.click('#pgCanon [data-pg="canonok"]')
        page.wait_for_timeout(600)
        n_pg = page.eval_on_selector_all('#pg .pgnm', 'els => els.map(e => e.innerText)')
        ok('%s: 정본 없는 날짜 — 설정 시트에서 0명으로 비움' % tag, len(n_pg) == 0, n_pg)
        ok('%s: 정본 없는 날짜 — 기기 등록분 삭제' % tag, FAKE_DATE not in stored(page), list(stored(page).keys()))
        tt = txt(page, '#mpToastEl')
        ok('%s: 0명 안내 토스트' % tag, '0명' in tt and '없어' in tt, tt)
        page.screenshot(path='%s/%s_6_blank_progress.png' % (OUT, tag))
        if page.locator('#pgSettings').is_visible():
            page.click('#pgSettings [data-pg="setclose"]')
            page.wait_for_timeout(250)
        page.click('[data-pg="close"]')
        page.wait_for_timeout(300)

        # ---------- 6) 정본 없는 날짜 — 편집창 초기화 ----------
        seed(page)
        open_editor(page)
        hist_edit(page, FAKE_DATE)
        page.click('#mpCanonReset')
        page.wait_for_timeout(250)
        page.click('#mpCanonEd [data-mpcanon="ok"]')
        page.wait_for_timeout(600)
        ok('%s: 정본 없는 날짜 — 편집창 0명' % tag, len(editor_names(page)) == 0, editor_names(page))
        ok('%s: 편집창 초기화 후 기기 등록분 삭제' % tag, FAKE_DATE not in stored(page), list(stored(page).keys()))
        tt = txt(page, '#mpToastEl')
        ok('%s: 편집창 0명 안내 토스트' % tag, '0명' in tt and '빈칸' in tt, tt)
        ok('%s: 편집창 유지(닫히지 않음)' % tag, page.locator('#mpModal').is_visible())
        page.screenshot(path='%s/%s_7_blank_editor.png' % (OUT, tag))

        # ---------- 7) 인원 미달이면 🏀 경기 진행하기는 안내만 ----------
        page.click('#mpSaveGo')
        page.wait_for_timeout(400)
        ok('%s: 인원 미달 — 진행 화면 열지 않음' % tag,
           page.locator('#pg').is_hidden() and page.locator('#mpModal').is_visible())
        msg = txt(page, '#mpMsg')
        ok('%s: 인원 미달 안내 문구' % tag, '3~6명' in msg, msg)
        page.screenshot(path='%s/%s_8_go_invalid.png' % (OUT, tag))

        # ---------- JS 오류 ----------
        ok('%s: JS 오류 0건' % tag, not errs, errs[:4])
        ctx.close()
    browser.close()

print('\n%d/%d PASS' % (sum(1 for r in results if r[1]), len(results)))
sys.exit(0 if all(r[1] for r in results) else 1)
