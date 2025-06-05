# File: chunking.py

import os
import re
import json
import logging
from pathlib import Path

# ──────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _parse_loi_kinh_block(block: str):
    """
    Tách 1 khối bắt đầu bởi 'LỜI KINH' thành các trường:
      - lời_kinh
      - dịch_âm
      - dịch_nghĩa
      - truyện_của_Trình_Di
      - bản_nghĩa_của_Chu_Hy
      - lời_bàn_của_tiên_nho
    (Đã bỏ 'giải_nghĩa'.)
    Mẫu trong main.txt dùng dấu en dash (–) chứ không phải hyphen (-), nên chúng ta
    cần cho regex chấp nhận cả hai.
    """
    fields = {
        "lời_kinh": None,
        "dịch_âm": None,
        "dịch_nghĩa": None,
        "truyện_của_Trình_Di": None,
        "bản_nghĩa_của_Chu_Hy": None,
        "lời_bàn_của_tiên_nho": None,
    }

    pats = {
        # Xem ví dụ trong main.txt: "LỜI KINH" luôn ở đầu khối
        "lời_kinh": r"LỜI\s+KINH\s*(.*?)\s*(?=Dịch âm\.|Dịch nghĩa\.|Truyện của Trình Di|Bản nghĩa của Chu Hy|Lời bàn của Tiên Nho|$)",

        # Dấu [–-] cho phép en dash hoặc hyphen
        "dịch_âm": r"Dịch âm\.\s*[–-]\s*(.*?)\s*(?=Dịch nghĩa\.|Truyện của Trình Di|Bản nghĩa của Chu Hy|Lời bàn của Tiên Nho|$)",

        "dịch_nghĩa": r"Dịch nghĩa\.\s*[–-]\s*(.*?)\s*(?=Truyện của Trình Di|Bản nghĩa của Chu Hy|Lời bàn của Tiên Nho|$)",

        "truyện_của_Trình_Di": r"Truyện của Trình Di\s*[–-]\s*(.*?)\s*(?=Bản nghĩa của Chu Hy|Lời bàn của Tiên Nho|$)",

        "bản_nghĩa_của_Chu_Hy": r"Bản nghĩa của Chu Hy\.\s*[–-]\s*(.*?)\s*(?=Lời bàn của Tiên Nho|$)",

        "lời_bàn_của_tiên_nho": r"Lời bàn của Tiên Nho\.\s*[–-]\s*(.*?)\s*$",
    }

    for k, pat in pats.items():
        m = re.search(pat, block, flags=re.S | re.I)
        if m:
            text = re.sub(r"\s+", " ", m.group(1)).strip()
            # Nếu là lời_kinh, bỏ luôn từ "LỜI KINH" ở đầu khối
            if k == "lời_kinh":
                text = re.sub(r"(?i)^\s*LỜI\s+KINH\s*", "", text)
            fields[k] = text

    return fields


def parse_hexagram_text(raw_text: str, hexagram: str):
    """
    Trả về list các chunk (đã bỏ 'giải_nghĩa').
    Mỗi chunk có cấu trúc:
      {
        "chunk_id": "{HEX}_{số thứ tự}",
        "hexagram": HEX,
        "que": (dòng biểu đồ quẻ nếu có),
        "lời_kinh": ...,
        "dịch_âm": ...,
        "dịch_nghĩa": ...,
        "truyện_của_Trình_Di": ...,
        "bản_nghĩa_của_Chu_Hy": ...,
        "lời_bàn_của_tiên_nho": ...
      }
    """
    chunks = []

    # 1) Tìm dòng chứa biểu đồ quẻ (nếu có)
    que_match = re.search(r"^\s*[☰☱☲☳☴☵☶☷].+$", raw_text, flags=re.M)
    que_str = que_match.group(0).strip() if que_match else None

    # 2) Tách phần mở đầu (trước 'LỜI KINH')
    parts = re.split(r"\bLỜI\s+KINH", raw_text, maxsplit=1, flags=re.I)
    preface = parts[0]
    rest = ("LỜI KINH" + parts[1]) if len(parts) > 1 else ""

    # ➜ Chunk đầu tiên (mở đầu) chỉ chứa 'que' (nếu có) và để các trường khác None
    chunks.append({
        "chunk_id": f"{hexagram}_001",
        "hexagram": hexagram,
        "que": que_str,
        "lời_kinh": None,
        "dịch_âm": None,
        "dịch_nghĩa": None,
        "truyện_của_Trình_Di": None,
        "bản_nghĩa_của_Chu_Hy": None,
        "lời_bàn_của_tiên_nho": None,
    })

    # 3) Tách từng khối bắt đầu bởi 'LỜI KINH'
    blocks = re.split(r"\n(?=LỜI\s+KINH)", rest, flags=re.I)
    idx = 2
    for blk in blocks:
        if not blk.strip():
            continue
        fields = _parse_loi_kinh_block(blk)
        chunks.append({
            "chunk_id": f"{hexagram}_{idx:03d}",
            "hexagram": hexagram,
            "que": None,
            "lời_kinh": fields["lời_kinh"],
            "dịch_âm": fields["dịch_âm"],
            "dịch_nghĩa": fields["dịch_nghĩa"],
            "truyện_của_Trình_Di": fields["truyện_của_Trình_Di"],
            "bản_nghĩa_của_Chu_Hy": fields["bản_nghĩa_của_Chu_Hy"],
            "lời_bàn_của_tiên_nho": fields["lời_bàn_của_tiên_nho"],
        })
        idx += 1

    return chunks


def load_hexagram_data(hex_path: str):
    """
    Cho đường dẫn đến folder của 1 quẻ (ví dụ 'Kinh_Dich_Data/CHU_DICH_THUONG_KINH/QUE_KIEN'),
    đọc và trả về (raw_text, notes_dict).
    """
    main_txt_path = os.path.join(hex_path, "main.txt")
    notes_json_path = os.path.join(hex_path, "notes.json")

    if not os.path.isfile(main_txt_path):
        logger.warning(f"Không tìm thấy main.txt trong {hex_path}. Bỏ qua.")
        return None, None

    with open(main_txt_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    notes = {}
    if os.path.isfile(notes_json_path):
        with open(notes_json_path, "r", encoding="utf-8") as f:
            notes = json.load(f)

    return raw_text, notes


def process_two_directories(data_dir="Kinh_Dich_Data"):
    """
    Duyệt qua Kinh_Dich_Data/CHU_DICH_THUONG_KINH và Kinh_Dich_Data/CHU_DICH_HA_KINH,
    cho mỗi folder con (mỗi quẻ) gọi parse_hexagram_text rồi lưu chunks.json.
    """
    parents = ["CHU_DICH_THUONG_KINH", "CHU_DICH_HA_KINH"]
    total_chunks = 0

    for parent in parents:
        parent_path = os.path.join(data_dir, parent)
        if not os.path.isdir(parent_path):
            logger.warning(f"Directory '{parent_path}' không tồn tại. Bỏ qua.")
            continue

        for hexagram_name in sorted(os.listdir(parent_path)):
            hex_path = os.path.join(parent_path, hexagram_name)
            if not os.path.isdir(hex_path):
                continue

            raw_text, notes = load_hexagram_data(hex_path)
            if raw_text is None:
                continue

            hexagram_code = hexagram_name.upper()
            logger.info(f"→ Chunking quẻ: {hexagram_code}")
            chunks = parse_hexagram_text(raw_text, hexagram_code)

            # Gắn thêm thông tin notes (nếu cần)
            for c in chunks:
                c["notes"] = notes

            # Lưu từng quẻ thành chunks.json
            out_path = os.path.join(hex_path, "chunks.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(chunks, f, ensure_ascii=False, indent=2)

            logger.info(f"   Đã lưu {len(chunks)} chunks → {out_path}")
            total_chunks += len(chunks)

    logger.info(f"Tổng cộng đã tạo {total_chunks} chunks cho 2 thư mục.")


if __name__ == "__main__":
    data_dir = "Kinh_Dich_Data"
    process_two_directories(data_dir)
