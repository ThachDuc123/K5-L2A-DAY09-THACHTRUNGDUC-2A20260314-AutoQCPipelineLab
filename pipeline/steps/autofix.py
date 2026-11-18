"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.   ★★

Test:  pytest tests/test_autofix.py -q

`fix(ds, issues, cfg) -> list[dict]`: duyệt `issues` (chỉ lỗi severity ERROR), sửa thẳng vào thư mục `ds`,
và trả về danh sách thay đổi; mỗi phần tử có khoá: image, line, action, before, after
(đây chính là file `03_fixes.csv` — bằng chứng pipeline đã làm gì, người có thể kiểm lại).

| code lỗi                                       | cách sửa                                    | action           |
|------------------------------------------------|---------------------------------------------|------------------|
| BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX    | xoá dòng đó khỏi file nhãn                  | "drop_line"      |
| BOX_OUT_OF_IMAGE                               | cắt box về trong [0,1] (giữ nguyên lớp)     | "clip_box"       |
| MISSING_LABEL_FILE                             | KHÔNG sửa file (máy không thể bịa nhãn): ghi 1 dòng fix, before="(không có file)", after="chuyển người gán" | "needs_label" |
| BAD_CLASS_NAME                                 | ghi lại `names` trong data.yaml đúng `cfg["classes"]` | "rename_classes" |
| DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE| xoá ảnh + nhãn khỏi `ds`                    | "remove_image"   |

Bẫy cần nghĩ tới (có test cho từng cái)
- Một file có NHIỀU dòng lỗi: số dòng trong `issues` là số dòng GỐC. Nếu xoá từng dòng một thì số dòng lệch.
  Gom theo file, rồi ghi lại MỘT lần.
- Sau khi cắt, box có thể không còn diện tích (nằm hẳn ngoài ảnh): lúc đó xoá dòng thay vì ghi box rỗng.
- Một dòng có 2 lỗi (vd. BOX_OUT_OF_IMAGE + DUP_BOX): xoá dòng thắng, chỉ ghi 1 fix `drop_line`, không ghi thêm `clip_box`. Dòng trống ở giữa file vẫn đếm vào số dòng gốc.
- Ảnh vừa bị xoá (DUP_IMAGE_*...) mà còn issue dòng của chính nó: bỏ qua êm, không được báo lỗi/chết.
- Không động tới lỗi WARN (cảnh báo là việc của người). Không sửa file ở `data/raw/` — chỉ sửa `ds`.
- Chạy lần 2 trên dữ liệu đã sửa phải không làm gì thêm (idempotent) — NGOẠI LỆ duy nhất: `needs_label` được ghi lại mỗi lần còn lỗi `MISSING_LABEL_FILE` (vì ảnh vẫn chưa có nhãn).

- `needs_label` KHÔNG tạo file nhãn rỗng (rỗng = "ảnh nền", khác với "chưa gán"). `review_queue` sẽ đẩy ảnh này lên đầu hàng đợi cho người.

Gợi ý: `yaml.safe_load / safe_dump`.
"""
from collections import defaultdict

import yaml

from ..common import ERROR, parse_yolo_line

REMOVE_IMAGE_CODES = {"LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}
DROP_LINE_CODES = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}


def _is_remove_image(code: str) -> bool:
    return code in REMOVE_IMAGE_CODES or code.startswith("DUP_IMAGE_")


def fix(ds, issues, cfg):
    """Tự động sửa các lỗi bắt buộc (ERROR) trong thư mục `ds` và trả về log thay đổi."""
    err_issues = [i for i in issues if i.severity == ERROR]
    fixes = []
    removed_stems: set[str] = set()

    # 1. Loại ảnh hỏng / sai kích thước / trùng / rò rỉ trước
    for iss in err_issues:
        if _is_remove_image(iss.code) and iss.image not in removed_stems:
            img_p = ds.image_path(iss.image)
            lbl_p = ds.label_path(iss.image)
            before = img_p.name if img_p else iss.image
            if img_p and img_p.exists():
                img_p.unlink()
            if lbl_p.exists():
                lbl_p.unlink()
            removed_stems.add(iss.image)
            fixes.append(
                {
                    "image": iss.image,
                    "line": "",
                    "action": "remove_image",
                    "before": before,
                    "after": "(đã xoá)",
                }
            )

    # 2. Sửa tên lớp trong data.yaml (tối đa 1 lần)
    if any(iss.code == "BAD_CLASS_NAME" for iss in err_issues):
        expected = dict(enumerate(cfg["classes"]))
        current = ds.yaml_names()
        if current != expected:
            data = {}
            if ds.yaml_path.exists():
                data = yaml.safe_load(ds.yaml_path.read_text(encoding="utf-8")) or {}
            before = str(current)
            data["names"] = expected
            ds.yaml_path.write_text(
                yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            fixes.append(
                {
                    "image": "data.yaml",
                    "line": "",
                    "action": "rename_classes",
                    "before": before,
                    "after": str(cfg["classes"]),
                }
            )

    # 3. Ảnh thiếu file nhãn -> chuyển người gán (không tự tạo file rỗng)
    needs_label_seen: set[str] = set()
    for iss in err_issues:
        if (
            iss.code == "MISSING_LABEL_FILE"
            and iss.image not in removed_stems
            and iss.image not in needs_label_seen
        ):
            needs_label_seen.add(iss.image)
            fixes.append(
                {
                    "image": iss.image,
                    "line": "",
                    "action": "needs_label",
                    "before": "(không có file)",
                    "after": "chuyển người gán",
                }
            )

    # 4. Gom lỗi theo file & số dòng gốc để sửa một lần mỗi file
    by_file: dict[str, dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))
    for iss in err_issues:
        if iss.line is not None and iss.image not in removed_stems:
            if iss.code in DROP_LINE_CODES or iss.code == "BOX_OUT_OF_IMAGE":
                by_file[iss.image][iss.line].add(iss.code)

    for stem in sorted(by_file):
        lp = ds.label_path(stem)
        if not lp.exists():
            continue
        orig_lines = lp.read_text(encoding="utf-8", errors="replace").splitlines()
        new_lines = []
        modified = False
        line_map = by_file[stem]

        for line_no, raw in enumerate(orig_lines, 1):
            codes = line_map.get(line_no)
            if not codes:
                new_lines.append(raw)
                continue

            if codes & DROP_LINE_CODES:
                fixes.append(
                    {
                        "image": stem,
                        "line": line_no,
                        "action": "drop_line",
                        "before": raw.strip(),
                        "after": "(đã xoá)",
                    }
                )
                modified = True
                continue

            if "BOX_OUT_OF_IMAGE" in codes:
                try:
                    cls_id, cx, cy, w, h = parse_yolo_line(raw)
                except ValueError:
                    fixes.append(
                        {
                            "image": stem,
                            "line": line_no,
                            "action": "drop_line",
                            "before": raw.strip(),
                            "after": "(đã xoá)",
                        }
                    )
                    modified = True
                    continue

                x1 = max(0.0, min(1.0, cx - w / 2))
                y1 = max(0.0, min(1.0, cy - h / 2))
                x2 = max(0.0, min(1.0, cx + w / 2))
                y2 = max(0.0, min(1.0, cy + h / 2))
                nw, nh = x2 - x1, y2 - y1
                if nw <= 1e-9 or nh <= 1e-9:
                    fixes.append(
                        {
                            "image": stem,
                            "line": line_no,
                            "action": "drop_line",
                            "before": raw.strip(),
                            "after": "(đã xoá)",
                        }
                    )
                    modified = True
                    continue

                ncx, ncy = (x1 + x2) / 2, (y1 + y2) / 2
                fixed_line = f"{cls_id} {ncx:.6f} {ncy:.6f} {nw:.6f} {nh:.6f}"
                new_lines.append(fixed_line)
                fixes.append(
                    {
                        "image": stem,
                        "line": line_no,
                        "action": "clip_box",
                        "before": raw.strip(),
                        "after": fixed_line,
                    }
                )
                modified = True

        if modified:
            content = "\n".join(new_lines) + ("\n" if new_lines else "")
            lp.write_text(content, encoding="utf-8")

    return fixes
