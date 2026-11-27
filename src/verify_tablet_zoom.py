# -*- coding: utf-8 -*-
"""태블릿 확대(zoom) 검증 — 2026-11-27 폐기.

경기 진행 화면은 배율(zoom) 대신 flex/grid 로 화면을 꽉 채우고,
글씨는 --pg-fs-* 변수로 3단계(작게·보통·크게)만 조절합니다.
검사는 verify_tablet_full.py 로 옮겼습니다(이 파일은 그대로 실행만 합니다).

    python3 src/verify_tablet_zoom.py      # = verify_tablet_full.py
"""
import os, runpy, sys

HERE = os.path.dirname(os.path.abspath(__file__))
print('→ 배율(zoom) 검증은 verify_tablet_full.py 로 대체되었습니다(화면 꽉 채우기 + 글씨 3단계).')
sys.argv = [os.path.join(HERE, 'verify_tablet_full.py')]
runpy.run_path(os.path.join(HERE, 'verify_tablet_full.py'), run_name='__main__')
