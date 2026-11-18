# Báo cáo Day 09 — Thạch Trung Đức, 2A20260314

## 1. Kết luận trước
Pipeline trả kết luận **Hold** (mã thoát `10`). Trong **224** ảnh thô đưa vào kiểm tra đầu vào (intake), hệ thống loại **22** ảnh vi phạm và chấp nhận **202/224** ảnh; ở cuối pipeline xuất **202** ảnh bản nháp vào `submission/export/clean_v1/` (`manifest.json` SHA-1 `08522be8b27b006b8032e380e7574437996eef3b`) nhưng **không phát hành (Release)**. Lý do: tuy toàn bộ **0** lỗi mức `ERROR` đã được giải quyết (`07_error_list_v3.txt` còn `0` `ERROR`), vẫn còn **38/202** ảnh chưa qua duyệt mang cảnh báo `WARN` (`warn_ratio = 18.81%`, vượt ngưỡng `warn_ratio_hold = 10%`) với tổng **77** dòng `WARN` do ngân sách duyệt chỉ đủ xem **80/125** ảnh trong hàng đợi.

## 2. Lỗi và phân việc
Tổng hợp từ `submission/reports/02_error_list_v1.txt` (211 dòng lỗi/cảnh báo: 22 `ERROR` ở intake + 36 `ERROR` QC + 153 `WARN` QC):

| Mã lỗi | Số ảnh / dòng | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| `BAD_SIZE` | 3 / 3 | Máy (loại ở intake) | Ảnh có cạnh ngắn `< 250px` (`img_0107`, `img_0113`, `img_0122`), không đủ độ phân giải đưa vào train |
| `CORRUPT_IMAGE` | 2 / 2 | Máy (loại ở intake) | File ảnh hỏng không giải mã được (`img_0010`, `img_0136`), gây sập khi đọc |
| `DUP_IMAGE_EXACT` | 8 / 8 | Máy (loại ở intake) | Trùng byte hoàn toàn với ảnh trước đó trong lô |
| `DUP_IMAGE_NEAR` | 4 / 4 | Máy (loại ở intake) | Trùng gần đúng (`phash <= 10`, vd. nén/crop/sáng nhẹ), gây học lệch và đánh giá ảo |
| `LEAK_TEST` | 5 / 5 | Máy (loại ở intake) | Trùng ảnh trong tập `data/test` (`img_0049`, `img_0101`, `img_0167`, `img_0174`, `img_0221`), bắt buộc loại để tránh rò rỉ |
| `BAD_CLASS_NAME` | 1 nguồn (`data.yaml`) / 2 | Máy (`autofix`) | Chuẩn hoá tên lớp sai hoa/thường (`Person`, `Bus` → `person`, `bus`) một cách tất định |
| `BAD_CLASS_ID` | 6 / 6 | Máy (`autofix`) | Xoá dòng (`drop_line`) có ID lớp ngoài `{0, 1, 2, 3}` (gián tiếp xoá luôn `4` dòng `CLASS_RARE` ở v1) |
| `BAD_FORMAT` | 3 / 3 | Máy (`autofix`) | Xoá dòng (`drop_line`) sai định dạng cột / toạ độ không hợp lệ trong file `.txt` |
| `BOX_OUT_OF_IMAGE` | 8 / 8 | Máy (`autofix`) | Cắt toạ độ box về đoạn `[0, 1]` (`clip_box`) để khôi phục khung hợp lệ |
| `BOX_ZERO` | 4 / 4 | Máy (`autofix`) | Xoá dòng (`drop_line`) có chiều rộng hoặc chiều cao `<= 0` |
| `DUP_BOX` | 7 / 7 | Máy (`autofix`) | Xoá dòng box trùng lặp gần khít nhau trên cùng ảnh |
| `CLASS_RARE` | 1 nguồn / 4 | Máy (hệ quả autofix) | Bốn ID hiếm (`-1, 4, 7, 93`) biến mất về `0` sau khi autofix xoá `BAD_CLASS_ID` |
| `MISSING_LABEL_FILE` | 6 / 6 | Người (hàng đợi) | Thiếu hẳn file `.txt`, máy không thể tự bịa nhãn, phải gắn cờ `NEEDS_LABEL` ưu tiên mức `ERROR` |
| `EMPTY_LABEL` | 12 / 12 (15 sau fix) | Người (hàng đợi) | Cần người xác nhận ảnh thật sự không có đối tượng hay bị bỏ sót nhãn (tăng lên 15 do 3 ảnh bị xoá hết dòng hỏng) |
| `BOX_TINY` | 4 / 6 (5 / 7 sau fix) | Người (hàng đợi) | Đối tượng cạnh `< 10px` (thêm 1 box ở `img_0030` sau khi `clip_box`), cần người quyết định giữ hay bỏ |
| `BOX_HUGE` | 3 / 3 | Người (hàng đợi) | Box chiếm gần hết khung hình, cần kiểm tra có phải box bao nhầm nhiều vật thể/nền không |
| `POSSIBLE_MISSING` | 52 / 53 | Người (hàng đợi) | Model phụ thấy vật thể (`conf >= 0.6`) nhưng nhãn thiếu; cần người kiểm chứng để tránh chép sai từ model phụ |
| `POSSIBLE_FALSE_POS` | 27 / 29 (23 / 24 sau fix) | Người (hàng đợi) | Box nhãn không có model phụ đồng thuận; cần người quyết định là nhãn dư hay vật thể khó bị model phụ bỏ sót |
| `POSSIBLE_LOOSE_BOX` | 24 / 28 | Người (hàng đợi) | Khớp lớp nhưng `IoU <= 0.75`; cần người siết lại biên box nếu lỏng |
| `POSSIBLE_WRONG_CLASS` | 18 / 18 | Người (hàng đợi) | Khớp vị trí (`IoU >= 0.5`) nhưng lệch lớp so với `second_opinion`; lỗi nghiêm trọng trực tiếp gây nhầm lớp khi train |

**Cách xếp hàng đợi và hiệu quả ngân sách 80 ảnh**: `05_review_queue.csv` (125 ảnh) cộng dồn điểm ưu tiên theo độ nặng và mật độ lỗi: đứng #1 là `img_0020` (`11.524`, vừa bị `FIXED_DROP_LINE` vừa dính cả `POSSIBLE_MISSING` và `POSSIBLE_WRONG_CLASS`), tiếp theo là toàn bộ 6 ảnh `NEEDS_LABEL` (`10.0`) vì đang ở mức `ERROR`, rồi tới các ảnh hội tụ nhiều lỗi ngữ nghĩa nặng (`img_0160`: `8.887`, `img_0127`: `8.752`, `img_0004`: `8.357`...). Với ngân sách **80 ảnh** (`06_review_log.csv` khớp 80 ảnh đầu hàng đợi), người đã duyệt **74/80 ảnh có lỗi ngữ nghĩa `POSSIBLE_*`** (cùng 6 ảnh `NEEDS_LABEL`), xử lý trọn vẹn **18/18** ảnh `POSSIBLE_WRONG_CLASS`, **50/52** ảnh `POSSIBLE_MISSING`, **12/23** ảnh `POSSIBLE_FALSE_POS` và **8/24** ảnh `POSSIBLE_LOOSE_BOX`; tổng số dòng cảnh báo `POSSIBLE_*` giảm từ **123 dòng (v2)** xuống còn **57 dòng (v3)**, còn lại 45 ảnh cuối hàng đợi (29 ảnh mang `POSSIBLE_*`) chưa được duyệt.

## 3. Calibration (2 ngưỡng)

| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---:|---:|---|---|
| `duplicates.phash_dist` | 2 | 10 | `DUP_IMAGE_NEAR`: `1.00 / 0.50` → `1.00 / 0.67` (`DUP_IMAGE_EXACT` giữ `1.00 / 1.00`) | Nâng recall trùng gần đúng từ `0.50` lên `0.67` (F1 `0.67 → 0.80`) mà vẫn giữ `FP = 0`; không đẩy lên `16` vì trên `raw` phát sinh `9` dương tính giả |
| `second_opinion.conf` | 0.25 | 0.6 | `WRONG_CLASS`: `0.56 / 0.83` → `0.62 / 0.83`; `MISSING`: `0.50 / 1.00` → `0.57 / 1.00`; `LOOSE_BOX`: `0.29 / 0.40` → `0.20 / 0.20` | Lọc bớt nhiễu model phụ: giảm `POSSIBLE_MISSING` trên `raw` từ `151` xuống `53` để không làm nghẽn ngân sách 80 ảnh và giữ nguyên toàn bộ `18` `WRONG_CLASS`, chấp nhận đánh đổi giảm recall `LOOSE_BOX` (`0.40 → 0.20`) |

**Điểm calibration dễ đánh lừa & kiểm chứng thực tế trên dữ liệu**:
Nếu chỉ nhìn tổng số ca bắt được trên `raw` (`raw_hits`) khi tăng `duplicates.phash_dist`, rất dễ ngộ nhận ngưỡng lớn luôn tốt hơn, nhưng ở `phash_dist = 16` xuất hiện **9 dương tính giả trên `raw`** (gồm **6** cảnh báo `LEAK_TEST` sai và các cặp `DUP_IMAGE_NEAR` giả): kiểm tra trực tiếp cho thấy `img_0008.jpg` (2 người trượt tuyết trên núi) và `img_0011.jpg` (tay vợt tennis trên sân xanh) hoàn toàn khác cảnh nhưng có `phash_dist = 16`. Ngược lại, kiểm tra các ảnh bị loại ở mức chọn `phash_dist = 10` (tổng 22 ảnh loại ở intake) đều xác nhận hợp lý: `img_0049.jpg` trùng hệt `data/test/images/test_033.jpg` (tâng bóng trên vỉa hè), `img_0061` vs `img_0186` (`phash = 10`, cùng ảnh ngồi ghế công viên bị crop/đổi cân bằng trắng) và `img_0077` vs `img_0223` (`phash = 6`, cùng ảnh xe buýt trước tháp đồng hồ).

## 4. Cửa chặn và điều pipeline KHÔNG bắt được
- **(a) Chứng minh gate `Rework` chặn đúng**: Chạy lệnh `python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb` (không sửa tay `work/run/ds`). Khi `budget = 0`, 6 ảnh thiếu file nhãn (`MISSING_LABEL_FILE`) không được gán nên `work/rep_nb/07_error_list_v3.txt` còn nguyên **6 lỗi mức `ERROR`** (và `112/202 = 55.45%` ảnh mang `WARN`). Kết quả trong `work/rep_nb/08_summary.json` là quyết định **`Rework`**, mã thoát **`20`**, `exported: null` và **không tạo** thư mục `work/exp_nb/clean_v1`.
- **(b) ≥ 2 điểm mù có bằng chứng**:
  1. **Nhầm lớp và thừa/thiếu box khi model phụ mắc cùng thiên kiến với nguồn nhãn gốc**: Đối chiếu `clean_v1` với `data/review_reference/labels/` trên 122 ảnh chưa duyệt phát hiện `img_0007` vẫn giữ `6 car (0)`, trong khi đáp án người chỉ giữ `1 car` + `1 truck (2)` tại `(0.889, 0.823)`. Xem `data/cache/checker_preds.json` thấy model phụ cũng đoán xe bán tải đó là `car (0, conf = 0.702)` cùng 5 box xe nhỏ tương tự (`0.649–0.852`), nên `img_0007` không tạo bất kỳ cảnh báo nào và không lọt vào `05_review_queue.csv`.
  2. **Box lỏng nhẹ (IoU > `0.75`) và hạn chế của pHash trước biến đổi hình học mạnh**: Trên các ảnh chưa duyệt như `img_0002`, `img_0003`, `img_0008`, box nguồn chỉ lệch ~`0.5%–1.5%` toạ độ so với `review_reference` nên không bị gắn `POSSIBLE_LOOSE_BOX` (và ngay trên `calib`, recall `LOOSE_BOX` ở `conf=0.6` chỉ đạt `0.20`). Tương tự, `DUP_IMAGE_NEAR` tại `phash_dist = 10` trên `calib` chỉ đạt recall `0.67` (bỏ sót `2/6` cặp trùng biến đổi hình học mạnh như xoay/lật/crop sâu).

## 5. Train: raw vs clean
Cấu hình chạy Colab (`notebooks/day09_train_compare.ipynb`): `yolo26n.pt`, `20` epochs, `imgsz=640`, `batch=16`, Tesla T4, 2 seed (`0`, `1`), test `100` ảnh. Trên thực tế `raw` khai báo 224 ảnh nhưng Ultralytics bỏ qua **11 ảnh/nhãn hỏng (`corrupt`)** nên chỉ dùng `213` ảnh train (`19` background), còn `clean` dùng đủ **`202`** ảnh (`0` corrupt, `manifest_sha1 = 08522be8b27b006b8032e380e7574437996eef3b`).

Bảng tổng hợp từ `submission/results/comparison.md`:

| biến thể | #ảnh train | số seed | map50 (TB ± độ lệch) | map50_95 (TB ± độ lệch) | precision (TB ± độ lệch) | recall (TB ± độ lệch) |
|---|---|---|---|---|---|---|
| raw | 224 | 2 | 0.726 ± 0.000 | 0.512 ± 0.004 | 0.764 ± 0.061 | 0.649 ± 0.028 |
| clean | 202 | 2 | 0.701 ± 0.025 | 0.487 ± 0.008 | 0.759 ± 0.003 | 0.625 ± 0.019 |

Chênh mAP50 (clean − raw) = **-0.025**.

- **So sánh với độ lệch chuẩn và kết luận trung thực**: Mức chênh `-0.025` về trị tuyệt đối **bằng đúng độ lệch chuẩn giữa 2 seed của `clean` (`± 0.025`)** (`clean_seed0 = 0.7180`, `clean_seed1 = 0.6832`; trong khi `precision` của `raw` cũng dao động `± 0.061`). Theo từng lớp, `clean` thực tế ngang hoặc nhỉnh nhẹ ở `car` (`0.7381` vs `0.7375`), `person` (`0.8233` vs `0.8220`) và `bus` (`0.7033` vs `0.6949`), nhưng riêng lớp **`truck`** (chỉ có **41** box trong `clean_v1` theo `class_stats.csv`) giảm từ `0.6484 ± 0.013` xuống `0.5377 ± 0.074` (`clean_seed1` tụt còn `0.4856`). Vì `|clean − raw|` nằm trong nhiễu `1× std` với chỉ `2` seed và tập test `100` ảnh, **chưa thể kết luận `raw` hơn `clean` hay pipeline làm giảm chất lượng**.
- **Hai giả thuyết giải thích & cách kiểm**:
  1. **`raw` được hưởng lợi ảo từ 5 ảnh rò rỉ `LEAK_TEST` (và trùng lặp)**: `raw` vẫn chứa 5 ảnh giống `data/test` (`img_0049, img_0101, img_0167, img_0174, img_0221`) cùng 12 ảnh trùng, có thể kéo nâng mAP của `raw` khi train ngắn `20` epochs. *Cách kiểm*: Train biến thể `raw` nhưng loại 5 ảnh `LEAK_TEST` (và kiểm tra điểm trên `test` tách riêng), tăng lên `>= 3–5` seed.
  2. **`clean_v1` vẫn là bản nháp `Hold` còn nhãn máy chưa duyệt và lớp `truck` quá ít mẫu**: Với ngân sách 80/125, vẫn còn 38/202 ảnh mang `WARN` chưa được người sửa (`13` `POSSIBLE_MISSING`, `3` `POSSIBLE_WRONG_CLASS`, `20` `POSSIBLE_LOOSE_BOX`) và chỉ có 41 box `truck`, khiến nhiễu khởi tạo giữa seed 0/1 ảnh hưởng mạnh tới `AP50(truck)`. *Cách kiểm*: Nâng `--budget` lên `125` để sửa hết hàng đợi (đưa về `Release`), đồng thời chạy đối chiếu thêm biến thể **`oracle`** (`review_reference`) với `>= 3` seed để tách phần đóng góp của 45 ảnh chưa duyệt.

## 6. Quyết định và ghi chú AI
- **(a) Quyết định cuối & đường tới `Release`**: Hiện tại giữ nguyên quyết định **Hold** (không đưa bản nháp `clean_v1` vào phát hành chính thức). Để chuyển thành **Release** (mã thoát `0`), cần duyệt thêm tối thiểu ~**20–45 ảnh** còn lại trong `05_review_queue.csv` (ưu tiên 29 ảnh mang `POSSIBLE_*` ở cuối hàng đợi) nhằm kéo số ảnh chưa duyệt còn `WARN` từ `38/202` (`18.81%`) xuống dưới ngưỡng `warn_ratio_hold = 10%` (`< 21` ảnh), sau đó chạy lại `python -m pipeline.run` và xác nhận `decision = Release`.
- **(b) Ghi chú AI**:
  - **Prompt chính**: Cung cấp đầy đủ đặc tả kho mã (`GUIDE.md`, `docs/PIPELINE.md`, `RULES.md`), yêu cầu cài đặt tuần tự 4 module kiểm/autofix/gate theo TDD (`pytest`), tách riêng vòng calibration 2 ngưỡng, chạy chứng minh `Hold`/`Rework` và tổng hợp kết quả Colab vào báo cáo.
  - **Cách kiểm code AI**: Chạy toàn bộ test đơn vị (`79 passed`), kiểm tra SHA-1 tệp được bảo vệ (`scripts/_protected.json`), kiểm tra trực quan hình ảnh vẽ box (`work/viz/`, `work/viz_queue/`), kiểm tra `scripts/check_submission.py` và đối chiếu từng con số với file báo cáo thực tế.
  - **1 lần AI sai / trục trặc**: Khi dùng script tách dòng phân tích `04_error_list_v2.txt` bằng `.split()`, AI bỏ qua khoảng trắng trong tiền tố `[WARN ]` khiến kết quả đếm ban đầu trả về `0` lỗi `POSSIBLE_*`; ngoài ra khi chạy lại `summarize_results.py` trên Windows đã ghi `\r\n` làm đổi SHA-1 file `.md`/`.json` nên phải rà soát lại bằng script đối chiếu và khôi phục chuẩn LF từ Colab.
