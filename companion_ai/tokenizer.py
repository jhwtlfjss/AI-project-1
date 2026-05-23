from __future__ import annotations


class ByteTokenizer:
    """Tiny UTF-8 byte tokenizer.

    This tokenizer is deliberately simple and private: no pretrained vocabulary,
    no external merges, and full support for Chinese, Japanese, and English.
    """

    PAD = 0
    BOS = 1
    EOS = 2
    UNK = 3
    BYTE_OFFSET = 4
    vocab_size = 260

    def encode(self, text: str, add_bos: bool = True, add_eos: bool = True) -> list[int]:
        ids: list[int] = []
        if add_bos:
            ids.append(self.BOS)
        ids.extend(byte + self.BYTE_OFFSET for byte in text.encode("utf-8"))
        if add_eos:
            ids.append(self.EOS)
        return ids

    def decode(self, ids: list[int] | tuple[int, ...], skip_special: bool = True) -> str:
        buf = bytearray()
        for token_id in ids:
            token_id = int(token_id)
            if token_id >= self.BYTE_OFFSET:
                byte_value = token_id - self.BYTE_OFFSET
                if 0 <= byte_value <= 255:
                    buf.append(byte_value)
            elif not skip_special:
                buf.extend(f"<{token_id}>".encode("utf-8"))
        return buf.decode("utf-8", errors="replace")

