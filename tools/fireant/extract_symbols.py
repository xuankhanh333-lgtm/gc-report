#!/usr/bin/env python3
"""Trích danh sách mã ĐỘNG từ vnpool.html (khối D.flow) để feed cho WF.

Dashboard vnpool nhúng object `const D = {...}` trong đó `D.flow` gồm đúng các
mã section Dòng tiền đang hiển thị. Lấy key của D.flow => danh sách mã luôn khớp
dashboard, không cần sửa watchlist thủ công khi bộ mã đổi.

Dùng:
    python extract_symbols.py vnpool.html          # in mỗi mã một dòng
In ra rỗng (exit 0) nếu không trích được — caller nên fallback sang watchlist.txt.
"""

from __future__ import annotations

import re
import sys
import json


def extract(html: str) -> list[str]:
    # Lấy literal "const D = {...};" (ăn tới trước 'const fmt' cho khớp, fallback tham lam).
    m = re.search(r"const D = (\{.*?\});\s*\nconst fmt", html, re.S)
    if not m:
        m = re.search(r"const D = (\{.*\});", html, re.S)
    if not m:
        return []
    try:
        D = json.loads(m.group(1))
    except ValueError:
        return []

    tks: list[str] = list((D.get("flow") or {}).keys())

    # Fallback: nếu không có D.flow, thử các cấu trúc danh sách phổ biến.
    if not tks:
        for key in ("rows", "universe", "list", "items", "data"):
            v = D.get(key)
            if isinstance(v, list):
                cand = [
                    (r.get("tk") or r.get("symbol") or r.get("ticker"))
                    for r in v
                    if isinstance(r, dict)
                ]
                cand = [t for t in cand if t]
                if cand:
                    tks = cand
                    break

    # chuẩn hoá + khử trùng + sắp xếp
    seen, out = set(), []
    for t in tks:
        t = str(t).strip().upper()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return sorted(out)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        sys.stderr.write("Cần đường dẫn vnpool.html\n")
        return 2
    try:
        html = open(argv[1], encoding="utf-8").read()
    except OSError as exc:
        sys.stderr.write(f"Không đọc được {argv[1]}: {exc}\n")
        return 2
    tks = extract(html)
    if tks:
        sys.stdout.write("\n".join(tks) + "\n")
    sys.stderr.write(f"[extract_symbols] {len(tks)} mã\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
