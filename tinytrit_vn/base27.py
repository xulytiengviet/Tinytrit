"""Base27 symbolic index <-> three balanced trits.

The alphabet must be supplied by the researcher; no unverified CVNSS mapping.
This is NOT the separate 2-bit FPGA ternary weight encoding.
"""
from __future__ import annotations
import unicodedata

TRITS = (-1, 0, 1)
SIZE = 27


def validate_alphabet(alphabet: str) -> str:
    alphabet = unicodedata.normalize("NFC", alphabet)
    if len(alphabet) != SIZE or len(set(alphabet)) != SIZE:
        raise ValueError("Bảng chữ cái phải có đúng 27 ký hiệu Unicode khác nhau")
    if any(unicodedata.category(ch).startswith("C") for ch in alphabet):
        raise ValueError("Không dùng ký tự điều khiển trong bảng 27 ký hiệu")
    return alphabet


def index_to_trits(index: int) -> tuple[int, int, int]:
    if not isinstance(index, int) or not 0 <= index < SIZE:
        raise ValueError("Chỉ số Base27 phải thuộc [0, 26]")
    # 0=-1, 1=0, 2=+1; most significant trit first.
    return (index // 9 - 1, index // 3 % 3 - 1, index % 3 - 1)


def trits_to_index(trits) -> int:
    data = tuple(trits)
    if len(data) != 3 or any(type(t) is not int or t not in TRITS for t in data):
        raise ValueError("Mỗi ký hiệu phải gồm đúng 3 trit {-1,0,1}")
    return (data[0] + 1) * 9 + (data[1] + 1) * 3 + data[2] + 1


def encode(text: str, alphabet: str) -> list[tuple[int, int, int]]:
    alphabet = validate_alphabet(alphabet)
    lookup = {ch: idx for idx, ch in enumerate(alphabet)}
    result = []
    for ch in unicodedata.normalize("NFC", text):
        if ch not in lookup:
            raise ValueError(f"Ký hiệu không thuộc bảng 27: {ch!r}")
        result.append(index_to_trits(lookup[ch]))
    return result


def decode(triples, alphabet: str) -> str:
    alphabet = validate_alphabet(alphabet)
    return "".join(alphabet[trits_to_index(t)] for t in triples)


def pack_rtl_ternary_weights(weights) -> bytes:
    """Four weights per byte: 00=0, 01=+1, 10=-1; NOT Base27."""
    encode_map = {0: 0b00, 1: 0b01, -1: 0b10}
    values = list(weights)
    if any(w not in encode_map for w in values):
        raise ValueError("Trọng số chỉ được thuộc {-1,0,+1}")
    output = bytearray()
    for start in range(0, len(values), 4):
        b = 0
        for offset, w in enumerate(values[start:start + 4]):
            b |= encode_map[w] << (6 - 2 * offset)
        output.append(b)
    return bytes(output)


def unpack_rtl_ternary_weights(data: bytes, count: int) -> list[int]:
    if count < 0 or count > len(data) * 4:
        raise ValueError("Số lượng trọng số không hợp lệ")
    result = []
    decode_map = {0b00: 0, 0b01: 1, 0b10: -1}
    for i in range(count):
        value = (data[i // 4] >> (6 - 2 * (i % 4))) & 0b11
        if value not in decode_map:
            raise ValueError("Mã trọng số 11 không hợp lệ")
        result.append(decode_map[value])
    return result
