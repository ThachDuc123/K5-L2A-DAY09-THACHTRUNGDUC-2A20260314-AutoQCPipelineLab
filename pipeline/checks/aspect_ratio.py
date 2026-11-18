"""Check thưởng (+3) — phát hiện box lệch tỉ lệ khung hình quá mức (quá dẹt hoặc quá mảnh)."""
from __future__ import annotations

import argparse
from pathlib import Path

from ..common import ROOT, WARN, Dataset, Issue, load_config, parse_yolo_line

DEFAULT_MAX_RATIO = 7.0


def run(ds: Dataset, cfg: dict | None = None) -> list[Issue]:
    """Quét các box hợp lệ và cảnh báo khi tỉ lệ cạnh pixel max(w/h, h/w) > max_ratio."""
    ar_cfg = (cfg or {}).get("aspect_ratio", {})
    max_ratio = float(ar_cfg.get("max_ratio", DEFAULT_MAX_RATIO))
    issues: list[Issue] = []

    for imf in ds.image_files():
        stem = imf.stem
        size = ds.image_size(stem)
        if not size or size[0] <= 0 or size[1] <= 0:
            continue
        img_w, img_h = size
        lines = ds.read_label_lines(stem)
        if not lines:
            continue

        for line_no, raw in lines:
            try:
                cid, _, _, w, h = parse_yolo_line(raw)
            except ValueError:
                continue
            if w <= 0 or h <= 0:
                continue
            w_px = w * img_w
            h_px = h * img_h
            ratio = max(w_px / h_px, h_px / w_px)
            if ratio > max_ratio:
                cls_name = ds.classes[cid] if 0 <= cid < len(ds.classes) else str(cid)
                issues.append(
                    Issue(
                        check="aspect_ratio",
                        severity=WARN,
                        code="BOX_ASPECT_RATIO",
                        image=stem,
                        line=line_no,
                        message=(
                            f"box lớp {cls_name} lệch tỉ lệ khung hình "
                            f"({w_px:.1f}x{h_px:.1f}px, tỉ lệ {ratio:.2f} > {max_ratio:g})"
                        ),
                        extra={
                            "class": cls_name,
                            "ratio": round(ratio, 2),
                            "w_px": round(w_px, 1),
                            "h_px": round(h_px, 1),
                        },
                    )
                )
    return issues


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Kiểm tra box lệch tỉ lệ khung hình")
    ap.add_argument("--dataset", default="data/raw", help="thư mục YOLO chứa images/ và labels/")
    ap.add_argument("--labels", help="thư mục labels/ thay thế (vd. submission/export/clean_v1/labels)")
    ap.add_argument("--config", default="configs/pipeline.yaml")
    ap.add_argument("--max-ratio", type=float, help="ghi đè ngưỡng max(w/h, h/w)")
    args = ap.parse_args(argv)

    cfg = load_config(ROOT / args.config)
    if args.max_ratio is not None:
        cfg.setdefault("aspect_ratio", {})["max_ratio"] = args.max_ratio

    ds_root = Path(args.dataset)
    if not ds_root.is_absolute():
        ds_root = ROOT / ds_root
    ds = Dataset(ds_root, cfg["classes"])
    if args.labels:
        lbl_dir = Path(args.labels)
        ds.labels_dir = lbl_dir if lbl_dir.is_absolute() else ROOT / lbl_dir

    issues = run(ds, cfg)
    print(f"Quét {len(ds.image_files())} ảnh -> {len(issues)} cảnh báo BOX_ASPECT_RATIO")
    for iss in issues:
        loc = f"{iss.image}:{iss.line}" if iss.line else iss.image
        print(f"[WARN ] {iss.code:<18} {loc:<14} {iss.message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
