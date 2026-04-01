import re
from typing import Any


def _skill_tokens(text: str) -> set[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#.\-]{1,}", text.lower())
    return {w for w in words if len(w) > 1}


def _bullet_lines(resume_text: str) -> list[str]:
    lines = []
    for raw in resume_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if re.match(r"^[\u2022•\-\*]\s*", line) or re.match(
            r"^(Led|Built|Developed|Implemented|Designed|Managed|Created|Improved)\b",
            line,
            re.I,
        ):
            lines.append(line)
    if not lines:
        for raw in resume_text.splitlines():
            line = raw.strip()
            if 20 < len(line) < 400:
                lines.append(line)
    return lines[:25]


def _has_quant_metric(line: str) -> bool:
    return bool(
        re.search(
            r"\d+%|\d+\s*%|\$\d+|\d+\s*(k|m|billion|million|users|teams?|x|×)|"
            r"\d{2,4}\s*%|increased|decreased|reduced|improved|grew|saved",
            line,
            re.I,
        )
    )


def _looks_vague(line: str) -> bool:
    vague = (
        "worked on",
        "helped with",
        "assisted",
        "various",
        "several",
        "familiar with",
        "exposure to",
    )
    low = line.lower()
    return any(v in low for v in vague) and not _has_quant_metric(line)


def compute_scores(
    resume_text: str,
    job_text: str,
    ai_payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Doc 4.1: keyword 40%, relevance 30%, impact 20%, clarity 10%.
    Uses AI-derived fields where needed; fills gaps with heuristics.
    """
    jd_skills = _skill_tokens(job_text)
    res_skills = _skill_tokens(resume_text)
    required = jd_skills - {"and", "or", "the", "with", "for", "our", "you", "your"}
    if len(required) < 3:
        required_from_ai = ai_payload.get("required_skills") or []
        if isinstance(required_from_ai, list):
            required = {str(s).lower().strip() for s in required_from_ai if s}

    matched = len(required & res_skills) if required else max(1, len(res_skills & jd_skills))
    total_req = max(len(required), 1)
    keyword_score = min(40.0, (matched / total_req) * 40.0)

    rel_raw = ai_payload.get("relevance_rating")
    if rel_raw is None:
        bullets = _bullet_lines(resume_text)
        avg_sim = 3.0
        if bullets and required:
            hits = sum(1 for b in bullets if required & _skill_tokens(b))
            avg_sim = 2.0 + min(3.0, hits / max(len(bullets), 1) * 3.0)
        rel_raw = avg_sim
    rel = float(rel_raw)
    if rel > 5:
        rel = 5.0
    relevance_score = (rel / 5.0) * 30.0

    bullets = _bullet_lines(resume_text)
    if not bullets:
        bullets = [resume_text[:200]]
    quant = sum(1 for b in bullets if _has_quant_metric(b))
    impact_score = (quant / max(len(bullets), 1)) * 20.0

    vague_n = sum(1 for b in bullets if _looks_vague(b))
    clarity_score = (1.0 - (vague_n / max(len(bullets), 1))) * 10.0

    total = round(keyword_score + relevance_score + impact_score + clarity_score, 1)
    total = max(0.0, min(100.0, total))

    weak_points = ai_payload.get("weak_points") or []
    if isinstance(weak_points, list):
        vague_extra = sum(1 for b in bullets if _looks_vague(b))
        if vague_extra and not weak_points:
            weak_points = [b for b in bullets if _looks_vague(b)][:5]

    return {
        "keyword_score": round(keyword_score, 1),
        "relevance_score": round(relevance_score, 1),
        "impact_score": round(impact_score, 1),
        "clarity_score": round(clarity_score, 1),
        "total_score": total,
        "interview_probability": round(total, 1),
        "weak_points_normalized": weak_points if isinstance(weak_points, list) else [],
    }


def build_fix_priority(
    missing_skills: list[str],
    weak_points: list[str],
    improved_points: list[str],
) -> list[dict[str, Any]]:
    fixes: list[dict[str, Any]] = []
    for skill in missing_skills[:12]:
        fixes.append(
            {
                "fix": f"Add evidence of {skill} (project, certification, or bullet)",
                "impact": min(18, 8 + len(missing_skills)),
            }
        )
    if weak_points:
        fixes.append(
            {
                "fix": "Quantify and specify weak bullet points with metrics",
                "impact": 10,
            }
        )
    for i, imp in enumerate(improved_points[:5]):
        fixes.append({"fix": f"Adopt improved wording: {imp[:120]}", "impact": 6 - min(i, 3)})
    fixes.sort(key=lambda x: x["impact"], reverse=True)
    seen = set()
    out = []
    for f in fixes:
        key = f["fix"][:80]
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out[:12]


def potential_score_after_fixes(total: float, fixes: list[dict[str, Any]]) -> float:
    gain = sum(min(f.get("impact", 0), 15) for f in fixes[:6])
    return round(min(100.0, total + gain * 0.35), 1)
