# Backend/main.py

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path

# Phase 1 imports
from Backend.embed import create_project_and_ingest

# Phase 2 imports
from pydantic import BaseModel
from Backend.rag.testcase_generator import generate_testcases

# Phase 3 imports
from typing import Any, Dict
from Backend.rag.scriptgen import generate_script_for_testcase

# Debug / retrieval import
from Backend.rag.rag import retrieve as rag_retrieve

app = FastAPI(title="AutoTesting Agent Backend (Phase 1 + Phase 2 + Phase 3)")

# ====================================================
# PHASE 1 — KB BUILDING
# ====================================================
@app.post("/upload_and_build")
async def upload_and_build(
    files: list[UploadFile] = File(...),
    include_checkout_html: bool = Form(False)
):
    """
    Upload support docs (md/txt/pdf/json/html) + checkout.html
    Build per-project vector database in ProjectData/proj_<ID>/.
    """

    temp_paths = []
    for f in files:
        tmp = Path(f.filename)
        tmp.write_bytes(await f.read())
        temp_paths.append(tmp)

    # Find checkout.html if user included it
    checkout_path = None
    if include_checkout_html:
        for t in temp_paths:
            if t.name.lower() == "checkout.html":
                checkout_path = t
                break

    # Create vector DB for this project
    result = create_project_and_ingest(
        uploaded_files=temp_paths,
        checkout_path=checkout_path
    )

    # cleanup temp files
    for t in temp_paths:
        try:
            t.unlink()
        except:
            pass

    return JSONResponse(result)


# ====================================================
# PHASE 2 — RAG TEST CASE GENERATION
# ====================================================
class AgentQuery(BaseModel):
    project_id: str
    query: str
    top_k: int = 6


@app.post("/agent_query")
async def agent_query(body: AgentQuery):
    """
    Phase 2:
    Generate grounded test cases using:
    - embedding of query
    - retrieval from project vector DB
    - Gemini-based LLM (JSON ONLY output)
    """
    result = generate_testcases(
        project_id=body.project_id,
        query=body.query,
        top_k=body.top_k
    )
    return JSONResponse(result)


# ====================================================
# PHASE 3 — SELENIUM SCRIPT GENERATION
# ====================================================
class GenerateScriptRequest(BaseModel):
    project_id: str
    testcase: Dict[str, Any]


@app.post("/generate_script")
async def generate_script(body: GenerateScriptRequest):
    """
    Phase 3:
    Generate a runnable Selenium Python script
    grounded strictly in checkout.html + documentation.
    """
    res = generate_script_for_testcase(body.project_id, body.testcase)
    return JSONResponse(res)


# ====================================================
# DEBUG: retrieval-only endpoint (no LLM calls)
# ====================================================
@app.post("/debug/retrieve")
async def debug_retrieve(project_id: str = Form(...), query: str = Form(...), top_k: int = Form(6)):
    """
    Debug endpoint: run retrieval only and return raw retrieved chunks.
    Use this to confirm the backend's retrieval output separately from LLM.
    """
    try:
        items = rag_retrieve(project_id, query, top_k=top_k)
        return JSONResponse({"project_id": project_id, "query": query, "retrieved_count": len(items), "retrieved": items})
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
