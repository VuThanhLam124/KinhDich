import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union

# ──────────────────────────────────────────────────────────────
# Logging Configuration
# ──────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Notes Processing Functions
# ──────────────────────────────────────────────────────────────

def extract_notes_from_text(raw_text: str) -> Tuple[str, Dict]:
    """
    Tách phần 'Chú thích' từ cuối text và parse thành notes dict
    Returns: (cleaned_text, notes_dict)
    """
    
    # Tìm phần "Chú thích:" ở cuối text
    notes_pattern = r'\n\s*Chú\s+thích\s*:\s*(.+?)$'
    notes_match = re.search(notes_pattern, raw_text, flags=re.S | re.I)
    
    if not notes_match:
        return raw_text, {}
    
    # Tách text và notes
    notes_text = notes_match.group(1).strip()
    cleaned_text = raw_text[:notes_match.start()].strip()
    
    # Parse notes thành dict
    notes_dict = parse_notes_text(notes_text)
    
    logger.info(f" Đã tách {len(notes_dict)} chú thích từ main.txt")
    
    return cleaned_text, notes_dict

def parse_notes_text(notes_text: str) -> Dict[str, str]:
    """
    Parse text chú thích thành dict với format [số] nội dung
    """
    
    # Pattern để tách các chú thích: [số] nội dung
    pattern = r"\[(\d+)\]\s*([^\[]+)"
    notes_matches = re.findall(pattern, notes_text, flags=re.S)
    
    # Tạo dict với key là số và value là nội dung
    notes_dict = {}
    for num, text in notes_matches:
        # Làm sạch text
        clean_text = re.sub(r'\s+', ' ', text.strip())
        notes_dict[num] = clean_text
    
    return notes_dict

# ──────────────────────────────────────────────────────────────
# JSON File Loaders
# ──────────────────────────────────────────────────────────────

def load_multiple_json_objects(file_path: str) -> List[Dict]:
    """Load file chứa nhiều JSON objects (mỗi dòng một object)"""
    
    json_objects = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
            # Thử parse như một JSON array trước
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    return data
                else:
                    return [data]
            except json.JSONDecodeError:
                pass
            
            # Nếu không phải JSON array, thử parse từng dòng
            for line in content.split('\n'):
                line = line.strip()
                if line:
                    try:
                        obj = json.loads(line)
                        json_objects.append(obj)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Không thể parse JSON line: {line[:50]}... - {e}")
                        continue
                        
    except Exception as e:
        logger.error(f"Lỗi đọc file JSON {file_path}: {e}")
        return []
    
    return json_objects

def load_json_file(file_path: str) -> List[Dict]:
    """Load file JSON tùy theo format"""
    
    if not os.path.exists(file_path):
        logger.warning(f"File không tồn tại: {file_path}")
        return []
    
    # Thử load như JSON thông thường trước
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            else:
                return [data]
    except json.JSONDecodeError:
        # Nếu không được, thử load multiple objects
        return load_multiple_json_objects(file_path)

# ──────────────────────────────────────────────────────────────
# Chunking Strategies
# ──────────────────────────────────────────────────────────────

class JSONChunkingStrategy:
    """Chunking strategy cho các file JSON - giữ nguyên format đã được lọc tay"""
    
    def __init__(self, folder_name: str):
        self.folder_name = folder_name
        
    def chunk_content(self, json_data: List[Dict], notes: Dict = None) -> List[Dict]:
        """Chunk dữ liệu JSON - mỗi entry JSON thành một chunk riêng biệt"""
        
        chunks = []
        section_code = self.folder_name.upper()
        
        for idx, item in enumerate(json_data, 1):
            # Kiểm tra kiểu dữ liệu
            if not isinstance(item, dict):
                logger.warning(f"Item {idx} không phải dictionary, bỏ qua: {type(item)}")
                continue
            
            # Tạo chunk theo format gốc - KHÔNG chia nhỏ content
            chunk = {
                "chunk_id": f"{section_code}_{idx:03d}",
                "section": section_code,
                "content_type": "curated_content",  # Đánh dấu là content đã được lọc tay
                "title": item.get("Title", item.get("title", "")),
                "content": item.get("content", ""),
                "reference": item.get("reference", item.get("ref", "")),
                "notes": notes or {}
            }
            
            chunks.append(chunk)
        
        return chunks

class HexagramChunkingStrategy:
    """Chunking strategy cho các quẻ với enhanced notes support và fixed regex"""
    
    def __init__(self, folder_name: str):
        self.folder_name = folder_name
        
    def chunk_content(self, raw_text: str, notes: Dict) -> List[Dict]:
        return self._parse_hexagram_text(raw_text, self._extract_hexagram_code(), notes)
    
    def _extract_hexagram_code(self) -> str:
        """Trích xuất mã quẻ từ tên folder"""
        if "/" in self.folder_name:
            return self.folder_name.split("/")[-1].upper()
        return self.folder_name.upper()
    
    def _parse_loi_kinh_block(self, block: str) -> Dict[str, Optional[str]]:
        """Tách 1 khối LỜI KINH thành các trường cụ thể với regex đã được fix"""
        
        fields = {
            "lời_kinh": None,
            "dịch_âm": None,
            "dịch_nghĩa": None,
            "truyện_của_Trình_Di": None,
            "bản_nghĩa_của_Chu_Hy": None,
            "lời_bàn_của_tiên_nho": None,
        }

        # Tách phần chính và phần GIẢI NGHĨA
        giai_nghia_match = re.search(r'\bGIẢI\s+NGHĨA\b(.*?)$', block, flags=re.S | re.I)
        main_part = re.sub(r'\bGIẢI\s+NGHĨA\b.*$', '', block, flags=re.S | re.I).strip()
        giai_nghia_part = giai_nghia_match.group(1).strip() if giai_nghia_match else ""

        # FIXED: Patterns cho phần chính - dịch_nghĩa giờ dừng đúng chỗ
        main_patterns = {
            "lời_kinh": r"LỜI\s+KINH\s*(.*?)\s*(?=Dịch âm\.|$)",
            "dịch_âm": r"Dịch âm\.\s*[–-]\s*(.*?)\s*(?=Dịch nghĩa\.|$)",
            # FIX: Thêm lookahead để dừng trước các phần khác
            "dịch_nghĩa": r"Dịch nghĩa\.\s*[–-]\s*(.*?)(?=Truyện của Trình Di\.|Bản nghĩa của Chu Hy\.|Lời bàn của Tiên Nho\.|GIẢI\s+NGHĨA|$)",
        }

        # Patterns cho phần GIẢI NGHĨA và cả phần chính (trong trường hợp không có GIẢI NGHĨA)
        all_patterns = {
            "truyện_của_Trình_Di": r"Truyện của Trình Di\.\s*[–-]\s*(.*?)\s*(?=Bản nghĩa của Chu Hy\.|Lời bàn của Tiên Nho\.|$)",
            "bản_nghĩa_của_Chu_Hy": r"Bản nghĩa của Chu Hy\.\s*[–-]\s*(.*?)\s*(?=Lời bàn của Tiên Nho\.|$)",
            "lời_bàn_của_tiên_nho": r"Lời bàn của Tiên Nho\.\s*[–-]\s*(.*?)\s*$",
        }

        # Xử lý phần chính
        for field, pattern in main_patterns.items():
            match = re.search(pattern, main_part, flags=re.S | re.I)
            if match:
                text = re.sub(r"\s+", " ", match.group(1)).strip()
                if field == "lời_kinh":
                    text = re.sub(r"(?i)^\s*LỜI\s+KINH\s*", "", text)
                fields[field] = text

        # Xử lý các pattern khác trong cả main_part và giai_nghia_part
        search_text = main_part + "\n" + giai_nghia_part
        for field, pattern in all_patterns.items():
            match = re.search(pattern, search_text, flags=re.S | re.I)
            if match:
                text = re.sub(r"\s+", " ", match.group(1)).strip()
                fields[field] = text

        return fields

    def _parse_hexagram_text(self, raw_text: str, hexagram: str, notes: Dict) -> List[Dict]:
        """Parse text của quẻ thành chunks với notes support"""
        
        chunks = []
        
        # Tìm biểu đồ quẻ
        que_match = re.search(r"^\s*[☰☱☲☳☴☵☶☷].+$", raw_text, flags=re.M)
        que_str = que_match.group(0).strip() if que_match else None
        
        # Tách phần mở đầu
        parts = re.split(r"\bLỜI\s+KINH", raw_text, maxsplit=1, flags=re.I)
        preface = parts[0]
        rest = ("LỜI KINH" + parts[1]) if len(parts) > 1 else ""
        
        # Chunk đầu tiên (mở đầu)
        chunks.append({
            "chunk_id": f"{hexagram}_001",
            "hexagram": hexagram,
            "que": que_str,
            "content_type": "preface",
            "lời_kinh": None,
            "dịch_âm": None,
            "dịch_nghĩa": None,
            "truyện_của_Trình_Di": None,
            "bản_nghĩa_của_Chu_Hy": None,
            "lời_bàn_của_tiên_nho": None,
            "notes": notes  # Thêm notes từ main.txt
        })
        
        # Tách từng khối LỜI KINH
        blocks = re.split(r"\n(?=LỜI\s+KINH)", rest, flags=re.I)
        idx = 2
        
        for block in blocks:
            if not block.strip():
                continue
                
            fields = self._parse_loi_kinh_block(block)
            
            chunks.append({
                "chunk_id": f"{hexagram}_{idx:03d}",
                "hexagram": hexagram,
                "que": None,
                "content_type": "interpretation",
                "notes": notes,  # Thêm notes từ main.txt
                **fields
            })
            idx += 1
        
        return chunks

class TextChunkingStrategy:
    """Chunking strategy cho text content thông thường - ngắn gọn"""
    
    def __init__(self, folder_name: str):
        self.folder_name = folder_name
        
    def chunk_content(self, raw_text: str, notes: Dict) -> List[Dict]:
        """Chunk text content thông thường theo sections ngắn gọn"""
        
        chunks = []
        section_code = self.folder_name.upper()
        
        # Thử chia theo tiêu đề chính trước
        sections = self._split_by_main_headers(raw_text)
        
        if not sections:
            # Nếu không có tiêu đề, chia theo đoạn văn nhưng giữ ngắn gọn
            sections = self._split_by_paragraphs(raw_text)
        
        for idx, section in enumerate(sections, 1):
            if not section.strip():
                continue
                
            # Tách title và content nếu có
            lines = section.strip().split('\n', 1)
            title = lines[0].strip() if lines else ""
            content = lines[1].strip() if len(lines) > 1 else section.strip()
            
            chunk = {
                "chunk_id": f"{section_code}_{idx:03d}",
                "section": section_code,
                "content_type": "text_section",
                "title": title if len(title) < 100 else "",  # Chỉ lấy title ngắn
                "content": content,
                "notes": notes
            }
            
            chunks.append(chunk)
        
        return chunks
    
    def _split_by_main_headers(self, text: str) -> List[str]:
        """Chia theo tiêu đề chính (ALL CAPS hoặc tiêu đề rõ ràng)"""
        
        # Tìm các tiêu đề chính
        header_pattern = r'\n(?=[A-ZÀ-Ỹ\s]{10,}(?:\n|$))'
        sections = re.split(header_pattern, text)
        
        # Lọc bỏ sections quá ngắn
        filtered_sections = []
        for section in sections:
            if len(section.strip()) > 50:  # Chỉ giữ sections có nội dung đủ dài
                filtered_sections.append(section)
        
        return filtered_sections if len(filtered_sections) > 1 else []
    
    def _split_by_paragraphs(self, text: str) -> List[str]:
        """Chia theo đoạn văn, nhóm các đoạn liên quan"""
        
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        # Nhóm paragraphs thành chunks có ý nghĩa
        sections = []
        current_section = ""
        
        for para in paragraphs:
            # Nếu paragraph hiện tại trông như tiêu đề mới (ngắn, viết hoa)
            if (len(para) < 100 and 
                (para.isupper() or para.istitle()) and 
                current_section):
                
                sections.append(current_section)
                current_section = para
            else:
                current_section += "\n\n" + para if current_section else para
                
                # Giới hạn độ dài section để giữ ngắn gọn
                if len(current_section) > 800:
                    sections.append(current_section)
                    current_section = ""
        
        # Thêm section cuối
        if current_section:
            sections.append(current_section)
        
        return sections

# ──────────────────────────────────────────────────────────────
# Strategy Factory
# ──────────────────────────────────────────────────────────────

class ChunkingStrategyFactory:
    """Factory để tạo strategy chunking phù hợp"""
    
    @staticmethod
    def create_strategy(folder_name: str, data_type: str = "text"):
        """Tạo strategy phù hợp dựa trên tên folder và loại dữ liệu"""
        
        folder_upper = folder_name.upper()
        
        # Nếu là JSON data - sử dụng JSON strategy (giữ nguyên format)
        if data_type == "json":
            return JSONChunkingStrategy(folder_name)
        
        # Quẻ Kinh Dịch (chỉ cho text data) - sử dụng Hexagram strategy phức tạp
        elif ("CHU_DICH_THUONG_KINH" in folder_upper or "CHU_DICH_HA_KINH" in folder_upper) and data_type == "text":
            return HexagramChunkingStrategy(folder_name)
        
        # Text data khác - sử dụng Text strategy đơn giản
        else:
            return TextChunkingStrategy(folder_name)

# ──────────────────────────────────────────────────────────────
# Processing Functions
# ──────────────────────────────────────────────────────────────

def load_folder_data(folder_path: str) -> Tuple[Optional[str], Dict]:
    """Load dữ liệu từ folder và tự động tách notes từ main.txt"""
    
    main_txt_path = os.path.join(folder_path, "main.txt")
    notes_json_path = os.path.join(folder_path, "notes.json")
    
    if not os.path.isfile(main_txt_path):
        logger.warning(f"Không tìm thấy main.txt trong {folder_path}")
        return None, {}
    
    try:
        with open(main_txt_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
        
        # Tách notes từ main.txt trước
        cleaned_text, extracted_notes = extract_notes_from_text(raw_text)
        
        # Load notes.json nếu có
        json_notes = {}
        if os.path.isfile(notes_json_path):
            with open(notes_json_path, "r", encoding="utf-8") as f:
                json_notes = json.load(f)
        
        # Merge notes: ưu tiên notes từ main.txt, sau đó notes.json
        final_notes = {**json_notes, **extracted_notes}
        
        return cleaned_text, final_notes
        
    except Exception as e:
        logger.error(f"Lỗi đọc dữ liệu từ {folder_path}: {e}")
        return None, {}

def chunk_single_folder(folder_path: str) -> Optional[List[Dict]]:
    """Chunk dữ liệu của một folder (text format) với notes support"""
    
    folder_name = os.path.basename(folder_path)
    parent_name = os.path.basename(os.path.dirname(folder_path))
    
    # Tạo tên đầy đủ nếu cần
    if parent_name in ["CHU_DICH_THUONG_KINH", "CHU_DICH_HA_KINH"]:
        full_name = f"{parent_name}/{folder_name}"
    else:
        full_name = folder_name
    
    raw_text, notes = load_folder_data(folder_path)
    if raw_text is None:
        return None
    
    # Tạo strategy cho TEXT data
    strategy = ChunkingStrategyFactory.create_strategy(full_name, "text")
    chunks = strategy.chunk_content(raw_text, notes)
    
    return chunks

def process_json_file(json_file_path: str, output_dir: str) -> Optional[List[Dict]]:
    """Xử lý một file JSON và tạo chunks"""
    
    file_name = os.path.splitext(os.path.basename(json_file_path))[0]
    logger.info(f"→ Chunking JSON file: {file_name}")
    
    # Load JSON data
    json_data = load_json_file(json_file_path)
    
    if not json_data:
        logger.warning(f"   ✗ Không có dữ liệu trong file: {json_file_path}")
        return None
    
    # Tạo strategy cho JSON data
    strategy = ChunkingStrategyFactory.create_strategy(file_name, "json")
    chunks = strategy.chunk_content(json_data)
    
    # Tạo output folder nếu chưa có
    folder_output_dir = os.path.join(output_dir, file_name)
    os.makedirs(folder_output_dir, exist_ok=True)
    
    # Lưu chunks.json
    output_path = os.path.join(folder_output_dir, "chunks.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    
    logger.info(f"   ✓ Đã tạo {len(chunks)} chunks → {output_path}")
    return chunks

def process_all_data(data_dir: str = "Kinh_Dich_Data", json_dir: str = "JSON_FILE") -> None:
    """Xử lý chunking cho tất cả dữ liệu với enhanced notes support"""
    
    total_chunks = 0
    processed_items = 0
    
    # 1. Xử lý các folder text
    if os.path.isdir(data_dir):
        logger.info("=== XỬ LÝ DỮ LIỆU TEXT (với Notes Support & Fixed Regex) ===")
        
        for root, dirs, files in os.walk(data_dir):
            if "main.txt" in files:
                relative_path = os.path.relpath(root, data_dir)
                logger.info(f"→ Chunking folder: {relative_path}")
                
                chunks = chunk_single_folder(root)
                
                if chunks:
                    output_path = os.path.join(root, "chunks.json")
                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(chunks, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"   ✓ Đã tạo {len(chunks)} chunks → {output_path}")
                    total_chunks += len(chunks)
                    processed_items += 1
                else:
                    logger.warning(f"   ✗ Không thể chunk folder: {relative_path}")
    
    # 2. Xử lý các file JSON
    if os.path.isdir(json_dir):
        logger.info("=== XỬ LÝ DỮ LIỆU JSON ===")
        
        json_output_dir = os.path.join(data_dir, "JSON_PROCESSED")
        os.makedirs(json_output_dir, exist_ok=True)
        
        for filename in os.listdir(json_dir):
            if filename.lower().endswith('.json'):
                json_file_path = os.path.join(json_dir, filename)
                chunks = process_json_file(json_file_path, json_output_dir)
                
                if chunks:
                    total_chunks += len(chunks)
                    processed_items += 1
    
    logger.info(f"HOÀN THÀNH TẤT CẢ! Đã xử lý {processed_items} items, tạo {total_chunks} chunks.")

# ──────────────────────────────────────────────────────────────
# Main Execution
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    data_dir = "Kinh_Dich_Data"  
    json_dir = "JSON_FILE"       
    
    process_all_data(data_dir, json_dir)
