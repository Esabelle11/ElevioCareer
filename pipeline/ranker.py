from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def rank_jobs(resume_text, jobs):
    documents = [resume_text] + [j["description"] + j["title"] for j in jobs]

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf = vectorizer.fit_transform(documents)

    scores = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()

    ranked = sorted(zip(jobs, scores), key=lambda x: x[1], reverse=True)

    return ranked[:10]


def get_top_jobs(conn, resume_text):
    with conn.cursor() as cur:
        cur.execute("SELECT title, company, description FROM jobs WHERE is_active=TRUE")
        rows = cur.fetchall()

    jobs = [{"title": r[0], "company": r[1], "description": r[2]} for r in rows]

    return rank_jobs(resume_text, jobs)