import pdfplumber
import os
import json
import re
import logging
from pathlib import Path
from tqdm import tqdm
from pdf2image import convert_from_path
from PIL import Image

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Hàm trích xuất văn bản từ phạm vi trang
def extract_text_from_pages(pdf, start_page, end_page):
    """Trích xuất văn bản từ các trang PDF trong phạm vi chỉ định."""
    text = ""
    try:
        for page_num in tqdm(range(start_page, end_page + 1), desc=f"Trích xuất văn bản trang {start_page}-{end_page}"):
            page = pdf.pages[page_num - 1]  # Trang trong pdfplumber bắt đầu từ 0
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        logger.error(f"Lỗi khi trích xuất văn bản trang {start_page}-{end_page}: {e}")
        raise

# Hàm trích xuất hình ảnh từ phạm vi trang
def extract_images_from_pages(pdf_path, start_page, end_page, output_dir):
    """Trích xuất hình ảnh từ các trang PDF và lưu vào thư mục chỉ định."""
    try:
        images_dir = os.path.join(output_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        # Chuyển đổi các trang PDF thành hình ảnh
        images = convert_from_path(pdf_path, first_page=start_page, last_page=end_page)
        
        for i, image in enumerate(tqdm(images, desc=f"Trích xuất hình ảnh trang {start_page}-{end_page}")):
            image_path = os.path.join(images_dir, f"page_{start_page + i}.png")
            image.save(image_path, "PNG")
            logger.info(f"Đã lưu hình ảnh vào {image_path}")
        
        return images_dir
    except Exception as e:
        logger.error(f"Lỗi khi trích xuất hình ảnh trang {start_page}-{end_page}: {e}")
        return None

# Hàm làm sạch văn bản
def clean_text(text):
    """Loại bỏ các phần không mong muốn như quảng cáo."""
    logger.info("Làm sạch văn bản")
    text = text.replace("đ Tolu", "được").replace("kernelng", "không")  # Sửa lỗi OCR
    lines = text.split("\n")
    cleaned_lines = [
        line for line in lines
        if "Ebook miễn phí tại : www.Sachvui.Com" not in line and
           "Ebook thực hiện dành cho những bạn chưa có điều kiện mua sách." not in line and
           "Nếu bạn có khả năng hãy mua sách gốc để ủng hộ tác giả, người dịch và Nhà Xuất Bản" not in line
    ]
    return "\n".join(cleaned_lines)

# Hàm tách ghi chú và nội dung chính
def extract_notes(text):
    """Tách ghi chú dạng [n] và nội dung chính."""
    note_pattern = r"\[\d+\]\s+.*?(?=\n|$)"  # Ghi chú dạng [n] nội dung
    notes = re.findall(note_pattern, text, re.MULTILINE)
    note_dict = {}
    for note in notes:
        match = re.match(r"\[(\d+)\]\s+(.*)", note)
        if match:
            num, note_text = match.groups()
            note_dict[num] = note_text.strip()
    main_text = re.sub(note_pattern, "", text)  # Xóa ghi chú khỏi nội dung chính
    return main_text.strip(), note_dict

# Danh sách các phần từ mục lục
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

def main():
    # Đường dẫn tới tệp PDF và thư mục đầu ra
    pdf_path = "nhasachmienphi-kinh-dich-tron-bo.pdf"
    output_dir = "Kinh_Dich_Data"
    
    # Kiểm tra tệp PDF tồn tại
    if not os.path.exists(pdf_path):
        logger.error(f"Tệp PDF không tồn tại: {pdf_path}")
        return
    
    logger.info(f"Bắt đầu xử lý dữ liệu từ {pdf_path}")
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for section_name, start_page, end_page in sections:
                # Tạo đường dẫn thư mục cho phần
                section_folder = os.path.join(output_dir, section_name)
                os.makedirs(section_folder, exist_ok=True)
                
                # Trích xuất và làm sạch văn bản
                logger.info(f"Xử lý văn bản cho phần: {section_name} (trang {start_page}-{end_page})")
                text = extract_text_from_pages(pdf, start_page, end_page)
                text = clean_text(text)
                
                # Tách nội dung chính và ghi chú
                main_text, notes = extract_notes(text)
                
                # Lưu nội dung chính
                main_path = os.path.join(section_folder, "main.txt")
                with open(main_path, "w", encoding="utf-8") as f:
                    f.write(main_text)
                logger.info(f"Đã lưu nội dung chính vào {main_path}")
                
                # Lưu ghi chú dưới dạng JSON
                notes_path = os.path.join(section_folder, "notes.json")
                with open(notes_path, "w", encoding="utf-8") as f:
                    json.dump(notes, f, ensure_ascii=False, indent=4)
                logger.info(f"Đã lưu ghi chú vào {notes_path}")
                
                # Trích xuất hình ảnh cho chương ĐỒ THUYẾT CỦA CHU HY
                if section_name == "DO_THUYET_CUA_CHU_HY":
                    logger.info(f"Trích xuất hình ảnh cho phần: {section_name}")
                    images_dir = extract_images_from_pages(pdf_path, start_page, end_page, section_folder)
                    if images_dir:
                        logger.info(f"Hình ảnh đã được lưu vào {images_dir}")
                    else:
                        logger.warning(f"Không trích xuất được hình ảnh cho phần: {section_name}")
        
        logger.info("Dữ liệu đã được thu thập và tổ chức thành công!")
    
    except KeyboardInterrupt:
        logger.warning("Chương trình bị gián đoạn bởi người dùng (Ctrl+C)")
    except Exception as e:
        logger.error(f"Lỗi trong quá trình thực thi: {e}")

if __name__ == "__main__":
    main()
