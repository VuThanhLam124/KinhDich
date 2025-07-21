"""
Module retrieval_agent.py - Agent truy xuất dữ liệu với fuzzy matching & cached Mongo queries
"""
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

        # Full concept mapping dict
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
            
            # Quẻ 3: Truân - Initial Difficulty
            "difficulty": "QUE_TRUAN", "beginning": "QUE_TRUAN", "struggle": "QUE_TRUAN",
            "perseverance": "QUE_TRUAN", "sprouting": "QUE_TRUAN",
            "khó_khăn": "QUE_TRUAN", "bắt_đầu": "QUE_TRUAN", "đấu_tranh": "QUE_TRUAN",
            "kiên_trì": "QUE_TRUAN", "mới_mầm": "QUE_TRUAN",
            
            # Quẻ 4: Mông - Youthful Folly
            "learning": "QUE_MONG", "inexperience": "QUE_MONG", "teaching": "QUE_MONG",
            "guidance": "QUE_MONG", "youth": "QUE_MONG",
            "học_tập": "QUE_MONG", "thiếu_kinh_nghiệm": "QUE_MONG", "dạy_dỗ": "QUE_MONG",
            "hướng_dẫn": "QUE_MONG", "trẻ_trung": "QUE_MONG",
            
            # Quẻ 5: Nhu - Waiting
            "waiting": "QUE_NHU", "patience": "QUE_NHU", "preparation": "QUE_NHU",
            "nourishment": "QUE_NHU", "timing": "QUE_NHU",
            "chờ_đợi": "QUE_NHU", "kiên_nhẫn": "QUE_NHU", "chuẩn_bị": "QUE_NHU",
            "nuôi_dưỡng": "QUE_NHU", "thời_cơ": "QUE_NHU",
            
            # Quẻ 6: Tụng - Conflict
            "conflict": "QUE_TUNG", "dispute": "QUE_TUNG", "lawsuit": "QUE_TUNG",
            "argument": "QUE_TUNG", "disagreement": "QUE_TUNG",
            "xung_đột": "QUE_TUNG", "tranh_chấp": "QUE_TUNG", "kiện_tụng": "QUE_TUNG",
            "tranh_cãi": "QUE_TUNG", "bất_đồng": "QUE_TUNG",
            
            # Quẻ 7: Sư - Army
            "army": "QUE_SU", "discipline": "QUE_SU", "organization": "QUE_SU",
            "leadership": "QUE_SU", "collective": "QUE_SU",
            "quân_đội": "QUE_SU", "kỷ_luật": "QUE_SU", "tổ_chức": "QUE_SU",
            "lãnh_đạo": "QUE_SU", "tập_thể": "QUE_SU", "quân_nhân": "QUE_SU",
            "quân_lực": "QUE_SU", "chiến_tranh": "QUE_SU", "bộ_đội": "QUE_SU",
            "người_lính": "QUE_SU", "chiến_sĩ": "QUE_SU",
            
            # Quẻ 8: Tỷ - Holding Together
            "unity": "QUE_TY", "cooperation": "QUE_TY", "alliance": "QUE_TY",
            "support": "QUE_TY", "bonding": "QUE_TY",
            "đoàn_kết": "QUE_TY", "hợp_tác": "QUE_TY", "liên_minh": "QUE_TY",
            "ủng_hộ": "QUE_TY", "gắn_kết": "QUE_TY",
            
            # Quẻ 9: Tiểu Súc - Small Taming
            "restraint": "QUE_TIEU_SUC", "accumulation": "QUE_TIEU_SUC", "patience": "QUE_TIEU_SUC",
            "gathering": "QUE_TIEU_SUC", "preparation": "QUE_TIEU_SUC",
            "kiềm_chế": "QUE_TIEU_SUC", "tích_lũy": "QUE_TIEU_SUC", "nhẫn_nại": "QUE_TIEU_SUC",
            "thu_thập": "QUE_TIEU_SUC", "chuẩn_bị": "QUE_TIEU_SUC",
            
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
            
            # Quẻ 12: Phế Hạp - Standstill
            "stagnation": "QUE_PHE_HAP", "obstruction": "QUE_PHE_HAP", "decline": "QUE_PHE_HAP",
            "separation": "QUE_PHE_HAP", "blockage": "QUE_PHE_HAP",
            "trì_trệ": "QUE_PHE_HAP", "cản_trở": "QUE_PHE_HAP", "suy_thoái": "QUE_PHE_HAP",
            "chia_ly": "QUE_PHE_HAP", "tắc_nghẽn": "QUE_PHE_HAP",
            
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
            "modesty": "QUE_KHIEM", "humility": "QUE_KHIEM", "simplicity": "QUE_KHIEM",
            "balance": "QUE_KHIEM", "virtue": "QUE_KHIEM",
            "khiêm_tốn": "QUE_KHIEM", "khiêm_nhường": "QUE_KHIEM", "giản_dị": "QUE_KHIEM",
            "cân_bằng": "QUE_KHIEM", "đức_hạnh": "QUE_KHIEM",
            
            # Quẻ 16: Dự - Enthusiasm
            "enthusiasm": "QUE_DU", "inspiration": "QUE_DU", "music": "QUE_DU",
            "celebration": "QUE_DU", "joy": "QUE_DU",
            "nhiệt_tình": "QUE_DU", "cảm_hứng": "QUE_DU", "âm_nhạc": "QUE_DU",
            "kỷ_niệm": "QUE_DU", "vui_vẻ": "QUE_DU",
            
            # Quẻ 17: Tùy - Following
            "following": "QUE_TUY", "adaptation": "QUE_TUY", "flexibility": "QUE_TUY",
            "compliance": "QUE_TUY", "responsive": "QUE_TUY",
            "theo_dõi": "QUE_TUY", "thích_nghi": "QUE_TUY", "linh_hoạt": "QUE_TUY",
            "tuân_thủ": "QUE_TUY", "đáp_ứng": "QUE_TUY",
            
            # Quẻ 18: Cổ - Work on Decay
            "decay": "QUE_CO", "corruption": "QUE_CO", "repair": "QUE_CO",
            "renovation": "QUE_CO", "healing": "QUE_CO",
            "hư_hỏng": "QUE_CO", "tham_nhũng": "QUE_CO", "sửa_chữa": "QUE_CO",
            "cải_tạo": "QUE_CO", "chữa_lành": "QUE_CO",
            
            # Quẻ 19: Lâm - Approach
            "approach": "QUE_LAM", "leadership": "QUE_LAM", "supervision": "QUE_LAM",
            "guidance": "QUE_LAM", "care": "QUE_LAM",
            "tiếp_cận": "QUE_LAM", "lãnh_đạo": "QUE_LAM", "giám_sát": "QUE_LAM",
            "hướng_dẫn": "QUE_LAM", "chăm_sóc": "QUE_LAM",
            
            # Quẻ 20: Quán - Contemplation
            "contemplation": "QUE_QUAN", "observation": "QUE_QUAN", "meditation": "QUE_QUAN",
            "insight": "QUE_QUAN", "reflection": "QUE_QUAN",
            "chiêm_ngưỡng": "QUE_QUAN", "quan_sát": "QUE_QUAN", "thiền_định": "QUE_QUAN",
            "sáng_suốt": "QUE_QUAN", "suy_ngẫm": "QUE_QUAN",
            
            # Quẻ 21: Phế Hạp - Biting Through
            "justice": "QUE_PHE_HAP", "punishment": "QUE_PHE_HAP", "decision": "QUE_PHE_HAP",
            "breakthrough": "QUE_PHE_HAP", "resolution": "QUE_PHE_HAP",
            "công_lý": "QUE_PHE_HAP", "trừng_phạt": "QUE_PHE_HAP", "quyết_định": "QUE_PHE_HAP",
            "đột_phá": "QUE_PHE_HAP", "giải_quyết": "QUE_PHE_HAP",
            
            # Quẻ 22: Bí - Grace (Quẻ 22 là QUE_BI_2 theo danh sách)
            "beauty": "QUE_BI_2", "grace": "QUE_BI_2", "elegance": "QUE_BI_2",
            "refinement": "QUE_BI_2", "culture": "QUE_BI_2",
            "vẻ_đẹp": "QUE_BI_2", "duyên_dáng": "QUE_BI_2", "tao_nhã": "QUE_BI_2",
            "tinh_tế": "QUE_BI_2", "văn_hóa": "QUE_BI_2",
            
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
            
            # Quẻ 25: Vô Vọng - Innocence
            "innocence": "QUE_VO_VONG", "spontaneity": "QUE_VO_VONG", "natural": "QUE_VO_VONG",
            "sincerity": "QUE_VO_VONG", "authenticity": "QUE_VO_VONG",
            "ngây_thơ": "QUE_VO_VONG", "tự_phát": "QUE_VO_VONG", "tự_nhiên": "QUE_VO_VONG",
            "chân_thành": "QUE_VO_VONG", "thật_thà": "QUE_VO_VONG",
            
            # Quẻ 26: Đại Súc - Great Taming
            "restraint": "QUE_DAI_SUC", "accumulation": "QUE_DAI_SUC", "strength": "QUE_DAI_SUC",
            "control": "QUE_DAI_SUC", "discipline": "QUE_DAI_SUC",
            "kiềm_chế": "QUE_DAI_SUC", "tích_lũy": "QUE_DAI_SUC", "sức_mạnh": "QUE_DAI_SUC",
            "kiểm_soát": "QUE_DAI_SUC", "kỷ_luật": "QUE_DAI_SUC",
            
            # Quẻ 27: Di - Nourishment
            "nourishment": "QUE_DI", "nutrition": "QUE_DI", "feeding": "QUE_DI",
            "sustenance": "QUE_DI", "care": "QUE_DI",
            "nuôi_dưỡng": "QUE_DI", "dinh_dưỡng": "QUE_DI", "cho_ăn": "QUE_DI",
            "duy_trì": "QUE_DI", "chăm_sóc": "QUE_DI",
            
            # Quẻ 28: Đại Quá - Great Exceeding
            "excess": "QUE_DAI_QUA", "burden": "QUE_DAI_QUA", "overload": "QUE_DAI_QUA",
            "critical": "QUE_DAI_QUA", "extreme": "QUE_DAI_QUA",
            "thừa_thãi": "QUE_DAI_QUA", "gánh_nặng": "QUE_DAI_QUA", "quá_tải": "QUE_DAI_QUA",
            "quan_trọng": "QUE_DAI_QUA", "cực_đoan": "QUE_DAI_QUA",
            
            # Quẻ 29: Tập Khảm - Water/Abyss
            "danger": "QUE_TAP_KHAM", "difficulty": "QUE_TAP_KHAM", "water": "QUE_TAP_KHAM",
            "flowing": "QUE_TAP_KHAM", "persistence": "QUE_TAP_KHAM",
            "nguy_hiểm": "QUE_TAP_KHAM", "khó_khăn": "QUE_TAP_KHAM", "nước": "QUE_TAP_KHAM",
            "chảy": "QUE_TAP_KHAM", "kiên_trì": "QUE_TAP_KHAM",
            
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
            "retreat": "QUE_DON", "withdrawal": "QUE_DON", "strategic": "QUE_DON",
            "yielding": "QUE_DON", "timing": "QUE_DON",
            "rút_lui": "QUE_DON", "rút_về": "QUE_DON", "chiến_lược": "QUE_DON",
            "nhường_bộ": "QUE_DON", "thời_điểm": "QUE_DON",
            
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
            
            # Quẻ 39: Giản - Obstruction (cần xác nhận tên chính xác)
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
            
            # Quẻ 43: Quải - Breakthrough
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
            "gathering": "QUE_TUY", "collection": "QUE_TUY", "assembly": "QUE_TUY",
            "unity": "QUE_TUY", "concentration": "QUE_TUY",
            "tập_hợp": "QUE_TUY", "sưu_tầm": "QUE_TUY", "hội_họp": "QUE_TUY",
            "đoàn_kết": "QUE_TUY", "tập_trung": "QUE_TUY",
            
            # Quẻ 46: Thăng - Pushing Upward
            "ascending": "QUE_THANG", "growth": "QUE_THANG", "promotion": "QUE_THANG",
            "rising": "QUE_THANG", "development": "QUE_THANG",
            "thăng_tiến": "QUE_THANG", "tăng_trưởng": "QUE_THANG", "thăng_chức": "QUE_THANG",
            "dâng_cao": "QUE_THANG", "phát_triển": "QUE_THANG",
            
            # Quẻ 47: Khốn - Oppression (cần xác nhận có trong danh sách không)
            # Tạm thời bỏ qua vì không có trong danh sách bạn cung cấp
            
            # Quẻ 48: Tỉnh - The Well
            "well": "QUE_TINH", "source": "QUE_TINH", "nourishment": "QUE_TINH",
            "community": "QUE_TINH", "renewal": "QUE_TINH",
            "giếng": "QUE_TINH", "nguồn": "QUE_TINH", "nuôi_dưỡng": "QUE_TINH",
            "cộng_đồng": "QUE_TINH", "đổi_mới": "QUE_TINH", "gốc": "QUE_TINH",
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
            "văn_hóa": "QUE_DINH", "tinh_tế": "QUE_DINH",
            
            # Quẻ 51: Chấn - Thunder
            "thunder": "QUE_CHAN", "shock": "QUE_CHAN", "arousing": "QUE_CHAN",
            "movement": "QUE_CHAN", "awakening": "QUE_CHAN",
            "sấm": "QUE_CHAN", "chấn_động": "QUE_CHAN", "khởi_động": "QUE_CHAN",
            "chuyển_động": "QUE_CHAN", "thức_tỉnh": "QUE_CHAN", "đánh_thức": "QUE_CHAN",
            "kích_thích": "QUE_CHAN", "khơi_gợi": "QUE_CHAN", "động_lực": "QUE_CHAN",
            "kích_hoạt": "QUE_CHAN", "kích_động": "QUE_CHAN", "khơi_dậy": "QUE_CHAN",
            "bừng_tỉnh": "QUE_CHAN", "sốc": "QUE_CHAN",
            
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
            "hôn_ước": "QUE_QUI_MUOI", "hôn_lễ": "QUE_QUI_MUOI", "lễ_cưới": "QUE_QUI_MUOI",
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
            "êm_ái": "QUE_TON_2", "êm_dịu": "QUE_TON_2", "mềm_mỏng": "QUE_TON_2", "uyển_chuyển": "QUE_TON_2",
            
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
            "exceeding": "QUE_TIEU_QUA", "small": "QUE_TIEU_QUA", "detail": "QUE_TIEU_QUA",
            "caution": "QUE_TIEU_QUA", "humility": "QUE_TIEU_QUA",
            "vượt_quá": "QUE_TIEU_QUA", "nhỏ": "QUE_TIEU_QUA", "chi_tiết": "QUE_TIEU_QUA",
            "thận_trọng": "QUE_TIEU_QUA", "khiêm_tốn": "QUE_TIEU_QUA",
            
            # Quẻ 63: Ký Tế - After Completion
            "completion": "QUE_KY_TE", "accomplished": "QUE_KY_TE", "finished": "QUE_KY_TE",
            "success": "QUE_KY_TE", "fulfillment": "QUE_KY_TE",
            "hoàn_thành": "QUE_KY_TE", "đạt_được": "QUE_KY_TE", "kết_thúc": "QUE_KY_TE",
            "thành_công": "QUE_KY_TE", "thỏa_mãn": "QUE_KY_TE",
            
            # Quẻ 64: Vị Tế - Before Completion
            "incomplete": "QUE_VI_TE", "unfinished": "QUE_VI_TE", "transition": "QUE_VI_TE",
            "potential": "QUE_VI_TE", "preparation": "QUE_VI_TE",
            "chưa_hoàn_thành": "QUE_VI_TE", "chưa_xong": "QUE_VI_TE", "chuyển_tiếp": "QUE_VI_TE",
            "tiềm_năng": "QUE_VI_TE", "chuẩn_bị": "QUE_VI_TE", "chưa_sẵn_sàng": "QUE_VI_TE",
            "chưa_hoàn_tất": "QUE_VI_TE", "chưa_hoàn_mĩ": "QUE_VI_TE", "chưa_hoàn_hảo": "QUE_VI_TE",
            "chưa_hoàn_thiện": "QUE_VI_TE"
        }
        self._concept_keys = list(self.concept_mapping.keys())

    # ------------------------------------------------------------------
    async def process(self, state: ProcessingState) -> ProcessingState:  # noqa: C901
        query: str = state.expanded_query or state.query
        query_type = state.query_type

        # 🎯 NEW: PRIORITY 1 - Hexagram từ casting result
        if state.hexagram_info and state.hexagram_info.get("name"):
            cast_hexagram_name = state.hexagram_info.get("name")
            
            # Map hexagram name to code
            hexagram_code = self._map_hexagram_name_to_code(cast_hexagram_name)
            if hexagram_code:
                docs = await self._hexagram_docs(hexagram_code)
                if docs:
                    state.retrieved_docs = docs
                    state.reasoning_chain.append(f"PRIORITY: Cast hexagram {cast_hexagram_name} → {hexagram_code}")
                    return state

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
    
    def _map_hexagram_name_to_code(self, hexagram_name: str) -> Optional[str]:
        """Map hexagram name to database code"""
        
        # Direct mapping cho 64 quẻ
        name_to_code_mapping = {
            "Kiền": "QUE_KIEN", "Khôn": "QUE_KHON", "Truân": "QUE_TRUAN", "Mông": "QUE_MONG",
            "Nhu": "QUE_NHU", "Tụng": "QUE_TUNG", "Sư": "QUE_SU", "Tỷ": "QUE_TY",
            "Tiểu Súc": "QUE_TIEU_SUC", "Lý": "QUE_LY", "Thái": "QUE_THAI", "Phế Hạp": "QUE_PHE_HAP",
            "Đồng Nhân": "QUE_DONG_NHAN", "Đại Hữu": "QUE_DAI_HUU", "Khiêm": "QUE_KHIEM", "Dự": "QUE_DU",
            "Tùy": "QUE_TUY", "Cổ": "QUE_CO", "Lâm": "QUE_LAM", "Quán": "QUE_QUAN",
            "Thích Hạc": "QUE_PHE_HAP", "Bí": "QUE_BI_2", "Bác": "QUE_BAC", "Phục": "QUE_PHUC",
            "Vô Vọng": "QUE_VO_VONG", "Đại Súc": "QUE_DAI_SUC", "Di": "QUE_DI", "Đại Quá": "QUE_DAI_QUA",
            "Khảm": "QUE_TAP_KHAM", "Ly": "QUE_LY_2", "Hàm": "QUE_HAM", "Hằng": "QUE_HANG",
            "Độn": "QUE_DON", "Đại Tráng": "QUE_DAI_TRANG", "Tấn": "QUE_TAN", "Minh Di": "QUE_MINH_DI",
            "Gia Nhân": "QUE_GIA_NHAN", "Khuê": "QUE_KHUE", "Giản": "QUE_GIAN", "Giải": "QUE_GIAI",
            "Tổn": "QUE_TON", "Ích": "QUE_ICH", "Quái": "QUE_QUAI", "Cấu": "QUE_CAU",
            "Tụy": "QUE_TUY", "Thăng": "QUE_THANG", "Khốn": "QUE_KHON", "Tỉnh": "QUE_TINH",
            "Cách": "QUE_CACH", "Đỉnh": "QUE_DINH", "Chấn": "QUE_CHAN", "Cấn": "QUE_CAN",
            "Tiệm": "QUE_TIEM", "Quy Muội": "QUE_QUI_MUOI", "Phong": "QUE_PHONG", "Lữ": "QUE_LU",
            "Tốn": "QUE_TON_2", "Đoài": "QUE_DOAI", "Hoán": "QUE_HOAN", "Tiết": "QUE_TIET",
            "Trung Phu": "QUE_TRUNG_PHU", "Tiểu Quá": "QUE_TIEU_QUA", "Ký Tế": "QUE_KY_TE",
            "Vị Tế": "QUE_VI_TE"  # KEY: Quẻ có vấn đề
        }
        
        return name_to_code_mapping.get(hexagram_name)

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
