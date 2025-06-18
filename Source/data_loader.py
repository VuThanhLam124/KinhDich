import json
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
from underthesea import word_tokenize
from tqdm import tqdm

from config import (
    MONGO_URI, DB_NAME, COLLECTION,
    EMBED_MODEL, CACHE_DIR,
    CHUNKS_DATA_DIR, BATCH_SIZE
)

class KinhDichDataLoader:
    """Pipeline ETL cho dữ liệu Kinh Dịch vào MongoDB"""

    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.collection = self.client[DB_NAME][COLLECTION]
        self.embedder = SentenceTransformer(EMBED_MODEL, cache_folder=CACHE_DIR)

    def extract_text_from_chunk(self, chunk: Dict[str, Any]) -> str:
        """
        Ghép các phần của chunk thành chuỗi text với label rõ ràng:
          - quẻ
          - lời kinh
          - dịch âm
          - dịch nghĩa
          - truyện của Trình Di
          - bản nghĩa của Chu Hy
          - lời bàn của tiên nho
        """
        parts: List[str] = []
        que = chunk.get("que") or chunk.get("hexagram")
        if que:
            parts.append(f"quẻ: {que}")
        if chunk.get("lời_kinh"):
            parts.append(f"lời kinh: {chunk['lời_kinh']}")
        if chunk.get("dịch_âm"):
            parts.append(f"dịch âm: {chunk['dịch_âm']}")
        if chunk.get("dịch_nghĩa"):
            parts.append(f"dịch nghĩa: {chunk['dịch_nghĩa']}")
        if chunk.get("truyện_của_Trình_Di"):
            parts.append(f"truyện của Trình Di: {chunk['truyện_của_Trình_Di']}")
        if chunk.get("bản_nghĩa_của_Chu_Hy"):
            parts.append(f"bản nghĩa của Chu Hy: {chunk['bản_nghĩa_của_Chu_Hy']}")
        if chunk.get("lời_bàn_của_tiên_nho"):
            parts.append(f"lời bàn của tiên nho: {chunk['lời_bàn_của_tiên_nho']}")

        # Fallback: any additional string fields
        skip_keys = {
            "que", "lời_kinh", "dịch_âm", "dịch_nghĩa",
            "truyện_của_Trình_Di", "bản_nghĩa_của_Chu_Hy",
            "lời_bàn_của_tiên_nho", "chunk_id", "hexagram",
            "content_type", "notes"
        }
        for key, value in chunk.items():
            if key not in skip_keys and isinstance(value, str):
                parts.append(f"{key}: {value}")

        return "\n\n".join(parts)

    def process_chunks_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Đọc file chunks.json, trích text, tokenize, embedding và build document dict"""
        raw = json.loads(file_path.read_text(encoding='utf-8'))
        docs: List[Dict[str, Any]] = []
        for item in raw:
            text = self.extract_text_from_chunk(item)
            if not text.strip():
                continue
            # Tokenize
            tokenized = word_tokenize(text, format="text")
            # Embed
            emb = self.embedder.encode([tokenized])[0].tolist()
            docs.append({
                "_id": item["chunk_id"],
                "text": text,
                "tokenized_text": tokenized,
                "embedding": emb,
                "hexagram": item.get("hexagram"),
                "que": item.get("que"),
                "content_type": item.get("content_type"),
                "original_chunk": item
            })
        return docs

    def load_all_data(self) -> None:
        """Load toàn bộ dữ liệu từ directory vào MongoDB và in danh sách quẻ đã xử lý cùng mã tương ứng"""
        # Drop old collection
        self.collection.drop()

        # Read and process all chunk files
        all_docs: List[Dict[str, Any]] = []
        for root, _, files in os.walk(CHUNKS_DATA_DIR):
            for fname in files:
                if fname.endswith('.json') and 'chunks' in fname:
                    fp = Path(root) / fname
                    all_docs.extend(self.process_chunks_file(fp))

        # Deduplicate by _id to avoid duplicate key errors
        unique_docs = {doc["_id"]: doc for doc in all_docs}.values()
        docs_list = list(unique_docs)

        # Insert in batches
        for i in tqdm(range(0, len(docs_list), BATCH_SIZE), desc="Inserting docs"):
            batch = docs_list[i : i + BATCH_SIZE]
            self.collection.insert_many(batch)

        # Create indexes
        self.collection.create_index("hexagram")
        self.collection.create_index("content_type")

        # Print processed que - hexagram pairs
        processed_pairs: List[Tuple[str, str]] = sorted({
            (doc["que"], doc["hexagram"])
            for doc in docs_list
            if doc.get("que") and doc.get("hexagram")
        })
        print("Danh sách quẻ đã xử lý:")
        for que_name, hex_code in processed_pairs:
            print(f"- {que_name} - {hex_code}")

if __name__ == "__main__":
    loader = KinhDichDataLoader()
    loader.load_all_data()
