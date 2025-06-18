# retrieval_agent.py
from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Optional

from cachetools import TTLCache
from pymongo import MongoClient, errors as mongo_errors
from rapidfuzz import fuzz, process as rf_process
from sentence_transformers import SentenceTransformer
from underthesea import word_tokenize

from base_agent import BaseAgent, AgentType, ProcessingState
from config import *  # MONGO_URI, DB_NAME, COLLECTION, EMBED_MODEL, CACHE_DIR, etc.

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

FUZZY_THRESHOLD = 80  # RapidFuzz score

# TTL caches -------------------------------------------------------------
_HEX_CACHE: TTLCache = TTLCache(maxsize=1024, ttl=600)   # 10 min
_SEM_CACHE: TTLCache = TTLCache(maxsize=512, ttl=300)    # 5 min
_TXT_CACHE: TTLCache = TTLCache(maxsize=512, ttl=300)    # 5 min


class RetrievalAgent(BaseAgent):
    """Retrieval agent with fuzzy matching & cached Mongo queries."""

    def __init__(self):
        super().__init__("RetrievalAgent", AgentType.RETRIEVAL)

        # Mongo + embedder ----------------------------------------------
        self.client = MongoClient(MONGO_URI)
        self.collection = self.client[DB_NAME][COLLECTION]
        self.embedder = SentenceTransformer(EMBED_MODEL, cache_folder=CACHE_DIR)

        # Full concept mapping dict (⚠️ phải điền đủ 64 quẻ) -------------
        self.concept_mapping: Dict[str, str] = {
            # ═══════════════════════════════════════════════════════════════
            # THƯỢNG KINH (Quẻ 1-30) - Upper Canon
            # ═══════════════════════════════════════════════════════════════
            
            # Quẻ 1: Kiền - The Creative
            "creative": "QUE_KIEN", "leadership": "QUE_KIEN", "initiative": "QUE_KIEN", 
            "strength": "QUE_KIEN", "heaven": "QUE_KIEN",
            "sáng_tạo": "QUE_KIEN", "lãnh_đạo": "QUE_KIEN", "chủ_động": "QUE_KIEN", 
            "mạnh_mẽ": "QUE_KIEN", "trời": "QUE_KIEN",
            
            # Quẻ 2: Khôn - The Receptive
            "receptive": "QUE_KHON", "nurturing": "QUE_KHON", "supportive": "QUE_KHON",
            "patient": "QUE_KHON", "earth": "QUE_KHON",
            "tiếp_nhận": "QUE_KHON", "nuôi_dưỡng": "QUE_KHON", "hỗ_trợ": "QUE_KHON",
            "kiên_nhẫn": "QUE_KHON", "đất": "QUE_KHON",
            
            # Quẻ 3: Tun - Initial Difficulty
            "difficulty": "QUE_TUAN", "beginning": "QUE_TUAN", "struggle": "QUE_TUAN",
            "perseverance": "QUE_TUAN", "sprouting": "QUE_TUAN",
            "khó_khăn": "QUE_TUAN", "bắt_đầu": "QUE_TUAN", "đấu_tranh": "QUE_TUAN",
            "kiên_trì": "QUE_TUAN", "mới_mầm": "QUE_TUAN",
            
            # Quẻ 4: Mông - Youthful Folly
            "learning": "QUE_MONG", "inexperience": "QUE_MONG", "teaching": "QUE_MONG",
            "guidance": "QUE_MONG", "youth": "QUE_MONG",
            "học_tập": "QUE_MONG", "thiếu_kinh_nghiệm": "QUE_MONG", "dạy_dỗ": "QUE_MONG",
            "hướng_dẫn": "QUE_MONG", "trẻ_trung": "QUE_MONG",
            
            # Quẻ 5: Nhu - Waiting
            "waiting": "QUE_XU", "patience": "QUE_XU", "preparation": "QUE_XU",
            "nourishment": "QUE_XU", "timing": "QUE_XU",
            "chờ_đợi": "QUE_XU", "kiên_nhẫn": "QUE_XU", "chuẩn_bị": "QUE_XU",
            "nuôi_dưỡng": "QUE_XU", "thời_cơ": "QUE_XU",
            
            # Quẻ 6: Tụng - Conflict
            "conflict": "QUE_TUNG", "dispute": "QUE_TUNG", "lawsuit": "QUE_TUNG",
            "argument": "QUE_TUNG", "disagreement": "QUE_TUNG",
            "xung_đột": "QUE_TUNG", "tranh_chấp": "QUE_TUNG", "kiện_tụng": "QUE_TUNG",
            "tranh_cãi": "QUE_TUNG", "bất_đồng": "QUE_TUNG",
            
            # Quẻ 7: Sư - Army
            "army": "QUE_SU", "discipline": "QUE_SU", "organization": "QUE_SU",
            "leadership": "QUE_SU", "collective": "QUE_SU",
            "quân_đội": "QUE_SU", "kỷ_luật": "QUE_SU", "tổ_chức": "QUE_SU",
            "lãnh_đạo": "QUE_SU", "tập_thể": "QUE_SU","quân nhân": "QUE_SU",
            "quân_lực": "QUE_SU", "chiến_tranh": "QUE_SU", "bộ_đội": "QUE_SU",
            "người_lính": "QUE_SU", "chiến_sĩ": "QUE_SU",
            
            # Quẻ 8: Tỷ - Holding Together
            "unity": "QUE_TI", "cooperation": "QUE_TI", "alliance": "QUE_TI",
            "support": "QUE_TI", "bonding": "QUE_TI",
            "đoàn_kết": "QUE_TI", "hợp_tác": "QUE_TI", "liên_minh": "QUE_TI",
            "ủng_hộ": "QUE_TI", "gắn_kết": "QUE_TI",
            
            # Quẻ 9: Tiểu Súc - Small Taming
            "restraint": "QUE_TIEU_CAO", "accumulation": "QUE_TIEU_CAO", "patience": "QUE_TIEU_CAO",
            "gathering": "QUE_TIEU_CAO", "preparation": "QUE_TIEU_CAO",
            "kiềm_chế": "QUE_TIEU_CAO", "tích_lũy": "QUE_TIEU_CAO", "nhẫn_nại": "QUE_TIEU_CAO",
            "thu_thập": "QUE_TIEU_CAO", "chuẩn_bị": "QUE_TIEU_CAO",
            
            # Quẻ 10: Lý - Treading
            "conduct": "QUE_LY", "behavior": "QUE_LY", "etiquette": "QUE_LY",
            "careful": "QUE_LY", "proper": "QUE_LY",
            "ứng_xử": "QUE_LY", "hành_vi": "QUE_LY", "lễ_nghi": "QUE_LY",
            "cẩn_thận": "QUE_LY", "đúng_đắn": "QUE_LY", "chỉn_chu": "QUE_LY",
            
            
            # Quẻ 11: Thái - Peace
            "peace": "QUE_THAI", "harmony": "QUE_THAI", "prosperity": "QUE_THAI",
            "balance": "QUE_THAI", "success": "QUE_THAI",
            "hòa_bình": "QUE_THAI", "hài_hòa": "QUE_THAI", "thịnh_vượng": "QUE_THAI",
            "cân_bằng": "QUE_THAI", "thành_công": "QUE_THAI",
            
            # Quẻ 12: Phì - Standstill
            "stagnation": "QUE_PHI", "obstruction": "QUE_PHI", "decline": "QUE_PHI",
            "separation": "QUE_PHI", "blockage": "QUE_PHI",
            "trì_trệ": "QUE_PHI", "cản_trở": "QUE_PHI", "suy_thoái": "QUE_PHI",
            "chia_ly": "QUE_PHI", "tắc_nghẽn": "QUE_PHI",
            
            # Quẻ 13: Đồng Nhân - Fellowship
            "fellowship": "QUE_DONG_NHAN", "community": "QUE_DONG_NHAN", "cooperation": "QUE_DONG_NHAN",
            "friendship": "QUE_DONG_NHAN", "unity": "QUE_DONG_NHAN",
            "đồng_nghiệp": "QUE_DONG_NHAN", "cộng_đồng": "QUE_DONG_NHAN", "hợp_tác": "QUE_DONG_NHAN",
            "tình_bạn": "QUE_DONG_NHAN", "đoàn_kết": "QUE_DONG_NHAN", "tập_thể": "QUE_DONG_NHAN",
            
            # Quẻ 14: Đại Hữu - Great Possession
            "abundance": "QUE_DAI_HUU", "wealth": "QUE_DAI_HUU", "prosperity": "QUE_DAI_HUU",
            "success": "QUE_DAI_HUU", "possession": "QUE_DAI_HUU",
            "dồi_dào": "QUE_DAI_HUU", "giàu_có": "QUE_DAI_HUU", "thịnh_vượng": "QUE_DAI_HUU",
            "thành_công": "QUE_DAI_HUU", "sở_hữu": "QUE_DAI_HUU",
            
            # Quẻ 15: Khiêm - Modesty
            "modesty": "QUE_KIEN_2", "humility": "QUE_KIEN_2", "simplicity": "QUE_KIEN_2",
            "balance": "QUE_KIEN_2", "virtue": "QUE_KIEN_2",
            "khiêm_tốn": "QUE_KIEN_2", "khiêm_nhường": "QUE_KIEN_2", "giản_dị": "QUE_KIEN_2",
            "cân_bằng": "QUE_KIEN_2", "đức_hạnh": "QUE_KIEN_2",
            
            # Quẻ 16: Dự - Enthusiasm
            "enthusiasm": "QUE_DU", "inspiration": "QUE_DU", "music": "QUE_DU",
            "celebration": "QUE_DU", "joy": "QUE_DU",
            "nhiệt_tình": "QUE_DU", "cảm_hứng": "QUE_DU", "âm_nhạc": "QUE_DU",
            "kỷ_niệm": "QUE_DU", "vui_vẻ": "QUE_DU",
            
            # Quẻ 17: Tùy - Following
            "following": "QUE_TUI", "adaptation": "QUE_TUI", "flexibility": "QUE_TUI",
            "compliance": "QUE_TUI", "responsive": "QUE_TUI",
            "theo_dõi": "QUE_TUI", "thích_nghi": "QUE_TUI", "linh_hoạt": "QUE_TUI",
            "tuân_thủ": "QUE_TUI", "đáp_ứng": "QUE_TUI",
            
            # Quẻ 18: Cỗ - Work on Decay
            "decay": "QUE_CO", "corruption": "QUE_CO", "repair": "QUE_CO",
            "renovation": "QUE_CO", "healing": "QUE_CO",
            "hư_hỏng": "QUE_CO", "tham_nhũng": "QUE_CO", "sửa_chữa": "QUE_CO",
            "cải_tạo": "QUE_CO", "chữa_lành": "QUE_CO",
            
            # Quẻ 19: Lâm - Approach
            "approach": "QUE_LAN", "leadership": "QUE_LAN", "supervision": "QUE_LAN",
            "guidance": "QUE_LAN", "care": "QUE_LAN",
            "tiếp_cận": "QUE_LAN", "lãnh_đạo": "QUE_LAN", "giám_sát": "QUE_LAN",
            "hướng_dẫn": "QUE_LAN", "chăm_sóc": "QUE_LAN",
            
            # Quẻ 20: Quán - Contemplation
            "contemplation": "QUE_QUAN", "observation": "QUE_QUAN", "meditation": "QUE_QUAN",
            "insight": "QUE_QUAN", "reflection": "QUE_QUAN",
            "chiêm_ngưỡng": "QUE_QUAN", "quan_sát": "QUE_QUAN", "thiền_định": "QUE_QUAN",
            "sáng_suốt": "QUE_QUAN", "suy_ngẫm": "QUE_QUAN",
            
            # Quẻ 21: Thích Hạc - Biting Through
            "justice": "QUE_THICH_HAC", "punishment": "QUE_THICH_HAC", "decision": "QUE_THICH_HAC",
            "breakthrough": "QUE_THICH_HAC", "resolution": "QUE_THICH_HAC",
            "công_lý": "QUE_THICH_HAC", "trừng_phạt": "QUE_THICH_HAC", "quyết_định": "QUE_THICH_HAC",
            "đột_phá": "QUE_THICH_HAC", "giải_quyết": "QUE_THICH_HAC",
            
            # Quẻ 22: Bí - Grace
            "beauty": "QUE_BI", "grace": "QUE_BI", "elegance": "QUE_BI",
            "refinement": "QUE_BI", "culture": "QUE_BI",
            "vẻ_đẹp": "QUE_BI", "duyên_dáng": "QUE_BI", "tao_nhã": "QUE_BI",
            "tinh_tế": "QUE_BI", "văn_hóa": "QUE_BI",
            
            # Quẻ 23: Bác - Splitting Apart
            "splitting": "QUE_BAC", "dissolution": "QUE_BAC", "decay": "QUE_BAC",
            "erosion": "QUE_BAC", "breakdown": "QUE_BAC",
            "tách_rời": "QUE_BAC", "tan_rã": "QUE_BAC", "suy_thoái": "QUE_BAC",
            "xói_mòn": "QUE_BAC", "sụp_đổ": "QUE_BAC",
            
            # Quẻ 24: Phục - Return
            "return": "QUE_PHUC", "renewal": "QUE_PHUC", "revival": "QUE_PHUC",
            "rebirth": "QUE_PHUC", "restoration": "QUE_PHUC",
            "trở_về": "QUE_PHUC", "đổi_mới": "QUE_PHUC", "hồi_sinh": "QUE_PHUC",
            "tái_sinh": "QUE_PHUC", "phục_hồi": "QUE_PHUC",
            
            # Quẻ 25: Vô Vong - Innocence
            "innocence": "QUE_VO_VONG", "spontaneity": "QUE_VO_VONG", "natural": "QUE_VO_VONG",
            "sincerity": "QUE_VO_VONG", "authenticity": "QUE_VO_VONG",
            "ngây_thơ": "QUE_VO_VONG", "tự_phát": "QUE_VO_VONG", "tự_nhiên": "QUE_VO_VONG",
            "chân_thành": "QUE_VO_VONG", "thật_thà": "QUE_VO_VONG",
            
            # Quẻ 26: Đại Súc - Great Taming
            "restraint": "QUE_DAI_CAO", "accumulation": "QUE_DAI_CAO", "strength": "QUE_DAI_CAO",
            "control": "QUE_DAI_CAO", "discipline": "QUE_DAI_CAO",
            "kiềm_chế": "QUE_DAI_CAO", "tích_lũy": "QUE_DAI_CAO", "sức_mạnh": "QUE_DAI_CAO",
            "kiểm_soát": "QUE_DAI_CAO", "kỷ_luật": "QUE_DAI_CAO",
            
            # Quẻ 27: Di - Nourishment
            "nourishment": "QUE_DI", "nutrition": "QUE_DI", "feeding": "QUE_DI",
            "sustenance": "QUE_DI", "care": "QUE_DI",
            "nuôi_dưỡng": "QUE_DI", "dinh_dưỡng": "QUE_DI", "cho_ăn": "QUE_DI",
            "duy_trì": "QUE_DI", "chăm_sóc": "QUE_DI",
            
            # Quẻ 28: Đại Quá - Great Exceeding
            "excess": "QUE_DAI_QUAT", "burden": "QUE_DAI_QUAT", "overload": "QUE_DAI_QUAT",
            "critical": "QUE_DAI_QUAT", "extreme": "QUE_DAI_QUAT",
            "thừa_thãi": "QUE_DAI_QUAT", "gánh_nặng": "QUE_DAI_QUAT", "quá_tải": "QUE_DAI_QUAT",
            "quan_trọng": "QUE_DAI_QUAT", "cực_đoan": "QUE_DAI_QUAT",
            
            # Quẻ 29: Khảm - Water/Abyss
            "danger": "QUE_CAM", "difficulty": "QUE_CAM", "water": "QUE_CAM",
            "flowing": "QUE_CAM", "persistence": "QUE_CAM",
            "nguy_hiểm": "QUE_CAM", "khó_khăn": "QUE_CAM", "nước": "QUE_CAM",
            "chảy": "QUE_CAM", "kiên_trì": "QUE_CAM",
            
            # Quẻ 30: Ly - Fire/Clinging
            "fire": "QUE_LY_2", "brightness": "QUE_LY_2", "clarity": "QUE_LY_2",
            "illumination": "QUE_LY_2", "attachment": "QUE_LY_2",
            "lửa": "QUE_LY_2", "sáng_sủa": "QUE_LY_2", "rõ_ràng": "QUE_LY_2",
            "chiếu_sáng": "QUE_LY_2", "gắn_bó": "QUE_LY_2",
            
            # ═══════════════════════════════════════════════════════════════
            # HẠ KINH (Quẻ 31-64) - Lower Canon
            # ═══════════════════════════════════════════════════════════════
            
            # Quẻ 31: Hàm - Influence
            "influence": "QUE_HAM", "attraction": "QUE_HAM", "courtship": "QUE_HAM",
            "magnetism": "QUE_HAM", "sensitivity": "QUE_HAM",
            "ảnh_hưởng": "QUE_HAM", "thu_hút": "QUE_HAM", "tán_tỉnh": "QUE_HAM",
            "từ_tính": "QUE_HAM", "nhạy_cảm": "QUE_HAM",
            
            # Quẻ 32: Hằng - Duration
            "duration": "QUE_HANG", "perseverance": "QUE_HANG", "endurance": "QUE_HANG",
            "consistency": "QUE_HANG", "stability": "QUE_HANG",
            "bền_vững": "QUE_HANG", "kiên_trì": "QUE_HANG", "sức_bền": "QUE_HANG",
            "nhất_quán": "QUE_HANG", "ổn_định": "QUE_HANG",
            
            # Quẻ 33: Độn - Retreat
            "retreat": "QUE_DUN", "withdrawal": "QUE_DUN", "strategic": "QUE_DUN",
            "yielding": "QUE_DUN", "timing": "QUE_DUN",
            "rút_lui": "QUE_DUN", "rút_về": "QUE_DUN", "chiến_lược": "QUE_DUN",
            "nhường_bộ": "QUE_DUN", "thời_điểm": "QUE_DUN",
            
            # Quẻ 34: Đại Tráng - Great Power
            "power": "QUE_DAI_TRANG", "strength": "QUE_DAI_TRANG", "vigor": "QUE_DAI_TRANG",
            "force": "QUE_DAI_TRANG", "energy": "QUE_DAI_TRANG",
            "quyền_lực": "QUE_DAI_TRANG", "sức_mạnh": "QUE_DAI_TRANG", "sinh_lực": "QUE_DAI_TRANG",
            "lực_lượng": "QUE_DAI_TRANG", "năng_lượng": "QUE_DAI_TRANG",
            
            # Quẻ 35: Tấn - Progress
            "progress": "QUE_TAN", "advancement": "QUE_TAN", "promotion": "QUE_TAN",
            "rising": "QUE_TAN", "improvement": "QUE_TAN",
            "tiến_bộ": "QUE_TAN", "thăng_tiến": "QUE_TAN", "thăng_chức": "QUE_TAN",
            "lên_cao": "QUE_TAN", "cải_thiện": "QUE_TAN",
            
            # Quẻ 36: Minh Di - Darkening Light
            "darkness": "QUE_MINH_DI", "hidden": "QUE_MINH_DI", "persecution": "QUE_MINH_DI",
            "concealment": "QUE_MINH_DI", "injury": "QUE_MINH_DI",
            "bóng_tối": "QUE_MINH_DI", "ẩn_giấu": "QUE_MINH_DI", "bức_hại": "QUE_MINH_DI",
            "che_giấu": "QUE_MINH_DI", "tổn_thương": "QUE_MINH_DI",
            
            # Quẻ 37: Gia Nhân - Family
            "family": "QUE_GIA_NHAN", "household": "QUE_GIA_NHAN", "domestic": "QUE_GIA_NHAN",
            "relatives": "QUE_GIA_NHAN", "tradition": "QUE_GIA_NHAN",
            "gia_đình": "QUE_GIA_NHAN", "hộ_gia_đình": "QUE_GIA_NHAN", "nội_trợ": "QUE_GIA_NHAN",
            "họ_hàng": "QUE_GIA_NHAN", "truyền_thống": "QUE_GIA_NHAN",
            
            # Quẻ 38: Khuê - Opposition
            "opposition": "QUE_KHUE", "conflict": "QUE_KHUE", "estrangement": "QUE_KHUE",
            "division": "QUE_KHUE", "misunderstanding": "QUE_KHUE",
            "đối_lập": "QUE_KHUE", "xung_đột": "QUE_KHUE", "xa_cách": "QUE_KHUE",
            "chia_rẽ": "QUE_KHUE", "hiểu_lầm": "QUE_KHUE",
            
            # Quẻ 39: Giản - Obstruction
            "obstruction": "QUE_GIAN", "difficulty": "QUE_GIAN", "impediment": "QUE_GIAN",
            "barrier": "QUE_GIAN", "challenge": "QUE_GIAN",
            "cản_trở": "QUE_GIAN", "khó_khăn": "QUE_GIAN", "trở_ngại": "QUE_GIAN",
            "rào_cản": "QUE_GIAN", "thách_thức": "QUE_GIAN",
            
            # Quẻ 40: Giải - Deliverance
            "liberation": "QUE_GIAI", "deliverance": "QUE_GIAI", "release": "QUE_GIAI",
            "solution": "QUE_GIAI", "freedom": "QUE_GIAI",
            "giải_phóng": "QUE_GIAI", "cứu_rỗi": "QUE_GIAI", "thả": "QUE_GIAI",
            "giải_pháp": "QUE_GIAI", "tự_do": "QUE_GIAI",
            
            # Quẻ 41: Tổn - Decrease
            "decrease": "QUE_TON", "reduction": "QUE_TON", "sacrifice": "QUE_TON",
            "simplification": "QUE_TON", "loss": "QUE_TON",
            "giảm": "QUE_TON", "cắt_giảm": "QUE_TON", "hy_sinh": "QUE_TON",
            "đơn_giản_hóa": "QUE_TON", "mất_mát": "QUE_TON",
            
            # Quẻ 42: Ích - Increase
            "increase": "QUE_ICH", "benefit": "QUE_ICH", "advantage": "QUE_ICH",
            "gain": "QUE_ICH", "growth": "QUE_ICH",
            "tăng": "QUE_ICH", "lợi_ích": "QUE_ICH", "thuận_lợi": "QUE_ICH",
            "thu_được": "QUE_ICH", "tăng_trưởng": "QUE_ICH",
            
            # Quẻ 43: Quái - Breakthrough
            "breakthrough": "QUE_QUAI", "resolution": "QUE_QUAI", "determination": "QUE_QUAI",
            "decisive": "QUE_QUAI", "elimination": "QUE_QUAI",
            "đột_phá": "QUE_QUAI", "giải_quyết": "QUE_QUAI", "quyết_tâm": "QUE_QUAI",
            "quyết_đoán": "QUE_QUAI", "loại_bỏ": "QUE_QUAI",
            
            # Quẻ 44: Cấu - Coming to Meet
            "meeting": "QUE_CAU", "encounter": "QUE_CAU", "temptation": "QUE_CAU",
            "seduction": "QUE_CAU", "yielding": "QUE_CAU",
            "gặp_gỡ": "QUE_CAU", "chạm_trán": "QUE_CAU", "cám_dỗ": "QUE_CAU",
            "quyến_rũ": "QUE_CAU", "nhường_bộ": "QUE_CAU",
            
            # Quẻ 45: Tụy - Gathering
            "gathering": "QUE_TOI", "collection": "QUE_TOI", "assembly": "QUE_TOI",
            "unity": "QUE_TOI", "concentration": "QUE_TOI",
            "tập_hợp": "QUE_TOI", "sưu_tầm": "QUE_TOI", "hội_họp": "QUE_TOI",
            "đoàn_kết": "QUE_TOI", "tập_trung": "QUE_TOI",
            
            # Quẻ 46: Thăng - Pushing Upward
            "ascending": "QUE_THANG", "growth": "QUE_THANG", "promotion": "QUE_THANG",
            "rising": "QUE_THANG", "development": "QUE_THANG",
            "thăng_tiến": "QUE_THANG", "tăng_trưởng": "QUE_THANG", "thăng_chức": "QUE_THANG",
            "dâng_cao": "QUE_THANG", "phát_triển": "QUE_THANG",
            
            # Quẻ 47: Khốn - Oppression
            "oppression": "QUE_KHON_2", "exhaustion": "QUE_KHON_2", "hardship": "QUE_KHON_2",
            "adversity": "QUE_KHON_2", "constraint": "QUE_KHON_2",
            "áp_bức": "QUE_KHON_2", "kiệt_sức": "QUE_KHON_2", "gian_khổ": "QUE_KHON_2",
            "nghịch_cảnh": "QUE_KHON_2", "ràng_buộc": "QUE_KHON_2",
            
            # Quẻ 48: Tỉnh - The Well
            "well": "QUE_TINH", "source": "QUE_TINH", "nourishment": "QUE_TINH",
            "community": "QUE_TINH", "renewal": "QUE_TINH",
            "giếng": "QUE_TINH", "nguồn": "QUE_TINH", "nuôi_dưỡng": "QUE_TINH",
            "cộng_đồng": "QUE_TINH", "đổi_mới": "QUE_TINH","gốc": "QUE_TINH",
            "căn_bản": "QUE_TINH", "cội_nguồn": "QUE_TINH",
            
            # Quẻ 49: Cách - Revolution
            "revolution": "QUE_CACH", "change": "QUE_CACH", "transformation": "QUE_CACH",
            "reform": "QUE_CACH", "molting": "QUE_CACH",
            "cách_mạng": "QUE_CACH", "thay_đổi": "QUE_CACH", "biến_đổi": "QUE_CACH",
            "cải_cách": "QUE_CACH", "lột_xác": "QUE_CACH", "sáng_tạo": "QUE_CACH",
            "đổi_mới": "QUE_CACH",
            
            # Quẻ 50: Đỉnh - Cauldron
            "cauldron": "QUE_DINH", "transformation": "QUE_DINH", "nourishment": "QUE_DINH",
            "culture": "QUE_DINH", "refinement": "QUE_DINH",
            "chung": "QUE_DINH", "biến_đổi": "QUE_DINH", "nuôi_dưỡng": "QUE_DINH",
            "văn_hóa": "QUE_DINH", "tinh_tế": "QUE_DINH", ""
            
            # Quẻ 51: Chấn - Thunder
            "thunder": "QUE_CHAN", "shock": "QUE_CHAN", "arousing": "QUE_CHAN",
            "movement": "QUE_CHAN", "awakening": "QUE_CHAN",
            "sấm": "QUE_CHAN", "chấn_động": "QUE_CHAN", "khởi_động": "QUE_CHAN",
            "chuyển_động": "QUE_CHAN", "thức_tỉnh": "QUE_CHAN", "đánh_thức": "QUE_CHAN",
            "kích_thích": "QUE_CHAN"," khơi_gợi": "QUE_CHAN","động_lực": "QUE_CHAN",
            "kích_hoạt": "QUE_CHAN", "kích_động": "QUE_CHAN"," khơi_dậy": "QUE_CHAN",
            "kích_thích": "QUE_CHAN", "kích_động": "QUE_CHAN","bừng_tỉnh": "QUE_CHAN",
            "sốc":"QUE_CHAN",
            
            # Quẻ 52: Cấn - Mountain
            "mountain": "QUE_CAN", "stillness": "QUE_CAN", "meditation": "QUE_CAN",
            "stopping": "QUE_CAN", "keeping": "QUE_CAN",
            "núi": "QUE_CAN", "tĩnh_lặng": "QUE_CAN", "thiền_định": "QUE_CAN",
            "dừng_lại": "QUE_CAN", "giữ_gìn": "QUE_CAN",
            
            # Quẻ 53: Tiệm - Development
            "development": "QUE_TIEM", "gradual": "QUE_TIEM", "progress": "QUE_TIEM",
            "marriage": "QUE_TIEM", "steady": "QUE_TIEM",
            "phát_triển": "QUE_TIEM", "từ_từ": "QUE_TIEM", "tiến_bộ": "QUE_TIEM",
            "hôn_nhân": "QUE_TIEM", "ổn_định": "QUE_TIEM",
            
            # Quẻ 54: Quy Muội - Marrying Maiden
            "marriage": "QUE_QUI_MUOI", "subordinate": "QUE_QUI_MUOI", "position": "QUE_QUI_MUOI",
            "propriety": "QUE_QUI_MUOI", "relationship": "QUE_QUI_MUOI",
            "hôn_nhân": "QUE_QUI_MUOI", "phụ_thuộc": "QUE_QUI_MUOI", "vị_trí": "QUE_QUI_MUOI",
            "đúng_mực": "QUE_QUI_MUOI", "quan_hệ": "QUE_QUI_MUOI", "cưới_hỏi": "QUE_QUI_MUOI",
            "lấy_chồng": "QUE_QUI_MUOI", "kết_hôn": "QUE_QUI_MUOI", "lấy_vợ": "QUE_QUI_MUOI",
            "hôn_uớc": "QUE_QUI_MUOI", "hôn_lễ": "QUE_QUI_MUOI", "lễ_cưới": "QUE_QUI_MUOI",
            "tình_yêu": "QUE_QUI_MUOI", "tình_cảm": "QUE_QUI_MUOI", "đám_cưới": "QUE_QUI_MUOI",
            
            # Quẻ 55: Phong - Abundance
            "abundance": "QUE_PHONG", "fullness": "QUE_PHONG", "prosperity": "QUE_PHONG",
            "peak": "QUE_PHONG", "zenith": "QUE_PHONG",
            "dồi_dào": "QUE_PHONG", "đầy_đủ": "QUE_PHONG", "thịnh_vượng": "QUE_PHONG",
            "đỉnh_cao": "QUE_PHONG", "tuyệt_đỉnh": "QUE_PHONG",
            
            # Quẻ 56: Lữ - Traveler
            "travel": "QUE_LU", "journey": "QUE_LU", "wanderer": "QUE_LU",
            "stranger": "QUE_LU", "temporary": "QUE_LU",
            "du_lịch": "QUE_LU", "hành_trình": "QUE_LU", "kẻ_lang_thang": "QUE_LU",
            "người_lạ": "QUE_LU", "tạm_thời": "QUE_LU",
            
            # Quẻ 57: Tốn - Gentle Wind
            "gentle": "QUE_TON_2", "penetrating": "QUE_TON_2", "wind": "QUE_TON_2",
            "influence": "QUE_TON_2", "persistent": "QUE_TON_2",
            "nhẹ_nhàng": "QUE_TON_2", "thấm_sâu": "QUE_TON_2", "gió": "QUE_TON_2",
            "ảnh_hưởng": "QUE_TON_2", "dai_dẳng": "QUE_TON_2", "mềm_mại": "QUE_TON_2",
            "mềm_dẻo": "QUE_TON_2", "dịu_dàng": "QUE_TON_2",
            "êm_ái": "QUE_TON_2", "êm_dịu": "QUE_TON_2", "mềm_mỏng": "QUE_TON_2","uyển_chuyển": "QUE_TON_2",
            
            # Quẻ 58: Đoài - Joyous Lake
            "joy": "QUE_DOAI", "pleasure": "QUE_DOAI", "lake": "QUE_DOAI",
            "cheerful": "QUE_DOAI", "satisfaction": "QUE_DOAI",
            "vui_vẻ": "QUE_DOAI", "khoái_lạc": "QUE_DOAI", "hồ": "QUE_DOAI",
            "vui_tươi": "QUE_DOAI", "hài_lòng": "QUE_DOAI",
            
            # Quẻ 59: Hoán - Dispersion
            "dispersion": "QUE_HOAN", "dissolution": "QUE_HOAN", "scattering": "QUE_HOAN",
            "separation": "QUE_HOAN", "wind": "QUE_HOAN",
            "phân_tán": "QUE_HOAN", "tan_rã": "QUE_HOAN", "rải_rác": "QUE_HOAN",
            "tách_rời": "QUE_HOAN", "gió": "QUE_HOAN",
            
            # Quẻ 60: Tiết - Limitation
            "limitation": "QUE_TIET", "restraint": "QUE_TIET", "moderation": "QUE_TIET",
            "discipline": "QUE_TIET", "regulation": "QUE_TIET",
            "giới_hạn": "QUE_TIET", "kiềm_chế": "QUE_TIET", "điều_độ": "QUE_TIET",
            "kỷ_luật": "QUE_TIET", "quy_định": "QUE_TIET",
            
            # Quẻ 61: Trung Phu - Inner Truth
            "truth": "QUE_TRUNG_PHU", "sincerity": "QUE_TRUNG_PHU", "confidence": "QUE_TRUNG_PHU",
            "inner": "QUE_TRUNG_PHU", "faith": "QUE_TRUNG_PHU",
            "chân_lý": "QUE_TRUNG_PHU", "chân_thành": "QUE_TRUNG_PHU", "tự_tin": "QUE_TRUNG_PHU",
            "nội_tâm": "QUE_TRUNG_PHU", "đức_tin": "QUE_TRUNG_PHU",
            
            # Quẻ 62: Tiểu Quá - Small Exceeding
            "exceeding": "QUE_TIEU_QUAT", "small": "QUE_TIEU_QUAT", "detail": "QUE_TIEU_QUAT",
            "caution": "QUE_TIEU_QUAT", "humility": "QUE_TIEU_QUAT",
            "vượt_quá": "QUE_TIEU_QUAT", "nhỏ": "QUE_TIEU_QUAT", "chi_tiết": "QUE_TIEU_QUAT",
            "thận_trọng": "QUE_TIEU_QUAT", "khiêm_tốn": "QUE_TIEU_QUAT",
            
            # Quẻ 63: Ký Tế - After Completion
            "completion": "QUE_KI_TE", "accomplished": "QUE_KI_TE", "finished": "QUE_KI_TE",
            "success": "QUE_KI_TE", "fulfillment": "QUE_KI_TE",
            "hoàn_thành": "QUE_KI_TE", "đạt_được": "QUE_KI_TE", "kết_thúc": "QUE_KI_TE",
            "thành_công": "QUE_KI_TE", "thỏa_mãn": "QUE_KI_TE",
            
            # Quẻ 64: Vị Tế - Before Completion
            "incomplete": "QUE_VI_TE", "unfinished": "QUE_VI_TE", "transition": "QUE_VI_TE",
            "potential": "QUE_VI_TE", "preparation": "QUE_VI_TE",
            "chưa_hoàn_thành": "QUE_VI_TE", "chưa_xong": "QUE_VI_TE", "chuyển_tiếp": "QUE_VI_TE",
            "tiềm_năng": "QUE_VI_TE", "chuẩn_bị": "QUE_VI_TE", "chưa_sẵn_sàng": "QUE_VI_TE",
            "chưa_hoàn_tất": "QUE_VI_TE","chưa_hoàn_mĩ": "QUE_VI_TE","chưa_hoàn_hảo": "QUE_VI_TE",
            "chưa_hoàn_thiện": "QUE_VI_TE"
        }
        self._concept_keys = list(self.concept_mapping.keys())

    # ------------------------------------------------------------------
    async def process(self, state: ProcessingState) -> ProcessingState:  # noqa: C901
        query: str = state.expanded_query or state.query
        query_type = state.query_type

        # 1️⃣ concept (fuzzy+exact) --------------------------------------
        code = self._detect_hexagram_by_concept(query)
        if code:
            docs = await self._hexagram_docs(code)
            if docs:
                state.retrieved_docs = docs
                state.reasoning_chain.append(f"concept→{code}")
                return state

        # 2️⃣ explicit hexagram in query ---------------------------------
        if query_type == "hexagram_specific" or state.entities.get("hexagrams"):
            docs = await self._hexagram_search(query, state)
            if docs:
                state.retrieved_docs = docs
                state.reasoning_chain.append("hexagram-specific")
                return state

        # 3️⃣ fallback strategies ---------------------------------------
        for name, func in [
            ("semantic", self._semantic_search),
            ("text", self._text_search),
            ("random", self._random_sample),
        ]:
            try:
                docs = await func(query, state)
                if docs:
                    state.retrieved_docs = docs
                    state.reasoning_chain.append(f"{name} {len(docs)} docs")
                    return state
            except Exception as e:
                logger.warning("%s failed: %s", name, e)

        state.retrieved_docs = []
        state.reasoning_chain.append("no result")
        return state

    # ------------------------------------------------------------------
    # Concept matching --------------------------------------------------
    def _detect_hexagram_by_concept(self, query: str) -> Optional[str]:
        ql = query.lower()
        # exact first
        for kw, code in self.concept_mapping.items():
            if kw in ql:
                return code
        # fuzzy second
        best = rf_process.extractOne(ql, self._concept_keys, scorer=fuzz.partial_ratio)
        if best and best[1] >= FUZZY_THRESHOLD:
            return self.concept_mapping[best[0]]
        return None

    # ------------------------------------------------------------------
    # Mongo helpers with caching ---------------------------------------
    async def _hexagram_docs(self, code: str) -> List[Dict]:
        if code in _HEX_CACHE:
            return _HEX_CACHE[code]
        docs = list(self.collection.find({"hexagram": code}).limit(TOP_K_RETRIEVE))
        _HEX_CACHE[code] = docs
        return docs

    async def _hexagram_search(self, query: str, state: ProcessingState) -> List[Dict]:
        from mapping import detect_hexagram
        code = detect_hexagram(query)
        if not code and state.entities.get("hexagrams"):
            for name in state.entities["hexagrams"]:
                code = detect_hexagram(name)
                if code:
                    break
        return await self._hexagram_docs(code) if code else []

    async def _semantic_search(self, query: str, state: ProcessingState) -> List[Dict]:
        if query in _SEM_CACHE:
            return _SEM_CACHE[query]
        emb = self.embedder.encode(word_tokenize(query, format="text")).tolist()
        pipeline = [
            {"$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": emb,
                "numCandidates": TOP_K_RETRIEVE * 3,
                "limit": TOP_K_RETRIEVE,
            }},
            {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
            {"$match": {"score": {"$gte": SIMILARITY_THRESHOLD}}},
        ]
        docs = list(self.collection.aggregate(pipeline))
        _SEM_CACHE[query] = docs
        return docs

    async def _text_search(self, query: str, state: ProcessingState) -> List[Dict]:
        if query in _TXT_CACHE:
            return _TXT_CACHE[query]
        try:
            try:
                self.collection.create_index([("text", "text")])
            except mongo_errors.OperationFailure as err:
                if err.code != 85:
                    raise
            cursor = (
                self.collection.find({"$text": {"$search": query}}, {"score": {"$meta": "textScore"}})
                .sort([("score", {"$meta": "textScore"})])
                .limit(TOP_K_RETRIEVE)
            )
            docs = list(cursor)
            _TXT_CACHE[query] = docs
            return docs
        except Exception as exc:
            logger.error("text_search: %s", exc)
            return []

    async def _random_sample(self, query: str, state: ProcessingState) -> List[Dict]:
        return list(self.collection.aggregate([{"$sample": {"size": min(TOP_K_RETRIEVE, 5)}}]))
