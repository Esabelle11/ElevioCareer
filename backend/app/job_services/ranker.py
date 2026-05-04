from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.db.connection import get_jobs_by_section_random_seed


def rank_jobs(resume_text: str, jobs: list[dict]) -> list[dict]:
    if not jobs:
        return []

    documents = [resume_text] + [f'{j.get("title", "")} {j.get("description", "")}' for j in jobs]

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf = vectorizer.fit_transform(documents)

    scores = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()

    ranked = sorted(zip(jobs, scores), key=lambda x: x[1], reverse=True)

    out: list[dict] = []
    for job, score in ranked[:10]:
        row = {
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "description": (job.get("description") or "")[:2000],
            "job_url": job.get("job_url", ""),
            "source": job.get("source", ""),
            "relevance_score": round(float(score) * 100, 2),
        }
        out.append(row)
    return out


def get_top_jobs(section_random_seed: str, resume_text: str) -> list[dict]:
    jobs = get_jobs_by_section_random_seed(section_random_seed)
    return rank_jobs(resume_text, jobs)
