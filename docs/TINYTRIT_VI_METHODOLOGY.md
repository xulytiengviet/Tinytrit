# Phương pháp thực nghiệm Tinytrit — tiếng Việt / CVNSS4.0 / tam phân / FPGA

## 1. Định nghĩa lại mục tiêu nghiên cứu

Bản Tinytrit không được xem là bản dịch nhãn giao diện thuần túy. Mục tiêu là **kiểm thử có thể lặp lại** giả thuyết: chuẩn hóa tiếng Việt sang CVNSS4.0 có thể cung cấp phân bố ký hiệu phù hợp biểu diễn 27 trạng thái (3³), từ đó giảm chi phí tokenizer và phần suy luận tam phân trên FPGA mà không làm mất chất lượng ngôn ngữ.

Ba biến thể cần so sánh dưới cùng tập dữ liệu và ngân sách huấn luyện:
1. Unicode UTF-8 + BPE byte-level (baseline Zig gốc).
2. CVNSS4.0 đã gán nhãn + tokenizer tương đương (không tự suy đoán luật).
3. CVNSS4.0 + mã Base27 3 trit/ký hiệu + trọng số tam phân.

Không suy ra rằng mã hóa gọn hơn luôn làm mô hình tốt hơn. Mã 3 trit/ký hiệu là biểu diễn **trừu tượng**; FPGA Artix-7 vẫn dùng cell nhị phân. RTL dùng 2 bit/trọng số, còn lý thuyết entropy tối thiểu của ba mức là log2(3) ≈ 1,585 bit.

## 2. Độ trung thực CVNSS4.0

CQN → CVNSS4.0 phải dùng oracle được lưu phiên bản và bộ test đối chiếu chuyên gia. Bộ oracle 5.0.0-audit-safe ghi nhận **56 nhóm đa nghĩa**, bao gồm 5 va chạm quan trọng. Các số audit này **không phải tỷ lệ chính xác**. Mẫu giải mã canonical không thể chứng minh tái tạo duy nhất CQN. Phải định nghĩa chính sách chấm điểm với tập gold và báo cáo CER/WER riêng; cổng mặc định đặt 98% *exact match* để tránh lấy số đếm nhóm làm bằng chứng.

Dữ liệu `{"cqn": "...", "cvnss": "..."}` được chuyển đổi bên ngoài, kiểm tra độc lập, không giả tạo nhãn từ phép encode Base27.

## 3. Tập dữ liệu

- Nguồn đề xuất: ngữ liệu văn học/nói tự nhiên và các tập tiếng Việt có quyền khai thác; tránh trộn train/test theo câu.
- Chuẩn Unicode NFC; lập hash nguồn và lưu phiên bản thuật toán CVNSS4.0.
- Deduplicate và chia deterministic theo hash văn bản nguồn 80/10/10; với tài liệu nhiều câu, nâng cấp sang hash **document ID** để ngăn rò rỉ ngữ cảnh.
- Bản dataset.py hiện chia theo câu CQN, vì vậy **chưa đạt chống rò rỉ ở mức tài liệu** nếu nhiều câu từ một tài liệu. Đưa vào đánh giá độc lập cần kiểm tra document-level overlap.
- Việc cắt bỏ dấu câu/ngoại lệ được coi là lỗi, không im lặng tự sửa.

## 4. Huấn luyện và đánh giá

- Ghi seed, phiên bản Zig, thông số STE/AdamW, lịch learning rate, batch, số bước, checkpoint SHA256, phần cứng host.
- Huấn luyện baseline và Tinytrit dưới số token và thời gian tính toán có thể so sánh; báo cáo loss, perplexity, CER/WER đầu ra, top-1 token accuracy trên held-out.
- Thử riêng ảnh hưởng của CVNSS4.0: Unicode-BPE vs CVNSS-BPE vs CVNSS-Base27.
- Định lượng trọng số {-1,0,+1}; xác định chuẩn export cùng kích thước tensor, thứ tự endian và quy tắc 00=0, 01=+1, 10=-1, 11=invalid.
- Model HSLM Zig mặc định 729 vocab / 3 block / ~1,95M param; RTL full 128 vocab / 4 block, **không thể nạp trực tiếp checkpoint Zig vào RTL**. Cần adapter/đào tạo lại hoặc cấu hình kiến trúc thống nhất, đồng thời đối chiếu token CPU–RTL.

## 5. Tái lập FPGA

Gói 52 tệp sạch đi kèm từ upstream thiếu module Verilog phụ thuộc và các trọng số .mem; cần nhập lại mã RTL và generator **theo commit được ghim hash** từ source đầy đủ, không phát minh bitstream. Trước synthesis: unit test Base27, golden vectors cho matvec, mô phỏng RTL, so khớp CPU–RTL; sau synthesis: Yosys thống kê DSP/LUT/BRAM, nextpnr timing; sau flash: UART ≥16 token, đối chiếu trace, đo tok/s và watt bằng thiết bị thật.

Số upstream (`63 tok/s@92MHz, ~1W, 0 DSP`) là mục tiêu **tham chiếu**, không phải kết quả đo trên Tinytrit. Chính báo cáo upstream ghi TODO **Trained weights: replace deterministic patterns with actual trained ternary weights**.

## 6. Chỉ PASS nếu đầy đủ bằng chứng

- CVNSS: ≥1.000 cặp gold/test độc lập; exact match ≥98%.
- Roundtrip CVNSS có chính sách công bố: ≥1.000 cặp; ≥98%.
- Dự đoán token held-out: ≥1.000; top-1 ≥98% (mục tiêu nghiên cứu rất cao, không mặc định đạt).
- CPU–FPGA token parity: ≥16 token thật; ≥98%.
- Throughput ≥61,74 tok/s; Fmax ≥90,16 MHz; 0 DSP48, ≥16 token autoregressive.
- Công suất đo 0–1,25 W (dung sai kỹ thuật khai báo 25% so với số ~1 W; không coi là “98% chính xác về điện năng”).
- Checkpoint huấn luyện tiếng Việt, bitstream, log tổng hợp, timing, UART và công suất kèm hash SHA256.
- Cần phản biện độc lập kết quả và chống ghi đè bằng chứng. Workflow FAIL khi thiếu evidence.

**Không đạt = FAIL / chưa nghiệm thu.** Không có cơ chế auto-PASS do chỉ tồn tại file mô tả, unit test giả lập hoặc kết quả công bố của upstream.

## 7. Ghi nhận

Nguồn kiến trúc: [Trinity](https://github.com/Trinity-S-AI-DNA/trinity) v2.0.2-fpga-autoregressive-clean, MIT. Phần tiếng Việt: Long Ngo. Nền tảng CVNSS4.0: Kiều Trường Lâm và Trần Tư Bình (ghi nhận nghiên cứu). Việc kế thừa mã nguồn không hàm ý tác giả upstream xác nhận Tinytrit.
