# -*- coding: utf-8 -*-
"""리버스 웹페이지용 DATA 생성 + 누적 기록 검증 (원본: basketball/reverse-records.md, reverse-guests.md)"""
import json, re, sys, io, os

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(SITE)
rec = io.open(ROOT + "/basketball/reverse-records.md", encoding="utf-8").read()
gst = io.open(ROOT + "/basketball/reverse-guests.md", encoding="utf-8").read()

def clean(s):
    return s.replace("**", "").replace("`", "").strip()

def parse_name(cell):
    c = clean(cell)
    captain = "👑" in c
    perfect = "🔥" in c
    name = c.replace("👑", "").replace("🔥", "").strip()
    return name, captain, perfect

def rows(text):
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("|") and not re.match(r"^\|[\s\-|]+\|$", line):
            cells = [c.strip() for c in line.strip("|").split("|")]
            out.append(cells)
    return out

# ---------- 정규 / 순위 외 ----------
reg_block = rec.split("## 🏆 정규 순위")[1].split("## ⏳ 순위 외")[0]
out_block = rec.split("## ⏳ 순위 외")[1].split("## 📅 주간 경기 로그")[0]

members = []
for r in rows(reg_block)[1:]:
    name, cap, perf = parse_name(r[1])
    weeks = int(re.search(r"(\d+)주", r[2]).group(1))
    att = float(re.search(r"\(([\d.]+)%\)", r[2]).group(1))
    m = re.search(r"(\d+)승\s*(\d+)패", r[3])
    w, l = int(m.group(1)), int(m.group(2))
    rate = float(clean(r[4]).replace("%", ""))
    lead = None
    lm = re.search(r"(\d+)승\s*(\d+)패\s*\(([\d.]+)%\)", clean(r[5]))
    if lm:
        lead = {"w": int(lm.group(1)), "l": int(lm.group(2)), "rate": float(lm.group(3))}
    members.append(dict(rank=int(clean(r[0])), name=name, weeks=weeks, att=att, w=w, l=l,
                        rate=rate, lead=lead, captain=cap, perfect=perf))

outsiders = []
for r in rows(out_block)[1:]:
    name, cap, perf = parse_name(r[1])
    weeks = int(re.search(r"(\d+)주", r[2]).group(1))
    att = float(re.search(r"\(([\d.]+)%\)", r[2]).group(1))
    m = re.search(r"(\d+)승\s*(\d+)패", r[3])
    w, l = int(m.group(1)), int(m.group(2))
    rate = float(clean(r[4]).replace("%", "%").replace("%", ""))
    lead = None
    lm = re.search(r"(\d+)승\s*(\d+)패\s*\(([\d.]+)%\)", clean(r[5]))
    if lm:
        lead = {"w": int(lm.group(1)), "l": int(lm.group(2)), "rate": float(lm.group(3))}
    note = clean(r[6])
    outsiders.append(dict(rank=clean(r[0]), name=name, weeks=weeks, att=att, w=w, l=l,
                          rate=rate, lead=lead, captain=cap, perfect=perf, note=note))

absent = re.findall(r"미출전 정회원 \(2명\): (.+)", rec)[0].split(",")
absent = [a.strip() for a in absent]

# ---------- 게스트 ----------
guests = []
for r in rows(gst.split("## 📊 게스트 누적 전적")[1])[1:]:
    name, _, _ = parse_name(r[1])
    weeks = int(re.search(r"(\d+)주", r[2]).group(1))
    dates = [d.strip() for d in r[3].split(",")]
    w, l = [int(x) for x in re.findall(r"(\d+)승\s*(\d+)패", r[4])[0]] if False else \
           (int(re.search(r"(\d+)승", r[4]).group(1)), int(re.search(r"(\d+)패", r[4]).group(1)))
    rate = float(clean(r[5]).replace("%", ""))
    guests.append(dict(rank=int(clean(r[0])), name=name, weeks=weeks, dates=dates, w=w, l=l, rate=rate))

# ---------- 로스터(등번호·신장) ----------
# basketball/reverse-roster.md — 「이름 | 신장 | 등번호 | 비고」 표. 계속 추가되는 파일이므로
# 등록된 선수만 height(cm)·number 필드를 붙이고, 미등록 선수는 필드 없이 둡니다.
ROSTER_PATH = ROOT + "/basketball/reverse-roster.md"
roster = {}
if os.path.isfile(ROSTER_PATH):
    for r in rows(io.open(ROSTER_PATH, encoding="utf-8").read()):
        if len(r) < 3 or clean(r[0]) in ("이름", "선수", "성명"):
            continue
        name = clean(r[0])
        hm = re.search(r"(\d+(?:\.\d+)?)", clean(r[1]))
        nm = re.search(r"(\d+)", clean(r[2]))
        info = {}
        if hm:
            hv = float(hm.group(1))
            info["height"] = int(hv) if hv.is_integer() else hv
        if nm:
            info["number"] = int(nm.group(1))
        if name and info:
            roster[name] = info
for p in members + outsiders + guests:
    p.update(roster.get(p["name"], {}))
print("로스터 등록", len(roster), "명:", ", ".join(
    f"{n} #{v.get('number', '-')} {v.get('height', '-')}cm" for n, v in roster.items()) or "없음")

# ---------- 주간 로그 ----------
week_blocks = re.split(r"### ", rec.split("## 📅 주간 경기 로그")[1])[1:]
weeks = []
for b in week_blocks:
    head, body = b.split("\n", 1)
    dm = re.match(r"(\d{4}-\d{2}-\d{2}) \(토\) (.+?)(?: — (.+))?$", head.strip())
    date, title, venue = dm.group(1), dm.group(2), (dm.group(3) or "부천JW스포츠센터")
    no_leader = "(팀장 없음)" in title
    standings = []
    for part in [p.strip() for p in re.search(r"\*\*최종 순위\*\*: (.+)", body).group(1).split(" / ")]:
        sm = re.match(r"(\d)위\s*(\S+?)\((\d+)승\s*(\d+)패(?:,\s*`?\*([^)`]+)`?)?\)", part)
        standings.append(dict(pos=int(sm.group(1)), team=sm.group(2), w=int(sm.group(3)),
                              l=int(sm.group(4)), cap=(sm.group(5) or "").strip()))
    games = []
    for part in [p.strip() for p in re.search(r"\*\*스코어\*\*: (.+)", body).group(1).split(" / ")]:
        gm = re.match(r"(\S+)\s+(\d+):(\d+)\s+(\S+)", part)
        games.append(dict(a=gm.group(1), as_=int(gm.group(2)), b=gm.group(4), bs=int(gm.group(3))))
    rosters = {}
    for team, names in re.findall(r"([가-힣]+)\(([^)]+)\)", re.search(r"\*\*명단\*\*: (.+)", body).group(1)):
        rosters[team] = [n.strip().replace("`", "").replace("*", "") for n in names.split("·")]
    note = ""
    nm = re.search(r"\*\*비고\*\*: (.+)", body)
    if nm:
        note = nm.group(1).strip()
    weeks.append(dict(date=date, title=title, venue=venue, noLeader=no_leader,
                      standings=standings, games=games, rosters=rosters, note=note))

weeks.sort(key=lambda x: x["date"], reverse=True)

# ---------- 검증: 주차별 로스터로 개인 전적 재계산 ----------
def label(d):
    return d[5:7] + "/" + d[8:10]

errors = []
calc = {}
week_detail = {}
for wk in weeks:
    twl = {s["team"]: (s["w"], s["l"]) for s in wk["standings"]}
    for team, names in wk["rosters"].items():
        for nm in names:
            c = calc.setdefault(nm, {"w": 0, "l": 0, "weeks": []})
            c["w"] += twl[team][0]
            c["l"] += twl[team][1]
            detail = {"date": wk["date"], "label": label(wk["date"]), "team": team,
                      "tw": twl[team][0], "tl": twl[team][1]}
            if team in [s["team"] for s in wk["standings"] if s["cap"] == nm]:
                detail["cap"] = True
            week_detail.setdefault(nm, []).append(detail)

for p in members + outsiders:
    c = calc.get(p["name"])
    if not c:
        errors.append("미출전? " + p["name"]); continue
    if (c["w"], c["l"]) != (p["w"], p["l"]):
        errors.append(f"{p['name']}: 표 {p['w']}-{p['l']} vs 계산 {c['w']}-{c['l']}")
    if len(c["weeks"]) if False else len(week_detail[p["name"]]) != p["weeks"]:
        errors.append(f"{p['name']}: 주차수 {p['weeks']} vs 계산 {len(week_detail[p['name']])}")
for g in guests:
    c = calc.get(g["name"])
    if not c:
        errors.append("게스트 미출전? " + g["name"]); continue
    if (c["w"], c["l"]) != (g["w"], g["l"]):
        errors.append(f"게스트 {g['name']}: 표 {g['w']}-{g['l']} vs 계산 {c['w']}-{c['l']}")

print("정규", len(members), "순위외", len(outsiders), "게스트", len(guests), "주차", len(weeks))
print("등번호·신장 포함 선수:", [p["name"] for p in members + outsiders + guests if "number" in p or "height" in p] or "없음")
print("검증 오류:", errors if errors else "없음")

# 순위 검증: 승률 desc, 다승 desc
sorted_check = sorted(members, key=lambda p: (-p["rate"], -p["w"]))
print("순위 일치:", [p["rank"] for p in sorted_check] == list(range(1, len(members) + 1)))

# 예정 경기 프리뷰 — 다음 주차 명단이 확정되면 이 블록만 고칩니다(주차별로 교체).
#  이 값은 누적 승률·순위(PERIOD/members/outsiders/guests)에 포함되지 않습니다.
PREVIEW = dict(
    date="2026-11-28",
    label="2026-11-28 (예정 · 9주차 프리뷰)",
    title="매치 프리뷰 & 승률 예상",
    venue="부천JW스포츠센터",
    note="아직 치르지 않은 경기이므로 승률·순위·누적 집계는 2026-11-21(8주차) 확정 기준을 그대로 유지합니다. 평균 승률은 각 팀 기록 보유 선수의 8주 확정 개인 승률 단순 평균입니다.",
    teams=[
        dict(team="형광", cap="박광현", avg=53.7, expected="2승 0패 또는 1승 1패", note="최정범 첫 출전",
             roster=["박광현", "김준성", "심호길", "김현준", "최정범"]),
        dict(team="화이트", cap="유동훈", avg=51.3, expected="1승 1패 또는 2승 0패", note="",
             roster=["변정훈", "정승혁", "유동훈", "나윤", "김영익"]),
        dict(team="블랙", cap="고건우", avg=41.3, expected="0승 2패", note="이변 시 1승",
             roster=["정민규", "고건우", "조성현", "김재호", "김영수"]),
    ],
)

data = dict(
    team="리버스", teamEn="REVERSE", venue="부천JW스포츠센터",
    preview=PREVIEW,
    period=dict(start="2026-10-03", end="2026-11-21", weeks=8),
    criteria=dict(minRate=40, minWeeks=4, totalWeeks=8,
                  tiebreak=["다승", "팀장 승률", "가나다 순"],
                  text="전체 경기 수 40% 이상 참여자 정규 순위 집계 (8주 중 4주 이상)"),
    members=members, outsiders=outsiders, absent=absent, guests=guests, weeks=weeks,
    leaders=[dict(name=p["name"], **p["lead"]) for p in members + outsiders if p["lead"]],
)
json_text = json.dumps(data, ensure_ascii=False, indent=1)
# build_site.py 는 src/data.json 을 우선 읽는다 → 두 경로 모두 최신으로 유지
for path in (SITE + "/src/data.json", SITE + "/data.json"):
    io.open(path, "w", encoding="utf-8").write(json_text)
print("저장 완료:", "src/data.json, data.json")
