# Báo cáo Day 09 — Thạch Trung Đức, 2A20260314

## 1. Kết luận trước
Pipeline chạy ra kết luận **Hold** ( `10`). Trong 224 ảnh thô đưa vào bước intake, máy loại 22 ảnh lỗi đầu vào và giữ lại 202/224 ảnh. Cuối pipeline xuất bản nháp 202 ảnh sang `submission/export/clean_v1/` (`manifest.json` sha1 `08522be8b27b006b8032e380e7574437996eef3b`), chưa chuyển sang Release. Lý do chính là tuy đã hết lỗi bắt buộc (`07_error_list_v3.txt` còn 0 `ERROR`, 6 ảnh thiếu file nhãn đã được người duyệt trong ngân sách 80 ảnh), nhưng vẫn còn 38/202 ảnh chưa duyệt mang cảnh báo `WARN` (`18.81% >= 10%`), tổng cộng 77 dòng cảnh báo còn lại do hàng đợi có 125 ảnh mà ngân sách chỉ cho duyệt 80 ảnh.

## 2. Lỗi và phân việc
Số liệu gom từ `submission/reports/02_error_list_v1.txt` (tổng 211 dòng gồm 22 `ERROR` từ bước intake, 36 `ERROR` và 153 `WARN` ở vòng QC 1):

| Mã lỗi | Số ảnh / dòng | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| `BAD_SIZE` | 3 / 3 | Máy (loại ở intake) | Ảnh có cạnh ngắn dưới `250px` (`img_0107`, `img_0113`, `img_0122`), quá nhỏ để train |
| `CORRUPT_IMAGE` | 2 / 2 | Máy (loại ở intake) | File ảnh hỏng không mở hoặc đọc hết pixel được (`img_0010`, `img_0136`) |
| `DUP_IMAGE_EXACT` | 8 / 8 | Máy (loại ở intake) | Trùng hoàn toàn từng byte với ảnh khác trong cùng lô |
| `DUP_IMAGE_NEAR` | 4 / 4 | Máy (loại ở intake) | Ảnh trùng gần (`phash <= 10`) do nén lại, crop nhẹ hoặc đổi độ sáng |
| `LEAK_TEST` | 5 / 5 | Máy (loại ở intake) | Trùng với ảnh trong tập `data/test` (`img_0049`, `img_0101`, `img_0167`, `img_0174`, `img_0221`), phải loại để tránh rò rỉ |
| `BAD_CLASS_NAME` | 1 chỗ (`data.yaml`) / 2 | Máy (`autofix`) | Chuẩn hoá tên lớp viết sai hoa/thường (`Person`, `Bus` -> `person`, `bus`) |
| `BAD_CLASS_ID` | 6 / 6 | Máy (`autofix`) | Xoá dòng (`drop_line`) có ID lớp nằm ngoài `0..3` |
| `BAD_FORMAT` | 3 / 3 | Máy (`autofix`) | Xoá dòng sai định dạng cột hoặc chứa `nan` |
| `BOX_OUT_OF_IMAGE` | 8 / 8 | Máy (`autofix`) | Cắt toạ độ box tràn biên về đoạn `[0, 1]` (`clip_box`) |
| `BOX_ZERO` | 4 / 4 | Máy (`autofix`) | Xoá dòng có chiều rộng hoặc chiều cao `<= 0` |
| `DUP_BOX` | 7 / 7 | Máy (`autofix`) | Xoá box bị lặp gần như y hệt trên cùng một ảnh |
| `CLASS_RARE` | 1 chỗ / 4 | Máy (hết sau fix) | 4 dòng ID lạ (`-1, 4, 7, 93`) biến mất theo sau khi `autofix` xoá `BAD_CLASS_ID` |
| `MISSING_LABEL_FILE` | 6 / 6 | Người (hàng đợi) | Thiếu hẳn file `.txt`, máy không tự bịa nhãn được nên đưa vào hàng đợi để người gán |
| `EMPTY_LABEL` | 12 / 12 (15 sau fix) | Người (hàng đợi) | Cần người xem ảnh đó thật sự không có xe/người hay do gán sót (tăng lên 15 vì 3 ảnh bị xoá hết dòng hỏng) |
| `BOX_TINY` | 4 / 6 (5 / 7 sau fix) | Người (hàng đợi) | Box có cạnh ngắn dưới `12px` (tăng thêm 1 ở `img_0030` sau khi cắt biên), cần người kiểm xem có đáng giữ không |
| `BOX_HUGE` | 3 / 3 | Người (hàng đợi) | Box chiếm gần hết khung hình, dễ là gán nhầm hoặc bao cả nền |
| `POSSIBLE_MISSING` | 52 / 53 | Người (hàng đợi) | Model phụ bắt được vật (`conf >= 0.6`) nhưng file nhãn chưa có; để người quyết định thay vì tự chép |
| `POSSIBLE_FALSE_POS` | 27 / 29 (23 / 24 sau fix) | Người (hàng đợi) | Box có trong nhãn nhưng model phụ không thấy; cần người xem là nhãn thừa hay model phụ sót |
| `POSSIBLE_LOOSE_BOX` | 24 / 28 | Người (hàng đợi) | Trùng lớp với model phụ nhưng `IoU < 0.5`, có thể box bị lệch hoặc quá rộng |
| `POSSIBLE_WRONG_CLASS` | 18 / 18 | Người (hàng đợi) | Trùng vị trí (`IoU >= 0.5`) nhưng khác lớp so với model phụ, ảnh hưởng trực tiếp lúc train nên cần người sửa |

Về cách sắp xếp hàng đợi: `05_review_queue.csv` có 125 ảnh, được xếp theo tổng điểm ưu tiên của các lỗi trên từng ảnh. Đứng đầu là `img_0020` (`11.524` điểm) vì vừa có `FIXED_DROP_LINE`, vừa dính cả `POSSIBLE_MISSING` và `POSSIBLE_WRONG_CLASS`. Tiếp theo là 6 ảnh `NEEDS_LABEL` (`10.0` điểm) do đang thiếu file nhãn ở mức `ERROR`, rồi tới các ảnh có nhiều cảnh báo ngữ nghĩa nặng (`img_0160`: `8.887`, `img_0127`: `8.752`, `img_0004`: `8.357`...). Với ngân sách 80 ảnh (`06_review_log.csv` khớp 80 dòng đầu của hàng đợi), người đã duyệt 74/80 ảnh có lỗi ngữ nghĩa `POSSIBLE_*` (cùng 6 ảnh thiếu nhãn), xử lý hết toàn bộ 18/18 ảnh `POSSIBLE_WRONG_CLASS`, 50/52 ảnh `POSSIBLE_MISSING`, 12/23 ảnh `POSSIBLE_FALSE_POS` và 8/24 ảnh `POSSIBLE_LOOSE_BOX`. Tổng số dòng cảnh báo `POSSIBLE_*` giảm từ 123 dòng ở `v2` xuống còn 57 dòng ở `v3`, còn lại 45 ảnh cuối hàng đợi chưa tới lượt (trong đó 29 ảnh có `POSSIBLE_*`).

## 3. Calibration (2 ngưỡng)

| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước -> sau) | Lý do (đánh đổi) |
|---|---:|---:|---|---|
| `duplicates.phash_dist` | 2 | 10 | `DUP_IMAGE_NEAR`: `1.00 / 0.50` -> `1.00 / 0.67` (`DUP_IMAGE_EXACT` giữ `1.00 / 1.00`) | Tăng recall từ `0.50` lên `0.67` (F1 `0.67 -> 0.80`) mà FP vẫn bằng 0; không tăng lên 16 vì trên `raw` bắt đầu bị bắt nhầm |
| `second_opinion.conf` | 0.25 | 0.6 | `WRONG_CLASS`: `0.56 / 0.83` -> `0.62 / 0.83`; `MISSING`: `0.50 / 1.00` -> `0.57 / 1.00`; `LOOSE_BOX`: `0.29 / 0.40` -> `0.20 / 0.20` | Cắt bớt báo nhầm trên `raw` (`POSSIBLE_MISSING` giảm từ 151 xuống 53 dòng để vừa hàng đợi 80 ảnh) và giữ nguyên 18 ca `WRONG_CLASS`, chấp nhận recall của `LOOSE_BOX` tụt từ `0.40` xuống `0.20` |

Chỗ calibration dễ đánh lừa: nếu nhìn kết quả trên tập `calib` có `phash_dist = 16` đạt F1 cao hơn (`0.91`), dễ chọn theo, nhưng chạy sang lô `raw` thì mức 16 gây ra 9 dương tính giả (6 lỗi `LEAK_TEST` nhầm và các cặp `DUP_IMAGE_NEAR` sai). Mở xem ảnh thật thấy `img_0008.jpg` (hai người trượt tuyết) và `img_0011.jpg` (một người đánh tennis) hoàn toàn không liên quan nhưng lại có `phash_dist = 16`. Ở mức chọn `phash_dist = 10`, tổng 22 ảnh bị loại ở bước 1 đều hợp lý khi kiểm tra lại: `img_0049.jpg` giống hệt `data/test/images/test_033.jpg`, cặp `img_0061` vs `img_0186` (`phash = 10`) cùng là cảnh ngồi ghế công viên bị crop/chỉnh màu nhẹ, còn `img_0077` vs `img_0223` (`phash = 6`) cùng là ảnh chiếc xe buýt trước tháp đồng hồ.

## 4. Cửa chặn và điều pipeline KHÔNG bắt được
- Chứng minh cửa chặn `Rework`: chạy `python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb` (không sửa tay `work/run/ds`). Do ngân sách bằng 0 nên 6 ảnh `MISSING_LABEL_FILE` không có người gán, `work/rep_nb/07_error_list_v3.txt` còn 6 `ERROR` (cùng 112/202 ảnh `WARN`, chiếm `55.45%`). Kết quả trong `work/rep_nb/08_summary.json` là **Rework**, mã thoát `20`, `exported: null` và không tạo thư mục `work/exp_nb/clean_v1`.
- Những điểm mù pipeline bỏ sót (có bằng chứng):
  1. Model phụ đoán sai cùng kiểu với nhãn gốc: so với `data/review_reference/labels/` trên 122 ảnh chưa duyệt, ảnh `img_0007` vẫn còn 6 box `car`, trong đó box ở `(0.889, 0.823)` thực chất là `truck` và phần lớn xe nhỏ ở bãi đỗ không có trong đáp án người (đáp án chỉ giữ 1 `car` + 1 `truck`). Do `data/cache/checker_preds.json` cũng đoán đúng 6 box `car` đó (kể cả box xe tải bị đoán thành `car` với `conf = 0.702`), ảnh này không sinh cảnh báo nào và không vào hàng đợi.
  2. Box lệch nhẹ (`IoU >= 0.5`): vì `second_opinion.iou_loose = 0.5`, các box chỉ rộng/lệch nhẹ so với vật thể (như `img_0002` có IoU từ `0.683` đến `0.9`, hay `img_0003`, `img_0008`) không bị gắn `POSSIBLE_LOOSE_BOX`. Ngoài ra với `DUP_IMAGE_NEAR`, trên `calib` tại `phash_dist = 10` vẫn sót `2/6` cặp trùng bị biến đổi mạnh hơn (recall `0.67`).
  3. Box mảnh bất thường theo tỉ lệ khung hình: khi viết thêm check bổ sung `aspect_ratio.py` (`BOX_ASPECT_RATIO`, ngưỡng `max_ratio = 7.0`), chạy trên `clean_v1` (202 ảnh) bắt được thêm `img_0042:5` (`person`, `25.1x240.8px`, tỉ lệ `9.58 > 7`), là box mảnh sát rìa trái đã bị người bỏ trong `review_reference` nhưng lọt qua cả pipeline chính lẫn hàng đợi, cùng `img_0124:6` (`car`, `118.4x13.0px`, tỉ lệ `9.11 > 7`, phần nóc xe lộ ở mép dưới).

## 5. Train: raw vs clean
Chạy trên Colab (`notebooks/day09_train_compare.ipynb`): model `yolo26n.pt`, `20` epoch, `imgsz=640`, `batch=16`, GPU T4, 2 seed (`0`, `1`), đo trên 100 ảnh test. Bộ `raw` khai báo 224 ảnh nhưng khi train Ultralytics bỏ qua 11 ảnh/nhãn lỗi (`corrupt`) nên thực tế dùng 213 ảnh (19 background); bộ `clean` dùng đủ 202 ảnh (`0` corrupt, `manifest_sha1 = 08522be8b27b006b8032e380e7574437996eef3b`).

Bảng từ `submission/results/comparison.md`:

| biến thể | #ảnh train | số seed | map50 (TB ± độ lệch) | map50_95 (TB ± độ lệch) | precision (TB ± độ lệch) | recall (TB ± độ lệch) |
|---|---|---|---|---|---|---|
| raw | 224 | 2 | 0.726 ± 0.000 | 0.512 ± 0.004 | 0.764 ± 0.061 | 0.649 ± 0.028 |
| clean | 202 | 2 | 0.701 ± 0.025 | 0.487 ± 0.008 | 0.759 ± 0.003 | 0.625 ± 0.019 |

Chênh mAP50 (clean − raw) = **-0.025**.

Nhận xét số liệu: mức chênh `-0.025` bằng đúng độ lệch chuẩn giữa 2 seed của `clean` (`± 0.025`, trong đó `clean_seed0` đạt `0.7180` còn `clean_seed1` đạt `0.6832`). Theo từng lớp, `clean` không hề thua ở `car` (`0.7381` vs `0.7375`), `person` (`0.8233` vs `0.8220`) và `bus` (`0.7033` vs `0.6949`), chủ yếu tụt ở lớp `truck` (`0.5377 ± 0.074` so với `0.6484 ± 0.013` của `raw`, riêng `clean_seed1` xuống `0.4856`, trên lớp chỉ có 41 box trong `class_stats.csv`). Vì độ lệch nằm gọn trong 1 độ lệch chuẩn với chỉ 2 seed và 100 ảnh test, chưa đủ cơ sở để kết luận `raw` tốt hơn `clean`.

Hai giả thuyết giải thích và cách kiểm:
1. `raw` vẫn còn 5 ảnh trùng với tập test (`LEAK_TEST`: `img_0049, img_0101, img_0167, img_0174, img_0221`) cùng 12 ảnh trùng lặp nên điểm test của `raw` có thể bị kéo lên giả tạo. Cách kiểm: tạo thêm biến thể `raw` đã bỏ 5 ảnh `LEAK_TEST` rồi train lại với ít nhất 3 đến 5 seed.
2. `clean_v1` mới là bản nháp `Hold` vì ngân sách 80/125 chỉ sửa được hơn nửa hàng đợi, vẫn còn 38/202 ảnh mang `WARN` chưa duyệt (`13` `POSSIBLE_MISSING`, `3` `POSSIBLE_WRONG_CLASS`, `20` `POSSIBLE_LOOSE_BOX`), cộng với lớp `truck` chỉ có 41 box nên dễ dao động giữa các seed. Cách kiểm: chạy pipeline với `--budget 125` cho duyệt hết hàng đợi (hoặc chạy thêm biến thể `oracle`) và train đủ `>= 3` seed để so sánh trực tiếp.

## 6. Quyết định và ghi chú AI
- Quyết định cuối: giữ ở **Hold**, chưa phát hành `clean_v1`. Để lên được **Release** (mã thoát `0`), cần tăng ngân sách duyệt để xem thêm ít nhất 18 đến 45 ảnh còn lại ở cuối `05_review_queue.csv` (tập trung 29 ảnh có `POSSIBLE_*`) nhằm hạ số ảnh chưa duyệt còn `WARN` từ `38/202` (`18.81%`) xuống dưới ngưỡng `10%` (`<= 20` ảnh), sau đó chạy lại `python -m pipeline.run`.
- Phần thưởng thêm (+3): viết check mới `pipeline/checks/aspect_ratio.py` (`BOX_ASPECT_RATIO`, đọc `max_ratio` từ `cfg`, mặc định `7.0`) kèm 4 unit test trong `tests/test_aspect_ratio.py` (`4 passed`); khi chạy trên 224 ảnh `data/raw` phát hiện 4 box bất thường (`img_0042:5`, `img_0068:8`, `img_0076:5`, `img_0155:2`), còn trên 202 ảnh `clean_v1` còn 2 cảnh báo (`img_0042:5` và `img_0124:6`).
- Ghi chú dùng AI:
  - Prompt chính: đưa yêu cầu bài từ `GUIDE.md` và `docs/PIPELINE.md`, mô tả rõ tham số, kiểu `Issue`/`Decision` và các ca biên để AI viết từng module theo thứ tự TDD (`label_format`, `gate`, `autofix`, `second_opinion`) rồi kiểm lại bằng `pytest`.
  - Cách kiểm code AI: chạy toàn bộ unit test `pytest`, rà từng nhánh xử lý dòng trống/dòng lỗi/ảnh thiếu nhãn và `reviewed`, rồi chạy `python -m pipeline.run` và mở ảnh ở `work/viz/` xem trực tiếp box.
  - 1 lần AI sai: lúc viết đoạn phân tích nhanh file báo cáo lỗi, AI dùng `.split()` mặc định nên bị dính dấu cách trong chuỗi `[WARN ]`, đếm ra `0` lỗi `POSSIBLE_*`; ngoài ra khi chạy script trên Windows ghi `\r\n` làm lệch SHA-1 so với file từ Colab nên phải đối chiếu và chuyển lại `\n`.
