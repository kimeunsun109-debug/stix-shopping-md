"""실행 진입점.

폴더 이름이 숫자로 시작해 파이썬 패키지 이름(import)이 되지 않는다.
이 파일을 직접 실행한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
