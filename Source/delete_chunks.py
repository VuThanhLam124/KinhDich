import os

def delete_all_chunks_json(root_dir: str):
    """
    Xóa tất cả file chunks.json trong thư mục gốc và các thư mục con
    
    Args:
        root_dir (str): Thư mục gốc để tìm kiếm
    
    Returns:
        list: Danh sách các file đã xóa thành công
    """
    deleted_files = []
    error_files = []
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename == "chunks.json":
                file_path = os.path.join(dirpath, filename)
                try:
                    os.remove(file_path)
                    deleted_files.append(file_path)
                    print(f"✓ Đã xóa: {file_path}")
                except Exception as e:
                    error_files.append((file_path, str(e)))
                    print(f"✗ Lỗi khi xóa {file_path}: {e}")
    
    print(f"\nKết quả:")
    print(f"   - Đã xóa thành công: {len(deleted_files)} files")
    print(f"   - Lỗi: {len(error_files)} files")
    
    return deleted_files, error_files

# Cách sử dụng:
if __name__ == "__main__":
    root_directory = "Kinh_Dich_Data"  # Thay đổi đường dẫn nếu cần
    
    # Xác nhận trước khi xóa
    confirm = input(f"Bạn có chắc muốn xóa tất cả file chunks.json trong '{root_directory}'? (y/N): ")
    
    if confirm.lower() in ['y', 'yes']:
        deleted, errors = delete_all_chunks_json(root_directory)
        
        if deleted:
            print(f"\nHoàn thành! Đã xóa {len(deleted)} files chunks.json")
        else:
            print(f"\nKhông tìm thấy file chunks.json nào trong '{root_directory}'")
    else:
        print("Hủy bỏ thao tác xóa.")
