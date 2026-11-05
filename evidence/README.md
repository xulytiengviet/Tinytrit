# Evidence directory — không có bằng chứng thì FAIL

Mọi dữ liệu trong thư mục `evidence/real/` phải đến từ một lần chạy **thực nghiệm trên FPGA**. Không commit file ví dụ được đánh dấu như đã nghiệm thu.

Đặt `metrics.json` và các file sau (tên có thể khác, nhưng phải trỏ đúng trong khóa `evidence`): `cvnss_gold.jsonl`, `cvnss_roundtrip.jsonl`, `heldout_token_predictions.jsonl`, `cpu_fpga_trace.jsonl`, `training.log`, `checkpoint`, `bitstream.bit`, `yosys.rpt`, `timing.rpt`, `uart.log`, `power.csv`. Mỗi entry có `path` tương đối và `sha256` thực tế. Các JSONL có `{"expected":"...","actual":"..."}` từng dòng, phải đúng là kết quả trên tập test độc lập.

Mẫu schema JSON (chưa thể PASS):
```json
{
  "dataset": {"sha256": "64-character-sha256", "independent_test_set": false, "leakage_count": null},
  "model": {"trained_on_vietnamese": false, "weights_sha256": null},
  "fpga": {
    "board": "QMTech XC7A100T-1FGG676C",
    "physical_board_verified": false,
    "uses_vietnamese_trained_weights": false,
    "dsp48_count": null, "tokens_generated": null,
    "benchmark_clock_mhz": 50, "throughput_tok_s": null, "fmax_mhz": null, "power_w": null
  },
  "evidence": {}
}
```

Lệnh: `python -m tinytrit_vn.gate98 --report evidence/real/metrics.json --evidence-dir evidence/real --output evidence/gate_result.json`. Sẽ trả exit code 1 cho mọi hồ sơ không hợp lệ.

**Cảnh báo:** file có hash đúng chỉ xác minh sự toàn vẹn của file, không xác minh thiết bị ghi, bằng chứng có bị dựng giả hoặc mẫu đánh giá có bị học thuộc; hội đồng nghiệm thu vẫn cần kiểm tra độc lập.
