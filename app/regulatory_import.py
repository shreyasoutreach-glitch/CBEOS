"""Fail-closed legacy regulatory workbook promotion guard.

No staged workbook is runtime-ready before full canonical-source reconciliation,
independent review, calculation golden tests and approved promotion.
"""
BLOCK_MESSAGE = ("Regulatory workbook promotion is disabled. The workbook must first pass "
                 "isolated staging, full binding-annex reconciliation, independent review, "
                 "calculation golden tests and approved versioned promotion. No database changes were made.")

def import_workbook(path, version='2.2.1'):
    raise RuntimeError(BLOCK_MESSAGE)

def main():
    raise SystemExit(BLOCK_MESSAGE)

if __name__ == '__main__':
    main()
