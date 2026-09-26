import chromadb 
from sentence_transformers import SentenceTransformer,CrossEncoder
import uuid
import os
from langchain_openai import ChatOpenAI
from config import DEEPSEEK_API_KEY,DEEPSEEK_BASE_URL,DEEPSEEK_MODEL,validate_config
import jieba

model = SentenceTransformer("models/all-MiniLM-L6-v2")
reranker = CrossEncoder("models/ms-marco-MiniLM-L6-v2")
chroma_client=chromadb.PersistentClient(path=os.path.join(os.path.dirname(__file__), "chroma_db"))
collection=chroma_client.get_or_create_collection(name="my_collection")

from Retry import retry

@retry(max_attempts=3, delay=1)
def call_llm(messages):
    """调用 LLM，失败自动重试"""
    return llm.invoke(messages)

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
            chunks.append(chunk)
    return chunks

def add_document(text: str, user_id: int, file_name: str = ""):
    chunks = split_text(text)
    embeddings = model.encode(chunks).tolist()
    doc_ids = [str(uuid.uuid4())[:8] for _ in chunks]
    metadatas = [{"user_id": user_id, "file_name": file_name} for _ in chunks]
    
    collection.add(
        ids=doc_ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas
    )

def get_all_filename():
    result=collection.get()
    names=[f["file_name"] for f in result["metadatas"]]
    if not names:
        return "未找到文档"
    return "\n".join(names)

STOP = {"的","了","是","在","和","与","有","就","都","什么","怎么","如何",
        "这份","这个","一下","吗","呢","里","说","讲","部分","提到"}

def keywords_of(question, topk=3):
    tags = jieba.analyse.extract_tags(question, topK=topk*2)
    return [w for w in tags if len(w) > 1 and w not in STOP][:topk]

def query_db(question):
    embedding=get_embedding(question)
    Docs=collection.query(query_embeddings=embedding,n_results=5)
    
    docs=list(Docs["documents"][0])
    if not docs:
        return {"error":"未找到相关资料","result":""}

    keywords = keywords_of(question)
    if keywords:                                   
        kw_result = collection.get(
            where_document={"$or":[{"$contains":w} for w in keywords]},
            limit=10
            )   
        for doc in kw_result["documents"]:
            if doc not in docs:
                docs.append(doc)

    #精排，取分数
    pairs=[(question,doc) for doc in docs]
    scores=reranker.predict(pairs)

    #排序,取前分数最高的3条
    top_indices = sorted(range(len(scores)), key=lambda x: scores[x], reverse=True)[:3]
    top_doc=[docs[i] for i in top_indices]

    context="\n".join(top_doc)
    response = call_llm([
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

