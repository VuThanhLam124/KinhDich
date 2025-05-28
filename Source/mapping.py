# Source/mapping.py
"""
• Chứa bảng ánh xạ tên quẻ tiếng Việt → mã hexagram trong MongoDB
• Hỗ trợ: có dấu / không dấu / viết liền – thân thiện với người dùng
"""
from typing import Dict
import unicodedata, difflib, re
from Source.db import collection   # để tự lấy thêm alias từ DB

# ────────────────────────────────────────────────────────────────
def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")

def keyize(txt: str) -> str:
    """chuỗi -> không dấu, thường, bỏ khoảng trắng"""
    return strip_accents(txt).lower().replace(" ", "")

# ── Bảng 64 quẻ (tên chuẩn tiếng Việt có dấu) ───────────────────
VI_HEX = [
    ("Càn", "QUE_KIEN"), ("Khôn", "QUE_KHON"), ("Truân", "QUE_TRUAN"),
    ("Mông", "QUE_MONG"), ("Nhu", "QUE_NHU"), ("Tụng", "QUE_TUNG"),
    ("Sư", "QUE_SU"), ("Tỷ", "QUE_TY"),
    ("Tiểu Súc", "QUE_TIEU_SUC"), ("Lý", "QUE_LY"),
    ("Thái", "QUE_THAI"), ("Bĩ", "QUE_BI_2"),
    ("Đồng Nhân", "QUE_DONG_NHAN"), ("Đại Hữu", "QUE_DAI_HUU"),
    ("Khiêm", "QUE_KHIEM"), ("Dự", "QUE_DU"),
    ("Tùy", "QUE_TUY"), ("Cổ", "QUE_CO"), ("Lâm", "QUE_LAM"), ("Quán", "QUE_QUAN"),
    ("Phệ Hạp", "QUE_PHE_HAP"), ("Bí (2)", "QUE_BI_2"), ("Bác", "QUE_BAC"),
    ("Phục", "QUE_PHUC"), ("Vô Vong", "QUE_VO_VONG"), ("Đại Súc", "QUE_DAI_SUC"),
    ("Di", "QUE_DI"), ("Đại Quá", "QUE_DAI_QUA"),
    ("Khảm", "QUE_KHAM"), ("Ly", "QUE_LY"),
    ("Hàm", "QUE_HAM"), ("Hằng", "QUE_HANG"),
    ("Độn", "QUE_DON"), ("Đại Tráng", "QUE_DAI_TRANG"),
    ("Tấn", "QUE_TAN"), ("Minh Di", "QUE_MINH_DI"),
    ("Gia Nhân", "QUE_GIA_NHAN"), ("Khốn", "QUE_KHON_2"),
    ("Tỉnh", "QUE_TINH"), ("Cách", "QUE_CACH"),
    ("Đỉnh", "QUE_DINH"), ("Chấn", "QUE_CHAN"), ("Cấn", "QUE_CAN"),
    ("Tiệm", "QUE_TIEM"), ("Quy Muội", "QUE_QUI_MUOI"),
    ("Phong", "QUE_PHONG"), ("Lữ", "QUE_LU"), ("Hoán", "QUE_TON_2"),
    ("Hoàn", "QUE_HOAN"), ("Tiết", "QUE_TIET"),
    ("Trung Phu", "QUE_TRUNG_PHU"), ("Tiểu Quá", "QUE_TIEU_QUA"),
    ("Kỵ Tế", "QUE_KY_TE"), ("Vị Tế", "QUE_VI_TE")
]

# ── Xây map chính & alias không dấu ──────────────────────────────
HEX_MAP: Dict[str, str] = {}
for name, code in VI_HEX:
    HEX_MAP[keyize(name)] = code
    # alias: viết liền & không dấu đã cover bởi keyize

# ── Thêm alias tự động từ DB (phòng khi mã khác) ────────────────
for code in collection.distinct("hexagram"):
    HEX_MAP.setdefault(keyize(code.split("_",1)[-1]), code)

# ────────────────────────────────────────────────────────────────
def detect_hexagram(query: str) -> str | None:
    """
    Trả về mã quẻ (QUE_*) nếu phát hiện từ khoá quẻ trong câu hỏi.
    Nhận dạng không dấu, viết liền/viết cách đều được.
    """
    plain = keyize(query)
    # lấy từ cuối hoặc ngay sau từ "que"
    m = re.search(r"(?:que)?([a-z]+)$", plain)
    if not m:
        return None
    key = m.group(1)
    if key in HEX_MAP:
        return HEX_MAP[key]
    close = difflib.get_close_matches(key, HEX_MAP.keys(), n=1, cutoff=0.8)
    return HEX_MAP[close[0]] if close else None
