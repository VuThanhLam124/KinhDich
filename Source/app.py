# app.py - Updated để sử dụng multi-agent system
import gradio as gr
import asyncio
from orchestrator import answer_with_agents

class MultiAgentKinhDichApp:
    """Gradio app using multi-agent system"""
    
    def create_interface(self):
        """Create Gradio interface"""
        
        with gr.Blocks(title="Multi-Agent Kinh Dịch Chatbot", theme=gr.themes.Soft()) as interface:
            
            gr.Markdown("# 🤖 Multi-Agent Kinh Dịch Chatbot")
            
            with gr.Row():
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
                
                with gr.Column(scale=1):
                    user_name = gr.Textbox(label="Tên (tùy chọn)")
                    
                    # Agent monitoring
                    with gr.Accordion("🤖 Agent Monitoring", open=False):
                        agent_stats = gr.JSON(label="Agent Performance")
                        reasoning_display = gr.JSON(label="Reasoning Chain")
                    
                    clear_btn = gr.Button("Xóa cuộc trò chuyện")
            
            # Event handlers
            def respond_sync(message, history, user_name):
                """Sync wrapper cho async function"""
                if not message.strip():
                    return history, "", {}, []
                
                # Run async function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(answer_with_agents(message, user_name))
                finally:
                    loop.close()
                
                # Add to chat history
                history.append(gr.ChatMessage(role="user", content=message))
                history.append(gr.ChatMessage(role="assistant", content=result["answer"]))
                
                return (history, "", result.get("agent_stats", {}), 
                       result.get("reasoning_chain", []))
            
            # Bind events
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
            
            clear_btn.click(lambda: ([], {}, []), outputs=[chatbot_ui, agent_stats, reasoning_display])
            
            # Examples
            gr.Examples(
                examples=[
                    "Quẻ Cách có ý nghĩa gì trong Kinh Dịch?",
                    "Triết lý âm dương được hiểu như thế nào?",
                    "Tôi gieo được ngửa-úp-úp-ngửa-ngửa-úp, cho tôi lời khuyên"
                ],
                inputs=msg_box
            )
        
        return interface

def main():
    """Launch multi-agent app"""
    app = MultiAgentKinhDichApp()
    interface = app.create_interface()
    
    print("🤖 Multi-Agent Kinh Dịch Chatbot")
    print("🚀 Agents: Dispatcher → Linguistics → Retrieval → Reasoning")
    print("🌐 Access: http://localhost:7860")
    
    interface.launch(
        server_name="127.0.0.1",
        server_port=7860,
        inbrowser=True
    )

if __name__ == "__main__":
    main()
