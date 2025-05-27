import pdfplumber
import os
import json
import re
import logging
import unicodedata
from pathlib import Path
from tqdm import tqdm
from pdf2image import convert_from_path
from PIL import Image
from pymongo import MongoClient
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings

# Kiểm tra và import spacy (tùy chọn)
try:
    import spacy
    nlp = spacy.load("vi_core_news_sm", disable=["parser", "lemmatizer"])
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logging.warning("spacy không được cài đặt. Sẽ sử dụng regex cho trích xuất thực thể.")

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Danh sách mục lục
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

# Hàm trích xuất văn bản từ phạm vi trang
def extract_text_from_pages(pdf, start_page, end_page):
    """Trích xuất văn bản từ các trang PDF trong phạm vi chỉ định."""
    text = ""
    try:
        for page_num in tqdm(range(start_page, end_page + 1), desc=f"Trích xuất văn bản trang {start_page}-{end_page}"):
            page = pdf.pages[page_num - 1]
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        logger.error(f"Lỗi khi trích xuất văn bản trang {start_page}-{end_page}: {e}")
        raise

# Hàm trích xuất và nén hình ảnh
def extract_images_from_pages(pdf_path, start_page, end_page, output_dir):
    """Trích xuất và nén hình ảnh từ các trang PDF."""
    try:
        images_dir = os.path.join(output_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        image_metadata = []
        
        images = convert_from_path(pdf_path, first_page=start_page, last_page=end_page, dpi=200)
        for i, image in enumerate(tqdm(images, desc=f"Trích xuất hình ảnh trang {start_page}-{end_page}")):
            page_num = start_page + i
            image_path = os.path.join(images_dir, f"page_{page_num}.png")
            image.save(image_path, "PNG", optimize=True, quality=85)
            image_metadata.append({
                "page": page_num,
                "path": image_path,
                "description": f"Hình ảnh từ trang {page_num} trong phần ĐỒ THUYẾT CỦA CHU HY"
            })
        
        metadata_path = os.path.join(images_dir, "images.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(image_metadata, f, ensure_ascii=False, indent=4)
        logger.info(f"Đã lưu siêu dữ liệu hình ảnh vào {metadata_path}")
        return images_dir
    except Exception as e:
        logger.error(f"Lỗi khi trích xuất hình ảnh trang {start_page}-{end_page}: {e}")
        return None

# Hàm làm sạch và chuẩn hóa văn bản
def clean_and_normalize_text(text):
    """Chuẩn hóa Unicode NFC, loại bỏ control chars, chuẩn hóa dấu câu."""
    # Chuẩn hóa Unicode NFC
    text = unicodedata.normalize('NFC', text)
    # Loại bỏ control characters
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
    # Chuẩn hóa dấu câu: smart quotes → ASCII
    text = text.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    # Loại bỏ khoảng trắng thừa
    text = re.sub(r'\s+', ' ', text).strip()
    # Loại bỏ quảng cáo
    text = text.replace("Ebook miễn phí tại : www.Sachvui.Com", "")
    text = text.replace("Ebook thực hiện dành cho những bạn chưa có điều kiện mua sách.", "")
    text = text.replace("Nếu bạn có khả năng hãy mua sách gốc để ủng hộ tác giả, người dịch và Nhà Xuất Bản", "")
    # Sửa lỗi OCR
    text = text.replace("đ Tolu", "được").replace("kernelng", "không")
    return text

# Hàm tách ghi chú và nội dung chính
def extract_notes(text):
    """Tách ghi chú dạng [n] và nội dung chính."""
    note_pattern = r"\[\d+\]\s+.*?(?=\n|$)"
    notes = re.findall(note_pattern, text, re.MULTILINE)
    note_dict = {}
    for note in notes:
        match = re.match(r"\[(\d+)\]\s+(.*)", note)
        if match:
            num, note_text = match.groups()
            note_dict[num] = note_text.strip()
    main_text = re.sub(note_pattern, "", text)
    return main_text.strip(), note_dict

# Hàm tiền xử lý dữ liệu từ PDF
def preprocess_data(pdf_path, output_dir="Kinh_Dich_Data"):
    """Tiền xử lý dữ liệu từ PDF theo mục lục."""
    if not os.path.exists(pdf_path):
        logger.error(f"Tệp PDF không tồn tại: {pdf_path}")
        return
    
    logger.info(f"Bắt đầu tiền xử lý dữ liệu từ {pdf_path}")
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for section_name, start_page, end_page in sections:
                section_folder = os.path.join(output_dir, section_name)
                os.makedirs(section_folder, exist_ok=True)
                
                logger.info(f"Xử lý văn bản cho phần: {section_name} (trang {start_page}-{end_page})")
                text = extract_text_from_pages(pdf, start_page, end_page)
                text = clean_and_normalize_text(text)
                
                main_text, notes = extract_notes(text)
                
                main_path = os.path.join(section_folder, "main.txt")
                with open(main_path, "w", encoding="utf-8") as f:
                    f.write(main_text)
                logger.info(f"Đã lưu nội dung chính vào {main_path}")
                
                notes_path = os.path.join(section_folder, "notes.json")
                with open(notes_path, "w", encoding="utf-8") as f:
                    json.dump(notes, f, ensure_ascii=False, indent=4)
                logger.info(f"Đã lưu ghi chú vào {notes_path}")
                
                if section_name == "DO_THUYET_CUA_CHU_HY":
                    logger.info(f"Trích xuất hình ảnh cho phần: {section_name}")
                    images_dir = extract_images_from_pages(pdf_path, start_page, end_page, section_folder)
                    if images_dir:
                        logger.info(f"Hình ảnh đã được lưu vào {images_dir}")
                    else:
                        logger.warning(f"Không trích xuất được hình ảnh cho phần: {section_name}")
        
        logger.info("Tiền xử lý dữ liệu hoàn tất!")
    except Exception as e:
        logger.error(f"Lỗi trong quá trình tiền xử lý: {e}")

# Hàm đọc dữ liệu gốc
def load_raw_data(data_dir="Kinh_Dich_Data"):
    """Đọc main.txt và notes.json, tổ chức theo quẻ."""
    raw_data = {}
    for root, _, files in os.walk(data_dir):
        section_name = Path(root).relative_to(data_dir).as_posix()
        if "main.txt" not in files:
            continue
        
        # Lấy tên quẻ từ section_name
        hexagram = section_name.split("/")[-1] if "/" in section_name else section_name
        hexagram = hexagram.upper()
        
        # Đọc main.txt
        main_path = os.path.join(root, "main.txt")
        with open(main_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
        
        # Đọc notes.json
        notes = {}
        notes_path = os.path.join(root, "notes.json")
        if os.path.exists(notes_path):
            with open(notes_path, "r", encoding="utf-8") as f:
                notes = json.load(f)
        
        raw_data[hexagram] = {
            "hexagram": hexagram,
            "raw_text": raw_text,
            "notes": notes
        }
    
    logger.info(f"Đã đọc {len(raw_data)} tài liệu gốc")
    return raw_data

# Hàm chia câu và tạo chunk
def split_and_chunk_text(text, hexagram, chunk_size=200, chunk_overlap=20):
    """Chia văn bản thành câu và gom thành chunk 200–300 từ."""
    sentences = re.split(r'[.;？！]\s*', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    chunks = []
    current_chunk = []
    current_word_count = 0
    chunk_id = 1
    
    for sentence in sentences:
        word_count = len(sentence.split())
        if current_word_count + word_count > chunk_size and current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append({
                "chunk_id": f"{hexagram}_{chunk_id:03d}",
                "text": chunk_text
            })
            current_chunk = current_chunk[-2:] if len(current_chunk) >= 2 else current_chunk
            current_word_count = sum(len(s.split()) for s in current_chunk)
            chunk_id += 1
        
        current_chunk.append(sentence)
        current_word_count += word_count
    
    if current_chunk:
        chunk_text = " ".join(current_chunk)
        chunks.append({
            "chunk_id": f"{hexagram}_{chunk_id:03d}",
            "text": chunk_text
        })
    
    return chunks

# Hàm trích xuất thực thể
def extract_entities(text):
    """Trích xuất tên quẻ, hào, khái niệm như Âm/Dương."""
    entities = []
    # Regex cho tên quẻ, hào, khái niệm
    hexagram_pattern = r"Quẻ\s+[A-Z][a-zA-Z\s]+"
    hao_pattern = r"Hào\s+(Sáu|Chín)\s+(Đầu|Hai|Ba|Bốn|Năm|Trên)"
    concept_pattern = r"(Âm|Dương)"
    
    # Trích xuất bằng regex
    entities.extend(re.findall(hexagram_pattern, text))
    entities.extend([f"Hào {x[0]} {x[1]}" for x in re.findall(hao_pattern, text, re.IGNORECASE)])
    entities.extend(re.findall(concept_pattern, text))
    
    # Trích xuất bằng spaCy nếu có
    if SPACY_AVAILABLE:
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ in ["PERSON", "ORG", "LOC"]:
                entities.append(ent.text)
    
    entities = list(set(entities))
    return entities

# Hàm ánh xạ ghi chú
def map_notes(text, notes):
    """Ánh xạ [n] trong text với nội dung ghi chú."""
    note_links = {}
    note_ids = re.findall(r"\[(\d+)\]", text)
    for note_id in note_ids:
        if note_id in notes:
            note_links[note_id] = notes[note_id]
    return note_links

# Hàm lưu vào MongoDB
def save_to_mongodb(chunks, mongo_uri, db_name="kinhdich_kb", collection_name="chunks"):
    """Lưu chunks vào MongoDB."""
    try:
        client = MongoClient(mongo_uri)
        db = client[db_name]
        collection = db[collection_name]
        
        collection.delete_many({})
        logger.info("Đã xóa collection cũ")
        
        embeddings_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        total_chunks = 0
        
        for chunk_data in tqdm(chunks, desc="Lưu chunks vào MongoDB"):
            chunk_id = chunk_data["chunk_id"]
            hexagram = chunk_data["hexagram"]
            text = chunk_data["text"]
            notes = chunk_data["notes"]
            section = chunk_data["section"]
            page_range = chunk_data["source_page_range"]
            
            embedding = embeddings_model.embed_query(text)
            entities = extract_entities(text)
            note_links = map_notes(text, notes)
            
            mongo_doc = {
                "_id": chunk_id,
                "hexagram": hexagram,
                "text": text,
                "embedding": embedding,
                "entities": entities,
                "note_links": note_links,
                "section": section,
                "source_page_range": page_range
            }
            collection.insert_one(mongo_doc)
            total_chunks += 1
        
        logger.info(f"Hoàn tất lưu {total_chunks} chunks vào MongoDB")
        client.close()
    except Exception as e:
        logger.error(f"Lỗi khi lưu vào MongoDB: {e}")
        client.close()
        raise

# Hàm chính
def main():
    # đoạn mongo_uri hãy thay thế bằng chuỗi kết nối của bạn
    pdf_path = "nhasachmienphi-kinh-dich-tron-bo.pdf"
    data_dir = "Kinh_Dich_Data"
    mongo_uri = "mongodb+srv://doibuonjqk:doibuonjqk123@cluster0.jvlxnix.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    db_name = "kinhdich_kb"
    collection_name = "chunks"
    
    if not os.path.exists(data_dir):
        logger.info("Thư mục Kinh_Dich_Data chưa tồn tại, bắt đầu tiền xử lý")
        preprocess_data(pdf_path, data_dir)
    
    try:
        logger.info("Đọc dữ liệu gốc từ thư mục Kinh_Dich_Data")
        raw_data = load_raw_data(data_dir)
        
        logger.info("Tạo chunks và trích xuất thông tin")
        all_chunks = []
        for hexagram, data in raw_data.items():
            raw_text = data["raw_text"]
            notes = data["notes"]
            
            section_info = next((s for s in sections if s[0].split("/")[-1].upper() == hexagram or s[0].upper() == hexagram), None)
            section = section_info[0] if section_info else hexagram
            page_range = [section_info[1], section_info[2]] if section_info else [0, 0]
            
            chunks = split_and_chunk_text(raw_text, hexagram)
            for chunk in chunks:
                chunk["hexagram"] = hexagram
                chunk["notes"] = notes
                chunk["section"] = section
                chunk["source_page_range"] = page_range
                all_chunks.append(chunk)
        
        logger.info("Lưu dữ liệu vào MongoDB")
        save_to_mongodb(all_chunks, mongo_uri, db_name, collection_name)
        
        logger.info("Kiểm tra dữ liệu trong MongoDB")
        client = MongoClient(mongo_uri)
        db = client[db_name]
        collection = db[collection_name]
        sample_doc = collection.find_one()
        if sample_doc:
            logger.info("Mẫu tài liệu trong MongoDB:")
            logger.info(json.dumps(sample_doc, ensure_ascii=False, indent=4))
        else:
            logger.warning("Không tìm thấy tài liệu trong collection")
        client.close()
        
    except KeyboardInterrupt:
        logger.warning("Chương trình bị gián đoạn bởi người dùng (Ctrl+C)")
    except Exception as e:
        logger.error(f"Lỗi trong quá trình thực thi: {e}")

if __name__ == "__main__":
    main()