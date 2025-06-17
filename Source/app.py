# app.py - Updated để sử dụng multi-agent system
import gradio as gr
import asyncio
from orchestrator import answer_with_agents
from hexagram_caster import HexagramCaster

class MultiAgentKinhDichApp:  # GIỮ NGUYÊN class name hiện có
    def __init__(self):
        # THÊM dòng này vào __init__ hiện có
        self.hexagram_caster = HexagramCaster()
    
    def create_interface(self):  # GIỮ NGUYÊN method hiện có
        
        with gr.Blocks(title="Multi-Agent Kinh Dịch Chatbot", theme=gr.themes.Soft()) as interface:
            
            # GIỮ NGUYÊN header hiện có
            gr.Markdown("# 🤖 Multi-Agent Kinh Dịch Chatbot")
            
            with gr.Row():
                # GIỮ NGUYÊN conversation area hiện có (scale=2)
                with gr.Column(scale=2):
                    chatbot_ui = gr.Chatbot(
                        type="messages",
                        height=500,
                        label="Cuộc trò chuyện",
                        render_markdown=True
                    )
                    
                    with gr.Row():
                        msg_box = gr.Textbox(
                            placeholder="Nhập câu hỏi về Kinh Dịch...",
                            label="Tin nhắn",
                            scale=4
                        )
                        send_btn = gr.Button("Gửi", variant="primary", scale=1)
                
                # THÊM VÀO sidebar hiện có (scale=1)
                with gr.Column(scale=1):
                    user_name = gr.Textbox(label="Tên (tùy chọn)")
                    
                    # ===== THÊM PHẦN NÀY VÀO SIDEBAR =====
                    with gr.Accordion("🎲 Gieo Quẻ Ngẫu Nhiên", open=True):
                        # Loại gieo quẻ
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
                        
                        # Button gieo
                        cast_btn = gr.Button("🎲 GIEO QUẺ", variant="secondary", size="lg")
                        
                        # Hiển thị kết quả
                        cast_result = gr.Textbox(
                            label="Thông tin quẻ",
                            lines=6,
                            interactive=False
                        )
                        
                        # Buttons hành động
                        with gr.Row():
                            copy_btn = gr.Button("📋 Copy", scale=1)
                            clear_btn = gr.Button("🗑️ Xóa", scale=1)
                    # ===== HẾT PHẦN THÊM =====
                    
                    # GIỮ NGUYÊN phần monitoring hiện có
                    with gr.Accordion("🤖 Agent Monitoring", open=False):
                        agent_stats = gr.JSON(label="Agent Performance")
                        reasoning_display = gr.JSON(label="Reasoning Chain")
                    
                    clear_btn = gr.Button("Xóa cuộc trò chuyện")
            
            # ===== THÊM CÁC FUNCTION NÀY =====
            def simple_cast_hexagram(cast_type):
                """Đơn giản: chỉ gieo quẻ ngẫu nhiên và trả về thông tin"""
                try:
                    # Gieo quẻ ngẫu nhiên
                    result = self.hexagram_caster.cast_hexagram("Random casting")
                    
                    # Format đơn giản để lấy thông tin
                    info = f"""🎯 QUẺ: {result.hexagram_name}
📍 Số thứ tự: {result.hexagram_number}/64
📝 Ý nghĩa: {result.general_meaning}

🏗️ Cấu trúc:
{result.format_structure()}

⚡ Giao thay đổi: {result.changing_lines if result.changing_lines else "Không có"}

🎲 Loại gieo: {cast_type}
⏰ Gieo lúc: {result.timestamp[:19]}"""
                    
                    return info
                    
                except Exception as e:
                    return f"Lỗi: {str(e)}"
            
            def copy_to_clipboard(text):
                """Copy text (placeholder - browser sẽ handle)"""
                return text  # Gradio tự động copy với show_copy_button
            
            def clear_result():
                """Xóa kết quả"""
                return ""
            # ===== HẾT FUNCTION THÊM =====
            
            # GIỮ NGUYÊN event handlers hiện có của conversation
            def respond_sync(message, history, user_name):
                # GIỮ NGUYÊN toàn bộ code respond_sync hiện có
                if not message.strip():
                    return history, "", {}, []
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(answer_with_agents(message, user_name))
                finally:
                    loop.close()
                
                history.append(gr.ChatMessage(role="user", content=message))
                history.append(gr.ChatMessage(role="assistant", content=result["answer"]))
                
                return (history, "", result.get("agent_stats", {}), 
                       result.get("reasoning_chain", []))
            
            # GIỮ NGUYÊN event bindings hiện có
            send_btn.click(
                respond_sync,
                inputs=[msg_box, chatbot_ui, user_name],
                outputs=[chatbot_ui, msg_box, agent_stats, reasoning_display]
            )
            
            msg_box.submit(
                respond_sync,
                inputs=[msg_box, chatbot_ui, user_name],
                outputs=[chatbot_ui, msg_box, agent_stats, reasoning_display]
            )
            
            # ===== THÊM event bindings cho gieo quẻ =====
            cast_btn.click(
                simple_cast_hexagram,
                inputs=[casting_type],
                outputs=[cast_result]
            )
            
            copy_btn.click(
                copy_to_clipboard,
                inputs=[cast_result],
                outputs=[]
            )
            
            clear_btn.click(
                clear_result,
                outputs=[cast_result]
            )
            # ===== HẾT event bindings thêm =====
            
            # GIỮ NGUYÊN clear button và examples hiện có
            clear_btn.click(lambda: ([], {}, []), outputs=[chatbot_ui, agent_stats, reasoning_display])
            
            gr.Examples(
                examples=[
                    "Quẻ Cách có ý nghĩa gì trong Kinh Dịch?",
                    "Triết lý âm dương được hiểu như thế nào?",
                    "Tôi gieo được ngửa-úp-úp-ngửa-ngửa-úp, cho tôi lời khuyên",
                    "Fellowship liên quan tới quẻ nào?"
                ],
                inputs=msg_box
            )
        
        return interface

# GIỮ NGUYÊN main function hiện có
def main():
    app = MultiAgentKinhDichApp()
    interface = app.create_interface()
    
    print("🤖 Multi-Agent Kinh Dịch Chatbot")
    print("🚀 Agents: Dispatcher → Linguistics → Retrieval → Reasoning")
    print("🎲 THÊM: Gieo quẻ ngẫu nhiên")  # CHỈ thêm dòng này
    print("🌐 Access: http://localhost:7860")
    
    interface.launch(
        server_name="127.0.0.1",
        server_port=7860,
        inbrowser=True
    )

if __name__ == "__main__":
    main()