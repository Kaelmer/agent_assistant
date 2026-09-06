import chromadb 
from sentence_transformers import SentenceTransformer,CrossEncoder
import uuid
import os
from langchain_openai import ChatOpenAI
from config import DEEPSEEK_API_KEY,DEEPSEEK_BASE_URL,DEEPSEEK_MODEL,validate_config

model = SentenceTransformer("models/all-MiniLM-L6-v2")
reranker = CrossEncoder("models/ms-marco-MiniLM-L6-v2")
chroma_client=chromadb.PersistentClient(path=os.path.join(os.path.dirname(__file__), "chroma_db"))
collection=chroma_client.get_or_create_collection(name="my_collection")

llm=ChatOpenAI(model=DEEPSEEK_MODEL,api_key=DEEPSEEK_API_KEY,base_url=DEEPSEEK_BASE_URL,temperature=0.7,max_tokens=1000)
validate_config()

from langchain_openai import ChatOpenAI


def get_embedding(text):
    return model.encode(text).tolist()

def split_text(text,chunk_max=500,overlap=50):
    """文本切成重叠小块"""
    chunks=[]
    for i in range(0,len(text),chunk_max-overlap):
        chunk=text[i:i+chunk_max]
        if chunk.strip():
            chunk.append(chunk)
    return chunks

def add_document(text: str, file_name: str = ""):
    chunks=split_text(text)
    embedding =model.encode(chunks).tolist()
    doc_ids = [str(uuid.uuid4())[:8]  for _ in range(len(chunks))]
    collection.add(
        ids=doc_ids,
        embeddings=embedding,
        documents=chunks,
        metadatas=[{"file_name": file_name}]
    )

def get_all_filename():
    result=collection.get()
    names=[f["file_name"] for f in result["metadatas"]]
    if not names:
        return "未找到文档"
    return "\n".join(names)

def query_db(question):
    embedding = get_embedding(question)

    # 多路召回
    Docs = collection.query(query_embeddings=[embedding], n_results=5)
    keyword = question.split()[0]
    keyword_result = collection.query(where={"$contains": keyword} if keyword else None, limit=5)

    # 合并去重
    docs = list(Docs["documents"][0])
    for doc in keyword_result["documents"]:
        if doc not in docs:
            docs.append(doc)

    if not docs:
        return None

    #精排，取分数
    pairs=[(question,doc) for doc in docs]
    scores=reranker.predict(pairs)

    #排序,取前分数最高的3条
    top_indices=sorted(range(len(scores),key=lambda x:scores(x),reverse=True)[:3])
    top_doc=[docs[i] for i in top_indices]

    context="\n".join(top_doc)
    response = llm.invoke([
    {"role": "system", "content": f"根据资料回答问题,{context}"},
    {"role": "user", "content": question}
    ])
    
    return response.content

def delete_file(file_name):
    result=collection.get(where={"file_name": file_name})
    if result["ids"]:
        for id in result["ids"]:
            collection.delete(ids=[id])
        return "删除成功"
    else:
        return "未找到文档"

