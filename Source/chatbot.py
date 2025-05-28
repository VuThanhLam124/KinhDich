from typing import List, Dict
from Source.retriever import smart_search
from Source.reranker  import rerank
from Source.llm       import generate
from Source.config    import TOP_K_RERANK

def build_prompt(query: str, docs: List[Dict], name: str|None=None) -> str:
    ctx = "\n".join(f"{{#{i+1}:{d['_id']}}} {d['text'][:500]}…" for i,d in enumerate(docs))
    hello = f"Xin chào {name}! " if name else ""
    return (
        f"{hello}Người dùng hỏi: “{query}”\n\n"
        f"Tài liệu:\n{ctx}\n\n"
        "Trả lời ≤400 chữ, dẫn nguồn. Tập trung vào kiến thức trong tài liệu."
    )

def answer(query: str, user_name: str|None=None) -> str:
    docs = rerank(query, smart_search(query))
    prompt = build_prompt(query, docs, user_name)
    return generate(prompt)
