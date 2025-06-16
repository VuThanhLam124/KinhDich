import json
import os
from typing import List, Dict, Any
from pathlib import Path
import logging
from tqdm import tqdm

from sentence_transformers import SentenceTransformer
from pymongo import MongoClient
from underthesea import word_tokenize

from config import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KinhDichDataLoader:
    """Tải và xử lý dữ liệu Kinh Dịch vào MongoDB với vector embeddings"""
    
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[DB_NAME]
        self.collection = self.db[COLLECTION]
        self.embedder = SentenceTransformer(EMBED_MODEL, cache_folder=CACHE_DIR)
        
    def extract_text_from_chunk(self, chunk: Dict) -> str:
        """Trích xuất text từ chunk để embedding"""
        content_type = chunk.get("content_type", "")
        
        if content_type in ["preface", "interpretation"]:
            return self._extract_hexagram_text(chunk)
        elif content_type == "curated_content":
            return self._extract_json_text(chunk)
        else:
            return self._extract_general_text(chunk)
    
    def _extract_hexagram_text(self, chunk: Dict) -> str:
        """Trích xuất text từ chunk quẻ"""
        parts = []
        
        if chunk.get("hexagram"):
            parts.append(f"Quẻ {chunk['hexagram']}")
        
        fields = ["lời_kinh", "dịch_âm", "dịch_nghĩa", 
                 "truyện_của_Trình_Di", "bản_nghĩa_của_Chu_Hy", "lời_bàn_của_tiên_nho"]
        
        for field in fields:
            if chunk.get(field):
                clean_text = chunk[field].strip()
                if clean_text:
                    parts.append(f"{field.replace('_', ' ').title()}: {clean_text}")
        
        # Thêm notes
        if chunk.get("notes"):
            notes_text = " ".join([f"Chú thích {k}: {v}" for k, v in chunk["notes"].items()])
            parts.append(notes_text)
        
        return " | ".join(parts)
    
    def _extract_json_text(self, chunk: Dict) -> str:
        """Trích xuất text từ chunk JSON"""
        parts = []
        
        if chunk.get("title"):
            parts.append(f"Tiêu đề: {chunk['title']}")
        
        if chunk.get("content"):
            parts.append(f"Nội dung: {chunk['content']}")
        
        if chunk.get("reference"):
            parts.append(f"Tham khảo: {chunk['reference']}")
        
        return " | ".join(parts)
    
    def _extract_general_text(self, chunk: Dict) -> str:
        """Trích xuất text từ chunk thông thường"""
        parts = []
        
        for key in ["title", "content", "section"]:
            if chunk.get(key):
                parts.append(str(chunk[key]))
        
        return " | ".join(parts)
    
    def create_vector_index(self):
        """Tạo vector search index trên MongoDB Atlas"""
        index_definition = {
            "fields": [{
                "type": "vector",
                "path": "embedding",
                "numDimensions": 768,  # vietnamese-sbert dimensions
                "similarity": "cosine"
            }]
        }
        
        try:
            # Lưu ý: Index phải được tạo qua Atlas UI hoặc Atlas CLI
            logger.info("Vector index cần được tạo thủ công qua MongoDB Atlas UI")
            logger.info(f"Index definition: {json.dumps(index_definition, indent=2)}")
        except Exception as e:
            logger.error(f"Lỗi tạo vector index: {e}")
    
    def process_chunks_file(self, file_path: str) -> List[Dict]:
        """Xử lý một file chunks.json"""
        with open(file_path, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        
        processed_chunks = []
        for chunk in chunks:
            # Trích xuất text để embedding
            text = self.extract_text_from_chunk(chunk)
            
            if not text.strip():
                continue
            
            # Tokenize Vietnamese text
            tokenized_text = word_tokenize(text, format="text")
            
            # Tạo embedding
            embedding = self.embedder.encode(tokenized_text).tolist()
            
            # Chuẩn bị document cho MongoDB
            doc = {
                "_id": chunk["chunk_id"],
                "text": text,
                "tokenized_text": tokenized_text,
                "embedding": embedding,
                "hexagram": chunk.get("hexagram"),
                "section": chunk.get("section"),
                "content_type": chunk.get("content_type"),
                "original_chunk": chunk
            }
            
            processed_chunks.append(doc)
        
        return processed_chunks
    
    def load_all_data(self, data_dir: str = "Kinh_Dich_Data"):
        """Tải tất cả dữ liệu từ chunks vào MongoDB"""
        logger.info("Bắt đầu tải dữ liệu vào MongoDB...")
        
        # Xóa collection cũ
        self.collection.drop()
        
        all_docs = []
        
        # Duyệt tất cả file chunks.json
        for root, dirs, files in os.walk(data_dir):
            if "chunks.json" in files:
                file_path = os.path.join(root, "chunks.json")
                logger.info(f"Xử lý: {file_path}")
                
                try:
                    docs = self.process_chunks_file(file_path)
                    all_docs.extend(docs)
                except Exception as e:
                    logger.error(f"Lỗi xử lý {file_path}: {e}")
        
        # Bulk insert
        if all_docs:
            logger.info(f"Đang chèn {len(all_docs)} documents vào MongoDB...")
            
            batch_size = 100
            for i in tqdm(range(0, len(all_docs), batch_size)):
                batch = all_docs[i:i+batch_size]
                try:
                    self.collection.insert_many(batch, ordered=False)
                except Exception as e:
                    logger.error(f"Lỗi insert batch {i}: {e}")
            
            logger.info(f"Hoàn thành! Đã tải {len(all_docs)} documents")
        
        # Tạo indexes
        self.collection.create_index("hexagram")
        self.collection.create_index("section")
        self.collection.create_index("content_type")
        
        logger.info("Data loading hoàn thành!")

if __name__ == "__main__":
    loader = KinhDichDataLoader()
    loader.load_all_data()
