# File: preprocess.py

import os
import re
import json
import unicodedata
import logging
from pathlib import Path

import pdfplumber
from tqdm import tqdm
from pdf2image import convert_from_path
from PIL import Image

# ──────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# OPTIONAL: spaCy (có thể bỏ qua nếu chưa cài)
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
# MỤC LỤC – (start_page, end_page) theo file PDF (1-indexed)
# ──────────────────────────────────────────────────────────────
sections = [
    ("NHUNG_DIEU_NEN_BIET",           7,  17),
    ("TUA_CUA_TRINH_DI",             18,  19),
    ("DO_THUYET_CUA_CHU_HY",         20,  39),
    ("DICH_THUYET_CUONG_LINH",       64,  78),
    ("CHU_DICH_THUONG_KINH/QUE_KIEN", 80, 128),
    ("CHU_DICH_THUONG_KINH/QUE_KHON",129,154),
    ("CHU_DICH_THUONG_KINH/QUE_TRUAN",155,168),
    ("CHU_DICH_THUONG_KINH/QUE_MONG", 169,183),
    ("CHU_DICH_THUONG_KINH/QUE_NHU",  184,195),
    ("CHU_DICH_THUONG_KINH/QUE_TUNG", 196,208),
    ("CHU_DICH_THUONG_KINH/QUE_SU",   209,221),
    ("CHU_DICH_THUONG_KINH/QUE_TY",   222,234),
    ("CHU_DICH_THUONG_KINH/QUE_TIEU_SUC",235,247),
    ("CHU_DICH_THUONG_KINH/QUE_LY",   248,258),
    ("CHU_DICH_THUONG_KINH/QUE_THAI", 259,272),
    ("CHU_DICH_THUONG_KINH/QUE_BI",   273,283),
    ("CHU_DICH_THUONG_KINH/QUE_DONG_NHAN",284,296),
    ("CHU_DICH_THUONG_KINH/QUE_DAI_HUU", 298,309),
    ("CHU_DICH_THUONG_KINH/QUE_KHIEM", 310,320),
    ("CHU_DICH_THUONG_KINH/QUE_DU",   321,332),
    ("CHU_DICH_THUONG_KINH/QUE_TUY",  333,345),
    ("CHU_DICH_THUONG_KINH/QUE_CO",   346,358),
    ("CHU_DICH_THUONG_KINH/QUE_LAM",  359,369),
    ("CHU_DICH_THUONG_KINH/QUE_QUAN", 370,381),
    ("CHU_DICH_THUONG_KINH/QUE_PHE_HAP",382,394),
    ("CHU_DICH_THUONG_KINH/QUE_BI_2", 395,407),
    ("CHU_DICH_THUONG_KINH/QUE_BAC",  408,418),
    ("CHU_DICH_THUONG_KINH/QUE_PHUC", 419,431),
    ("CHU_DICH_THUONG_KINH/QUE_VO_VONG",433,445),
    ("CHU_DICH_THUONG_KINH/QUE_DAI_SUC",446,458),
    ("CHU_DICH_THUONG_KINH/QUE_DI",   459,470),
    ("CHU_DICH_THUONG_KINH/QUE_DAI_QUA",471,482),
    ("CHU_DICH_THUONG_KINH/QUE_TAP_KHAM",483,497),
    ("CHU_DICH_HA_KINH/QUE_HAM",      508,520),
    ("CHU_DICH_HA_KINH/QUE_HANG",     521,533),
    ("CHU_DICH_HA_KINH/QUE_DON",      534,545),
    ("CHU_DICH_HA_KINH/QUE_DAI_TRANG",546,556),
    ("CHU_DICH_HA_KINH/QUE_TAN",      558,568),
    ("CHU_DICH_HA_KINH/QUE_MINH_DI",  569,582),
    ("CHU_DICH_HA_KINH/QUE_GIA_NHAN", 583,594),
    ("CHU_DICH_HA_KINH/QUE_KHUE",     595,608),
    ("CHU_DICH_HA_KINH/QUE_KIEN",     609,621),
    ("CHU_DICH_HA_KINH/QUE_GIAI",     622,635),
    ("CHU_DICH_HA_KINH/QUE_TON",      636,651),
    ("CHU_DICH_HA_KINH/QUE_ICH",      652,667),
    ("CHU_DICH_HA_KINH/QUE_QUAI",     668,683),
    ("CHU_DICH_HA_KINH/QUE_CAU",      684,697),
    ("CHU_DICH_HA_KINH/QUE_TUY",      698,712),
    ("CHU_DICH_HA_KINH/QUE_THANG",    714,723),
    ("CHU_DICH_HA_KINH/QUE_KHON",     724,738),
    ("CHU_DICH_HA_KINH/QUE_TINH",     739,752),
    ("CHU_DICH_HA_KINH/QUE_CACH",     753,765),
    ("CHU_DICH_HA_KINH/QUE_DINH",     766,777),
    ("CHU_DICH_HA_KINH/QUE_CHAN",     778,789),
    ("CHU_DICH_HA_KINH/QUE_CAN",      790,801),
    ("CHU_DICH_HA_KINH/QUE_TIEM",     802,813),
    ("CHU_DICH_HA_KINH/QUE_QUI_MUOI", 814,825),
    ("CHU_DICH_HA_KINH/QUE_PHONG",    826,839),
    ("CHU_DICH_HA_KINH/QUE_LU",       840,851),
    ("CHU_DICH_HA_KINH/QUE_TON_2",    852,863),
    ("CHU_DICH_HA_KINH/QUE_DOAI",     864,873),
    ("CHU_DICH_HA_KINH/QUE_HOAN",     874,884),
    ("CHU_DICH_HA_KINH/QUE_TIET",     886,894),
    ("CHU_DICH_HA_KINH/QUE_TRUNG_PHU",895,904),
    ("CHU_DICH_HA_KINH/QUE_TIEU_QUA", 905,916),
    ("CHU_DICH_HA_KINH/QUE_KY_TE",    917,926),
    ("CHU_DICH_HA_KINH/QUE_VI_TE",    927,936),
]

# ═════════════════════════════════════════════════════════════
# 1. EXTRACT ─ TEXT & IMAGES
# ═════════════════════════════════════════════════════════════
def extract_text_from_pages(pdf, start_page: int, end_page: int) -> str:
    """
    Trích xuất text trong khoảng trang (1-index).
    """
    text = ""
    for p in tqdm(range(start_page, end_page + 1),
                  desc=f"Extract {start_page}-{end_page}"):
        page = pdf.pages[p - 1]
        t = page.extract_text()
        if t:
            text += t + "\n"
    return text


def extract_images_from_pages(pdf_path: str, start_page: int,
                              end_page: int, output_dir: str) -> None:
    """
    Lưu mỗi trang thành PNG (nén nhẹ) và tạo metadata JSON.
    """
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
            meta.append({
                "page": page_num,
                "path": fn,
                "description": f"Trang {page_num}"
            })

        with open(os.path.join(img_dir, "images.json"), "w",
                  encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Lỗi trích xuất ảnh: {e}")

# ═════════════════════════════════════════════════════════════
# 2. CLEAN & NORMALIZE (vẫn giữ nguyên như cách đã chỉnh trước)
# ═════════════════════════════════════════════════════════════
def clean_and_normalize_text(text: str) -> str:
    """
    1) Chuẩn hoá Unicode, xoá control‐chars.
    2) Chèn newline trước/sau các marker (TIÊU ĐỀ / NHÃN) để tách dòng đúng.
    3) Replace các ký tự Unicode không mong muốn, xóa quảng cáo OCR.
    4) Cuối cùng: collapse nhiều whitespace thành một khoảng trắng, nhưng vẫn giữ newline.
    """
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[^\S\n\xA0]", " ", text)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", text)

    markers = [
        r"\bQUẺ\s+[A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠƯẠẢẮẰẲẴẶẸẺẼỀỀỂẾỄỆỈỊỌỎỐỒỔỖỘỚỜỞỠỢỤỦỨỪỬỮỰỳ]{2,}\b",
        r"☰|☱|☲|☳|☴|☵|☶|☷",
        r"\bGIẢI\s+NGHĨA\b",
        r"\bDịch\sâm\.\b",
        r"\bDịch\snghĩa\.\b",
        r"\bTruyện\s+của\s+Trình\s+Di\.\b",
        r"\bBản\s+nghĩa\s+của\s+Chu\s+Hy\.\b",
        r"\bLời\s+bàn\s+của\s+Tiên\s+Nho\.\b",
    ]

    for pat in markers:
        text = re.sub(pat, lambda m: "\n" + m.group(0), text, flags=re.IGNORECASE)
        text = re.sub(pat, lambda m: m.group(0) + "\n", text, flags=re.IGNORECASE)

    text = text.replace("Ebook miễn phí tại : www.Sachvui.Com", "")
    text = text.replace("Ebook thực hiện dành cho những bạn chưa có điều kiện mua sách.", "")
    text = text.replace("Nếu bạn có khả năng hãy mua sách gốc để ủng hộ tác giả, người dịch và Nhà Xuất Bản", "")
    text = text.replace("đ Tolu", "được").replace("kernelng", "không")

    text = re.sub(r"[ \t\u00A0]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines).strip()

    return text


# ═════════════════════════════════════════════════════════════
# 3. EXTRACT NOTES nhưng *không* xóa các “[n]” trong main.txt
# ═════════════════════════════════════════════════════════════
def extract_notes(text: str):
    """
    Trích các phần ghi chú “[n] …” vào notes dict.
    Trả về:
      - main_text: NGUYÊN VĂN (vẫn giữ nguyên “[n]”)
      - notes: { n: nội dung bên trong "[n] …" }
    """
    pat = r"\[(\d+)\]\s+(.+?)(?=\[\d+\]|\n|$)"
    # Ghi chú: pattern tìm “[số]” rồi mọi ký tự cho đến dấu [kế tiếp] hoặc xuống dòng hoặc hết chuỗi

    notes = {}
    for m in re.finditer(pat, text, flags=re.S):
        idx = m.group(1)
        content = re.sub(r"\s+", " ", m.group(2)).strip()
        notes[idx] = content

    # Không xóa "[n]" khỏi main_text
    main_text = text

    return main_text, notes


# ═════════════════════════════════════════════════════════════
# 4. PREPROCESS PDF → TXT / JSON
# ═════════════════════════════════════════════════════════════
def preprocess_data(pdf_path: str, out_dir="Kinh_Dich_Data"):
    """
    Với mỗi mục trong `sections`, tạo folder con, trích text, clean & normalize,
    tách notes (giữ nguyên “[n]”), và lưu:
      - main.txt (nguyên văn có "[n]")
      - notes.json
    """
    if not os.path.exists(pdf_path):
        logger.error(f"Không tìm thấy file PDF: {pdf_path}")
        return

    with pdfplumber.open(pdf_path) as pdf:
        for name, st, ed in sections:
            sec_dir = os.path.join(out_dir, name)
            os.makedirs(sec_dir, exist_ok=True)

            logger.info(f"● XỬ LÝ SECTION: {name} [{st}-{ed}]")
            text = extract_text_from_pages(pdf, st, ed)
            text = clean_and_normalize_text(text)
            main_txt, notes = extract_notes(text)

            # Lưu main.txt (VẪN có "[n]")
            with open(os.path.join(sec_dir, "main.txt"), "w", encoding="utf-8") as f:
                f.write(main_txt)

            # Lưu notes.json (tách được { n: nội dung })
            with open(os.path.join(sec_dir, "notes.json"), "w", encoding="utf-8") as f:
                json.dump(notes, f, ensure_ascii=False, indent=4)

            # Nếu phần DO_THUYET_CUA_CHU_HY, vẫn extract ảnh
            if name == "DO_THUYET_CUA_CHU_HY":
                extract_images_from_pages(pdf_path, st, ed, sec_dir)


if __name__ == "__main__":
    pdf_path = "nhasachmienphi-kinh-dich-tron-bo.pdf"
    data_dir = "Kinh_Dich_Data"

    if not os.path.exists(data_dir):
        logger.info("→ Bắt đầu tiền xử lý PDF → TXT/JSON")
        preprocess_data(pdf_path, data_dir)
    else:
        logger.info(f"Thư mục đầu ra '{data_dir}' đã tồn tại, có thể bỏ qua bước preprocess.")
    logger.info("Tiền xử lý hoàn tất!")