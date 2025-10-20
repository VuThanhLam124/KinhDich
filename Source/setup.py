#!/usr/bin/env python3
"""
Script kiểm tra và thiết lập môi trường cho Chatbot Kinh Dịch
"""
from pathlib import Path

def check_config():
    """Kiểm tra file config"""
    try:
        from config import (
            DB_NAME,
            EMBED_MODEL,
            LLM_PROVIDER,
            GEMINI_API_KEY,
            GEMINI_MODEL,
            OPENAI_API_KEY,
            OPENAI_MODEL,
            LOCAL_MODEL_PATH,
        )
        print("Config file loaded successfully")
        
        print("="*40)
        print(f"Database: {DB_NAME}")
        print(f"Model: {EMBED_MODEL}")
        print(f"LLM Provider: {LLM_PROVIDER}")

        provider_ok = True
        if LLM_PROVIDER == "gemini":
            if not GEMINI_API_KEY:
                print("GEMINI_API_KEY chưa được cấu hình")
                provider_ok = False
            else:
                print(f"Gemini model: {GEMINI_MODEL}")
        elif LLM_PROVIDER == "openai":
            if not OPENAI_API_KEY:
                print("OPENAI_API_KEY chưa được cấu hình")
                provider_ok = False
            else:
                print(f"OpenAI model: {OPENAI_MODEL}")
        elif LLM_PROVIDER == "local":
            if not LOCAL_MODEL_PATH:
                print("LOCAL_MODEL_PATH chưa được cấu hình")
                provider_ok = False
            else:
                print(f"Local model path: {LOCAL_MODEL_PATH}")
        else:
            print(f"Provider '{LLM_PROVIDER}' không được hỗ trợ")
            provider_ok = False

        print("="*40)
        return provider_ok
        
    except ImportError as e:
        print(f"Config import failed: {e}")
        return False

def check_data():
    """Kiểm tra dữ liệu đã được chunking"""
    data_dir = Path("Kinh_Dich_Data")
    if not data_dir.exists():
        print("Thư mục 'Kinh_Dich_Data' không tồn tại")
        return False
    
    # Đếm số file chunks.json
    chunks_files = list(data_dir.rglob("chunks.json"))
    print(f"Tìm thấy {len(chunks_files)} file chunks.json")
    
    if len(chunks_files) == 0:
        print("Chưa có file chunks.json. Chạy: python chunking.py")
        return False
    
    return True

def check_mongodb_connection():
    """Kiểm tra kết nối MongoDB Atlas"""
    try:
        from pymongo import MongoClient
        from config import MONGO_URI, DB_NAME
        
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        
        # Test connection
        client.admin.command('ping')
        print("MongoDB Atlas connection successful")
        
        # Check collections và documents
        collections = db.list_collection_names()
        if "chunks" not in collections:
            print("Collection 'chunks' not found. Chạy: python data_loader.py")
            return False
        else:
            count = db.chunks.count_documents({})
            print(f"Collection 'chunks' có {count} documents")
            
            # Check vector embeddings
            sample = db.chunks.find_one({"embedding": {"$exists": True}})
            if sample:
                print(f"Vector embeddings có sẵn ({len(sample['embedding'])} dimensions)")
            else:
                print("Chưa có vector embeddings. Chạy: python data_loader.py")
                return False
            
        return True
        
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        return False

def setup_vector_index_instructions():
    """Hướng dẫn thiết lập Vector Search Index"""
    print("""
THIẾT LẬP VECTOR SEARCH INDEX:

1. Đăng nhập MongoDB Atlas: https://cloud.mongodb.com
2. Chọn cluster → Atlas Search → Create Search Index
3. Chọn "Vector Search"
4. Database: 'kinhdich_kb', Collection: 'chunks'
5. Index name: 'vector_index'
6. JSON Configuration:

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

7. Create Index → Chờ build hoàn thành (3-5 phút)
""")

def main():
    """Kiểm tra toàn bộ hệ thống"""
    print("KIỂM TRA HỆ THỐNG CHATBOT KINH DỊCH\n")
    
    checks = [
        ("Config", check_config),
        ("Data", check_data),
        ("MongoDB", check_mongodb_connection)
    ]
    
    all_passed = True
    for name, check_func in checks:
        print(f"\n{name}:")
        if not check_func():
            all_passed = False
    
    if all_passed:
        print(f"\nTẤT CẢ KIỂM TRA PASSED!")
        print(f"\nSẴN SÀNG CHẠY:")
        print(f"   python Source/app.py              # Gradio interface")
    else:
        print(f"\nMỘT SỐ KIỂM TRA FAILED. Xem hướng dẫn trên để khắc phục.")
        setup_vector_index_instructions()

if __name__ == "__main__":
    main()
