import json
import re
from typing import Any

import httpx

from app.config import settings

SYSTEM_PROMPT = """
You are a professional career coach and hiring manager. Compare the resume and job description. 
Return ONLY valid JSON with ALL fields present:

{
  "match_score": 0,                     # 0–100
  "interview_probability_hint": 0,      # 0–100 , estimated probability of the candidate being interviewed by the company
  "missing_skills": [],                 # list of missing or weak skills from the candidate's resume
  "required_skills": [],                # skills that are must-have from JOB DESCRIPTION
  "weak_points": [],                    # vague or weak resume lines from the candidate's resume
  "improved_points": [],                # quantified replacement bullets from the candidate's resume
  "relevance_rating": 1,                # 1–30, measures overall relevance of the candidate’s experience to the JOB DESCRIPTION
  "impact_score": 0,                    # 0–20, measures quantified results and achievements from the candidate's resume
  "clarity_score": 0,                   # 0–10, measures readability and conciseness from the candidate's resume
  "suggested_fixes": [
    { 
      "fix": "short actionable recommendation", 
      "impact_score": 1,                # 1–20
      "impact_label": "Optional | Medium | Critical" 
    }
  ],
  "summary": "summary of the analysis",
  "keywords": ["keyword1", "keyword2", "keyword3"]  # keywords that recruiters or ATS look for based on JOB DESCRIPTION.
}

Rules:
- ALL fields are REQUIRED
- Do NOT omit any field
- If unsure, return a best guess
- suggested_fixes must contain 3 to 7 items
- impact_score in suggested_fixes must be 1–20
- impact_label must follow:
  - 16–20 = Critical
  - 11–15 = Medium
  - 1–10 = Optional
- improved_points must include metrics where possible
- Group similar missing skills into fewer, stronger fixes
- Avoid repeating "add evidence of X"
- keywords must be 20-60 keywords
- Return ONLY JSON (no explanation, no markdown)
"""

JSON_BLOCK = re.compile(r"\{[\s\S]*\}")


def _parse_json(content: str) -> dict[str, Any]:
    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        m = JSON_BLOCK.search(content)
        if m:
            return json.loads(m.group(0))
        raise


async def analyze_with_groq(resume_text: str, job_text: str) -> dict[str, Any]:
    if not settings.groq_api_key:
        return _demo_ai_response(resume_text, job_text)

    user_msg = (
        f"RESUME:\n{resume_text[:12000]}\n\nJOB DESCRIPTION:\n{job_text[:8000]}\n"
        "Respond with JSON only."
    )
    print("Using AI API")
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.groq_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                "temperature": 0.3,
                "max_tokens": 4096,
            },
        )
        r.raise_for_status()
        data = r.json()
        content = data["choices"][0]["message"]["content"]
    return _parse_json(content)


def _demo_ai_response(resume_text: str, job_text: str) -> dict[str, Any]:
    """Deterministic fallback when GROQ_API_KEY is unset (local demo)."""
    print("Using DEMO METHOD")
    rlow, jlow = resume_text.lower(), job_text.lower()
    missing = []
    for token in ("python", "sql", "docker", "kubernetes", "aws", "react"):
        if token in jlow and token not in rlow:
            missing.append(token.title())
    weak: list[str] = []
    for line in resume_text.splitlines():
        s = line.strip()
        if "worked on" in s.lower() or "helped with" in s.lower():
            weak.append(s[:200])
    if not weak:
        weak = ["Add more quantified achievements tied to the job requirements."]
    improved = [
        "Delivered X feature, cutting latency 35% for 50k daily users (example—replace with your metrics).",
    ]
    hint = 55.0
    if not missing:
        hint = 72.0
    return {
        "match_score": hint - 5,
        "interview_probability_hint": hint,
        "missing_skills": missing[:8] or ["Align resume keywords with JD"],
        "required_skills": ["See job description requirements"],
        "weak_points": weak[:5],
        "improved_points": improved,
        "relevance_rating": 3.5 if missing else 4.2,
        "suggested_fixes": [
            {"fix": "Mirror JD language in summary and top bullets", "impact": 12},
            {"fix": "Add measurable outcomes to each role", "impact": 10},
        ],
    }


def normalize_ai_payload(raw: dict[str, Any]) -> dict[str, Any]:
    def as_list(v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x) for x in v if x is not None]
        return [str(v)]

    def as_fixes(v: Any) -> list[dict[str, Any]]:
        if not isinstance(v, list):
            return []
        out = []
        for item in v:
            if isinstance(item, dict) and "fix" in item:
                imp = item.get("impact", 8)
                try:
                    imp = int(imp)
                except (TypeError, ValueError):
                    imp = 8
                out.append({"fix": str(item["fix"]), "impact": max(1, min(20, imp))})
        return out

    return {
        "match_score": float(raw.get("match_score") or 0),
        "interview_probability_hint": float(raw.get("interview_probability_hint") or raw.get("match_score") or 0),
        "missing_skills": as_list(raw.get("missing_skills")),
        "required_skills": as_list(raw.get("required_skills")),
        "weak_points": as_list(raw.get("weak_points")),
        "improved_points": as_list(raw.get("improved_points")),
        "relevance_rating": float(raw.get("relevance_rating") or 3),
        "impact_score": float(raw.get("impact_score") or 0),
        "clarity_score": float(raw.get("clarity_score") or 0),
        "keywords": as_list(raw.get("keywords")),
        "suggested_fixes": as_fixes(raw.get("suggested_fixes")),
        "summary": str(raw.get("summary") or ""),
    }
