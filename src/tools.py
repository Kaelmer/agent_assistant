import sys
import os
from rag_util import query_db,add_document as rag_add,get_all_filename,delete_file as rag_delete_file
import webbrowser
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_core.tools import tool
import shutil

from config import WORKSPACE_ROOT


def _safe_path(path: str) -> str:
    if not path:
        raise ValueError("路径不能为空")

    # 如果是绝对路径，直接使用，不受工作区限制
    if os.path.isabs(path):
        return os.path.abspath(path)

    # 相对路径限制在工作区内
    abs_path = os.path.abspath(os.path.join(WORKSPACE_ROOT, path))
    workspace_root = os.path.abspath(WORKSPACE_ROOT)
    if not abs_path.startswith(workspace_root + os.sep) and abs_path != workspace_root:
        raise ValueError(f"路径 '{path}' 超出工作区范围，操作被拒绝")
    return abs_path


@tool
def create_files(file_name: str) -> str:
    """
    当用户提到要创建文件夹时，创建文件夹/目录（可递归创建多级目录）。
    """
    try:
        safe_path = _safe_path(file_name)
        os.makedirs(safe_path, exist_ok=True)
        return f"创建成功: {file_name}"
    except Exception as e:
        return str(e)


@tool
def create_file(file_name: str) -> str:
    """
    当用户提到要创建文件时，创建文件（空文件）。
    """
    try:
        safe_path = _safe_path(file_name)
        with open(safe_path, "w", encoding="utf-8") as f:
            pass
        return f"创建成功: {file_name}"
    except Exception as e:
        return str(e)


@tool
def get_file(file_name: str) -> str:
    """
    需要获取文件内容的时候，使用，获取文件内容。
    """
    try:
        safe_path = _safe_path(file_name)
        if not os.path.isfile(safe_path):
            return f"文件不存在: {file_name}"
        with open(safe_path, "r", encoding="utf-8") as f:
            return "\n".join(f.read().splitlines())
    except Exception as e:
        return str(e)


@tool
def save_file(file_name: str, content: str) -> str:
    """
    当用户提到要修改文件内容或者写入文件内容时，修改/保存文件内容（覆盖写入）。
    """
    try:
        safe_path = _safe_path(file_name)
        # 确保父目录存在
        parent_dir = os.path.dirname(safe_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"保存成功: {file_name}"
    except Exception as e:
        return str(e)


@tool
def list_files(folder_path: str = "") -> str:
    """列出指定文件夹的内容，可以传文件夹名或路径"""
    path = _safe_path(folder_path) if folder_path else WORKSPACE_ROOT
    try:
        items = os.listdir(path)
        if not items:
            return "(空目录)"
        result = []
        for item in sorted(items):
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                result.append(f"[目录] {item}/")
            else:
                result.append(f"[文件] {item}")
        return "\n".join(result)
    except Exception as e:
        return str(e)


@tool
def delete_file(file_name: str) -> str:
    """
    删除文件。
    """
    try:
        safe_path = _safe_path(file_name)
        if not os.path.isfile(safe_path):
            return f"文件不存在: {file_name}"
        os.remove(safe_path)
        return f"删除成功: {file_name}"
    except Exception as e:
        return str(e)


@tool
def rename_file(old_name: str, new_name: str) -> str:
    """
    重命名文件或文件夹。
    """
    try:
        safe_old = _safe_path(old_name)
        safe_new = _safe_path(new_name)
        
        if not os.path.exists(safe_old):
            return f"文件或目录不存在: {old_name}"
        if os.path.exists(safe_new):
            return f"目标已存在: {new_name}"
        
        os.rename(safe_old, safe_new)
        return f"重命名成功: {old_name} -> {new_name}"
    except Exception as e:
        return str(e)


@tool
def delete_files(file_name: str) -> str:
    """
    删除文件夹/目录（递归删除，包括其中所有内容）。
    """
    try:
        safe_path = _safe_path(file_name)
        if not os.path.isdir(safe_path):
            return f"目录不存在: {file_name}"
        if safe_path == os.path.abspath(WORKSPACE_ROOT):
            return "不能删除工作区根目录"
        shutil.rmtree(safe_path)
        return f"删除成功: {file_name}"
    except Exception as e:
        return str(e)

@tool
def query_ch_documents(question: str) -> str:
    """
    查询向量数据库，回答问题。
    """
    result=query_db(question)
    if result==None:
        return "没有找到相关文档"
    else:
        return result

@tool
def add_ch_document(text: str,filename: str) -> str:
    """添加文档到向量数据库"""
    rag_add(text, filename)
    return "文档已添加"

@tool
def get_ch_file() -> str:
    """
    获取数据向量库里面的文件列表
    """
    result=get_all_filename() 
    return result;

@tool
def delete_ch_file(filename: str) -> str:
    """
    删除向量数据库里面的文件
    """
    result= rag_delete_file(filename)
    return result


# ========== 联网功能 ==========

@tool
def fetch_webpage(url: str) -> str:
    """获取网页的文字内容，传入网址"""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(" ", strip=True)
        text = " ".join(text.split())  # 清理多余空白
        return text[:3000] if text else "页面内容为空"
    except Exception as e:
        return f"抓取网页失败：{e}"


@tool
def web_search(query: str) -> str:
    """联网搜索工具。当用户询问以下内容时必须调用此工具：
    - 天气、新闻、股价、赛事、日期、放假安排等实时信息
    - 你不知道答案或不确定的问题
    - 用户明确说"搜索""联网""查一下""帮我看看"
    - 任何需要最新数据而不是你内部知识的问题
    传入搜索关键词，返回搜索结果列表。"""
    try:
        url = f"https://www.bing.com/search?q={query}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        results = []
        for item in soup.select("li.b_algo h2 a"):
            text = item.get_text(strip=True)
            href = item.get("href", "")
            if text:
                results.append(f"{text}: {href}")
        
        if not results:
            return "没有找到搜索结果"
        return "\n".join(results[:5])
    except Exception as e:
        return f"搜索失败：{str(e)}"


@tool
def get_links(url: str) -> str:
    """获取网页中的所有链接，传入网址"""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        links = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a['href']
            if href.startswith(('http://', 'https://')) and href not in seen:
                seen.add(href)
                text = a.get_text(strip=True)[:30]
                links.append(f"{text}: {href}" if text else href)
        
        return "\n".join(links[:30]) if links else "未找到链接"
    except Exception as e:
        return f"获取链接失败：{e}"


# 1. 文件操作 Agent 工具
file_tools = [
    create_files,      # 创建文件夹
    create_file,       # 创建文件
    get_file,          # 读文件
    save_file,         # 写文件
    list_files,        # 列文件
    delete_file,       # 删文件
    rename_file,       # 重命名
    delete_files       # 删文件夹
]

# 2. 知识库 RAG Agent 工具
rag_tools = [
    query_ch_documents,  # 查知识库
    add_ch_document,     # 存知识库
    get_ch_file,         # 列知识库文件
    delete_ch_file       # 删知识库文件
]

# 3. 联网 Agent 工具
web_tools = [
    fetch_webpage,      # 抓网页
    web_search,         # 搜索
    get_links           # 提取链接
]