"""Prepare externally verified CVNSS4.0 pairs for Trinity Zig trainer.

NEVER silently convert Unicode to CVNSS4.0. The oracle must run separately.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import unicodedata
from .base27 import validate_alphabet, encode


def norm(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def split_for(cqn: str) -> str:
    n = int(hashlib.sha256(norm(cqn).encode("utf-8")).hexdigest()[:8], 16) % 100
    return "train" if n < 80 else ("val" if n < 90 else "test")


def prepare(source: Path, alphabet_file: Path, out: Path, oracle_version: str, min_records: int = 100):
    if not oracle_version.strip():
        raise ValueError("Bắt buộc ghi phiên bản oracle và chính sách giải mã")
    alphabet = validate_alphabet(alphabet_file.read_text(encoding="utf-8").rstrip("\r\n"))
    splits = {"train": [], "val": [], "test": []}
    seen = {}
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    for line_no, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        record = json.loads(line)
        if not isinstance(record, dict) or not isinstance(record.get("cqn"), str) or not isinstance(record.get("cvnss"), str):
            raise ValueError(f"Dòng {line_no}: cần cqn/cvnss là chuỗi")
        cqn, cvnss = norm(record["cqn"]), norm(record["cvnss"])
        if not cqn or not cvnss:
            raise ValueError(f"Dòng {line_no}: dữ liệu rỗng")
        encode(cvnss, alphabet)  # Strict alphabet check; no silent replacement.
        if cqn in seen:
            if seen[cqn] != cvnss:
                raise ValueError(f"Dòng {line_no}: trùng CQN nhưng CVNSS không nhất quán")
            continue  # Dedup before splitting; leakage prevented.
        seen[cqn] = cvnss
        splits[split_for(cqn)].append((cqn, cvnss))
    total = sum(map(len, splits.values()))
    if total < min_records or not all(splits.values()):
        raise ValueError(f"Dữ liệu không đủ: {total} cặp; train/val/test phải có mẫu")
    out.mkdir(parents=True, exist_ok=True)
    for split, records in splits.items():
        (out / f"{split}.txt").write_text(
            "".join(cvnss + "\n" for _, cvnss in records), encoding="utf-8")
        (out / f"{split}.jsonl").write_text(
            "".join(json.dumps({"cqn": cqn, "cvnss": cvnss}, ensure_ascii=False) + "\n"
                    for cqn, cvnss in records), encoding="utf-8")
    manifest = {
        "source_sha256": source_hash,
        "oracle_version": oracle_version,
        "alphabet_sha256": hashlib.sha256(alphabet.encode("utf-8")).hexdigest(),
        "counts": {k: len(v) for k, v in splits.items()},
        "deduplicated_count": total,
        "split_method": "sha256(NFC(CQN))[:8] % 100; 80/10/10",
        "lossless_base27_encoding": True,
        "trained": False,
        "verified_on_fpga": False
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--alphabet-file", type=Path, required=True)
    p.add_argument("--oracle-version", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--min-records", type=int, default=100)
    args = p.parse_args()
    print(json.dumps(prepare(args.input, args.alphabet_file, args.out, args.oracle_version, args.min_records), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
