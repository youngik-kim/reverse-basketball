# 🏀 REVERSE · 리버스 승률 &amp; 주간 결과

토요일 농구팀 **리버스(REVERSE)** 의 누적 승률·주간 경기 결과를 폰에서 보기 좋게 정리한 단일 HTML 페이지입니다.

- 🌐 **https://youngik-kim.github.io/reverse-basketball/**
- 🏟 구장: 부천JW스포츠센터 · 매주 토요일 3파전(팀당 2경기)
- 📅 집계 기간: 2026-10-03 ~ 2026-11-21 (8주 · 24경기)

## 화면 구성

첫 화면에서 **최근 경기 결과**와 **최종 승률(정규 순위)** 을 함께 볼 수 있습니다.

1. **주차 선택 바(상단 고정)** — `‹` / 날짜 드롭다운(8주) / `›` / `최신`. 과거 날짜를 고르면 그 주차 경기 결과와 **그 주차까지의 누적 승률·순위·팀장 전적·게스트**로 화면 전체가 바뀝니다.
2. **경기 결과** — 선택 주차의 우승팀, 3팀 전적·팀장, 스코어, 팀 명단·특이사항
3. **최종 승률** — 정규 순위(참여율 40%↑), 순위 외(정규 진입 조건), 👑 팀장 전적, 🔥 개근, 👥 게스트
4. **주간 결과 전체** — 최신 주차부터 8주 아코디언

선수 이름을 검색하거나 누르면 개인 전적 카드(승률·출전·전적·팀장 전적·주차별 상대/스코어)가 뜹니다.
`<meta name="robots" content="noindex, nofollow">` 로 검색엔진 노출은 차단되어 있습니다.

정규 순위 커트라인은 그때까지 진행된 주차의 40%(올림)이며, 최종 8주에서는 기록지 기준과 같은 **4주**가 됩니다. 최종 주차 화면의 값은 기록지 표와 전건 일치합니다.

## 매주 갱신 방법

`index.html` 상단의 `const DATA = { … }` **한 곳만** 고치면 화면에 바로 반영됩니다.

1. `weeks` 배열에 새 주차 추가 — `date`, `title`, `venue`, `standings`, `games`, `rosters`, `note`
   - 결과지가 아직 없는 주차는 `{ "date": "2026-09-26", "noSheet": true }` 로 넣으면 화면에 **"원본 결과지 보완 예정"** 으로 표시됩니다.
2. `members`(정규)·`outsiders`(순위 외)·`guests`(게스트)는 **최종 주차 공식 기록** — `weeks`·`att`·`w`·`l`·`rate` 갱신 (`att` = `weeks / criteria.totalWeeks * 100`)
3. `criteria.totalWeeks`, `period` 갱신

과거 주차 화면은 `weeks` 의 로스터·스코어에서 자동 재계산되므로 위 1번만 채우면 됩니다.

`src/` 에는 결과지 마크다운에서 DATA를 만드는 도구가 있습니다(선택).

```bash
# basketball/reverse-records.md · reverse-guests.md 를 읽어 src/data.json 재생성 + 검증
python3 src/build_data.py
# template.html + data.json -> index.html
python3 src/build_site.py
```

`build_data.py` 는 주차별 로스터로 개인 전적을 다시 계산해 기록지 표와 대조합니다(불일치 시 출력).

## 구조

```
index.html        배포 페이지 (단일 파일, DATA 내장)
src/template.html 페이지 템플릿
src/data.json     DATA 원본 (기록지에서 자동 추출)
src/build_*.py    데이터 추출·검증 및 빌드 스크립트
```
