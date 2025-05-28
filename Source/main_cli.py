from Source.db import reembed_if_needed
from Source.chatbot import answer

def main():
    reembed_if_needed()          # tái-nhúng nếu cần
    name = input("Tên bạn (Enter để bỏ qua): ").strip() or None
    while True:
        q = input("\n🡆 ").strip()
        if not q:
            print("Kết thúc!"); break
        print("\n" + answer(q, name) + "\n")

if __name__ == "__main__":
    main()
