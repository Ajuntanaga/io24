#!/usr/bin/env python3
"""Compatibility entry point for the production UC 4.7.2 EQ designer."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from io24_uc472_vintage_eq import *
from io24_uc472_vintage_eq import main


if __name__ == "__main__":
    raise SystemExit(main())
