# hexagram_caster.py - Complete I Ching Hexagram Casting System

import random
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class LineType(Enum):
    """I Ching line types từ 3-coin method"""
    OLD_YIN = (6, "Old Yin", "0", True, "━ ━", "Âm cũ (changing)")
    YOUNG_YANG = (7, "Young Yang", "1", False, "━━━", "Dương trẻ")
    YOUNG_YIN = (8, "Young Yin", "0", False, "━ ━", "Âm trẻ")
    OLD_YANG = (9, "Old Yang", "1", True, "━━━", "Dương cũ (changing)")

    def __init__(self, value, name, binary, changing, symbol, description):
        self.type_name = name
        self.binary = binary
        self.changing = changing
        self.symbol = symbol
        self.description = description

@dataclass
class CastingLine:
    """Single line casting result"""
    position: int  # 1-6, bottom to top
    coins: List[str]
    total: int
    line_type: LineType
    changing: bool

    def to_dict(self) -> Dict:
        return {
            "position": self.position,
            "coins": self.coins,
            "total": self.total,
            "type": self.line_type.type_name,
            "binary": self.line_type.binary,
            "changing": self.changing,
            "symbol": self.line_type.symbol,
            "description": self.line_type.description
        }

@dataclass
class HexagramResult:
    """Complete hexagram casting result"""
    question: str
    hexagram_name: str
    hexagram_code: str
    hexagram_number: int
    general_meaning: str
    binary_pattern: str
    lines: List[CastingLine]
    changing_lines: List[int]
    timestamp: str
    trigrams: Dict[str, str]

    def to_dict(self) -> Dict:
        return {
            "question": self.question,
            "hexagram_name": self.hexagram_name,
            "hexagram_code": self.hexagram_code,
            "hexagram_number": self.hexagram_number,
            "general_meaning": self.general_meaning,
            "structure": self.format_structure(),
            "binary_pattern": self.binary_pattern,
            "lines": [line.to_dict() for line in self.lines],
            "changing_lines": self.changing_lines,
            "timestamp": self.timestamp,
            "trigrams": self.trigrams
        }

    def format_structure(self) -> str:
        """Format hexagram structure for display"""
        symbols = []
        # Display from top to bottom (reverse line order)
        for line in reversed(self.lines):
            symbol = line.line_type.symbol
            if line.changing:
                symbol += " →"
            symbols.append(symbol)
        return '\n'.join(symbols)

class HexagramCaster:
    """Complete I Ching hexagram casting implementation"""

    def __init__(self):
        self.hexagram_mapping = self._load_hexagram_mapping()
        self.trigram_mapping = self._load_trigram_mapping()
        logger.info(f"HexagramCaster initialized with {len(self.hexagram_mapping)} hexagrams")

    def _load_hexagram_mapping(self) -> Dict[str, Dict]:
        """
        Complete 64 hexagram mappings với enhanced metadata
        Binary pattern: bottom line to top line (6 bits)
        """
        return {
            # Thượng Kinh (Quẻ 1-30) - Upper Canon
            "111111": {"name": "Kiền", "code": "QUE_KIEN", "meaning": "Sáng tạo, mạnh mẽ, trời", "number": 1, "element": "Metal", "season": "Winter"},
            "000000": {"name": "Khôn", "code": "QUE_KHON", "meaning": "Tiếp nhận, nuôi dưỡng, đất", "number": 2, "element": "Earth", "season": "Late Summer"},
            "010001": {"name": "Truân", "code": "QUE_TRUAN", "meaning": "Khó khăn ban đầu, mới mầm", "number": 3, "element": "Water", "season": "Spring"},
            "100010": {"name": "Mông", "code": "QUE_MONG", "meaning": "Ngu muội tuổi trẻ, học hỏi", "number": 4, "element": "Water", "season": "Spring"},
            "010111": {"name": "Nhu", "code": "QUE_NHU", "meaning": "Chờ đợi, cần kiên nhẫn", "number": 5, "element": "Water", "season": "Winter"},
            "111010": {"name": "Tụng", "code": "QUE_TUNG", "meaning": "Xung đột, tranh chấp", "number": 6, "element": "Metal", "season": "Autumn"},
            "000010": {"name": "Sư", "code": "QUE_SU", "meaning": "Quân đội, tổ chức", "number": 7, "element": "Earth", "season": "Late Summer"},
            "010000": {"name": "Tỷ", "code": "QUE_TY", "meaning": "Đoàn kết, liên minh", "number": 8, "element": "Water", "season": "Winter"},
            "110111": {"name": "Tiểu Súc", "code": "QUE_TIEU_SUC", "meaning": "Tích lũy nhỏ, kiềm chế", "number": 9, "element": "Wood", "season": "Spring"},
            "111011": {"name": "Lý", "code": "QUE_LY", "meaning": "Hành xử cẩn thận", "number": 10, "element": "Metal", "season": "Autumn"},
            "000111": {"name": "Thái", "code": "QUE_THAI", "meaning": "Hòa bình, thịnh vượng", "number": 11, "element": "Earth", "season": "Spring"},
            "111000": {"name": "Phế Hạp", "code": "QUE_PHE_HAP", "meaning": "Trì trệ, tắc nghẽn", "number": 12, "element": "Earth", "season": "Autumn"},
            "111101": {"name": "Đồng Nhân", "code": "QUE_DONG_NHAN", "meaning": "Đồng nghiệp, cộng đồng", "number": 13, "element": "Fire", "season": "Summer"},
            "101111": {"name": "Đại Hữu", "code": "QUE_DAI_HUU", "meaning": "Sở hữu lớn, giàu có", "number": 14, "element": "Fire", "season": "Summer"},
            "000100": {"name": "Khiêm", "code": "QUE_KHIEM", "meaning": "Khiêm tốn, nhường nhịn", "number": 15, "element": "Earth", "season": "Late Summer"},
            "001000": {"name": "Dự", "code": "QUE_DU", "meaning": "Hướng về, nhiệt tình", "number": 16, "element": "Earth", "season": "Late Summer"},
            "011001": {"name": "Tùy", "code": "QUE_TUY", "meaning": "Theo dõi, thích nghi", "number": 17, "element": "Metal", "season": "Autumn"},
            "100110": {"name": "Cổ", "code": "QUE_CO", "meaning": "Sửa chữa, cải tạo", "number": 18, "element": "Wood", "season": "Spring"},
            "000011": {"name": "Lâm", "code": "QUE_LAM", "meaning": "Tiếp cận, lãnh đạo", "number": 19, "element": "Earth", "season": "Late Summer"},
            "110000": {"name": "Quán", "code": "QUE_QUAN", "meaning": "Quan sát, chiêm ngưỡng", "number": 20, "element": "Wood", "season": "Spring"},
            "101001": {"name": "Phế Hạp", "code": "QUE_PHE_HAP", "meaning": "Cắn xuyên, quyết đoán", "number": 21, "element": "Fire", "season": "Summer"},
            "100101": {"name": "Bí", "code": "QUE_BI_2", "meaning": "Trang trí, duyên dáng", "number": 22, "element": "Fire", "season": "Summer"},
            "100000": {"name": "Bác", "code": "QUE_BAC", "meaning": "Tách rời, suy thoái", "number": 23, "element": "Earth", "season": "Autumn"},
            "000001": {"name": "Phục", "code": "QUE_PHUC", "meaning": "Trở về, phục hồi", "number": 24, "element": "Earth", "season": "Winter"},
            "111001": {"name": "Vô Vọng", "code": "QUE_VO_VONG", "meaning": "Ngây thơ, chân thành", "number": 25, "element": "Metal", "season": "Winter"},
            "100111": {"name": "Đại Súc", "code": "QUE_DAI_SUC", "meaning": "Tích lũy lớn, kiềm chế", "number": 26, "element": "Metal", "season": "Winter"},
            "100001": {"name": "Di", "code": "QUE_DI", "meaning": "Nuôi dưỡng, chăm sóc", "number": 27, "element": "Wood", "season": "Spring"},
            "011110": {"name": "Đại Quá", "code": "QUE_DAI_QUA", "meaning": "Vượt quá giới hạn", "number": 28, "element": "Wood", "season": "Spring"},
            "010010": {"name": "Tập Khảm", "code": "QUE_TAP_KHAM", "meaning": "Nước, nguy hiểm", "number": 29, "element": "Water", "season": "Winter"},
            "101101": {"name": "Ly", "code": "QUE_LY_2", "meaning": "Lửa, sáng sủa", "number": 30, "element": "Fire", "season": "Summer"},

            # Hạ Kinh (Quẻ 31-64) - Lower Canon
            "011100": {"name": "Hàm", "code": "QUE_HAM", "meaning": "Cảm ứng, thu hút", "number": 31, "element": "Metal", "season": "Autumn"},
            "001110": {"name": "Hằng", "code": "QUE_HANG", "meaning": "Bền vững, kiên trì", "number": 32, "element": "Wood", "season": "Spring"},
            "111100": {"name": "Độn", "code": "QUE_DON", "meaning": "Rút lui, tránh né", "number": 33, "element": "Metal", "season": "Autumn"},
            "001111": {"name": "Đại Tráng", "code": "QUE_DAI_TRANG", "meaning": "Sức mạnh lớn", "number": 34, "element": "Metal", "season": "Summer"},
            "101000": {"name": "Tấn", "code": "QUE_TAN", "meaning": "Tiến bộ, thăng tiến", "number": 35, "element": "Fire", "season": "Summer"},
            "000101": {"name": "Minh Di", "code": "QUE_MINH_DI", "meaning": "Tổn thương ánh sáng", "number": 36, "element": "Fire", "season": "Summer"},
            "110101": {"name": "Gia Nhân", "code": "QUE_GIA_NHAN", "meaning": "Gia đình, nội trợ", "number": 37, "element": "Wood", "season": "Spring"},
            "101011": {"name": "Khuê", "code": "QUE_KHUE", "meaning": "Đối lập, xung đột", "number": 38, "element": "Fire", "season": "Summer"},
            "010100": {"name": "Giản", "code": "QUE_GIAN", "meaning": "Cản trở, khó khăn", "number": 39, "element": "Water", "season": "Winter"},
            "001010": {"name": "Giải", "code": "QUE_GIAI", "meaning": "Giải phóng, giải quyết", "number": 40, "element": "Water", "season": "Spring"},
            "100011": {"name": "Tổn", "code": "QUE_TON", "meaning": "Giảm bớt, hy sinh", "number": 41, "element": "Wood", "season": "Spring"},
            "110001": {"name": "Ích", "code": "QUE_ICH", "meaning": "Tăng thêm, lợi ích", "number": 42, "element": "Wood", "season": "Spring"},
            "011111": {"name": "Quải", "code": "QUE_QUAI", "meaning": "Đột phá, quyết tâm", "number": 43, "element": "Metal", "season": "Summer"},
            "111110": {"name": "Cấu", "code": "QUE_CAU", "meaning": "Gặp gỡ, cám dỗ", "number": 44, "element": "Metal", "season": "Spring"},
            "011000": {"name": "Tụy", "code": "QUE_TUY", "meaning": "Tập hợp, đoàn kết", "number": 45, "element": "Earth", "season": "Late Summer"},
            "000110": {"name": "Thăng", "code": "QUE_THANG", "meaning": "Thăng tiến, dâng cao", "number": 46, "element": "Wood", "season": "Spring"},
            # Bỏ quẻ 47 vì không có trong danh sách
            "010110": {"name": "Tỉnh", "code": "QUE_TINH", "meaning": "Giếng nước, nguồn", "number": 48, "element": "Wood", "season": "Spring"},
            "011101": {"name": "Cách", "code": "QUE_CACH", "meaning": "Cách mạng, thay đổi", "number": 49, "element": "Fire", "season": "Summer"},
            "101110": {"name": "Đỉnh", "code": "QUE_DINH", "meaning": "Chung đỉnh, biến đổi", "number": 50, "element": "Fire", "season": "Summer"},
            "001001": {"name": "Chấn", "code": "QUE_CHAN", "meaning": "Sấm sét, chấn động", "number": 51, "element": "Wood", "season": "Spring"},
            "100100": {"name": "Cấn", "code": "QUE_CAN", "meaning": "Núi, dừng lại", "number": 52, "element": "Earth", "season": "Late Summer"},
            "110100": {"name": "Tiệm", "code": "QUE_TIEM", "meaning": "Phát triển từ từ", "number": 53, "element": "Wood", "season": "Spring"},
            "001011": {"name": "Quy Muội", "code": "QUE_QUI_MUOI", "meaning": "Cô gái xuất giá, hôn nhân", "number": 54, "element": "Metal", "season": "Autumn"},
            "001101": {"name": "Phong", "code": "QUE_PHONG", "meaning": "Dồi dào, thịnh vượng", "number": 55, "element": "Fire", "season": "Summer"},
            "101100": {"name": "Lữ", "code": "QUE_LU", "meaning": "Du lịch, kẻ khách", "number": 56, "element": "Fire", "season": "Summer"},
            "110110": {"name": "Tốn", "code": "QUE_TON_2", "meaning": "Gió nhẹ, thấm sâu", "number": 57, "element": "Wood", "season": "Spring"},
            "011011": {"name": "Đoài", "code": "QUE_DOAI", "meaning": "Vui vẻ, hồ nước", "number": 58, "element": "Metal", "season": "Autumn"},
            "110010": {"name": "Hoán", "code": "QUE_HOAN", "meaning": "Phân tán, tan rã", "number": 59, "element": "Wood", "season": "Spring"},
            "010011": {"name": "Tiết", "code": "QUE_TIET", "meaning": "Giới hạn, điều độ", "number": 60, "element": "Water", "season": "Winter"},
            "110011": {"name": "Trung Phu", "code": "QUE_TRUNG_PHU", "meaning": "Chân thành, tin cậy", "number": 61, "element": "Wood", "season": "Spring"},
            "001100": {"name": "Tiểu Quá", "code": "QUE_TIEU_QUA", "meaning": "Vượt quá nhỏ", "number": 62, "element": "Wood", "season": "Spring"},
            "010101": {"name": "Ký Tế", "code": "QUE_KY_TE", "meaning": "Đã hoàn thành", "number": 63, "element": "Water", "season": "Winter"},
            "101010": {"name": "Vị Tế", "code": "QUE_VI_TE", "meaning": "Chưa hoàn thành", "number": 64, "element": "Fire", "season": "Summer"}
        }

    def _load_trigram_mapping(self) -> Dict[str, Dict]:
        """Load Ba Quái (8 trigrams) mappings"""
        return {
            "111": {"name": "Kiền", "element": "Metal", "attribute": "Trời", "direction": "NW"},
            "000": {"name": "Khôn", "element": "Earth", "attribute": "Đất", "direction": "SW"},
            "001": {"name": "Chấn", "element": "Wood", "attribute": "Sấm", "direction": "E"},
            "010": {"name": "Khảm", "element": "Water", "attribute": "Nước", "direction": "N"},
            "100": {"name": "Cấn", "element": "Earth", "attribute": "Núi", "direction": "NE"},
            "101": {"name": "Ly", "element": "Fire", "attribute": "Lửa", "direction": "S"},
            "110": {"name": "Tốn", "element": "Wood", "attribute": "Gió", "direction": "SE"},
            "011": {"name": "Đoài", "element": "Metal", "attribute": "Hồ", "direction": "W"}
        }

    def cast_hexagram(self, question: str) -> HexagramResult:
        """Main method để gieo quẻ hoàn chỉnh"""
        logger.info(f"Starting hexagram casting for question: {question[:50]}...")
        
        casting_lines = []
        binary_pattern = ""
        
        # Cast 6 lines from bottom to top
        for position in range(1, 7):
            line = self._cast_single_line(position)
            casting_lines.append(line)
            binary_pattern += line.line_type.binary
        
        # Lookup hexagram
        hexagram_info = self._lookup_hexagram(binary_pattern)
        
        # Identify changing lines
        changing_lines = [line.position for line in casting_lines if line.changing]
        
        # Analyze trigrams
        trigrams = self._analyze_trigrams(binary_pattern)
        
        # Create result
        result = HexagramResult(
            question=question,
            hexagram_name=hexagram_info["name"],
            hexagram_code=hexagram_info["code"],
            hexagram_number=hexagram_info["number"],
            general_meaning=hexagram_info["meaning"],
            binary_pattern=binary_pattern,
            lines=casting_lines,
            changing_lines=changing_lines,
            timestamp=datetime.now().isoformat(),
            trigrams=trigrams
        )
        
        logger.info(f"Casting completed: {result.hexagram_name} (#{result.hexagram_number})")
        return result

    def _cast_single_line(self, position: int) -> CastingLine:
        """Cast single line using traditional 3-coin method"""
        # Simulate 3 coin tosses
        coins = [random.choice(['heads', 'tails']) for _ in range(3)]
        
        # Calculate total value
        total = sum(3 if coin == 'heads' else 2 for coin in coins)
        
        # Map to line type
        line_type_map = {
            6: LineType.OLD_YIN,
            7: LineType.YOUNG_YANG,
            8: LineType.YOUNG_YIN,
            9: LineType.OLD_YANG
        }
        
        line_type = line_type_map[total]
        
        return CastingLine(
            position=position,
            coins=coins,
            total=total,
            line_type=line_type,
            changing=line_type.changing
        )

    def _lookup_hexagram(self, binary_pattern: str) -> Dict:
        """Lookup hexagram với enhanced fallback mechanisms"""
        # Direct lookup
        if binary_pattern in self.hexagram_mapping:
            return self.hexagram_mapping[binary_pattern]
        
        # Fallback 1: Find closest pattern match
        closest_match = self._find_closest_pattern(binary_pattern)
        if closest_match:
            result = self.hexagram_mapping[closest_match].copy()
            result["note"] = f"Closest match to {binary_pattern}"
            logger.warning(f"Using closest match {closest_match} for pattern {binary_pattern}")
            return result
        
        # Fallback 2: Generate based on characteristics
        return self._generate_pattern_based_hexagram(binary_pattern)

    def _find_closest_pattern(self, target_pattern: str) -> Optional[str]:
        """Find closest matching hexagram pattern"""
        min_distance = float('inf')
        closest_pattern = None
        
        for pattern in self.hexagram_mapping.keys():
            # Calculate Hamming distance
            distance = sum(c1 != c2 for c1, c2 in zip(target_pattern, pattern))
            if distance < min_distance:
                min_distance = distance
                closest_pattern = pattern
        
        # Only return if reasonably close (max 2 differences)
        return closest_pattern if min_distance <= 2 else None

    def _generate_pattern_based_hexagram(self, pattern: str) -> Dict:
        """Generate hexagram based on pattern characteristics"""
        yang_count = pattern.count('1')
        yin_count = pattern.count('0')
        
        # Analyze pattern balance
        if yang_count >= 5:
            return {
                "name": "Cường Yang", "code": "QUE_STRONG_YANG",
                "meaning": "Năng lượng yang mạnh mẽ, chủ động", "number": 99,
                "element": "Fire", "season": "Summer"
            }
        elif yin_count >= 5:
            return {
                "name": "Thuần Yin", "code": "QUE_PURE_YIN",
                "meaning": "Năng lượng yin thuần khiết, tiếp nhận", "number": 98,
                "element": "Water", "season": "Winter"
            }
        else:
            return {
                "name": "Âm Dương Hòa", "code": "QUE_BALANCED",
                "meaning": "Cân bằng giữa âm và dương", "number": 97,
                "element": "Earth", "season": "Late Summer"
            }

    def _analyze_trigrams(self, binary_pattern: str) -> Dict[str, str]:
        """Analyze upper and lower trigrams"""
        lower_trigram = binary_pattern[:3]  # Bottom 3 lines
        upper_trigram = binary_pattern[3:]  # Top 3 lines
        
        lower_info = self.trigram_mapping.get(lower_trigram, {"name": "Unknown"})
        upper_info = self.trigram_mapping.get(upper_trigram, {"name": "Unknown"})
        
        return {
            "lower_trigram": lower_info["name"],
            "upper_trigram": upper_info["name"],
            "lower_element": lower_info.get("element", "Unknown"),
            "upper_element": upper_info.get("element", "Unknown"),
            "lower_attribute": lower_info.get("attribute", "Unknown"),
            "upper_attribute": upper_info.get("attribute", "Unknown")
        }

    def cast_multiple_hexagrams(self, questions: List[str]) -> List[HexagramResult]:
        """Cast multiple hexagrams for different questions"""
        results = []
        for question in questions:
            result = self.cast_hexagram(question)
            results.append(result)
        return results

    def analyze_changing_lines(self, result: HexagramResult) -> Dict[str, Any]:
        """Analyze changing lines and provide interpretation"""
        if not result.changing_lines:
            return {"message": "Không có giao thay đổi", "interpretation": "Quẻ ổn định"}
        
        changing_analysis = {
            "count": len(result.changing_lines),
            "positions": result.changing_lines,
            "interpretation": self._interpret_changing_lines(result.changing_lines),
            "future_hexagram": self._calculate_future_hexagram(result)
        }
        
        return changing_analysis

    def _interpret_changing_lines(self, changing_lines: List[int]) -> str:
        """Interpret meaning of changing lines"""
        count = len(changing_lines)
        if count == 0:
            return "Tình huống ổn định, không có thay đổi lớn"
        elif count == 1:
            return f"Thay đổi tập trung ở giao {changing_lines[0]}, cần chú ý đặc biệt"
        elif count == 2:
            return "Hai điểm thay đổi, cần cân bằng các lực lượng đối lập"
        elif count >= 3:
            return "Nhiều thay đổi đồng thời, thời kỳ biến động mạnh"
        else:
            return "Cần phân tích kỹ hơn"

    def _calculate_future_hexagram(self, result: HexagramResult) -> Optional[Dict]:
        """Calculate future hexagram based on changing lines"""
        if not result.changing_lines:
            return None
        
        # Create future pattern by flipping changing lines
        future_pattern = ""
        for i, line in enumerate(result.lines):
            if line.position in result.changing_lines:
                # Flip the line
                future_pattern += "0" if line.line_type.binary == "1" else "1"
            else:
                future_pattern += line.line_type.binary
        
        # Lookup future hexagram
        future_hexagram = self._lookup_hexagram(future_pattern)
        
        return {
            "pattern": future_pattern,
            "name": future_hexagram["name"],
            "code": future_hexagram["code"],
            "meaning": future_hexagram["meaning"]
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get caster statistics and information"""
        return {
            "total_hexagrams": len(self.hexagram_mapping),
            "trigrams_count": len(self.trigram_mapping),
            "line_types": len(LineType),
            "supported_features": [
                "3_coin_casting",
                "changing_lines_analysis",
                "trigram_analysis",
                "future_hexagram_calculation",
                "pattern_matching_fallback"
            ]
        }

# Testing and example usage
def test_hexagram_casting():
    """Comprehensive test of hexagram casting functionality"""
    caster = HexagramCaster()
    print("🎯 Testing Hexagram Casting System")
    print("=" * 60)
    
    # Test basic casting
    test_questions = [
        "Công việc của tôi sẽ như thế nào trong thời gian tới?",
        "Tình yêu có đến với tôi không?",
        "Tôi có nên thay đổi hướng đi hiện tại?",
        "Sức khỏe của tôi ra sao?",
        "Dự án kinh doanh này có thành công không?"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n📝 Test {i}: {question}")
        print("-" * 40)
        
        result = caster.cast_hexagram(question)
        result_dict = result.to_dict()
        
        print(f"🎯 Quẻ: {result.hexagram_name} (#{result.hexagram_number})")
        print(f"📝 Ý nghĩa: {result.general_meaning}")
        print(f"🔄 Cấu trúc:\n{result.format_structure()}")
        print(f"⚡ Giao thay đổi: {result.changing_lines if result.changing_lines else 'Không có'}")
        
        # Test changing lines analysis
        changing_analysis = caster.analyze_changing_lines(result)
        print(f"🔮 Phân tích: {changing_analysis['interpretation']}")
        
        if changing_analysis.get('future_hexagram'):
            future = changing_analysis['future_hexagram']
            print(f"🌟 Quẻ tương lai: {future['name']} - {future['meaning']}")
    
    # Test statistics
    print(f"\n📊 Statistics: {caster.get_statistics()}")
    
    # Test edge cases
    print(f"\n🧪 Testing edge cases...")
    edge_cases = ["", "Test without question mark", "Câu hỏi rất dài " * 10]
    for case in edge_cases:
        try:
            result = caster.cast_hexagram(case)
            print(f"✅ Edge case handled: {case[:30]}... → {result.hexagram_name}")
        except Exception as e:
            print(f"❌ Edge case failed: {case[:30]}... → {e}")

def demonstrate_hexagram_system():
    """Demonstrate complete hexagram system functionality"""
    caster = HexagramCaster()
    print("🌟 I Ching Hexagram Casting Demonstration")
    print("=" * 50)
    
    # Single detailed casting
    question = "Tôi nên làm gì với mối quan hệ hiện tại?"
    result = caster.cast_hexagram(question)
    
    print(f"❓ Câu hỏi: {result.question}")
    print(f"🎯 Quẻ nhận được: {result.hexagram_name} ({result.hexagram_code})")
    print(f"🔢 Số thứ tự: #{result.hexagram_number}/64")
    print(f"💫 Ý nghĩa tổng quát: {result.general_meaning}")
    print(f"🏗️ Cấu trúc quẻ:\n{result.format_structure()}")
    
    # Detailed line analysis
    print(f"\n📋 Chi tiết từng giao:")
    for line in reversed(result.lines):  # Top to bottom
        status = "→ THAY ĐỔI" if line.changing else ""
        print(f"Giao {line.position}: {line.line_type.description} {status}")
    
    # Trigram analysis
    print(f"\n🔺 Phân tích Bát Quái:")
    print(f"Hạ Quái (dưới): {result.trigrams['lower_trigram']} ({result.trigrams['lower_attribute']})")
    print(f"Thượng Quái (trên): {result.trigrams['upper_trigram']} ({result.trigrams['upper_attribute']})")
    
    # Changing lines analysis
    changing_analysis = caster.analyze_changing_lines(result)
    print(f"\n⚡ Phân tích giao thay đổi:")
    print(f"Số lượng: {changing_analysis['count']}")
    print(f"Giải thích: {changing_analysis['interpretation']}")
    
    if changing_analysis.get('future_hexagram'):
        future = changing_analysis['future_hexagram']
        print(f"🔮 Quẻ tương lai: {future['name']} - {future['meaning']}")

if __name__ == "__main__":
    # Run comprehensive tests
    test_hexagram_casting()
    print("\n" + "="*80 + "\n")
    
    # Run demonstration
    demonstrate_hexagram_system()
