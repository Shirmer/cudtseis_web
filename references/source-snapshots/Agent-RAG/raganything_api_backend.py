#!/usr/bin/env python
"""
FastAPI 后端：基于 MinerU + RAGAnything 的多模态对话服务
"""

import os
import sys
import re
import asyncio
import json
import shutil
import math
from pathlib import Path
from typing import Optional, List

import numpy as np
import requests
from dotenv import load_dotenv

import logging
import logging.config

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import networkx as nx
from networkx.algorithms import community
from collections import defaultdict, Counter

# 保证能 import raganything / lightrag
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

from lightrag.llm.openai import openai_complete_if_cache
from lightrag.utils import EmbeddingFunc, logger, set_verbose_debug
from raganything import RAGAnything, RAGAnythingConfig

load_dotenv(dotenv_path=".env", override=False)

# ========= 日志配置 =========
def configure_logging():
    project_root = PROJECT_ROOT
    log_dir = os.getenv("LOG_DIR", str(project_root))
    log_file_path = os.path.abspath(os.path.join(log_dir, "raganything_api.log"))

    print(f"\nRAGAnything API log file: {log_file_path}\n")
    os.makedirs(log_dir, exist_ok=True)

    log_max_bytes = int(os.getenv("LOG_MAX_BYTES", 10485760))
    log_backup_count = int(os.getenv("LOG_BACKUP_COUNT", 5))

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {"format": "%(levelname)s: %(message)s"},
                "detailed": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                },
            },
            "handlers": {
                "console": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stderr",
                },
                "file": {
                    "formatter": "detailed",
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": log_file_path,
                    "maxBytes": log_max_bytes,
                    "backupCount": log_backup_count,
                    "encoding": "utf-8",
                },
            },
            "loggers": {
                "lightrag": {
                    "handlers": ["console", "file"],
                    "level": "INFO",
                    "propagate": False,
                },
            },
        }
    )
    logger.setLevel(logging.INFO)
    set_verbose_debug(os.getenv("VERBOSE", "false").lower() == "true")


# ========= 构建 RAG =========
async def build_rag(
    file_path: str,
    output_dir: str,
    api_key: str,
    base_url: Optional[str],
    working_dir: Optional[str],
    parser: Optional[str],
) -> RAGAnything:
    config = RAGAnythingConfig(
        working_dir=working_dir or "./rag_storage",
        parser=parser,
        parse_method="auto",
        enable_image_processing=True,
        enable_table_processing=True,
        enable_equation_processing=True,
    )

    def llm_model_func(prompt, system_prompt=None, history_messages=None, **kwargs):
        if history_messages is None:
            history_messages = []
        return openai_complete_if_cache(
            "qwen-max",
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        )

    def vision_model_func(
        prompt,
        system_prompt=None,
        history_messages=None,
        image_data=None,
        messages=None,
        **kwargs,
    ):
        if history_messages is None:
            history_messages = []

        if messages:
            return openai_complete_if_cache(
                "qwen-max", "", system_prompt=None, history_messages=[], messages=messages, api_key=api_key, base_url=base_url, **kwargs,
            )

        if image_data:
            mm = []
            if system_prompt:
                mm.append({"role": "system", "content": system_prompt})
            mm.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
                    ],
                }
            )
            return openai_complete_if_cache(
                "qwen-max", "", system_prompt=None, history_messages=[], messages=mm, api_key=api_key, base_url=base_url, **kwargs,
            )

        return llm_model_func(prompt, system_prompt, history_messages, **kwargs)

    embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")

    def _embed_raw_sync(texts):
        root = (base_url or "https://api.openai.com").rstrip("/")
        if root.endswith("/v1"):
            url = root + "/embeddings"
        else:
            url = root + "/v1/embeddings"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": embedding_model, "input": texts}
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()["data"]
        emb = [item["embedding"] for item in data]
        return np.asarray(emb, dtype=np.float32)

    async def embed_raw(texts):
        return await asyncio.to_thread(_embed_raw_sync, texts)

    probe = await embed_raw(["dim probe"])
    real_dim = len(probe[0])
    logger.info(f"[Embedding Probe] model={embedding_model} returned dim={real_dim}")

    embedding_func = EmbeddingFunc(
        embedding_dim=real_dim,
        max_token_size=8192,
        func=embed_raw,
    )

    rag = RAGAnything(
        config=config,
        llm_model_func=llm_model_func,
        vision_model_func=vision_model_func,
        embedding_func=embedding_func,
    )

    await rag.process_document_complete(
        file_path=file_path, output_dir=output_dir, parse_method="auto"
    )

    return rag


# ========= 全局配置 =========
configure_logging()
project_root = PROJECT_ROOT
DOCUMENT_PATH = os.getenv("DOC_PATH", str(project_root / "examples" / "example.pdf"))
WORKING_DIR = os.getenv("WORKING_DIR", str(project_root / "rag_storage"))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", str(project_root / "output"))
API_KEY = os.getenv("LLM_BINDING_API_KEY")
BASE_URL = os.getenv("LLM_BINDING_HOST")
PARSER = os.getenv("PARSER", "mineru")

STATIC_ROOT = os.path.abspath(OUTPUT_DIR)
rag: Optional[RAGAnything] = None


def resolve_startup_documents(document_path: str) -> List[str]:
    path = Path(document_path).expanduser()

    if not path.exists():
        return []

    if path.is_file():
        return [str(path.resolve())] if path.suffix.lower() == ".pdf" else []

    return sorted(
        str(pdf.resolve())
        for pdf in path.glob("*.pdf")
        if pdf.is_file()
    )


IMAGE_PATH_PATTERN = re.compile(re.escape(os.path.abspath(STATIC_ROOT).replace('\\', '/')) + r"[^\s*()\[\]\"']+", re.IGNORECASE)

def extract_image_paths_from_answer(answer: str) -> List[str]:
    return IMAGE_PATH_PATTERN.findall(answer)

def local_path_to_static_url(local_path: str) -> str:
    local_path = os.path.abspath(local_path)
    root = os.path.abspath(STATIC_ROOT)
    if not local_path.startswith(root): return ""
    
    if not os.path.exists(local_path):
        for ext in ['.jpg', '.png', '.jpeg']:
            if os.path.exists(local_path + ext):
                local_path = local_path + ext
                break
        else:
            return "" 
            
    return f"/static/{os.path.relpath(local_path, root).replace(os.sep, '/')}"

def load_doc_registry():
    docs = []
    if os.path.exists(OUTPUT_DIR):
        for item in os.listdir(OUTPUT_DIR):
            item_path = os.path.join(OUTPUT_DIR, item)
            if os.path.isdir(item_path) and not item.startswith('.'):
                file_name = f"{item}.pdf" if not item.lower().endswith('.pdf') else item
                docs.append({
                    "doc_id": item,
                    "file_name": file_name,
                    "folder_name": "parsed_papers",
                    "folder_label": "已解析的论文库"
                })
    return docs


# ========= FastAPI 应用 =========
app = FastAPI(title="RAGAnything FastAPI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(STATIC_ROOT, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")

class Scope(BaseModel):
    docs: List[str] = []

class ChatRequest(BaseModel):
    query: str
    scope: Optional[Scope] = None

class ChatResponse(BaseModel):
    answer: str
    images: List[str] = []
    page: int | None = None 
    citations: list = []

@app.on_event("startup")
async def startup_event():
    global rag
    if not API_KEY:
        logger.error("缺少 API Key")
        return

    startup_docs = resolve_startup_documents(DOCUMENT_PATH)
    if not startup_docs:
        logger.error(f"未找到可用 PDF：{DOCUMENT_PATH}")
        return

    logger.info(f"启动时发现 {len(startup_docs)} 个 PDF，正在构建索引...")
    rag = await build_rag(
        file_path=startup_docs[0],
        output_dir=OUTPUT_DIR,
        api_key=API_KEY,
        base_url=BASE_URL,
        working_dir=WORKING_DIR,
        parser=PARSER,
    )

    for extra_doc in startup_docs[1:]:
        logger.info(f"追加索引文档: {extra_doc}")
        await rag.process_document_complete(
            file_path=extra_doc,
            output_dir=OUTPUT_DIR,
            parse_method="auto",
        )

    logger.info("文档索引构建完成。")

@app.get("/api/documents")
async def get_documents():
    docs = load_doc_registry()
    tree = {}
    for doc in docs:
        fid = doc["folder_name"]
        if fid not in tree:
            tree[fid] = {"folder_id": fid, "folder_label": doc.get("folder_label", "未分类"), "children": []}
        tree[fid]["children"].append({"doc_id": doc["doc_id"], "file_name": doc["file_name"]})
    return {"code": 200, "data": list(tree.values())}

UPLOAD_DIR = os.path.join(WORKING_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    global rag
    if rag is None: raise HTTPException(status_code=503, detail="RAG 引擎未就绪")
    if not file.filename.lower().endswith('.pdf'): raise HTTPException(status_code=400, detail="仅支持 PDF")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        await rag.process_document_complete(file_path=file_path, output_dir=OUTPUT_DIR, parse_method="auto")
        return {"code": 200, "message": f"文件 {file.filename} 解析成功！"}
    except Exception as e:
        logger.exception("解析失败")
        raise HTTPException(status_code=500, detail=str(e))


def extract_pages(context: str):
    pages = []
    matches = re.findall(r"'page_idx'\s*:\s*(\d+)", context)
    for m in matches:
        pages.append(int(m) + 1)
    return sorted(list(set(pages)))

# 💡 核心升级 1：不仅提取 page，还精确提取对应的 bbox
def extract_citations(context: str):
    cites = []
    # 通过查找字典块的模式，避免顺序问题导致正则匹配失败
    blocks = re.findall(r'\{.*?\}', context, re.S)
    
    for block in blocks:
        bbox_match = re.search(r"'bbox'\s*:\s*\[([^\]]+)\]", block)
        page_match = re.search(r"'page_idx'\s*:\s*(\d+)", block)
        
        if bbox_match and page_match:
            try:
                coords = [float(x.strip()) for x in bbox_match.group(1).split(",")]
                page = int(page_match.group(1)) + 1
                cites.append({
                    "page": page,
                    "bbox": coords[:4]
                })
            except Exception:
                continue

    # 降级方案
    if not cites:
        pages = extract_pages(context)
        for p in pages:
            cites.append({"page": p, "bbox": [0,0,0,0]})
            
    return cites

# 💡 核心升级 2：将坐标拼接到 Markdown 引用标签中 [第X页|x1,y1,x2,y2]
def force_sentence_citation(answer: str, citations: list):
    if not citations:
        return answer

    # 按标点符号切分句子
    parts = re.split(r'([。.!?])', answer)
    
    cited_answer = ""
    cycle = [c for c in citations if c.get("bbox")]
    if not cycle:
        cycle = [{"page": 1, "bbox": [0,0,0,0]}]

    idx = 0
    for i in range(0, len(parts)-1, 2):
        sentence = parts[i]
        punct = parts[i+1] if i+1 < len(parts) else ""
        
        if not sentence.strip():
            cited_answer += sentence + punct
            continue
            
        c = cycle[idx % len(cycle)]
        page = c["page"]
        # 将 bbox 格式化保留一位小数
        bbox_str = ",".join([f"{x:.1f}" for x in c["bbox"]])
        
        cited_answer += f"{sentence}{punct} [第{page}页|{bbox_str}] "
        idx += 1

    # 尾部处理
    if len(parts) % 2 != 0 and parts[-1].strip():
        c = cycle[idx % len(cycle)]
        page = c["page"]
        bbox_str = ",".join([f"{x:.1f}" for x in c["bbox"]])
        cited_answer += f"{parts[-1]} [第{page}页|{bbox_str}]"
    elif len(parts) % 2 != 0:
        cited_answer += parts[-1]

    return cited_answer.strip()


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    global rag
    if rag is None:
        raise HTTPException(status_code=503, detail="RAG 引擎尚未就绪或初始化失败")

    try:
        kwargs = {}
        system_prompt = None
        target_query = req.query

        if req.scope and req.scope.docs:
            selected_docs = req.scope.docs
            all_docs = load_doc_registry()
            selected_names = [d["file_name"] for d in all_docs if d["doc_id"] in selected_docs]
            
            if selected_names:
                doc_list_str = "、".join(selected_names)
                
                system_prompt = (
                    f"【系统强制指令：严格知识库隔离】\n"
                    f"用户当前已明确指定只询问以下文档：{doc_list_str}。\n"
                    f"在接下来的所有检索内容中，你可能会看到来自其他文档的信息。你必须【绝对且唯一】地提取属于 {doc_list_str} 的内容进行回答。\n"
                    f"如果检索到的内容属于其他论文或模型，请【直接忽略】，不要在回答中提及任何非目标文档的概念！\n"
                    f"如果提供的上下文中确实没有针对目标文档的答案，请直接回答：'在您选中的文档（{doc_list_str}）中没有找到与该问题相关的直接描述。'"
                )
                
                target_query = f"在《{doc_list_str}》这篇文档中，{req.query}"

        # 1. 先用仅检索模式拿到上下文大文本
        raw_context = await rag.aquery(
            target_query, 
            mode="hybrid", 
            vlm_enhanced=False,  
            only_need_prompt=True
        )

        citations = extract_citations(raw_context)
        found_page = citations[0]["page"] if citations else 1

        print(f"【DEBUG】检测到引用块: {len(citations)} 个，跳转到 PDF 第 {found_page} 页")
        
        # 2. 调用模型生成回答
        raw_res = await rag.aquery(
            target_query, 
            mode="hybrid", 
            vlm_enhanced=True, 
            system_prompt=system_prompt, 
            **kwargs
        )

        if isinstance(raw_res, dict) and "answer" in raw_res:
            answer = raw_res["answer"]
        else:
            answer = str(raw_res)

        # ================= 再做句级引用 (携带坐标) =================
        answer = force_sentence_citation(answer, citations)

        raw_paths = extract_image_paths_from_answer(answer)
        image_urls: List[str] = []
        for p in raw_paths:
            url = local_path_to_static_url(p)
            if url:
                image_urls.append(url)
                
        return ChatResponse(answer=answer, images=image_urls, page=found_page, citations=citations)

    except Exception as e:
        logger.exception("对话处理失败")
        raise HTTPException(status_code=500, detail=str(e))


class GraphRequest(BaseModel):
    scope: Optional[Scope] = None

@app.post("/api/graph_data")
async def get_graph_data(req: GraphRequest):

    graph_path = os.path.join(WORKING_DIR, "graph_chunk_entity_relation.graphml")
    if not os.path.exists(graph_path):
        return {"nodes": [], "edges": []}

    try:
        G = nx.read_graphml(graph_path)
        selected_docs = set(req.scope.docs) if req.scope and req.scope.docs else set()

        def get_doc_id(data):
            fp = str(data.get("file_path",""))
            name = os.path.basename(fp)
            return name[:-4] if name.lower().endswith(".pdf") else name

        STOP_WORDS = {
            "method","model","data","analysis","approach",
            "system","paper","study","based","using"
        }

        def generate_topic_label(nodes):
            words = []
            for n in nodes:
                name = str(n).lower()
                parts = re.split(r"[\s\-_/]+", name)
                for p in parts:
                    if len(p) < 3: continue
                    if p in STOP_WORDS: continue
                    words.append(p)
            if not words: return "Research Topic"
            freq = Counter(words)
            top = [w for w,_ in freq.most_common(3)]
            return " ".join([w.capitalize() for w in top])

        ALLOWED_TYPES = {
            "concept","method","metric","software","organization",
            "person","data","theory","platform","task"
        }
        BLACKLIST = ["page ","figure ","equation","(image)","table ","header"]

        valid_nodes=set()
        node_doc={}

        for n,data in G.nodes(data=True):
            name=str(n).lower()
            typ=str(data.get("entity_type","")).lower()
            if any(b in name for b in BLACKLIST): continue
            if typ and typ not in ALLOWED_TYPES and typ!="unknown":
                if len(name)>35: continue
            doc=get_doc_id(data)
            if selected_docs and doc not in selected_docs: continue
            valid_nodes.add(n)
            node_doc[n]=doc

        G=G.subgraph(valid_nodes).copy()
        if len(G.nodes)==0: return {"nodes":[],"edges":[]}

        nodes_result=[]
        edges_result=[]
        eid=0

        if len(selected_docs)<=1:
            degree=dict(G.degree())
            top_nodes=sorted(degree.items(), key=lambda x:x[1], reverse=True)[:80]
            sub=G.subgraph([n for n,_ in top_nodes]).copy()
            deg=dict(sub.degree())
            max_deg=max(deg.values()) if deg else 1
            tier1=max_deg*0.5
            tier2=max_deg*0.2

            def tier(n):
                d=deg.get(n,0)
                if d>=tier1: return 1
                if d>=tier2: return 2
                return 3

            COLOR={1:"#ea580c",2:"#0284c7",3:"#64748b"}
            SIZE={1:28,2:14,3:6}

            for n in sub.nodes:
                t=tier(n)
                nodes_result.append({
                    "key":n,
                    "attributes":{
                        "label":str(n)[:25], "size":SIZE[t], "color":COLOR[t],
                        "tier":t, "entity_type":sub.nodes[n].get("entity_type","concept")
                    }
                })

            for s,t,_ in sub.edges(data=True):
                min_tier=min(tier(s),tier(t))
                edge_color="#f97316" if min_tier==1 else "#38bdf8"
                edge_size=1.5 if min_tier==1 else 0.5
                edges_result.append({
                    "key":f"e{eid}", "source":s, "target":t,
                    "attributes":{"size":edge_size, "color":edge_color}
                })
                eid+=1
        else:
            undirected=G.to_undirected()
            degree=dict(undirected.degree())
            top_nodes=sorted(degree.items(), key=lambda x:x[1], reverse=True)[:150]
            sub=undirected.subgraph([n for n,_ in top_nodes]).copy()

            try: communities=community.louvain_communities(sub,seed=42)
            except: communities=list(nx.connected_components(sub))

            node_cluster={}
            for cid,comm in enumerate(communities):
                for n in comm: node_cluster[n]=cid

            cluster_label={}
            for cid,comm in enumerate(communities):
                cluster_label[cid]=generate_topic_label(comm)

            cluster_papers=defaultdict(set)
            for n,c in node_cluster.items():
                doc=node_doc.get(n)
                if doc: cluster_papers[c].add(doc)

            COLORS=["#dc2626","#2563eb","#16a34a","#9333ea","#ea580c","#0891b2","#be185d","#65a30d"]
            paper_cluster=defaultdict(list)

            for cid,papers in cluster_papers.items():
                for p in papers: paper_cluster[p].append(cid)

            for p,clusters in paper_cluster.items():
                main=clusters[0]
                nodes_result.append({
                    "key":p,
                    "attributes":{
                        "label":p, "size":24, "color":COLORS[main%len(COLORS)],
                        "type":"paper", "topic":cluster_label[main], "cluster":main
                    }
                })

            edge_weight=defaultdict(int)
            for cid,papers in cluster_papers.items():
                papers=list(papers)
                for i in range(len(papers)):
                    for j in range(i+1,len(papers)):
                        a=papers[i]; b=papers[j]
                        key=tuple(sorted([a,b]))
                        edge_weight[key]+=1

            for (a,b),w in edge_weight.items():
                edges_result.append({
                    "key":f"e{eid}", "source":a, "target":b,
                    "attributes":{"size":0.8+w, "weight":w, "color":"#64748b"}
                })
                eid+=1

        return {"nodes":nodes_result, "edges":edges_result}

    except Exception as e:
        logger.exception("graph build failed")
        raise HTTPException(status_code=500,detail=str(e))

@app.get("/api/get_pdf/{doc_id}")
async def get_pdf_file(doc_id: str):

    # 文件名，不含后缀
    doc_id_clean = os.path.splitext(doc_id)[0]

    # 按照你提供的真实绝对路径结构拼装
    pdf_path = os.path.join(
        OUTPUT_DIR, 
        doc_id_clean, 
        "hybrid_auto", 
        f"{doc_id_clean}_origin.pdf"
    )
    
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail=f"文件不存在: {pdf_path}")
        
    return FileResponse(pdf_path, media_type="application/pdf")
