#!/usr/bin/env python3
"""
Script debug MongoDB Atlas Vector Search cho Kinh Dịch
"""
import json
from pymongo import MongoClient
from config import MONGO_URI, DB_NAME, COLLECTION

def debug_mongodb_atlas():
    """Comprehensive debugging cho MongoDB Atlas Vector Search"""
    
    print("BẮT ĐẦU CHẨN ĐOÁN MONGODB ATLAS VECTOR SEARCH")
    print("=" * 60)
    
    try:
        # 1. Test connection
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION]
        
        print("1. MongoDB connection successful")
        
        # 2. Check collection existence và document count
        collections = db.list_collection_names()
        print(f"Available collections: {collections}")
        
        if COLLECTION not in collections:
            print(f"Collection '{COLLECTION}' không tồn tại!")
            return False
        
        doc_count = collection.count_documents({})
        print(f"Collection '{COLLECTION}' có {doc_count} documents")
        
        if doc_count == 0:
            print("Collection rỗng! Chạy data_loader.py trước")
            return False
        
        # 3. Check document structure
        sample_doc = collection.find_one({})
        print(f"Sample document structure:")
        for key in sample_doc.keys():
            if key == "embedding":
                print(f"  - {key}: array[{len(sample_doc[key])}] (type: {type(sample_doc[key][0])})")
            else:
                print(f"  - {key}: {type(sample_doc[key])}")
        
        # 4. Check embedding field
        if "embedding" not in sample_doc:
            print("Không tìm thấy field 'embedding'!")
            return False
        
        embedding = sample_doc["embedding"]
        if not isinstance(embedding, list):
            print(f"Field 'embedding' không phải là array! Type: {type(embedding)}")
            return False
        
        embedding_dim = len(embedding)
        print(f"Embedding dimensions: {embedding_dim}")
        
        # 5. Check embedding có documents
        docs_with_embeddings = collection.count_documents({"embedding": {"$exists": True}})
        print(f"Documents có embedding: {docs_with_embeddings}/{doc_count}")
        
        # 6. Test aggregation pipeline (cơ bản)
        print("\nTESTING AGGREGATION...")
        try:
            # Simple aggregation để test collection accessibility
            pipeline = [{"$limit": 1}]
            result = list(collection.aggregate(pipeline))
            print(f"Basic aggregation successful: {len(result)} results")
        except Exception as e:
            print(f"Basic aggregation failed: {e}")
            return False
        
        # 7. Test vector search
        print("\nTESTING VECTOR SEARCH...")
        
        # Lấy embedding từ document đầu tiên để test
        test_embedding = embedding  # Từ sample_doc
        
        # Vector search pipeline
        vector_pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",  # Tên index cần khớp với Atlas
                    "path": "embedding",
                    "queryVector": test_embedding,
                    "numCandidates": 100,
                    "limit": 5
                }
            },
            {
                "$addFields": {
                    "similarity_score": {"$meta": "vectorSearchScore"}
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "text": 1,
                    "similarity_score": 1
                }
            }
        ]
        
        try:
            vector_results = list(collection.aggregate(vector_pipeline))
            print(f"Vector search results: {len(vector_results)}")
            
            if len(vector_results) > 0:
                print("Vector search hoạt động!")
                for i, result in enumerate(vector_results[:2]):
                    score = result.get("similarity_score", "N/A")
                    print(f"  {i+1}. {result['_id']} (score: {score})")
            else:
                print("Vector search trả về 0 results - CHÍNH LÀ VẤN ĐỀ!")
                print("\nPOSSIBLE FIXES:")
                print("  1. Kiểm tra vector index name trong Atlas UI")
                print("  2. Đảm bảo index status = 'READY'")
                print("  3. Verify index path = 'embedding'")
                print("  4. Check index dimensions = 768")
                
        except Exception as e:
            print(f"Vector search error: {e}")
            print("\nLIKELY CAUSES:")
            print("  1. Vector search index chưa được tạo")
            print("  2. Index name không đúng ('vector_index')")
            print("  3. Atlas tier không support vector search")
            return False
        
        return True
        
    except Exception as e:
        print(f"MongoDB connection error: {e}")
        return False

def check_atlas_vector_index():
    """Hướng dẫn kiểm tra vector index trên Atlas UI"""
    
    print("\n" + "="*60)
    print("HƯỚNG DẪN KIỂM TRA VECTOR INDEX TRÊN ATLAS")
    print("="*60)
    
    print("""
1. Đăng nhập MongoDB Atlas: https://cloud.mongodb.com
2. Chọn cluster của bạn
3. Vào Database → Browse Collections
4. Chọn database 'kinhdich_kb' và collection 'chunks'
5. Tab "Search Indexes" → Kiểm tra:
   
   ✅ Index name: 'vector_index' (chính xác)
   ✅ Status: READY (không phải BUILDING)
   ✅ Type: Vector Search
   ✅ Definition:
   
   {
     "fields": [
       {
         "type": "vector",
         "path": "embedding",
         "numDimensions": 768,
         "similarity": "cosine"
       }
     ]
   }

6. Nếu index không tồn tại → Tạo mới
7. Nếu index đang BUILDING → Chờ build xong (3-10 phút)
8. Nếu có lỗi → Xóa và tạo lại
""")

def suggest_fixes():
    """Đề xuất các cách khắc phục"""
    
    print("\n" + "="*60)
    print("CÁC CÁCH KHẮC PHỤC PHỔ BIẾN")
    print("="*60)
    
    print("""
CÁCH 1: TẠO LẠI VECTOR INDEX
1. Xóa index cũ (nếu có) trên Atlas UI
2. Tạo index mới với config:
   - Name: vector_index
   - Field: embedding
   - Dimensions: 768
   - Similarity: cosine

CÁCH 2: KIỂM TRA DỮLIỆU
python debug_vector_search.py

CÁCH 3: LOAD LẠI DỮ LIỆU
python data_loader.py

CÁCH 4: SỬA RETRIEVER CODE
- Thay đổi index name trong retriever.py
- Thêm fallback search
- Debug aggregation pipeline

CÁCH 5: UPGRADE ATLAS TIER
- Vector Search yêu cầu M10+ cluster
- Kiểm tra Atlas tier hiện tại
""")

if __name__ == "__main__":
    success = debug_mongodb_atlas()
    
    if not success:
        check_atlas_vector_index()
        suggest_fixes()
    else:
        print("\nTất cả checks PASSED! Vector search should work.")
