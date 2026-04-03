import re
from typing import Any


def _skill_tokens(text: str) -> set[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#.\-]{1,}", text.lower())
    return {w for w in words if len(w) > 1}


def compute_scores(
    resume_text: str,
    job_text: str,
    ai_payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Doc 4.1: keyword 40%, relevance 30%, impact 20%, clarity 10%.
    Uses AI-derived fields where needed; fills gaps with heuristics.
    """
    # Convert AI keywords (list) to text and extract tokens
    keywords_list = ai_payload.get("keywords") or []
    keywords_text = " ".join(keywords_list).replace("/", " ")
    required = _skill_tokens(keywords_text)
    res_skills = _skill_tokens(resume_text)
    
    # matched = len(required & res_skills) if required else max(1, len(res_skills & jd_skills))
    matched = len(required & res_skills)
    total_req = max(len(required), 1)

    keyword_score = min(40.0, (matched / total_req) * 40.0)

    relevance_score = ai_payload.get("relevance_rating")
    
    impact_score =  ai_payload.get("impact_score")

    clarity_score = ai_payload.get("clarity_score")

    total = round(keyword_score + relevance_score + impact_score + clarity_score, 1)
    total = max(0.0, min(100.0, total))


    return {
        "keyword_score": round(keyword_score, 1),
        "relevance_score": round(relevance_score, 1),
        "impact_score": round(impact_score, 1),
        "clarity_score": round(clarity_score, 1),
        "total_match_score": total,
        
    }


