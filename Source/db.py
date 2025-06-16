from typing import List, Dict
from tqdm import tqdm
from pymongo import MongoClient
from langchain_huggingface import HuggingFaceEmbeddings
from numpy import ndarray
from Source.config import MONGO_URI, DB_NAME, COLLECTION, EMBED_MODEL

client       = MongoClient(MONGO_URI)
collection   = client[DB_NAME][COLLECTION]
embedder     = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
MODEL_DIM    = len(embedder.embed_query("test"))

def _needs_reembed() -> bool:
    doc = collection.find_one({}, {"embedding":1})
    return doc and len(doc["embedding"]) != MODEL_DIM

def reembed_if_needed(batch: int = 64) -> None:
    if not _needs_reembed():
        return
    print("Re-embedding to", MODEL_DIM, "dimensions …")
    docs = list(collection.find({}, {"_id":1,"text":1}))
    for i in tqdm(range(0, len(docs), batch)):
        chunk = docs[i:i+batch]
        vecs: List[ndarray] = embedder.embed_documents([d["text"] for d in chunk])
        for d, v in zip(chunk, vecs):
            collection.update_one({"_id": d["_id"]}, {"$set": {"embedding": v}})
    print("Re-embed done.")
