# -*- coding: utf-8 -*-
"""폰 화면 회귀 검증 — 세로·가로 폰에서 '위로 쏠림 없이 꽉 참'을 확인합니다.

  ※ 2026-11-27: 사용자가 "폰도 세로 전체화면에서 위쪽으로 쏠려 있다"고 알려 와서
     폰도 태블릿과 같은 꽉 채우기 배치로 바꿨습니다(픽셀 동일 유지 제약 해제).
     그래서 예전의 'HEAD 와 픽셀 동일' 비교 대신, 폰 화면이 실제로 화면을 채우고
     이름·헤더가 잘리지 않는지를 검사합니다. 자세한 검사는 verify_tablet_full.py 가 전담합니다.

    python3 src/verify_phone_pixel.py
    MP_URL=... python3 src/verify_phone_pixel.py     # 배포 페이지
"""
import os, runpy, sys

HERE = os.path.dirname(os.path.abspath(__file__))
print('→ 폰 화면은 verify_tablet_full.py 의 phone390·phone430 항목이 검사합니다(꽉 채우기·잘림 0).')
sys.argv = [os.path.join(HERE, 'verify_tablet_full.py')]
runpy.run_path(os.path.join(HERE, 'verify_tablet_full.py'), run_name='__main__')
