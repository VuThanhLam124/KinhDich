#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import unicodedata
import logging
from pathlib import Path
from typing import List, Dict, Optional

import pdfplumber
from tqdm import tqdm
from pdf2image import convert_from_path
from PIL import Image
from pymongo import MongoClient
from langchain.text_splitter import CharacterTextSplitter     # vẫn dùng cho notes
from langchain_huggingface import HuggingFaceEmbeddings

# ──────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# OPTIONAL: spaCy hỗ trợ nhận diện tên riêng
# ──────────────────────────────────────────────────────────────
SPACY_AVAILABLE = False
try:
    import spacy
    try:
        nlp = spacy.load("vi_core_news_sm", disable=["parser", "lemmatizer"])
        SPACY_AVAILABLE = True
        logger.info("Đã load spaCy với mô hình 'vi_core_news_sm'")
    except OSError:
        logger.warning("Không tìm thấy mô hình 'vi_core_news_sm'. Sẽ bỏ qua spaCy.")
except ImportError:
    logger.warning("spaCy chưa được cài. Sẽ dùng regex đơn giản.")

# ──────────────────────────────────────────────────────────────
# MỤC LỤC – start_page & end_page đã có sẵn
# ──────────────────────────────────────────────────────────────
sections = [
    ("NHUNG_DIEU_NEN_BIET", 7, 17),
    ("TUA_CUA_TRINH_DI", 18, 19),
    ("DO_THUYET_CUA_CHU_HY", 20, 39),
    ("DICH_THUYET_CUONG_LINH", 64, 78),
    ("CHU_DICH_THUONG_KINH/QUE_KIEN", 80, 128),
    ("CHU_DICH_THUONG_KINH/QUE_KHON", 129, 154),
    ("CHU_DICH_THUONG_KINH/QUE_TRUAN", 155, 168),
    ("CHU_DICH_THUONG_KINH/QUE_MONG", 169, 183),
    ("CHU_DICH_THUONG_KINH/QUE_NHU", 184, 195),
    ("CHU_DICH_THUONG_KINH/QUE_TUNG", 196, 208),
    ("CHU_DICH_THUONG_KINH/QUE_SU", 209, 221),
    ("CHU_DICH_THUONG_KINH/QUE_TY", 222, 234),
    ("CHU_DICH_THUONG_KINH/QUE_TIEU_SUC", 235, 247),
    ("CHU_DICH_THUONG_KINH/QUE_LY", 248, 258),
    ("CHU_DICH_THUONG_KINH/QUE_THAI", 259, 272),
    ("CHU_DICH_THUONG_KINH/QUE_BI", 273, 283),
    ("CHU_DICH_THUONG_KINH/QUE_DONG_NHAN", 284, 296),
    ("CHU_DICH_THUONG_KINH/QUE_DAI_HUU", 298, 309),
    ("CHU_DICH_THUONG_KINH/QUE_KHIEM", 310, 320),
    ("CHU_DICH_THUONG_KINH/QUE_DU", 321, 332),
    ("CHU_DICH_THUONG_KINH/QUE_TUY", 333, 345),
    ("CHU_DICH_THUONG_KINH/QUE_CO", 346, 358),
    ("CHU_DICH_THUONG_KINH/QUE_LAM", 359, 369),
    ("CHU_DICH_THUONG_KINH/QUE_QUAN", 370, 381),
    ("CHU_DICH_THUONG_KINH/QUE_PHE_HAP", 382, 394),
    ("CHU_DICH_THUONG_KINH/QUE_BI_2", 395, 407),
    ("CHU_DICH_THUONG_KINH/QUE_BAC", 408, 418),
    ("CHU_DICH_THUONG_KINH/QUE_PHUC", 419, 431),
    ("CHU_DICH_THUONG_KINH/QUE_VO_VONG", 433, 445),
    ("CHU_DICH_THUONG_KINH/QUE_DAI_SUC", 446, 458),
    ("CHU_DICH_THUONG_KINH/QUE_DI", 459, 470),
    ("CHU_DICH_THUONG_KINH/QUE_DAI_QUA", 471, 482),
    ("CHU_DICH_THUONG_KINH/QUE_TAP_KHAM", 483, 497),
    ("CHU_DICH_HA_KINH/QUE_HAM", 508, 520),
    ("CHU_DICH_HA_KINH/QUE_HANG", 521, 533),
    ("CHU_DICH_HA_KINH/QUE_DON", 534, 545),
    ("CHU_DICH_HA_KINH/QUE_DAI_TRANG", 546, 556),
    ("CHU_DICH_HA_KINH/QUE_TAN", 558, 568),
    ("CHU_DICH_HA_KINH/QUE_MINH_DI", 569, 582),
    ("CHU_DICH_HA_KINH/QUE_GIA_NHAN", 583, 594),
    ("CHU_DICH_HA_KINH/QUE_KHUE", 595, 608),
    ("CHU_DICH_HA_KINH/QUE_KIEN", 609, 621),
    ("CHU_DICH_HA_KINH/QUE_GIAI", 622, 635),
    ("CHU_DICH_HA_KINH/QUE_TON", 636, 651),
    ("CHU_DICH_HA_KINH/QUE_ICH", 652, 667),
    ("CHU_DICH_HA_KINH/QUE_QUAI", 668, 683),
    ("CHU_DICH_HA_KINH/QUE_CAU", 684, 697),
    ("CHU_DICH_HA_KINH/QUE_TUY", 698, 712),
    ("CHU_DICH_HA_KINH/QUE_THANG", 714, 723),
    ("CHU_DICH_HA_KINH/QUE_KHON", 724, 738),
    ("CHU_DICH_HA_KINH/QUE_TINH", 739, 752),
    ("CHU_DICH_HA_KINH/QUE_CACH", 753, 765),
    ("CHU_DICH_HA_KINH/QUE_DINH", 766, 777),
    ("CHU_DICH_HA_KINH/QUE_CHAN", 778, 789),
    ("CHU_DICH_HA_KINH/QUE_CAN", 790, 801),
    ("CHU_DICH_HA_KINH/QUE_TIEM", 802, 813),
    ("CHU_DICH_HA_KINH/QUE_QUI_MUOI", 814, 825),
    ("CHU_DICH_HA_KINH/QUE_PHONG", 826, 839),
    ("CHU_DICH_HA_KINH/QUE_LU", 840, 851),
    ("CHU_DICH_HA_KINH/QUE_TON_2", 852, 863),
    ("CHU_DICH_HA_KINH/QUE_DOAI", 864, 873),
    ("CHU_DICH_HA_KINH/QUE_HOAN", 874, 884),
    ("CHU_DICH_HA_KINH/QUE_TIET", 886, 894),
    ("CHU_DICH_HA_KINH/QUE_TRUNG_PHU", 895, 904),
    ("CHU_DICH_HA_KINH/QUE_TIEU_QUA", 905, 916),
    ("CHU_DICH_HA_KINH/QUE_KY_TE", 917, 926),
    ("CHU_DICH_HA_KINH/QUE_VI_TE", 927, 936),
]

# ═════════════════════════════════════════════════════════════
# 1. EXTRACT ─ TEXT & IMAGES
# ═════════════════════════════════════════════════════════════
def extract_text_from_pages(pdf, start_page: int, end_page: int) -> str:
    """Trích xuất text trong khoảng trang (1-index)."""
    text = ""
    for p in tqdm(range(start_page, end_page + 1),
                  desc=f"Extract {start_page}-{end_page}"):
        page = pdf.pages[p - 1]
        t = page.extract_text()
        if t:
            text += t + "\n"
    return text


def extract_images_from_pages(pdf_path: str, start_page: int,
                              end_page: int, output_dir: str) -> Optional[str]:
    """Lưu mỗi trang thành PNG (nén nhẹ)."""
    try:
        img_dir = os.path.join(output_dir, "images")
        os.makedirs(img_dir, exist_ok=True)
        meta = []

        pages = convert_from_path(pdf_path,
                                  first_page=start_page,
                                  last_page=end_page, dpi=200)
        for i, im in enumerate(tqdm(pages,
                                    desc=f"Images {start_page}-{end_page}")):
            page_num = start_page + i
            fn = os.path.join(img_dir, f"page_{page_num}.png")
            im.save(fn, "PNG", optimize=True, quality=85)
            meta.append({"page": page_num,
                         "path": fn,
                         "description": f"Trang {page_num}"})
        with open(os.path.join(img_dir, "images.json"), "w",
                  encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=4)
        return img_dir
    except Exception as e:
        logger.error(f"Lỗi trích xuất ảnh: {e}")
        return None

# ═════════════════════════════════════════════════════════════
# 2. CLEAN & NORMALIZE
# ═════════════════════════════════════════════════════════════
def clean_and_normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[\x00-\x1F\x7F-\x9F]", "", text)
    text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    text = re.sub(r"\s+", " ", text).strip()
    # xoá quảng cáo OCR
    text = text.replace("Ebook miễn phí tại : www.Sachvui.Com", "")
    text = text.replace("Ebook thực hiện dành cho những bạn chưa có điều kiện mua sách.", "")
    text = text.replace("Nếu bạn có khả năng hãy mua sách gốc để ủng hộ tác giả, người dịch và Nhà Xuất Bản", "")
    # ví dụ fix OCR
    text = text.replace("đ Tolu", "được").replace("kernelng", "không")
    return text

# ═════════════════════════════════════════════════════════════
# 3. NOTES
# ═════════════════════════════════════════════════════════════
def extract_notes(text: str):
    pat = r"\[\d+\]\s+.*?(?=\n|$)"
    notes = {m.group(0)[1:m.group(0).find(']')]:
             re.sub(r"\s+", " ", m.group(0)[m.group(0).find(']')+1:]).strip()
             for m in re.finditer(pat, text, re.M)}
    main_text = re.sub(pat, "", text)
    return main_text.strip(), notes

# ═════════════════════════════════════════════════════════════
# 4. NEW ─ BLOCK PARSER
# ═════════════════════════════════════════════════════════════
def _parse_loi_kinh_block(block: str) -> Dict[str, Optional[str]]:
    """Tách 1 khối bắt đầu bởi 'LỜI KINH' thành các trường."""
    fields = {
        "lời_kinh": None,
        "dịch_âm": None,
        "dịch_nghĩa": None,
        "giải_nghĩa": None,
        "truyện_của_Trình_Di": None,
        "bản_nghĩa_của_Chu_Hy": None,
        "lời_bàn_của_tiên_nho": None,
    }

    pats = {
        "lời_kinh":               r"LỜI\s+KINH\s*(.*?)\s*(?=Dịch âm\.|Dịch nghĩa\.|GIẢI NGHĨA|Truyện của Trình Di\.|Bản nghĩa của Chu Hy\.|Lời bàn của Tiên Nho\.|$)",
        "dịch_âm":                r"Dịch âm\.\s*-\s*(.*?)\s*(?=Dịch nghĩa\.|GIẢI NGHĨA|Truyện của Trình Di\.|Bản nghĩa của Chu Hy\.|Lời bàn của Tiên Nho\.|$)",
        "dịch_nghĩa":             r"Dịch nghĩa\.\s*-\s*(.*?)\s*(?=GIẢI NGHĨA|Truyện của Trình Di\.|Bản nghĩa của Chu Hy\.|Lời bàn của Tiên Nho\.|$)",
        "giải_nghĩa":             r"GIẢI NGHĨA\s*(.*?)\s*(?=Truyện của Trình Di\.|Bản nghĩa của Chu Hy\.|Lời bàn của Tiên Nho\.|LỜI\s+KINH|$)",
        "truyện_của_Trình_Di":    r"Truyện của Trình Di\.\s*-\s*(.*?)\s*(?=Bản nghĩa của Chu Hy\.|Lời bàn của Tiên Nho\.|LỜI\s+KINH|$)",
        "bản_nghĩa_của_Chu_Hy":   r"Bản nghĩa của Chu Hy\.\s*-\s*(.*?)\s*(?=Lời bàn của Tiên Nho\.|LỜI\s+KINH|$)",
        "lời_bàn_của_tiên_nho":   r"Lời bàn của Tiên Nho\.\s*-\s*(.*?)\s*(?=LỜI\s+KINH|$)",
    }
    for k, pat in pats.items():
        m = re.search(pat, block, flags=re.S | re.I)
        if m:
            text = re.sub(r"\s+", " ", m.group(1)).strip()
            # loại bỏ “LỜI KINH” đầu khối nếu dính
            if k == "lời_kinh":
                text = re.sub(r"(?i)^\s*LỜI\s+KINH\s*", "", text)
            fields[k] = text
    return fields


def parse_hexagram_text(raw_text: str, hexagram: str,
                        chunk_prefix: str) -> List[Dict]:
    """
    Trả về list chunk có định dạng mong muốn.
    chunk_prefix = hexagram (đã .upper()).
    """
    chunks = []

    # 1. Lấy dòng biểu đồ quẻ (ví dụ '☱ Đoái trên ; ☲ Ly dưới')
    que_match = re.search(r"^\s*[☰☱☲☳☴☵☶☷].+$", raw_text, flags=re.M)
    que_str = que_match.group(0).strip() if que_match else None

    # 2. Tách phần mở đầu (trước LỜI KINH)
    split = re.split(r"\bLỜI\s+KINH", raw_text, maxsplit=1, flags=re.I)
    preface = split[0]
    rest    = "LỜI KINH" + split[1] if len(split) > 1 else ""

    # Trích “giải nghĩa / truyện Trình Di / bản nghĩa Chu Hy” trong preface
    pre_intro = {"giải_nghĩa": None,
                 "truyện_của_Trình_Di": None,
                 "bản_nghĩa_của_Chu_Hy": None}
    m1 = re.search(r"GIẢI NGHĨA\s*(.*?)(?=Truyện của Trình Di\.|Bản nghĩa của Chu Hy\.|$)",
                   preface, flags=re.S | re.I)
    if m1:
        pre_intro["giải_nghĩa"] = re.sub(r"\s+", " ", m1.group(1)).strip()

    m2 = re.search(r"Truyện của Trình Di\.\s*-\s*(.*?)(?=Bản nghĩa của Chu Hy\.|$)",
                   preface, flags=re.S | re.I)
    if m2:
        pre_intro["truyện_của_Trình_Di"] = re.sub(r"\s+", " ", m2.group(1)).strip()

    m3 = re.search(r"Bản nghĩa của Chu Hy\.\s*-\s*(.*)",
                   preface, flags=re.S | re.I)
    if m3:
        pre_intro["bản_nghĩa_của_Chu_Hy"] = re.sub(r"\s+", " ", m3.group(1)).strip()

    # ➜ Chunk 001 (mở đầu)
    chunks.append({
        "chunk_id": f"{chunk_prefix}_001",
        "hexagram": chunk_prefix,
        "que": que_str,
        "lời_kinh": None,
        "dịch_âm": None,
        "dịch_nghĩa": None,
        "giải_nghĩa": pre_intro["giải_nghĩa"],
        "truyện_của_Trình_Di": pre_intro["truyện_của_Trình_Di"],
        "bản_nghĩa_của_Chu_Hy": pre_intro["bản_nghĩa_của_Chu_Hy"],
        "lời_bàn_của_tiên_nho": None,
    })

    # 3. Tách từng khối LỜI KINH
    blocks = re.split(r"\n(?=LỜI\s+KINH)", rest, flags=re.I)
    idx = 2
    for blk in blocks:
        if not blk.strip():
            continue
        fields = _parse_loi_kinh_block(blk)
        chunks.append({
            "chunk_id": f"{chunk_prefix}_{idx:03d}",
            "hexagram": chunk_prefix,
            "que": None,
            **fields
        })
        idx += 1

    return chunks

# ═════════════════════════════════════════════════════════════
# 5. ENTITY & NOTE LINKS
# ═════════════════════════════════════════════════════════════
def extract_entities(text: str):
    ents = []
    ents += re.findall(r"Quẻ\s+[A-Z][a-zA-Z\s]+", text)
    ents += [f"Hào {x[0]} {x[1]}" for x in
             re.findall(r"Hào\s+(Sáu|Chín)\s+(Đầu|Hai|Ba|Bốn|Năm|Trên)",
                        text, flags=re.I)]
    ents += re.findall(r"(Âm|Dương)", text)
    if SPACY_AVAILABLE:
        doc = nlp(text)
        ents += [e.text for e in doc.ents if e.label_ in {"PERSON", "ORG", "LOC"}]
    return list(set(ents))


def map_notes(text: str, notes: Dict[str, str]):
    links = {}
    for n in re.findall(r"\[(\d+)\]", text):
        if n in notes:
            links[n] = notes[n]
    return links

# ═════════════════════════════════════════════════════════════
# 6. PREPROCESS PDF TO TXT/NOTES (giữ nguyên logic cũ)
# ═════════════════════════════════════════════════════════════
def preprocess_data(pdf_path: str, out_dir="Kinh_Dich_Data"):
    if not os.path.exists(pdf_path):
        logger.error(f"Không tìm thấy: {pdf_path}")
        return

    with pdfplumber.open(pdf_path) as pdf:
        for name, st, ed in sections:
            sec_dir = os.path.join(out_dir, name)
            os.makedirs(sec_dir, exist_ok=True)

            logger.info(f"● {name} [{st}-{ed}]")
            text = extract_text_from_pages(pdf, st, ed)
            text = clean_and_normalize_text(text)
            main_txt, notes = extract_notes(text)

            with open(os.path.join(sec_dir, "main.txt"), "w",
                      encoding="utf-8") as f:
                f.write(main_txt)
            with open(os.path.join(sec_dir, "notes.json"), "w",
                      encoding="utf-8") as f:
                json.dump(notes, f, ensure_ascii=False, indent=4)

            if name == "DO_THUYET_CUA_CHU_HY":
                extract_images_from_pages(pdf_path, st, ed, sec_dir)

# ═════════════════════════════════════════════════════════════
# 7. LOAD RAW DATA
# ═════════════════════════════════════════════════════════════
def load_raw_data(data_dir="Kinh_Dich_Data"):
    raw = {}
    for root, _, files in os.walk(data_dir):
        if "main.txt" not in files:
            continue
        sec_name = Path(root).relative_to(data_dir).as_posix()
        hexagram = sec_name.split("/")[-1].upper()

        with open(os.path.join(root, "main.txt"), encoding="utf-8") as f:
            raw_text = f.read()
        notes = {}
        npath = os.path.join(root, "notes.json")
        if os.path.exists(npath):
            with open(npath, encoding="utf-8") as f:
                notes = json.load(f)
        raw[hexagram] = {"hexagram": hexagram,
                         "raw_text": raw_text,
                         "notes": notes}
    logger.info(f"Đã đọc {len(raw)} quẻ")
    return raw

# ═════════════════════════════════════════════════════════════
# 8. SAVE TO MongoDB (FULLY FIXED)
# ═════════════════════════════════════════════════════════════
def generate_text_for_embedding(chunk: dict) -> str:
    """Ghép nội dụng các trường văn bản để tạo embedding."""
    return " ".join([
        str(chunk.get(field)) for field in [
            "lời_kinh",
            "dịch_âm",
            "dịch_nghĩa",
            "giải_nghĩa",
            "truyện_của_Trình_Di",
            "bản_nghĩa_của_Chu_Hy",
            "lời_bàn_của_tiên_nho"
        ] if chunk.get(field)
    ])

def save_to_mongodb(chunks: List[Dict], mongo_uri: str,
                    db_name="kinhdich_kb", col_name="chunks"):
    """Lưu dữ liệu vào MongoDB, bao gồm embedding và metadata."""
    try:
        client = MongoClient(mongo_uri)
        db = client[db_name]
        col = db[col_name]
        col.delete_many({})
        logger.info("Đã làm sạch collection cũ")

        embedder = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        total = 0

        for c in tqdm(chunks, desc="Mongo insert"):
            text_for_embedding = generate_text_for_embedding(c)
            embedding = embedder.embed_query(text_for_embedding)

            mongo_doc = {
                "_id": c["chunk_id"],
                "hexagram": c["hexagram"],
                "que": c["que"],
                "lời_kinh": c["lời_kinh"],
                "dịch_âm": c["dịch_âm"],
                "dịch_nghĩa": c["dịch_nghĩa"],
                "giải_nghĩa": c["giải_nghĩa"],
                "truyện_của_Trình_Di": c["truyện_của_Trình_Di"],
                "bản_nghĩa_của_Chu_Hy": c["bản_nghĩa_của_Chu_Hy"],
                "lời_bàn_của_tiên_nho": c["lời_bàn_của_tiên_nho"],
                "embedding": embedding,
                "entities": extract_entities(text_for_embedding),
                "note_links": map_notes(text_for_embedding, c.get("notes", {})),
                "section": c.get("section"),
                "source_page_range": c.get("source_page_range"),
            }

            col.insert_one(mongo_doc)
            total += 1

        logger.info(f"Đã lưu {total} chunks vào MongoDB")
        client.close()

    except Exception as e:
        logger.error(f"Lỗi khi lưu MongoDB: {e}")
        client.close()
        raise

# ═════════════════════════════════════════════════════════════
# 9. MAIN
# ═════════════════════════════════════════════════════════════
def main():
    pdf_path = "nhasachmienphi-kinh-dich-tron-bo.pdf"
    data_dir = "Kinh_Dich_Data"
    mongo_uri = "mongodb+srv://thanhlamdev:lamvthe180779@cluster0.jvlxnix.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    db_name, col_name = "kinhdich_kb", "chunks"

    if not os.path.exists(data_dir):
        logger.info("Bắt đầu tiền xử lý PDF → txt")
        preprocess_data(pdf_path, data_dir)

    raw = load_raw_data(data_dir)

    all_chunks = []
    for hexagram, data in raw.items():
        sec_info = next((s for s in sections
                         if s[0].split("/")[-1].upper() == hexagram
                         or s[0].upper() == hexagram), None)
        section = sec_info[0] if sec_info else hexagram
        page_range = [sec_info[1], sec_info[2]] if sec_info else [0, 0]

        for ch in parse_hexagram_text(data["raw_text"], hexagram, hexagram):
            ch["notes"] = data["notes"]
            ch["section"] = section
            ch["source_page_range"] = page_range
            all_chunks.append(ch)

    save_to_mongodb(all_chunks, mongo_uri, db_name, col_name)

    client = MongoClient(mongo_uri)
    sample = client[db_name][col_name].find_one()
    logger.info("Sample document:\n" +
                json.dumps(sample, ensure_ascii=False, indent=2))
    client.close()


if __name__ == "__main__":
    main()
