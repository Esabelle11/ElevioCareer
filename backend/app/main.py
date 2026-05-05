import asyncio
import json
from typing import Any, Optional
import uuid

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.resume_analysis.ai_client import analyze_with_groq, normalize_ai_payload
from app.config import settings
from app.db.connection import check_user_limit, init_db, insert_analysis, list_history
from app.db.connection import get_jobs_by_section_random_seed,get_resume_text_by_job_id
from app.resume_analysis.pdf_extract import extract_text_from_pdf
from app.resume_analysis.scoring import (
    compute_scores,
)
from app.job_services.run_scrapper import run_scrapper
from app.job_services.ranker import get_top_jobs,rank_jobs
from app.job_services.locations import JOB_SEARCH_LOCATIONS
from app.worker.queue import enqueue_scrape_job

app = FastAPI(title="Elevio Career API", version="0.1.0")
API_PREFIX = "/api"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


class UploadHistoryBody(BaseModel):
    user_id: Optional[str] = None
    resume_text: str
    job_text: str
    total_score: float
    ai_output: dict[str, Any]


@app.get(f"{API_PREFIX}/health")
def health() -> dict[str, str | bool]:
    return {"status": "ok", "groq_configured": bool(settings.groq_api_key)}


@app.get(f"{API_PREFIX}/job_locations")
def job_locations() -> dict[str, Any]:
    return {"locations": JOB_SEARCH_LOCATIONS}



@app.post(f"{API_PREFIX}/analyze")
async def analyze(
    resume_pdf: UploadFile = File(...),
    job_text: str = Form(...),
    user_id: str = Form(...),
) -> dict[str, Any]:

    # check limit
    if check_user_limit(user_id):
        raise HTTPException(status_code=429, detail="Daily limit reached: 3 analyses per day")

    if not resume_pdf.filename or not resume_pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF resume.")

    raw_bytes = await resume_pdf.read()
    if len(raw_bytes) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="PDF too large (max 15MB).")

    try:
        resume_text = extract_text_from_pdf(raw_bytes)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {e}") from e

    if len(resume_text.strip()) < 40:
        raise HTTPException(status_code=400, detail="Resume text too short — check the PDF.")

    if len(job_text.strip()) < 30:
        raise HTTPException(status_code=400, detail="Job description is too short.")

    try:
        ai_raw = await analyze_with_groq(resume_text, job_text)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"AI analysis failed: {e}") from e
    # print(ai_raw)
    ai_norm = normalize_ai_payload(ai_raw)
    # print(ai_norm)
    scored = compute_scores(resume_text, job_text, ai_norm)
    # print("\n score: ",scored)

    
    response: dict[str, Any] = {
        "total_score": scored["total_match_score"],
        "interview_probability": ai_norm["interview_probability_hint"],
        "job_role":ai_norm["job_role"],
        "summary": ai_norm["summary"],
        "missing_skills": ai_norm["missing_skills"],
        "weak_points": ai_norm["weak_points"],
        "improved_points": ai_norm["improved_points"],
        "fix_priority": ai_norm["suggested_fixes"],
        "score_breakdown": {
            "keyword_score": scored["keyword_score"],
            "relevance_score": scored["relevance_score"],
            "impact_score": scored["impact_score"],
            "clarity_score": scored["clarity_score"],
        },
        "demo_mode": not bool(settings.groq_api_key),
        "resume_text":resume_text,
    }
    return response


@app.post(f"{API_PREFIX}/upload_history")
def upload_history(body: UploadHistoryBody) -> dict[str, Any]:
    row_id = insert_analysis(
        body.user_id,
        body.resume_text,
        body.job_text,
        body.total_score,
        body.ai_output,
    )
    return {"id": row_id, "ok": True}


@app.get(f"{API_PREFIX}/history")
def history(user_id: Optional[str] = None, limit: int = 10) -> dict[str, Any]:
    rows = list_history(user_id, min(limit, 50))
    parsed = []
    for r in rows:
        try:
            payload = json.loads(r["ai_output_json"])
        except Exception:  # noqa: BLE001
            payload = {}
        parsed.append(
            {
                "id": r["id"],
                "user_id": r["user_id"],
                "total_score": r["total_score"],
                "created_at": r["created_at"],
                "summary": {
                    "missing_skills": payload.get("missing_skills", [])[:5],
                    "total_score": payload.get("total_score"),
                },
            }
        )
    return {"items": parsed}


@app.post(f"{API_PREFIX}/job_scrapping")
async def job_scrapping(
    job_role: str = Form(...),
    location: str = Form(...),
    user_id: str = Form(...),
) -> dict[str, Any]:
    if not user_id.strip():
        raise HTTPException(status_code=400, detail="user_id is required.")

    loc = location.strip()
    if loc not in JOB_SEARCH_LOCATIONS:
        raise HTTPException(
            status_code=400,
            detail="Unknown location. Pick a city from GET /api/job_locations.",
        )

    role = job_role.strip()
    if len(role) < 2:
        raise HTTPException(status_code=400, detail="job_role is too short.")

    job_id = str(uuid.uuid4())

    if settings.USE_WORKER:
        enqueue_scrape_job(loc, role, job_id)
    else:
        await asyncio.to_thread(run_scrapper, loc, role, job_id)

    print("done job scrapping")
  
    return {
        "job_ids": job_id,
        "status": "processing"
    }
    
    
@app.get(f"{API_PREFIX}/job_result/{{job_id}}/{{resume_analysis_id}}")
def job_result(job_id: str, resume_analysis_id: int):

    raw_jobs = get_jobs_by_section_random_seed(job_id)

    if not raw_jobs or len(raw_jobs)<10:
        return {"status": "processing"}

    resume_text = get_resume_text_by_job_id(resume_analysis_id)

    if not resume_text:
        return {"status": "resume_not_found"}

    jobs = rank_jobs(resume_text, raw_jobs)

    return {
        "status": "done",
        "jobs": jobs,
        "count": len(jobs),
        "ok": True,
    }
