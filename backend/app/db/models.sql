-- =========================
-- DROP (SAFE)
-- =========================
DROP TABLE IF EXISTS jobs CASCADE;
DROP TABLE IF EXISTS resume_analysis CASCADE;

CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    job_url TEXT UNIQUE,
    title TEXT,
    company TEXT,
    location TEXT,
    description TEXT,
    source TEXT,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    section_random_seed TEXT,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS resume_analysis (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    resume_text TEXT,
    job_text TEXT,
    total_score REAL,
    ai_output_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)