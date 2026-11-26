# 🏀 REVERSE · 리버스 승률 &amp; 주간 결과

토요일 농구팀 **리버스(REVERSE)** 의 누적 승률·주간 경기 결과를 폰에서 보기 좋게 정리한 단일 HTML 페이지입니다.

- 🌐 **https://youngik-kim.github.io/reverse-basketball/**
- 🏟 구장: 부천JW스포츠센터 · 매주 토요일 3파전(팀당 2경기)
- 📅 집계 기간: 2026-10-03 ~ 2026-11-21 (8주 · 24경기)

## 볼 수 있는 것

| 탭 | 내용 |
| --- | --- |
| 🏆 최종 승률 | 정규 순위(참여율 40%↑·4주↑ 15명), 동률 기준, 👑 팀장 전적·승률, 🔥 개근, 순위 외 7명(정규 진입 조건), 게스트 18명 |
| 📅 주간 결과 | 최신 주차부터 8주 경기 결과 — 최종 순위·팀장·스코어·팀 명단·특이사항 |

선수 이름을 **검색**하거나 **탭**하면 개인 전적 카드(승률·출전·전적·팀장 전적·주차별 상대/스코어)가 뜹니다.
`<meta name="robots" content="noindex, nofollow">` 로 검색엔진 노출은 차단되어 있습니다.

## 매주 갱신 방법

`index.html` 상단의 `const DATA = { … }` **한 곳만** 고치면 화면에 바로 반영됩니다.

1. `weeks` 배열 맨 앞에 새 주차 추가 — `date`, `title`, `venue`, `standings`, `games`, `rosters`, `note`
2. `members`(정규)·`outsiders`(순위 외)·`guests`(게스트)의 `weeks`·`att`·`w`·`l`·`rate` 갱신
   (`att` = `weeks / criteria.totalWeeks * 100`)
3. `criteria.totalWeeks`, `period` 갱신

`src/` 에는 같은 결과를 코드로 만드는 도구가 있습니다(선택).

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
