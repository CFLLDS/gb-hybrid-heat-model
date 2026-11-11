#!/usr/bin/env python3
"""Entry point for the GB hybrid-heating model v2 (scripts/spark/gbmodel/). See gbmodel/run.py for usage."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gbmodel.run import main  # noqa: E402

if __name__ == "__main__":
    main()
