# -*- coding: utf-8 -*-
"""src/data.json + src/template.html -> index.html  (암호화 빌드)

- data.json(평문)은 저장소에 커밋하지 않습니다(.gitignore).
- 빌드할 때마다 입장 코드로 암호화해 src/data.enc.json 을 만들고,
  index.html 에는 암호문(ENC_DATA)만 넣습니다.
- 암호: PBKDF2-SHA256(10만 회, 64바이트) -> AES-256-CTR(암호화) + HMAC-SHA256(무결성)
  브라우저 쪽 복호화 코드는 src/template.html 안에 있습니다(Web Crypto + 순수 JS 대체 구현).

사용:
    python3 src/build_site.py --code 2020
    REVERSE_CODE=2020 python3 src/build_site.py
    python3 src/build_site.py --code 2020 --reencrypt   # data.json 강제 재암호화
"""
import argparse, base64, getpass, hashlib, hmac, io, json, os, sys

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
except ImportError:  # pragma: no cover
    sys.exit("cryptography 모듈이 필요합니다:  python3 -m pip install cryptography")

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 저장소 루트
ITER = 100000
HEADER = "reverse-basketball|{v}|{kdf}|{iter}|"
V, KDF = 1, "PBKDF2-SHA256"


def b64(b):
    return base64.b64encode(b).decode("ascii")


def b64d(s):
    return base64.b64decode(s)


def derive(code, salt, it=ITER):
    return hashlib.pbkdf2_hmac("sha256", code.encode("utf-8"), salt, it, 64)


def mac_msg(salt, iv, ct, it=ITER):
    return HEADER.format(v=V, kdf=KDF, iter=it).encode("ascii") + salt + iv + ct


def encrypt(plain, code, salt=None, iv=None, it=ITER):
    salt = salt or os.urandom(16)
    iv = iv or os.urandom(16)
    k = derive(code, salt, it)
    enc = Cipher(algorithms.AES(k[:32]), modes.CTR(iv)).encryptor()
    ct = enc.update(plain) + enc.finalize()
    mac = hmac.new(k[32:], mac_msg(salt, iv, ct, it), hashlib.sha256).digest()
    return {"v": V, "kdf": KDF, "iter": it, "salt": b64(salt), "iv": b64(iv), "ct": b64(ct), "mac": b64(mac)}


def decrypt(obj, code):
    salt, iv, ct, mac = (b64d(obj[f]) for f in ("salt", "iv", "ct", "mac"))
    it = int(obj["iter"])
    k = derive(code, salt, it)
    want = hmac.new(k[32:], mac_msg(salt, iv, ct, it), hashlib.sha256).digest()
    if not hmac.compare_digest(want, mac):
        raise ValueError("입장 코드가 데이터와 맞지 않습니다.")
    dec = Cipher(algorithms.AES(k[:32]), modes.CTR(iv)).decryptor()
    return dec.update(ct) + dec.finalize()


def first_existing(*paths):
    for p in paths:
        if os.path.isfile(p):
            return p
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", help="입장 코드 (없으면 REVERSE_CODE 환경변수 또는 입력 프롬프트)")
    ap.add_argument("--reencrypt", action="store_true", help="data.json 이 있어도 강제로 다시 암호화")
    args = ap.parse_args()

    code = args.code or os.environ.get("REVERSE_CODE") or ""
    if not code:
        code = getpass.getpass("입장 코드: ").strip()
    if not code:
        sys.exit("입장 코드가 없습니다.")

    tpl_path = first_existing(os.path.join(SITE, "src", "template.html"), os.path.join(SITE, "_build", "template.html"))
    plain_path = first_existing(os.path.join(SITE, "src", "data.json"), os.path.join(SITE, "data.json"))
    enc_path = os.path.join(SITE, "src", "data.enc.json")
    if not tpl_path:
        sys.exit("src/template.html 을 찾을 수 없습니다.")

    # 1) 필요하면 평문 data.json 을 암호화해 src/data.enc.json 갱신
    need_enc = args.reencrypt or not os.path.isfile(enc_path)
    if plain_path and not need_enc:
        need_enc = os.path.getmtime(plain_path) > os.path.getmtime(enc_path)
    if need_enc:
        if not plain_path:
            sys.exit("data.json 이 없고 src/data.enc.json 도 없습니다. src/build_data.py 로 데이터를 먼저 만드세요.")
        raw = io.open(plain_path, encoding="utf-8").read().strip()
        json.loads(raw)  # 형식 확인
        enc = encrypt(raw.encode("utf-8"), code)
        io.open(enc_path, "w", encoding="utf-8").write(json.dumps(enc, ensure_ascii=False, separators=(",", ":")))
        print("encrypted: %s (%d bytes plain)" % (os.path.relpath(enc_path, SITE), len(raw.encode("utf-8"))))
    elif not os.path.isfile(enc_path):
        sys.exit("src/data.enc.json 이 없습니다.")

    # 2) 코드로 복호화되는지 검증 + 요약
    enc = json.load(io.open(enc_path, encoding="utf-8"))
    try:
        data = json.loads(decrypt(enc, code).decode("utf-8"))
    except ValueError as e:
        sys.exit(str(e) + "  (기존 암호문은 다른 코드로 만들어졌습니다. --reencrypt 로 새로 암호화하세요)")

    # 3) 템플릿에 암호문 삽입
    tpl = io.open(tpl_path, encoding="utf-8").read()
    blob = json.dumps(enc, ensure_ascii=False, separators=(",", ":"))
    out = tpl.replace("/*__ENC__*/", blob)
    assert "/*__ENC__*/" not in out, "ENC_DATA 자리표시자를 찾지 못했습니다."
    assert "/*__DATA__*/" not in out
    io.open(os.path.join(SITE, "index.html"), "w", encoding="utf-8").write(out)

    weeks = [w for w in data.get("weeks", []) if w.get("date")]
    period = data.get("period", {})
    pv = data.get("preview")
    print("index.html %d bytes  |  %d주 · 정규 %d명 · 게스트 %d명 · 기간 %s~%s%s"
          % (len(out), len(weeks), len(data.get("members", [])), len(data.get("guests", [])),
             period.get("start", "?"), period.get("end", "?"),
             "  |  예정 프리뷰 %s (%d팀)" % (pv.get("date"), len(pv.get("teams", []))) if pv else ""))


if __name__ == "__main__":
    main()
