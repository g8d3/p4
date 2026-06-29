#!/usr/bin/env python3
"""Entry point for `tds` command."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tds.cli import main

if __name__ == "__main__":
    main()
