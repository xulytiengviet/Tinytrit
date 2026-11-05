import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from tinytrit_vn.base27 import (
    decode, encode, index_to_trits, trits_to_index,
    pack_rtl_ternary_weights, unpack_rtl_ternary_weights
)
from tinytrit_vn.dataset import prepare, split_for
from tinytrit_vn.gate98 import validate
from tinytrit_vn.audit import audit

DEMO_ALPHABET = "abcdefghijklmnopqrstuvwxyz "  # Demo only; NOT official CVNSS4.0.


class Base27Tests(unittest.TestCase):
    def test_all_27_states(self):
        self.assertEqual(len({index_to_trits(i) for i in range(27)}), 27)
        for i in range(27):
            self.assertEqual(trits_to_index(index_to_trits(i)), i)

    def test_lossless_text(self):
        self.assertEqual(decode(encode(DEMO_ALPHABET, DEMO_ALPHABET), DEMO_ALPHABET), DEMO_ALPHABET)

    def test_reject_unknown(self):
        with self.assertRaises(ValueError):
            encode("tiếng việt", DEMO_ALPHABET)

    def test_rtl_encoding_is_distinct(self):
        vals = [0, 1, -1, 0, -1, 1, 1]
        self.assertEqual(unpack_rtl_ternary_weights(pack_rtl_ternary_weights(vals), len(vals)), vals)


class DatasetTests(unittest.TestCase):
    def test_duplicate_and_split(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "alphabet.txt").write_text(DEMO_ALPHABET, encoding="utf-8")
            corpus = []
            for i in range(300):
                value = "".join(DEMO_ALPHABET[(i // 27**j) % 27] for j in range(3))
                corpus.append({"cqn": f"câu {i}", "cvnss": value})
            corpus.append(corpus[0])
            (root / "input.jsonl").write_text(
                "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in corpus), encoding="utf-8")
            report = prepare(root / "input.jsonl", root / "alphabet.txt", root / "out", "oracle-test", 30)
            self.assertEqual(report["deduplicated_count"], 300)
            self.assertTrue(all(report["counts"].values()))
            self.assertEqual(split_for("câu 7"), split_for("câu 7"))
            self.assertFalse(report["trained"])


class GateTests(unittest.TestCase):
    def test_missing_evidence_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.assertEqual(validate(root / "missing.json", root)["status"], "FAIL")
            (root / "metrics.json").write_text(json.dumps({
                "evidence": {}, "dataset": {"sha256": "0" * 64, "independent_test_set": True, "leakage_count": 0},
                "model": {"trained_on_vietnamese": True, "weights_sha256": "1" * 64},
                "fpga": {"board": "QMTech XC7A100T-1FGG676C", "physical_board_verified": True,
                         "uses_vietnamese_trained_weights": True, "dsp48_count": 0,
                         "tokens_generated": 16, "throughput_tok_s": 63,
                         "fmax_mhz": 92, "power_w": 1}
            }), encoding="utf-8")
            self.assertEqual(validate(root / "metrics.json", root)["status"], "FAIL")

    def test_archive_flags_missing_sources(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.zip"
            with ZipFile(p, "w") as z:
                z.writestr("fpga/openxc7-synth/hslm_full_top.v",
                           'module hslm_full_top(); initial $readmemh("fpga/weights/w.mem", x); endmodule')
            out = audit(p)
            self.assertIn("fpga/weights/w.mem", out["missing_mem_files"])
            self.assertFalse(out["self_contained_fpga_rebuild"])


if __name__ == "__main__":
    unittest.main()
