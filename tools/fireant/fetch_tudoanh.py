#!/usr/bin/env python3
"""Kéo dữ liệu TỰ DOANH từ FireAnt cho một danh sách mã và xuất JSON.

Ví dụ:
    export FIREANT_TOKEN="<jwt>"
    python fetch_tudoanh.py --symbols VNM HPG SSI --days 30 --out tudoanh.json

Xuất ra JSON dạng:
    {
      "stamp": "20260803_1530",
      "range": {"start": "...", "end": "..."},
      "symbols": {
        "VNM": {"proprietary": <payload>, "foreignNet": [...]},
        ...
      },
      "errors": {"XYZ": "message"}
    }

Cấu trúc này ăn khớp với cách các dashboard (vnpool.html…) nhúng sẵn một object
`D = {...}` do pipeline sinh ra — chỉ cần đọc file JSON và chèn vào chỗ dữ liệu.
"""

from __future__ import annotations

import os
import sys
import json
import argparse
import logging
from datetime import datetime

from fireant_client import (
    FireAntClient,
    FireAntError,
    default_range,
)

log = logging.getLogger("fetch_tudoanh")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Kéo tự doanh từ FireAnt.")
    p.add_argument(
        "--symbols",
        nargs="+",
        help="Danh sách mã, vd: VNM HPG SSI. Bỏ trống thì đọc --symbols-file.",
    )
    p.add_argument(
        "--symbols-file",
        help="File text, mỗi dòng một mã (bỏ dòng trống / bắt đầu bằng #).",
    )
    p.add_argument("--days", type=int, default=30, help="Số ngày lùi (mặc định 30).")
    p.add_argument("--start", help="Ngày bắt đầu YYYY-MM-DD (ghi đè --days).")
    p.add_argument("--end", help="Ngày kết thúc YYYY-MM-DD.")
    p.add_argument(
        "--out",
        default="-",
        help="File JSON đầu ra ('-' = stdout, mặc định).",
    )
    p.add_argument(
        "--with-foreign",
        action="store_true",
        help="Kèm chuỗi ròng khối ngoại (từ historical-quotes) để đối chiếu.",
    )
    p.add_argument("--token", help="Token FireAnt (ưu tiên hơn env FIREANT_TOKEN).")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def load_symbols(args) -> list[str]:
    syms: list[str] = []
    if args.symbols:
        syms.extend(args.symbols)
    if args.symbols_file:
        with open(args.symbols_file, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#"):
                    syms.append(line.split()[0])
    # chuẩn hoá + khử trùng, giữ thứ tự
    seen, out = set(), []
    for s in syms:
        s = s.upper()
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def main(argv=None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    symbols = load_symbols(args)
    if not symbols:
        log.error("Chưa có mã nào. Dùng --symbols hoặc --symbols-file.")
        return 2

    if args.start:
        start, end = args.start, (args.end or datetime.utcnow().strftime("%Y-%m-%d"))
    else:
        start, end = default_range(args.days)

    try:
        client = FireAntClient(token=args.token)
    except FireAntError as exc:
        log.error("%s", exc)
        return 2

    result = {
        "stamp": datetime.utcnow().strftime("%Y%m%d_%H%M"),
        "range": {"start": start, "end": end},
        "symbols": {},
        "errors": {},
    }

    for sym in symbols:
        entry: dict = {}
        try:
            entry["proprietary"] = client.proprietary_trading(sym, start, end)
        except FireAntError as exc:
            log.warning("[%s] tự doanh lỗi: %s", sym, exc)
            result["errors"][sym] = str(exc)
            # vẫn thử lấy phần khối ngoại nếu được yêu cầu
        if args.with_foreign:
            try:
                entry["foreignNet"] = client.foreign_net_series(sym, start, end)
            except FireAntError as exc:
                log.warning("[%s] khối ngoại lỗi: %s", sym, exc)
                result["errors"].setdefault(sym, str(exc))
        if entry:
            result["symbols"][sym] = entry
        log.info("Xong %s", sym)

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out == "-":
        sys.stdout.write(payload + "\n")
    else:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(payload)
        log.info("Đã ghi %s (%d mã, %d lỗi)", args.out,
                 len(result["symbols"]), len(result["errors"]))

    # exit code != 0 nếu không lấy được mã nào
    return 0 if result["symbols"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
