# app.py - Enhanced Multi-Agent Kinh Dich Application
import gradio as gr
import asyncio
from orchestrator import answer_with_agents
from hexagram_caster import HexagramCaster

class MultiAgentKinhDichApp:
    def __init__(self):
        self.hexagram_caster = HexagramCaster()
    
    def create_interface(self):
        with gr.Blocks(title="Multi-Agent Kinh Dịch Chatbot", theme=gr.themes.Soft()) as interface:
            gr.Markdown("# 🤖 Multi-Agent Kinh Dịch Chatbot")
            gr.Markdown("Chào mừng bạn đến với chatbot Kinh Dịch. Hãy làm theo các bước dưới đây để nhận được luận giải sâu sắc nhất.")

            with gr.Row():
                # CỘT TRÁI: NHẬP LIỆU VÀ ĐIỀU KHIỂN
                with gr.Column(scale=1):
                    gr.Markdown("### Bước 1: Đặt câu hỏi")
                    msg_box = gr.Textbox(
                        placeholder="Nhập câu hỏi hoặc mô tả tình huống của bạn ở đây...",
                        label="Câu hỏi của bạn",
                        lines=3
                    )
                    
                    user_name = gr.Textbox(label="Tên (tùy chọn)", placeholder="Nhập tên của bạn...")

                    gr.Markdown("### Bước 2: Chọn cách gieo quẻ")
                    casting_type = gr.Radio(
                        choices=[
                            ("🪙 Ba Đồng Xu", "coins"),
                            ("⚡ Nhanh", "quick"), 
                            ("🎯 Hoàn Toàn Ngẫu Nhiên", "random"),
                            ("🧘 Thiền Định", "meditation")
                        ],
                        value="quick",
                        label="Chọn cách gieo"
                    )

                    gr.Markdown("### Bước 3: Bắt đầu luận giải")
                    with gr.Row():
                        main_btn = gr.Button("🎲 Gieo Quẻ và Luận Giải", variant="primary", scale=2)
                        quick_ask_btn = gr.Button("💬 Hỏi Nhanh", variant="secondary", scale=1)
                    
                    with gr.Accordion("ℹ️ Phân biệt 2 modes", open=False):
                        gr.Markdown("""
**🎲 Gieo Quẻ và Luận Giải:**
- ✅ Gieo quẻ ngẫu nhiên cho câu hỏi của bạn
- ✅ Phân tích tổng hợp: Quẻ + Tình huống cá nhân  
- ✅ Lời khuyên định hướng cụ thể
- 🎯 **Dành cho:** Tư vấn cá nhân, định hướng cuộc sống

**💬 Hỏi Nhanh:**
- ❌ Không gieo quẻ
- ✅ Trả lời thông tin từ cơ sở tri thức Kinh Dịch
- ✅ Giải thích khái niệm, ý nghĩa quẻ
- 🎯 **Dành cho:** Học hỏi, tìm hiểu kiến thức
                        """)
                    
                    with gr.Accordion("Thông tin quẻ đã gieo", open=True):
                        cast_result = gr.Textbox(
                            label="Kết quả gieo quẻ sẽ hiển thị ở đây",
                            lines=8,
                            interactive=False
                        )

                    with gr.Accordion("🤖 Agent Monitoring", open=False):
                        agent_stats = gr.JSON(label="Agent Performance")
                        reasoning_display = gr.JSON(label="Reasoning Chain")
                    
                    clear_chat_btn = gr.Button("🗑️ Xóa cuộc trò chuyện")

                # CỘT PHẢI: HIỂN THỊ KẾT QUẢ
                with gr.Column(scale=2):
                    chatbot_ui = gr.Chatbot(
                        type="messages",
                        height=700,
                        label="Cuộc trò chuyện",
                        render_markdown=True,
                        show_copy_button=True
                    )

            # --- ENHANCED BACKEND LOGIC ---
            async def cast_and_respond(message, history, user_name, cast_type):
                """Integrated workflow: Cast hexagram + AI analysis"""
                if not message.strip():
                    gr.Warning("Vui lòng nhập câu hỏi của bạn trước khi gieo quẻ.")
                    yield history, "", "", {}, []
                    return

                # 1. Gieo quẻ với enhanced error handling
                try:
                    cast_obj = self.hexagram_caster.cast_hexagram(f"Gieo quẻ cho câu hỏi: {message}")
                    
                    hexagram_info_dict = {
                        "name": cast_obj.hexagram_name,
                        "number": cast_obj.hexagram_number,
                        "general_meaning": cast_obj.general_meaning,
                        "structure_str": cast_obj.format_structure(),
                        "changing_lines": cast_obj.changing_lines or "Không có"
                    }

                    display_info = f"""🎯 QUẺ: {cast_obj.hexagram_name} ({cast_obj.hexagram_number}/64)
📝 Ý nghĩa: {cast_obj.general_meaning}
---
🏗️ Cấu trúc:
{cast_obj.format_structure()}
---
⚡ Hào động: {hexagram_info_dict['changing_lines']}
🎲 Cách gieo: {cast_type}"""
                    
                except Exception as e:
                    gr.Error(f"Lỗi khi gieo quẻ: {str(e)}")
                    yield history, message, "", {}, []
                    return

                # 2. Thêm câu hỏi của người dùng vào lịch sử chat
                history.append(gr.ChatMessage(role="user", content=message))
                
                # Thêm thông tin quẻ vào lịch sử chat như một bước riêng
                hexagram_chat_message = f"""**Đã gieo được quẻ:**

{display_info}"""
                history.append(gr.ChatMessage(
                    role="assistant", 
                    content=hexagram_chat_message,
                    metadata={"title": "Kết quả gieo quẻ"}
                ))

                # 3. Multi-agent analysis với progress feedback
                progress_message = "🤖 Đang phân tích qua Multi-Agent System...\n\n" + \
                                 "🔍 Dispatcher → 🗣️ Linguistics → 📚 Retrieval → 🧠 Reasoning"
                history.append(gr.ChatMessage(role="assistant", content=progress_message))
                yield history, "", display_info, {}, [] # Cập nhật UI ngay lập tức

                try:
                    result = await answer_with_agents(message, user_name, hexagram_info=hexagram_info_dict)
                    
                    # Xóa tin nhắn progress và thay bằng kết quả
                    history.pop()
                    
                    # Enhanced response với metadata
                    response_content = result["answer"]
                    if result.get("confidence", 0) < 0.7:
                        response_content += f"\n\n*Độ tin cậy: {result.get('confidence', 0):.1%} - Có thể cần thêm thông tin để phân tích chính xác hơn.*"
                    
                    history.append(gr.ChatMessage(
                        role="assistant", 
                        content=response_content,
                        metadata={"title": f"Luận giải hoàn tất (Confidence: {result.get('confidence', 0):.1%})"}
                    ))
                    
                except Exception as e:
                    history.pop()  # Remove progress message
                    history.append(gr.ChatMessage(
                        role="assistant", 
                        content=f"❌ Xin lỗi, đã có lỗi trong quá trình phân tích: {str(e)}"
                    ))
                    result = {"agent_stats": {}, "reasoning_chain": []}
                
                yield (history, "", display_info, 
                        result.get("agent_stats", {}), 
                        result.get("reasoning_chain", []))

            async def quick_respond(message, history, user_name):
                """Pure Q&A mode - No hexagram casting, focus on knowledge base"""
                if not message.strip():
                    gr.Warning("Vui lòng nhập câu hỏi của bạn.")
                    yield history, "", {}, []
                    return

                # Add user message với clear mode indicator
                history.append(gr.ChatMessage(role="user", content=message))
                
                # Enhanced progress feedback cho Q&A mode
                progress_message = "💡 Đang tìm kiếm trong cơ sở tri thức...\n\n" + \
                                 "📚 Mode: Hỏi đáp nhanh (không gieo quẻ)"
                history.append(gr.ChatMessage(role="assistant", content=progress_message))
                yield history, "", {}, []

                try:
                    # Pure Q&A: Không có hexagram context
                    result = await answer_with_agents(message, user_name, hexagram_info=None)
                    
                    # Replace progress với actual response
                    history.pop()
                    
                    # Enhanced response với mode indicator
                    response_content = result["answer"]
                    
                    # Add confidence indicator nếu thấp
                    if result.get("confidence", 0) < 0.6:
                        response_content += f"\n\n*Mode: Hỏi đáp nhanh | Độ tin cậy: {result.get('confidence', 0):.1%}*"
                        response_content += f"\n\n💡 *Gợi ý: Nếu cần tư vấn cá nhân, hãy sử dụng mode 'Gieo Quẻ và Luận Giải'*"
                    
                    history.append(gr.ChatMessage(
                        role="assistant", 
                        content=response_content,
                        metadata={"title": f"Trả lời nhanh (Q&A Mode)"}
                    ))
                    
                    yield (history, "", 
                           result.get("agent_stats", {}), 
                           result.get("reasoning_chain", []))
                           
                except Exception as e:
                    history.pop()
                    history.append(gr.ChatMessage(
                        role="assistant", 
                        content=f"❌ Xin lỗi, đã có lỗi: {str(e)}"
                    ))
                    yield history, "", {}, []

            # --- EVENT BINDINGS ---
            main_btn.click(
                cast_and_respond,
                inputs=[msg_box, chatbot_ui, user_name, casting_type],
                outputs=[chatbot_ui, msg_box, cast_result, agent_stats, reasoning_display]
            )
            
            quick_ask_btn.click(
                quick_respond,
                inputs=[msg_box, chatbot_ui, user_name],
                outputs=[chatbot_ui, msg_box, agent_stats, reasoning_display]
            )
            
            msg_box.submit(
                cast_and_respond,
                inputs=[msg_box, chatbot_ui, user_name, casting_type],
                outputs=[chatbot_ui, msg_box, cast_result, agent_stats, reasoning_display]
            )

            clear_chat_btn.click(
                lambda: ([], "", "", {}, []), 
                outputs=[chatbot_ui, msg_box, cast_result, agent_stats, reasoning_display]
            )
            
            # Enhanced examples với diverse use cases
            with gr.Accordion("📝 Ví dụ câu hỏi theo từng mode", open=False):
                gr.Markdown("**🎲 Dành cho 'Gieo Quẻ và Luận Giải' (Tư vấn cá nhân):**")
                gr.Examples(
                    examples=[
                        "Tôi đang cân nhắc chuyển việc, xin cho tôi một lời khuyên.",
                        "Mối quan hệ của tôi và người ấy sẽ đi về đâu?",
                        "Công việc kinh doanh sắp tới của tôi có thuận lợi không?",
                        "Tôi nên làm gì để cải thiện sức khỏe của mình?",
                        "Tôi đang muốn đi du lịch vào tháng này, hãy cho tôi lời khuyên."
                    ],
                    inputs=msg_box,
                    label=""
                )
                
                gr.Markdown("**💬 Dành cho 'Hỏi Nhanh' (Học hỏi kiến thức):**")
                gr.Examples(
                    examples=[
                        "Quẻ Cách có ý nghĩa gì trong Kinh Dịch?",
                        "Triết lý âm dương được hiểu như thế nào?",
                        "64 quẻ Kinh Dịch được chia thành mấy nhóm?",
                        "Hào động trong quẻ có tác dụng gì?",
                        "Thứ tự 8 quẻ cơ bản là gì?"
                    ],
                    inputs=msg_box,
                    label=""
                )
        
        return interface

def main():
    app = MultiAgentKinhDichApp()
    interface = app.create_interface()
    
    print("🤖 Multi-Agent Kinh Dịch Chatbot - HYBRID OPTIMIZED VERSION")
    print("🚀 Agents: Dispatcher → Linguistics → Retrieval → Reasoning")
    print("🎯 Features: Hexagram Context + Specialized Prompts + Enhanced UX")
    print("🔗 Dual Modes:")
    print("   🎲 Gieo Quẻ và Luận Giải: Divination + Personal Guidance")  
    print("   💬 Hỏi Nhanh: Pure Q&A + Knowledge Base")
    print("🌐 Access: http://localhost:7860")
    
    interface.launch(
        server_name="127.0.0.1",
        server_port=7860,
        inbrowser=True
    )

if __name__ == "__main__":
    main()