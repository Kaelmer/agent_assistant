import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse,StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from agent import run_agent               
import uvicorn
from fastapi.staticfiles import StaticFiles
from agent import get_history
from rag_util import add_document
from agent import agent
import time
from logger import log_error
import traceback

app = FastAPI()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

templates = Jinja2Templates(directory=os.path.join(PROJECT_ROOT, "templates"))

static_dir = os.path.join(PROJECT_ROOT, "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "chat.html")


class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[Message]
    thread_id: str = "default"  

@app.post("/api/chat")
def chat(req: ChatRequest):
    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    for attempt in range(3):
        try:
            reply = run_agent(messages, req.thread_id)
            def generate():
                for char in reply:
                    yield char
                    time.sleep(0.02)
            return StreamingResponse(generate())
        except Exception as e:
            if attempt==2:
                log_error(f"chat 接口报错：{str(e)}\n{traceback.format_exc()}")
                return {"error": "网络繁忙·请稍后再试"}
    return {"error":"未知错误"}


@app.post("/api/upload")
async def upload_file(files: list[UploadFile]):
    try:
        for file in files:
            text=(await file.read()).decode("utf-8",errors="ignore")
            add_document(text,file.filename)
        return {"message": "文件上传成功"}
    except Exception as e:
        log_error(f"upload接口错误：{str(e)}\n{traceback.format_exc()}")
        return {"error": str(e)}

@app.get("/api/history/{thread_id}")
def api_history(thread_id: str):
    return {"messages": get_history(thread_id)}

