# Tinytrit — Mô hình tiếng Việt trên nền tảng tam phân và FPGA

**Dự án nghiên cứu / chưa nghiệm thu phần cứng.** Đây là bản Việt hóa và lớp thực nghiệm độc lập của [Trinity v2.0.2 FPGA autoregressive](https://github.com/Trinity-S-AI-DNA/trinity/tree/v2.0.2-fpga-autoregressive-clean), kết hợp CVNSS4.0, mã cơ số 27, trọng số tam phân và FPGA. Người duy trì phần Việt hóa: **Long Ngo**. Giữ nguyên ghi nhận tác giả và giấy phép MIT của mã nguồn Trinity gốc.

> **Nguyên tắc:** CHỈ PASS KHI MỖI CHỈ TIÊU BẮT BUỘC ĐẠT TỐI THIỂU 98%, CÓ TẬP KIỂM TRA ĐỘC LẬP VÀ BẰNG CHỨNG FPGA THẬT. Không đồng nhất 98% độ chính xác với 98% mức sử dụng BRAM.

## Mục tiêu kỹ thuật

CQN (tiếng Việt gốc) → **oracle CVNSS4.0 có phiên bản và chính sách đa nghĩa** → dữ liệu CVNSS4.0 đã kiểm chứng → bảng mã 27 ký hiệu được khai báo tường minh → mã 3 trit/ký hiệu → tokenizer/tập học → **HSLM/Zig** (huấn luyện có STE, AdamW) → lượng tử {-1, 0, +1} → xuất trọng số/kiểm chứng CPU → RTL → FPGA XC7A100T → phép đo UART, tốc độ, timing, năng lượng.

Lưu ý: các mũi tên “xuất trọng số sang RTL” và “huấn luyện → bitstream” là **công việc nghiên cứu chưa hoàn thành**, không phải tính năng chạy sẵn. HSLM Zig mặc định có vocabulary 729 và 3 block, còn RTL full FPGA của báo cáo có vocabulary 128 và 4 block; cần tái cấu trúc tương thích trước khi ghép.

## Đối chứng gốc và tính trung thực

| Chỉ tiêu | Báo cáo Trinity gốc | Tinytrit Việt hóa |
|---|---:|---|
| Mục tiêu bo mạch | QMTech XC7A100T | Chưa xác minh bằng phần cứng |
| Tần số tối đa | 92 MHz (ước lượng timing) | Chưa đo |
| Thông lượng | ~34 token/s đo ở 50 MHz; ~63 tok/s là ngoại suy tại 92 MHz | Chưa đo |
| Công suất | Chưa có đo đạc công suất; tuyên bố ~1 W đã bị rút lại | Chưa đo |
| DSP48 | 0 | Chưa tổng hợp lại |
| HSLM Zig | ~1,95 triệu tham số, ~390 KB lý thuyết | Chưa huấn luyện trên tiếng Việt |
| RTL FPGA full | 128 token, 4 block | Chưa nạp trọng số học tiếng Việt |

Gói **Clean Scientific Release** đã cung cấp có 52 tệp (ZIP 1,2 MB; giải nén ~15,9 MB, gồm các bitstream). SHA-256 ZIP: `242b385bbcf68004bfcd98705d50ea3c14761e54958d829c49ca15d503c8e20b`.

**Rào cản tái lập:** gói ZIP thiếu 10 `.mem` tham chiếu bởi RTL và các module Verilog phụ thuộc như `embedding_lookup`, `trinity_block`, `lm_head_matvec`, `argmax_unit`. Tệp `.bit` dựng sẵn không chứng minh trọng số đã huấn luyện tiếng Việt. Không công bố kết quả Việt hóa dựa trên số công bố của Trinity.

## Cách chạy phần đã triển khai

Yêu cầu Python 3.10+ (thư viện chuẩn), Zig 0.15.x cho phần HSLM gốc.

```bash
# Kiểm thử mã Base27 và cổng nghiệm thu (không cần FPGA)
python -m unittest discover -s tests -p 'test_tinytrit_vn.py' -v

# Kiểm toán gói clean gốc (nếu lưu ZIP ở đường dẫn bên dưới)
python -m tinytrit_vn.audit path/to/trinity-v2.0.2-fpga-autoregressive.zip --strict

# Chuẩn bị dữ liệu ĐÃ ĐƯỢC oracle CVNSS4.0 chuyển đổi, gán nhãn
python -m tinytrit_vn.dataset --input data/vi_cvnss_gold.jsonl \
  --alphabet-file data/cvnss27.alphabet.txt --oracle-version 5.0.0-audit-safe \
  --out data/processed

# Dùng trainer gốc sau khi đã xác thực môi trường build và dữ liệu
zig build hslm-train -- --data data/processed/train.txt --steps 50000

# Gate nghiêm ngặt: thiếu bằng chứng hoặc <98% => FAIL (exit 1)
python -m tinytrit_vn.gate98 --report evidence/real/metrics.json \
  --evidence-dir evidence/real
```

Tệp đầu vào JSONL: mỗi dòng cần `{"cqn":"...","cvnss":"..."}`, là **cặp văn bản được kiểm chứng độc lập**. Không tự nhận một phép thay ký tự đơn giản là bộ chuyển CVNSS4.0 chuẩn. Do CVNSS4.0 có nhóm biểu diễn đa nghĩa, cần tập gold kiểm định chính sách canonical riêng.

Tệp `data/cvnss27.alphabet.txt` phải do người nghiên cứu cung cấp và xác nhận chính xác 27 ký hiệu; bộ công cụ **không tự suy đoán** bảng chữ cái chính thức. Phần Base27 dùng 3 trit cân bằng (-1/0/+1) cho 27 trạng thái, hoàn toàn khác mã trọng số RTL 2 bit (00/01/10). Ba trit không phải ba trit vật lý trên FPGA nhị phân.

## Cổng nghiệm thu >=98%

Cần **ít nhất 1.000 mẫu** cho từng bộ đánh giá CVNSS đầu ra, round-trip và dự đoán token trên tập held-out, cùng **>=16 token** cho đối chiếu CPU–FPGA. Mỗi phép đo phải >=98% exact match. FPGA phải có log, hash bằng chứng, trọng số đã huấn luyện, 0 DSP48, throughput >=33,32 token/s **đo ở 50 MHz**, Fmax >=90,16 MHz (tổng hợp timing) và báo cáo công suất đo thực tế, không lấy ~1 W làm chuẩn do upstream đã rút lại. Gate cố ý FAIL nếu thiếu một thành phần; phép kiểm phần mềm đơn thuần không cấp phép công bố kết quả phần cứng.

Xem [phương pháp khoa học và dữ liệu](docs/TINYTRIT_VI_METHODOLOGY.md), [hướng dẫn bằng chứng nghiệm thu](evidence/README.md), [mã gate98](tinytrit_vn/gate98.py) và [đơn vị kiểm thử](tests/test_tinytrit_vn.py).

## Giấy phép và xuất xứ

Tinytrit kế thừa Trinity theo giấy phép **MIT**; không xóa hoặc thay đổi bản quyền nguồn. CVNSS4.0 được ghi nhận từ công trình của **Kiều Trường Lâm và Trần Tư Bình**; luật chuyển đổi phải được lấy từ oracle đã kiểm toán, không suy diễn bảng ánh xạ. Bản phát hành khoa học mới chỉ được xem xét khi đạt gate98 và có kiểm tra độc lập.
