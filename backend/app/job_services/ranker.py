from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
# from sentence_transformers import SentenceTransformer
from app.db.connection import get_jobs_by_section_random_seed,get_resume_text_by_job_id

# model = SentenceTransformer("all-MiniLM-L6-v2")

def rank_jobs(resume_text: str, jobs: list[dict]) -> list[dict]:
    
    if not jobs:
        return []

    documents = [resume_text] + [f'{j.get("title", "")} {j.get("description", "")}' for j in jobs]

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf = vectorizer.fit_transform(documents)

    scores = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()
    print("score:",scores)

    ranked = sorted(zip(jobs, scores), key=lambda x: x[1], reverse=True)

    # job_texts = [
    #     f'{j.get("title", "")} {j.get("description", "")}'
    #     for j in jobs
    # ]

    # embeddings = model.encode([resume_text] + job_texts)

    # resume_vec = embeddings[0]
    # job_vecs = embeddings[1:]

    # scores = cosine_similarity([resume_vec], job_vecs).flatten()

    # ranked = sorted(zip(jobs, scores), key=lambda x: x[1], reverse=True)


    out: list[dict] = []
    for job, score in ranked[:5]:
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


def get_top_jobs(resume_text: str, raw_jobs: list[dict]) -> list[dict]:
   
    return rank_jobs(resume_text, raw_jobs)




# from sentence_transformers import SentenceTransformer
# from sklearn.metrics.pairwise import cosine_similarity

# model = SentenceTransformer("all-MiniLM-L6-v2")

# def rank_jobs_semantic(resume_text: str, jobs: list[dict]):
#     if not jobs:
#         return []

#     job_texts = [
#         f'{j.get("title", "")} {j.get("description", "")}'
#         for j in jobs
#     ]

#     embeddings = model.encode([resume_text] + job_texts)

#     resume_vec = embeddings[0]
#     job_vecs = embeddings[1:]

#     scores = cosine_similarity([resume_vec], job_vecs).flatten()

#     ranked = sorted(zip(jobs, scores), key=lambda x: x[1], reverse=True)

#     return [
#         {
#             **job,
#             "relevance_score": round(score * 100, 2)
#         }
#         for job, score in ranked[:5]
#     ]