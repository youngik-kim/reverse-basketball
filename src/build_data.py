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
print("검증 오류:", errors if errors else "없음")

# 순위 검증: 승률 desc, 다승 desc
sorted_check = sorted(members, key=lambda p: (-p["rate"], -p["w"]))
print("순위 일치:", [p["rank"] for p in sorted_check] == list(range(1, len(members) + 1)))

data = dict(
    team="리버스", teamEn="REVERSE", venue="부천JW스포츠센터",
    period=dict(start="2026-10-03", end="2026-11-21", weeks=8),
    criteria=dict(minRate=40, minWeeks=4, totalWeeks=8,
                  tiebreak=["다승", "팀장 승률", "가나다 순"],
                  text="전체 경기 수 40% 이상 참여자 정규 순위 집계 (8주 중 4주 이상)"),
    members=members, outsiders=outsiders, absent=absent, guests=guests, weeks=weeks,
    leaders=[dict(name=p["name"], **p["lead"]) for p in members + outsiders if p["lead"]],
)
json.dump(data, io.open(SITE + "/data.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("저장 완료")
