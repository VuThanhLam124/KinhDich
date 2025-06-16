import gradio as gr
import json
from datetime import datetime

from chatbot import KinhDichChatbot
from config import GEMINI_MODEL

class KinhDichApp:
    """Giao diện Gradio cho Chatbot Kinh Dịch với XAI và Citation Display"""
    
    def __init__(self):
        self.chatbot = KinhDichChatbot()
        self.session_counter = 0
    
    def create_interface(self):
        """Tạo Gradio interface với Messages Format và XAI features"""
        with gr.Blocks(
            title="Chatbot Kinh Dịch",
            theme=gr.themes.Soft(),
            css="""
            .gradio-container {
                font-family: 'Times New Roman', serif;
                max-width: 1400px;
                margin: 0 auto;
            }
            .chat-message {
                font-size: 16px; 
                line-height: 1.6;
            }
            .citation-box {
                background-color: #f8f9fa;
                border-left: 4px solid #007bff;
                padding: 10px;
                margin: 10px 0;
            }
            """
        ) as interface:
            
            gr.Markdown("# Chatbot Kinh Dịch với XAI", elem_classes=["header-title"])
            
            with gr.Row():
                with gr.Column(scale=2):
                    # Main chat interface
                    chatbot_ui = gr.Chatbot(
                        type="messages",
                        height=500,
                        label="Cuộc trò chuyện",
                        render_markdown=True,
                        show_copy_button=True
                    )
                    
                    with gr.Row():
                        msg_box = gr.Textbox(
                            placeholder="Nhập câu hỏi về Kinh Dịch...",
                            label="Tin nhắn",
                            scale=4,
                            max_lines=3
                        )
                        send_btn = gr.Button("Gửi", variant="primary", scale=1)
                
                with gr.Column(scale=1):
                    # User controls
                    user_name = gr.Textbox(label="Tên (tùy chọn)", max_lines=1)
                    
                    # XAI Controls
                    with gr.Accordion("Tùy chọn XAI", open=False):
                        show_sources = gr.Checkbox(label="Hiển thị nguồn tham khảo", value=True)
                        show_reasoning = gr.Checkbox(label="Hiển thị quá trình suy luận", value=False)
                        confidence_threshold = gr.Slider(0.0, 1.0, 0.3, label="Ngưỡng độ tin cậy")
                    
                    # System info
                    gr.Markdown(f"""
                    **Model:** {GEMINI_MODEL}
                    
                    **Tính năng XAI:**
                    - Citation tracking
                    - Source verification
                    - Confidence scoring
                    - Reasoning explanation
                    """)
                    
                    clear_btn = gr.Button("Xóa cuộc trò chuyện", variant="secondary")
                    status_md = gr.Markdown("Hệ thống sẵn sàng")
            
            # XAI Display Area
            with gr.Row():
                with gr.Column():
                    with gr.Accordion("Nguồn Tham Khảo & XAI", open=False) as sources_accordion:
                        sources_display = gr.HTML(label="Chi tiết nguồn")
                        reasoning_display = gr.Markdown(label="Quá trình suy luận")
            
            # Event handlers
            def respond(message, history, user_name, show_sources, show_reasoning, confidence_threshold):
                if not message.strip():
                    return history, "", "Hệ thống sẵn sàng", "", ""
                
                try:
                    # Get comprehensive response with XAI
                    result = self.chatbot.answer_with_xai(
                        message, 
                        user_name or None,
                        confidence_threshold=confidence_threshold
                    )
                    
                    answer = result["answer"]
                    
                    # Build XAI displays
                    sources_html = self._build_sources_html(result.get("sources", [])) if show_sources else ""
                    reasoning_text = self._build_reasoning_text(result.get("reasoning", {})) if show_reasoning else ""
                    
                    # Add metadata
                    metadata = {}
                    if result.get('detected_hexagram'):
                        metadata["title"] = f"Phát hiện: {result['detected_hexagram']}"
                    
                    # Append messages
                    history.append(gr.ChatMessage(role="user", content=message))
                    history.append(gr.ChatMessage(
                        role="assistant", 
                        content=answer,
                        metadata=metadata
                    ))
                    
                    return history, "", "Sẵn sàng", sources_html, reasoning_text
                    
                except Exception as e:
                    error_msg = f"Xin lỗi, đã có lỗi xảy ra: {str(e)}"
                    history.append(gr.ChatMessage(role="user", content=message))
                    history.append(gr.ChatMessage(role="assistant", content=error_msg))
                    
                    return history, "", "Lỗi hệ thống", "", ""
            
            def clear_chat():
                return [], "Hệ thống sẵn sàng", "", ""
            
            # Bind events
            send_btn.click(
                respond,
                inputs=[msg_box, chatbot_ui, user_name, show_sources, show_reasoning, confidence_threshold],
                outputs=[chatbot_ui, msg_box, status_md, sources_display, reasoning_display]
            )
            
            msg_box.submit(
                respond,
                inputs=[msg_box, chatbot_ui, user_name, show_sources, show_reasoning, confidence_threshold],
                outputs=[chatbot_ui, msg_box, status_md, sources_display, reasoning_display]
            )
            
            clear_btn.click(
                clear_chat,
                outputs=[chatbot_ui, status_md, sources_display, reasoning_display]
            )
            
            # Examples
            gr.Examples(
                examples=[
                    "Quẻ Cách có ý nghĩa gì trong Kinh Dịch?",
                    "Tôi gieo được: ngửa-úp-úp-ngửa-ngửa-úp. Hãy cho tôi lời khuyên",
                    "Giải thích triết lý âm dương trong Kinh Dịch"
                ],
                inputs=msg_box
            )
        
        return interface
    
    def _build_sources_html(self, sources):
        """Build HTML for sources display"""
        if not sources:
            return "<p>Không có nguồn tham khảo</p>"
        
        html_parts = ["<div class='citation-box'>"]
        for i, source in enumerate(sources, 1):
            html_parts.append(f"""
            <div style='margin-bottom: 15px; border-bottom: 1px solid #ddd; padding-bottom: 10px;'>
                <strong>[{i}] {source.get('chunk_id', 'N/A')}</strong><br>
                <em>Loại:</em> {source.get('content_type', 'N/A')}<br>
                <em>Độ liên quan:</em> {source.get('score', 0):.3f}<br>
                <em>Trích đoạn:</em> {source.get('preview', 'N/A')}<br>
                {self._format_notes(source.get('notes', {}))}
            </div>
            """)
        html_parts.append("</div>")
        return "".join(html_parts)
    
    def _format_notes(self, notes):
        """Format notes for display"""
        if not notes:
            return ""
        
        notes_html = "<em>Chú thích:</em><ul>"
        for key, value in notes.items():
            notes_html += f"<li>[{key}] {value}</li>"
        notes_html += "</ul>"
        return notes_html
    
    def _build_reasoning_text(self, reasoning):
        """Build reasoning explanation text"""
        if not reasoning:
            return "Không có thông tin suy luận"
        
        parts = [
            f"**Chiến lược tìm kiếm:** {reasoning.get('search_strategy', 'N/A')}",
            f"**Số tài liệu truy xuất:** {reasoning.get('retrieved_docs', 0)}",
            f"**Độ tin cậy tổng thể:** {reasoning.get('confidence', 0):.2%}",
            f"**Quá trình suy luận:** {reasoning.get('reasoning_path', 'N/A')}"
        ]
        
        return "\n\n".join(parts)

def main():
    app = KinhDichApp()
    interface = app.create_interface()
    
    print("\n" + "="*50)
    print("Chatbot Kinh Dịch với XAI")
    print("="*50)
    print("Truy cập: http://localhost:7860")
    print("="*50 + "\n")
    
    interface.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        debug=True,
        show_error=True,
        inbrowser=True
    )

if __name__ == "__main__":
    main()
