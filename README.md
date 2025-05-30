# KinhDich - Hệ thống AI Chatbot Kinh Dịch

Dự án xây dựng hệ thống AI chatbot thông minh để tra cứu và tư vấn về Kinh Dịch (I Ching). Hệ thống sử dụng công nghệ RAG (Retrieval-Augmented Generation) để cung cấp thông tin chính xác từ kho dữ liệu Kinh Dịch phong phú.

## Mô tả chi tiết

Hệ thống AI chatbot Kinh Dịch được thiết kế để:
- Trả lời các câu hỏi về nội dung Kinh Dịch một cách thông minh và chính xác
- Tìm kiếm thông tin từ cơ sở dữ liệu bao gồm Chu Dịch Hạ Kinh, Chu Dịch Thượng Kinh và các tài liệu liên quan
- Sử dụng công nghệ embedding và reranking để tìm kiếm semantic tối ưu
- Tích hợp AI generative (Gemini) để tạo ra câu trả lời tự nhiên và dễ hiểu

## Tính năng

*   ✅ **Chatbot AI thông minh**: Trả lời câu hỏi về Kinh Dịch bằng ngôn ngữ tự nhiên
*   ✅ **Tìm kiếm semantic**: Sử dụng embedding để tìm kiếm thông tin liên quan
*   ✅ **Reranking**: Sắp xếp lại kết quả tìm kiếm để đảm bảo độ chính xác
*   ✅ **Trích dẫn nguồn**: Cung cấp thông tin nguồn gốc cho mỗi câu trả lời
*   ✅ **Giao diện CLI**: Giao diện dòng lệnh đơn giản và dễ sử dụng
*   ✅ **Lưu trữ đám mây**: Sử dụng MongoDB Atlas để lưu trữ dữ liệu

## Công nghệ sử dụng

*   **Ngôn ngữ lập trình:** Python 3.10+
*   **AI Framework:** LangChain, Hugging Face Transformers
*   **Embedding Models:** 
    - VoVanPhuc/sup-SimCSE-VietNamese-phobert-base (768 dimensions)
    - dangvantuan/vietnamese-embedding-LongContext
    - intfloat/multilingual-e5-base (cross-encoder)
*   **LLM:** Google Gemini 2.0 Flash
*   **Vector Database:** FAISS (Facebook AI Similarity Search)
*   **Database:** MongoDB Atlas
*   **Libraries:** pymongo, faiss-cpu, sentence-transformers, pdfplumber
*   **Khác:** Git, VS Code

## Cài đặt

### Yêu cầu hệ thống
- Python 3.10 hoặc cao hơn
- Git
- Kết nối internet (để sử dụng MongoDB Atlas và Gemini API)

### Hướng dẫn cài đặt

1. **Clone repository:**
```bash
git clone https://github.com/your-username/KinhDich.git
cd KinhDich
```

2. **Cài đặt dependencies:**
```bash
pip install -r requirements.txt
```

3. **Cấu hình môi trường:**
   - Mở file `Source/config.py`
   - Cập nhật `MONGO_URI` với connection string MongoDB Atlas của bạn
   - Cập nhật `GEMINI_API_KEY` với API key Gemini của bạn

4. **Khởi tạo dữ liệu (nếu cần):**
```bash
python Source/pre-process.py
```

## Sử dụng

### Chạy ứng dụng CLI

```bash
python -m Source.main_cli
```

Sau khi chạy lệnh trên:
1. Nhập tên của bạn (hoặc Enter để bỏ qua)
2. Bắt đầu đặt câu hỏi về Kinh Dịch
3. Nhập chuỗi rỗng để thoát

### Ví dụ sử dụng

```
Tên bạn (Enter để bỏ qua): Minh

🡆 Quẻ Cách có ý nghĩa gì?

[AI sẽ trả lời dựa trên dữ liệu Kinh Dịch với trích dẫn nguồn]

🡆 
```

## Cấu trúc dự án

```
KinhDich/
├── Source/                     # Mã nguồn chính
│   ├── __init__.py
│   ├── main_cli.py            # Ứng dụng CLI chính
│   ├── chatbot.py             # Logic chatbot
│   ├── config.py              # Cấu hình hệ thống
│   ├── db.py                  # Kết nối cơ sở dữ liệu
│   ├── llm.py                 # Tích hợp Gemini LLM
│   ├── retriever.py           # Tìm kiếm semantic
│   ├── reranker.py            # Sắp xếp lại kết quả
│   ├── mapping.py             # Mapping dữ liệu
│   └── pre-process.py         # Tiền xử lý dữ liệu
├── Kinh_Dich_Data/            # Dữ liệu Kinh Dịch
│   ├── CHU_DICH_HA_KINH/      # Chu Dịch Hạ Kinh (64 quẻ)
│   ├── CHU_DICH_THUONG_KINH/  # Chu Dịch Thượng Kinh
│   ├── DICH_THUYET_CUONG_LINH/
│   ├── DO_THUYET_CUA_CHU_HY/
│   ├── NHUNG_DIEU_NEN_BIET/
│   └── TUA_CUA_TRINH_DI/
├── faiss_index/               # FAISS vector database
├── hf_cache/                  # Hugging Face models cache
├── requirements.txt           # Python dependencies
└── README.md                  # Tài liệu dự án
```

## Đóng góp

Nếu bạn muốn đóng góp cho dự án, vui lòng làm theo các bước sau:

1. Fork dự án
2. Tạo một nhánh mới (`git checkout -b feature/AmazingFeature`)
3. Commit các thay đổi của bạn (`git commit -m 'Add some AmazingFeature'`)
4. Push lên nhánh (`git push origin feature/AmazingFeature`)
5. Mở một Pull Request

## Giấy phép

Dự án này được phân phối dưới giấy phép MIT. Xem file `LICENSE` để biết thêm chi tiết.

## Liên hệ

Vũ Thành Lâm - [vuthanhlam848@gmail.com](mailto:vuthanhlam848@gmail.com)

Project Link: [(https://github.com/VuThanhLam124/KinhDich)]
