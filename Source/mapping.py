"""
Module mapping cho hệ thống Kinh Dịch - Phát hiện và chuyển đổi quẻ
"""
from typing import Dict, List, Optional
import re

# ──────────────────────────────────────────────────────────────
# Hexagram Mapping Data
# ──────────────────────────────────────────────────────────────

# Map 64 quẻ Kinh Dịch với các keywords phổ biến
HEXAGRAM_MAP = {
    # Thượng Kinh (Quẻ 1-30)
    "QUE_KIEN": ["kiền", "que kiền", "quẻ kiền", "qian", "creative", "heaven"],
    "QUE_KHON": ["khôn", "que khôn", "quẻ khôn", "kun", "receptive", "earth"],
    "QUE_TRUAN": ["truân", "que truân", "quẻ truân", "zhun", "difficulty", "sprouting"],
    "QUE_MONG": ["mông", "que mông", "quẻ mông", "meng", "youthful folly"],
    "QUE_NHU": ["nhu", "que nhu", "quẻ nhu", "xu", "waiting", "nourishment"],
    "QUE_TUNG": ["tụng", "que tụng", "quẻ tụng", "song", "conflict"],
    "QUE_SU": ["sư", "que sư", "quẻ sư", "shi", "army", "troops","quân đội", "chiến tranh","quân nhân","chiến binh","military", "warfare"],
    "QUE_TY": ["tỷ", "que tỷ", "quẻ tỷ", "bi", "holding together"],
    "QUE_TIEU_SUC": ["tiểu súc", "que tiểu súc", "quẻ tiểu súc", "small taming"],
    "QUE_LY": ["lý", "que lý", "quẻ lý", "li", "treading"],
    "QUE_THAI": ["thái", "que thái", "quẻ thái", "tai", "peace"],
    "QUE_PHE_HAP": ["phế hạp", "que phế hạp", "pi", "standstill"],
    "QUE_DONG_NHAN": ["đồng nhân", "que đồng nhân", "fellowship"],
    "QUE_DAI_HUU": ["đại hữu", "que đại hữu", "great possession"],
    "QUE_KHIEM": ["khiêm", "que khiêm", "quẻ khiêm", "qian", "modesty", "humility"],
    "QUE_DU": ["dự", "que dự", "quẻ dự", "yu", "enthusiasm"],
    "QUE_TUY": ["tùy", "que tùy", "quẻ tùy", "sui", "following"],
    "QUE_CO": ["cổ", "que cổ", "quẻ cổ", "gu", "work on decay"],
    "QUE_LAM": ["lâm", "que lâm", "quẻ lâm", "lin", "approach"],
    "QUE_QUAN": ["quán", "que quán", "quẻ quán", "guan", "contemplation"],
    "QUE_PHE_HAP": ["phế hạp", "que phế hạp", "biting through"],
    "QUE_BI": ["bí", "que bí", "quẻ bí", "bi", "grace"],
    "QUE_BAC": ["bác", "que bác", "quẻ bác", "bo", "splitting apart"],
    "QUE_PHUC": ["phục", "que phục", "quẻ phục", "fu", "return"],
    "QUE_VO_VONG": ["vô vọng", "que vô vọng", "innocence"],
    "QUE_DAI_SUC": ["đại súc", "que đại súc", "great taming"],
    "QUE_DI": ["di", "que di", "quẻ di", "yi", "nourishment"],
    "QUE_DAI_QUA": ["đại quá", "que đại quá", "great exceeding"],
    "QUE_TAP_KHAM": ["tập khảm", "que tập khảm", "quẻ tập khảm", "kan", "water", "abyss"],
    "QUE_LY_2": ["ly", "que ly", "quẻ ly", "li", "fire", "clinging"],

    # Hạ Kinh (Quẻ 31-64)
    "QUE_HAM": ["hàm", "que hàm", "quẻ hàm", "xian", "influence"],
    "QUE_HANG": ["hằng", "que hằng", "quẻ hằng", "heng", "duration"],
    "QUE_DON": ["độn", "que độn", "quẻ độn", "dun", "retreat"],
    "QUE_DAI_TRANG": ["đại tráng", "que đại tráng", "great power"],
    "QUE_TAN": ["tấn", "que tấn", "quẻ tấn", "jin", "progress"],
    "QUE_MINH_DI": ["minh di", "que minh di", "darkening light"],
    "QUE_GIA_NHAN": ["gia nhân", "que gia nhân", "family"],
    "QUE_KHUE": ["khuê", "que khuê", "quẻ khuê", "kui", "opposition"],
    "QUE_GIAN": ["giản", "que giản", "quẻ giản", "jian", "obstruction"],
    "QUE_GIAI": ["giải", "que giải", "quẻ giải", "jie", "deliverance"],
    "QUE_TON": ["tổn", "que tổn", "quẻ tổn", "sun", "decrease"],
    "QUE_ICH": ["ích", "que ích", "quẻ ích", "yi", "increase"],
    "QUE_QUAI": ["quải", "que quải", "quẻ quải", "guai", "breakthrough"],
    "QUE_CAU": ["cấu", "que cấu", "quẻ cấu", "gou", "coming to meet"],
    "QUE_TUY": ["tụy", "que tụy", "quẻ tụy", "cui", "gathering"],
    "QUE_THANG": ["thăng", "que thăng", "quẻ thăng", "sheng", "pushing upward"],
    "QUE_KHON_2": ["khốn", "que khốn", "quẻ khốn", "kun", "oppression"],
    "QUE_TINH": ["tỉnh", "que tỉnh", "quẻ tỉnh", "jing", "well"],
    "QUE_CACH": ["cách", "que cách", "quẻ cách", "ge", "revolution"],
    "QUE_DINH": ["đỉnh", "que đỉnh", "quẻ đỉnh", "ding", "cauldron"],
    "QUE_CHAN": ["chấn", "que chấn", "quẻ chấn", "zhen", "thunder"],
    "QUE_CAN": ["cấn", "que cấn", "quẻ cấn", "gen", "mountain"],
    "QUE_TIEM": ["tiệm", "que tiệm", "quẻ tiệm", "jian", "development"],
    "QUE_QUI_MUOI": ["qui muội", "que qui muội", "marrying maiden"],
    "QUE_PHONG": ["phong", "que phong", "quẻ phong", "feng", "abundance"],
    "QUE_LU": ["lữ", "que lữ", "quẻ lữ", "lu", "traveler"],
    "QUE_TON_2": ["tốn", "que tốn", "quẻ tốn", "xun", "gentle"],
    "QUE_DOAI": ["đoài", "que đoài", "quẻ đoài", "dui", "joyous"],
    "QUE_HOAN": ["hoán", "que hoán", "quẻ hoán", "huan", "dispersion"],
    "QUE_TIET": ["tiết", "que tiết", "quẻ tiết", "jie", "limitation"],
    "QUE_TRUNG_PHU": ["trung phu", "que trung phu", "inner truth"],
    "QUE_TIEU_QUA": ["tiểu quá", "que tiểu quá", "small exceeding"],
    "QUE_KY_TE": ["ký tế", "que ký tế", "after completion"],
    "QUE_VI_TE": ["vị tế", "que vị tế", "before completion"]
}

# Trigram mapping cho việc tính toán hexagram
TRIGRAM_MAP = {
    "111": "☰",  # Qian - Heaven
    "110": "☱",  # Dui - Lake  
    "101": "☲",  # Li - Fire
    "100": "☳",  # Zhen - Thunder
    "011": "☴",  # Xun - Wind
    "010": "☵",  # Kan - Water
    "001": "☶",  # Gen - Mountain
    "000": "☷"   # Kun - Earth
}

# Hexagram lookup table đầy đủ từ upper và lower trigrams
HEXAGRAM_LOOKUP = {
    # Upper Trigram, Lower Trigram: (Number, Code)
    
    # Thượng Kinh (Quẻ 1-30)
    ("☰", "☰"): (1, "QUE_KIEN"),          # 乾 Qian - The Creative
    ("☷", "☷"): (2, "QUE_KHON"),          # 坤 Kun - The Receptive
    ("☵", "☳"): (3, "QUE_TRUAN"),         # 屯 Zhun - Difficulty at the Beginning
    ("☶", "☵"): (4, "QUE_MONG"),          # 蒙 Meng - Youthful Folly
    ("☵", "☰"): (5, "QUE_NHU"),           # 需 Xu - Waiting
    ("☰", "☵"): (6, "QUE_TUNG"),          # 訟 Song - Conflict
    ("☷", "☵"): (7, "QUE_SU"),            # 師 Shi - The Army
    ("☵", "☷"): (8, "QUE_TY"),            # 比 Bi - Holding Together
    ("☴", "☰"): (9, "QUE_TIEU_SUC"),      # 小畜 Xiao Xu - Small Taming
    ("☰", "☱"): (10, "QUE_LY"),           # 履 Lu - Treading
    ("☷", "☰"): (11, "QUE_THAI"),         # 泰 Tai - Peace
    ("☰", "☷"): (12, "QUE_PHE_HAP"),      # 否 Pi - Standstill
    ("☰", "☲"): (13, "QUE_DONG_NHAN"),    # 同人 Tong Ren - Fellowship
    ("☲", "☰"): (14, "QUE_DAI_HUU"),      # 大有 Da You - Great Possession
    ("☷", "☶"): (15, "QUE_KHIEM"),        # 謙 Qian - Modesty
    ("☳", "☷"): (16, "QUE_DU"),           # 豫 Yu - Enthusiasm
    ("☱", "☳"): (17, "QUE_TUY"),          # 隨 Sui - Following
    ("☶", "☴"): (18, "QUE_CO"),           # 蠱 Gu - Work on the Decayed
    ("☷", "☱"): (19, "QUE_LAM"),          # 臨 Lin - Approach
    ("☴", "☷"): (20, "QUE_QUAN"),         # 觀 Guan - Contemplation
    ("☲", "☳"): (21, "QUE_PHE_HAP"),      # 噬嗑 Shi He - Biting Through
    ("☶", "☲"): (22, "QUE_BI"),           # 賁 Bi - Grace
    ("☶", "☷"): (23, "QUE_BAC"),          # 剝 Bo - Splitting Apart
    ("☷", "☳"): (24, "QUE_PHUC"),         # 復 Fu - Return
    ("☰", "☳"): (25, "QUE_VO_VONG"),      # 無妄 Wu Wang - Innocence
    ("☶", "☰"): (26, "QUE_DAI_SUC"),      # 大畜 Da Xu - Great Taming
    ("☶", "☳"): (27, "QUE_DI"),           # 頤 Yi - Nourishment
    ("☱", "☴"): (28, "QUE_DAI_QUA"),      # 大過 Da Guo - Great Exceeding
    ("☵", "☵"): (29, "QUE_TAP_KHAM"),     # 坎 Kan - The Abysmal Water
    ("☲", "☲"): (30, "QUE_LY_2"),         # 離 Li - The Clinging Fire
    
    # Hạ Kinh (Quẻ 31-64)
    ("☱", "☶"): (31, "QUE_HAM"),          # 咸 Xian - Influence
    ("☳", "☴"): (32, "QUE_HANG"),         # 恆 Heng - Duration
    ("☰", "☶"): (33, "QUE_DON"),          # 遯 Dun - Retreat
    ("☳", "☰"): (34, "QUE_DAI_TRANG"),    # 大壯 Da Zhuang - Great Power
    ("☲", "☷"): (35, "QUE_TAN"),          # 晉 Jin - Progress
    ("☷", "☲"): (36, "QUE_MINH_DI"),      # 明夷 Ming Yi - Darkening of the Light
    ("☴", "☲"): (37, "QUE_GIA_NHAN"),     # 家人 Jia Ren - The Family
    ("☲", "☱"): (38, "QUE_KHUE"),         # 睽 Kui - Opposition
    ("☵", "☶"): (39, "QUE_GIAN"),         # 蹇 Jian - Obstruction
    ("☳", "☵"): (40, "QUE_GIAI"),         # 解 Jie - Deliverance
    ("☶", "☱"): (41, "QUE_TON"),          # 損 Sun - Decrease
    ("☴", "☳"): (42, "QUE_ICH"),          # 益 Yi - Increase
    ("☱", "☰"): (43, "QUE_QUAI"),         # 夬 Guai - Breakthrough
    ("☰", "☴"): (44, "QUE_CAU"),          # 姤 Gou - Coming to Meet
    ("☱", "☷"): (45, "QUE_TUY"),          # 萃 Cui - Gathering Together
    ("☷", "☴"): (46, "QUE_THANG"),        # 升 Sheng - Pushing Upward
    ("☱", "☵"): (47, "QUE_KHON_2"),       # 困 Kun - Oppression
    ("☵", "☴"): (48, "QUE_TINH"),         # 井 Jing - The Well
    ("☱", "☲"): (49, "QUE_CACH"),         # 革 Ge - Revolution
    ("☲", "☴"): (50, "QUE_DINH"),         # 鼎 Ding - The Cauldron
    ("☳", "☳"): (51, "QUE_CHAN"),         # 震 Zhen - The Arousing Thunder
    ("☶", "☶"): (52, "QUE_CAN"),          # 艮 Gen - Keeping Still Mountain
    ("☴", "☶"): (53, "QUE_TIEM"),         # 漸 Jian - Development
    ("☳", "☱"): (54, "QUE_QUI_MUOI"),     # 歸妹 Gui Mei - The Marrying Maiden
    ("☳", "☲"): (55, "QUE_PHONG"),        # 豐 Feng - Abundance
    ("☲", "☶"): (56, "QUE_LU"),           # 旅 Lu - The Wanderer
    ("☴", "☴"): (57, "QUE_TON_2"),        # 巽 Xun - The Gentle Wind
    ("☱", "☱"): (58, "QUE_DOAI"),         # 兌 Dui - The Joyous Lake
    ("☴", "☵"): (59, "QUE_HOAN"),         # 渙 Huan - Dispersion
    ("☵", "☱"): (60, "QUE_TIET"),         # 節 Jie - Limitation
    ("☴", "☱"): (61, "QUE_TRUNG_PHU"),    # 中孚 Zhong Fu - Inner Truth
    ("☳", "☶"): (62, "QUE_TIEU_QUA"),     # 小過 Xiao Guo - Small Exceeding
    ("☲", "☵"): (63, "QUE_KY_TE"),        # 既濟 Ji Ji - After Completion
    ("☵", "☲"): (64, "QUE_VI_TE")         # 未濟 Wei Ji - Before Completion
}

# ──────────────────────────────────────────────────────────────
# Detection Functions
# ──────────────────────────────────────────────────────────────

def detect_hexagram(text: str) -> Optional[str]:
    """
    Phát hiện mã quẻ trong văn bản đầu vào
    
    Args:
        text: Văn bản đầu vào từ người dùng
        
    Returns:
        Mã quẻ (VD: "QUE_CACH") hoặc None nếu không phát hiện được
    """
    if not text:
        return None
        
    text_lower = text.lower().strip()
    
    # Loại bỏ dấu câu và ký tự đặc biệt
    text_clean = re.sub(r'[^\w\s]', ' ', text_lower)
    
    # Tìm kiếm theo độ ưu tiên (từ cụ thể đến tổng quát)
    for code, keywords in HEXAGRAM_MAP.items():
        for keyword in sorted(keywords, key=len, reverse=True):
            if keyword in text_clean:
                return code
    
    return None
