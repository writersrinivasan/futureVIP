-- ============================================================
-- FUTURE VIP — Initial Schema Migration
-- Migration: 001_initial
-- Created: 2024-01-01
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- for ILIKE fast search

-- ============================================================
-- ENUM TYPES
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'application_status_enum') THEN
        CREATE TYPE application_status_enum AS ENUM (
            'saved',
            'applied',
            'screening',
            'interview',
            'offer',
            'rejected',
            'withdrawn'
        );
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'job_type_enum') THEN
        CREATE TYPE job_type_enum AS ENUM (
            'full_time',
            'part_time',
            'contract',
            'freelance',
            'internship',
            'temporary'
        );
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notification_type_enum') THEN
        CREATE TYPE notification_type_enum AS ENUM (
            'job_match',
            'application_update',
            'interview_reminder',
            'resume_analyzed',
            'career_insight',
            'system'
        );
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'proficiency_level_enum') THEN
        CREATE TYPE proficiency_level_enum AS ENUM (
            'beginner',
            'intermediate',
            'advanced',
            'expert'
        );
    END IF;
END$$;

-- ============================================================
-- TABLE: users
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_admin        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_users_email      ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_is_active  ON users (is_active);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at DESC);

-- Auto-update updated_at trigger function (reusable)
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- TABLE: resumes
-- ============================================================

CREATE TABLE IF NOT EXISTS resumes (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename     VARCHAR(255) NOT NULL,
    file_path    VARCHAR(512) NOT NULL,
    file_size    INTEGER,
    content_text TEXT,
    parsed_data  JSONB,
    ats_score    DOUBLE PRECISION,
    resume_score DOUBLE PRECISION,
    version      INTEGER NOT NULL DEFAULT 1,
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resumes_user_id    ON resumes (user_id);
CREATE INDEX IF NOT EXISTS idx_resumes_is_active  ON resumes (is_active);
CREATE INDEX IF NOT EXISTS idx_resumes_created_at ON resumes (created_at DESC);

-- ============================================================
-- TABLE: jobs
-- ============================================================

CREATE TABLE IF NOT EXISTS jobs (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(255),
    source      VARCHAR(64) NOT NULL,
    title       VARCHAR(512) NOT NULL,
    company     VARCHAR(255) NOT NULL,
    location    VARCHAR(255),
    description TEXT,
    requirements TEXT,
    salary_min  DOUBLE PRECISION,
    salary_max  DOUBLE PRECISION,
    job_type    job_type_enum,
    remote      BOOLEAN NOT NULL DEFAULT FALSE,
    url         VARCHAR(2048),
    posted_at   TIMESTAMPTZ,
    scraped_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata    JSONB,

    CONSTRAINT uq_job_external_source UNIQUE (external_id, source)
);

CREATE INDEX IF NOT EXISTS idx_jobs_title       ON jobs USING GIN (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_jobs_company     ON jobs USING GIN (company gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_jobs_location    ON jobs (location);
CREATE INDEX IF NOT EXISTS idx_jobs_source      ON jobs (source);
CREATE INDEX IF NOT EXISTS idx_jobs_remote      ON jobs (remote);
CREATE INDEX IF NOT EXISTS idx_jobs_job_type    ON jobs (job_type);
CREATE INDEX IF NOT EXISTS idx_jobs_posted_at   ON jobs (posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_scraped_at  ON jobs (scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_salary_min  ON jobs (salary_min);
CREATE INDEX IF NOT EXISTS idx_jobs_salary_max  ON jobs (salary_max);

-- ============================================================
-- TABLE: job_matches
-- ============================================================

CREATE TABLE IF NOT EXISTS job_matches (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id      UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    resume_id   UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    match_score DOUBLE PRECISION NOT NULL,
    ats_score   DOUBLE PRECISION,
    skill_gap   JSONB,
    reasoning   TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_job_match_user_job_resume UNIQUE (user_id, job_id, resume_id)
);

CREATE INDEX IF NOT EXISTS idx_job_matches_user_id     ON job_matches (user_id);
CREATE INDEX IF NOT EXISTS idx_job_matches_job_id      ON job_matches (job_id);
CREATE INDEX IF NOT EXISTS idx_job_matches_resume_id   ON job_matches (resume_id);
CREATE INDEX IF NOT EXISTS idx_job_matches_match_score ON job_matches (match_score DESC);
CREATE INDEX IF NOT EXISTS idx_job_matches_created_at  ON job_matches (created_at DESC);

-- ============================================================
-- TABLE: applications
-- ============================================================

CREATE TABLE IF NOT EXISTS applications (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id         UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    status         application_status_enum NOT NULL DEFAULT 'saved',
    applied_at     TIMESTAMPTZ,
    notes          TEXT,
    follow_up_date TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_application_user_job UNIQUE (user_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_applications_user_id    ON applications (user_id);
CREATE INDEX IF NOT EXISTS idx_applications_job_id     ON applications (job_id);
CREATE INDEX IF NOT EXISTS idx_applications_status     ON applications (status);
CREATE INDEX IF NOT EXISTS idx_applications_created_at ON applications (created_at DESC);

DROP TRIGGER IF EXISTS trg_applications_updated_at ON applications;
CREATE TRIGGER trg_applications_updated_at
    BEFORE UPDATE ON applications
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- TABLE: notifications
-- ============================================================

CREATE TABLE IF NOT EXISTS notifications (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type       notification_type_enum NOT NULL,
    title      VARCHAR(255) NOT NULL,
    message    TEXT NOT NULL,
    is_read    BOOLEAN NOT NULL DEFAULT FALSE,
    data       JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id    ON notifications (user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read    ON notifications (is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread
    ON notifications (user_id, is_read)
    WHERE is_read = FALSE;

-- ============================================================
-- TABLE: user_skills
-- ============================================================

CREATE TABLE IF NOT EXISTS user_skills (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_name        VARCHAR(255) NOT NULL,
    proficiency_level proficiency_level_enum NOT NULL DEFAULT 'intermediate',
    years_experience  DOUBLE PRECISION,
    is_verified       BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT uq_user_skill UNIQUE (user_id, skill_name)
);

CREATE INDEX IF NOT EXISTS idx_user_skills_user_id    ON user_skills (user_id);
CREATE INDEX IF NOT EXISTS idx_user_skills_skill_name ON user_skills (skill_name);

-- ============================================================
-- TABLE: career_roadmaps
-- ============================================================

CREATE TABLE IF NOT EXISTS career_roadmaps (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    current_role VARCHAR(255),
    target_role  VARCHAR(255),
    roadmap_data JSONB,
    progress     INTEGER NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_career_roadmaps_user_id ON career_roadmaps (user_id);

DROP TRIGGER IF EXISTS trg_career_roadmaps_updated_at ON career_roadmaps;
CREATE TRIGGER trg_career_roadmaps_updated_at
    BEFORE UPDATE ON career_roadmaps
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- TABLE: interview_sessions
-- ============================================================

CREATE TABLE IF NOT EXISTS interview_sessions (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id       UUID REFERENCES jobs(id) ON DELETE SET NULL,
    session_data JSONB,
    score        DOUBLE PRECISION,
    feedback     TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_interview_sessions_user_id    ON interview_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_interview_sessions_job_id     ON interview_sessions (job_id);
CREATE INDEX IF NOT EXISTS idx_interview_sessions_created_at ON interview_sessions (created_at DESC);

-- ============================================================
-- TABLE: audit_logs
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id       UUID REFERENCES users(id) ON DELETE SET NULL,
    action        VARCHAR(128) NOT NULL,
    resource_type VARCHAR(128),
    resource_id   VARCHAR(255),
    details       JSONB,
    ip_address    VARCHAR(45),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id       ON audit_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action        ON audit_logs (action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource_type ON audit_logs (resource_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at    ON audit_logs (created_at DESC);

-- ============================================================
-- Migration bookkeeping table (optional but recommended)
-- ============================================================

CREATE TABLE IF NOT EXISTS schema_migrations (
    version    VARCHAR(64) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO schema_migrations (version) VALUES ('001_initial')
ON CONFLICT (version) DO NOTHING;
