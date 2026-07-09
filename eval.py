#!/usr/bin/env python3
"""Run JARVIS's self-evaluation and print a reliability score. Exit 0 if >=90%."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import eval_harness

def main() -> int:
    res = eval_harness.run()
    print(eval_harness.report_text(res))
    print(f"\nRELIABILITY SCORE: {res['score']}%  ({res['passed']}/{res['total']})")
    return 0 if res["score"] >= 90 else 1

if __name__ == "__main__":
    raise SystemExit(main())
