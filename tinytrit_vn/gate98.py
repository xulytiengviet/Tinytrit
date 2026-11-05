"""Fail-closed experimental release gate; cannot substitute claims for evidence."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

THRESHOLD = 0.98
REFERENCE_TOK_S = 63.0
REFERENCE_FMAX_MHZ = 92.0
REQUIRED = (
    "cvnss_gold", "cvnss_roundtrip", "heldout_token_predictions",
    "cpu_fpga_trace", "training_log", "checkpoint", "bitstream",
    "yosys_report", "timing_report", "uart_log", "power_log",
)
PAIR_FILES = {
    "cvnss_gold": 1000, "cvnss_roundtrip": 1000,
    "heldout_token_predictions": 1000, "cpu_fpga_trace": 16,
}


def is_sha256(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def score_pairs(path: Path) -> tuple[float, int]:
    good = count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        pair = json.loads(line)
        if not isinstance(pair, dict) or not isinstance(pair.get("expected"), str) or not isinstance(pair.get("actual"), str) or not pair["expected"]:
            raise ValueError(f"Thiếu cặp expected/actual trong {path}")
        good += pair["expected"] == pair["actual"]
        count += 1
    return good / count if count else 0, count


def _require(checks, name, ok, detail):
    checks.append({"check": name, "pass": bool(ok), "detail": detail})


def validate(report_path: Path, evidence_dir: Path) -> dict:
    checks = []
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        evidence = report["evidence"]
        data = report["dataset"]
        model = report["model"]
        fpga = report["fpga"]
        if not isinstance(evidence, dict):
            raise ValueError("evidence phải là đối tượng JSON")
    except (OSError, ValueError, KeyError, TypeError) as err:
        return {"status": "FAIL", "checks": [{"check": "report", "pass": False, "detail": str(err)}]}

    root = evidence_dir.resolve()
    paths = {}
    for label in REQUIRED:
        entry = evidence.get(label)
        ok = isinstance(entry, dict) and isinstance(entry.get("path"), str) and is_sha256(entry.get("sha256"))
        path = None
        if ok:
            path = (root / entry["path"]).resolve()
            ok = path.is_relative_to(root) and path.is_file()
        if ok:
            ok = hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
        _require(checks, f"evidence:{label}", ok, "Tệp và SHA-256 xác thực" if ok else "Thiếu tệp hoặc hash sai")
        if ok:
            paths[label] = path

    _require(checks, "dataset:sha256", is_sha256(data.get("sha256")), "SHA-256 tập dữ liệu")
    _require(checks, "dataset:independent", data.get("independent_test_set") is True, "Tập kiểm tra độc lập")
    _require(checks, "dataset:no_leakage", data.get("leakage_count") == 0, "Không có giao thoa train/test")
    _require(checks, "model:trained_weights", model.get("trained_on_vietnamese") is True and is_sha256(model.get("weights_sha256")), "Checkpoint có nguồn gốc huấn luyện")

    for label, minimum in PAIR_FILES.items():
        if label not in paths:
            continue
        try:
            score, count = score_pairs(paths[label])
            _require(checks, f"accuracy:{label}", count >= minimum and score >= THRESHOLD,
                     f"Exact-match={score:.4%}; n={count}; yêu cầu >=98% và n>={minimum}")
        except (ValueError, OSError, TypeError) as err:
            _require(checks, f"accuracy:{label}", False, str(err))

    def numeric(key):
        value = fpga.get(key)
        return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else float("nan")

    board = fpga.get("board")
    _require(checks, "hardware:board", board == "QMTech XC7A100T-1FGG676C" and fpga.get("physical_board_verified") is True,
             "Phải có xác minh trên board XC7A100T thật")
    _require(checks, "hardware:trained_image", fpga.get("uses_vietnamese_trained_weights") is True,
             "Bitstream có trọng số huấn luyện tiếng Việt, không dùng trọng số mẫu")
    _require(checks, "hardware:zero_dsp", fpga.get("dsp48_count") == 0, "Yosys: DSP48 phải bằng 0")
    _require(checks, "hardware:generated_tokens", numeric("tokens_generated") >= 16, "Tối thiểu 16 token autoregressive")
    _require(checks, "hardware:throughput", numeric("throughput_tok_s") >= THRESHOLD * REFERENCE_TOK_S,
             f"Thông lượng >= {THRESHOLD * REFERENCE_TOK_S:.2f} tok/s (98% của 63)")
    _require(checks, "hardware:fmax", numeric("fmax_mhz") >= THRESHOLD * REFERENCE_FMAX_MHZ,
             f"Fmax >= {THRESHOLD * REFERENCE_FMAX_MHZ:.2f} MHz (98% của 92)")
    # Source says ~1W; 1.25 W is a declared tolerance, not a 98% energy-accuracy claim.
    _require(checks, "hardware:power", 0 < numeric("power_w") <= 1.25,
             "Công suất đo >0 và <=1.25 W; sai số/thiết bị phải giải trình")
    passed = bool(checks) and all(c["pass"] for c in checks)
    return {
        "status": "PASS" if passed else "FAIL",
        "threshold": THRESHOLD,
        "reproduction_targets": {"tok_s": REFERENCE_TOK_S, "fmax_mhz": REFERENCE_FMAX_MHZ},
        "checks": checks,
        "note": "Đây là gate bằng chứng kỹ thuật; chưa thay thế phản biện khoa học hoặc kiểm định tính xác thực ngoài hệ thống."
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--evidence-dir", type=Path, required=True)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    result = validate(args.report, args.evidence_dir)
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output)
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
