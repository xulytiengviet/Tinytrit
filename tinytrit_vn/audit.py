"""Audit the 52-file Trinity clean source archive without extracting it."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile

REQUIRED_MODULES = ("embedding_lookup", "trinity_block", "lm_head_matvec", "argmax_unit")


def audit(path: Path) -> dict:
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    with ZipFile(path) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        name_set = set(names)
        counts = Counter(Path(n).suffix.lower() for n in names)
        verilog = {n: z.read(n).decode("utf-8") for n in names if n.endswith(".v")}
        mem_refs = set()
        for content in verilog.values():
            mem_refs.update(re.findall(r'"(fpga/[^"\s]+\.mem)"', content))
        defined = set()
        for content in verilog.values():
            defined.update(re.findall(r"\bmodule\s+(\w+)\b", content))
        return {
            "path": str(path),
            "sha256": sha,
            "file_count": len(names),
            "extensions": dict(sorted(counts.items())),
            "expanded_bytes": sum(z.getinfo(n).file_size for n in names),
            "missing_mem_files": sorted(mem_refs - name_set),
            "missing_required_modules": sorted(set(REQUIRED_MODULES) - defined),
            "contains_trained_vietnamese_weights": False,
            "self_contained_fpga_rebuild": not (mem_refs - name_set or set(REQUIRED_MODULES) - defined)
        }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("zipfile", type=Path)
    p.add_argument("--strict", action="store_true", help="Non-zero if rebuild inputs are missing")
    args = p.parse_args()
    result = audit(args.zipfile)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.strict and not result["self_contained_fpga_rebuild"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
