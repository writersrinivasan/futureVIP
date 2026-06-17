-- =============================================================================
--  FUTURE VIP — Initial Database Schema
--  Migration: 001_initial.sql
--  Description: Full schema for the Agentic AI Career Intelligence Platform
--  Idempotent: uses CREATE TABLE IF NOT EXISTS, CREATE INDEX IF NOT EXISTS, etc.
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- Trigram indexes for fuzzy text search
CREATE EXTENSION IF NOT EXISTS "unaccent";  -- Accent-insensitive search

-- =============================================================================
--  ENUMS
-- =============================================================================

DO $$ BEGIN
    CREATE TYPE application_status AS ENUM (
        'saved',
        'applied',
        'screening',
        'interview',
        'offer',
        'accepted',
        'rejected',
        'withdrawn'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE job_type AS ENUM (
        'full_time',
        'part_time',
        'contract',
        'freelance',
        'internship'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE notification_type AS ENUM (
        'job_match',
        'application_update',
        'resume_analyzed',
        'career_milestone',
        'system',
        'weekly_digest'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE skill_proficiency AS ENUM (
        'beginner',
        'intermediate',
        'advanced',
        'expert'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE user_role AS ENUM (
        'admin',
        'user',
        'premium'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE job_source AS ENUM (
        'adzuna',
        'jsearch',
        'usajobs',
        'linkedin',
        'indeed',
        'manual'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- =============================================================================
--  FUNCTION: updated_at auto-trigger
-- =============================================================================

CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
--  TABLE: users
-- =============================================================================

CREATE TABLE IF NOT EXISTS users (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email               VARCHAR(320) NOT NULL UNIQUE,
    hashed_password     TEXT NOT NULL,
    full_name           VARCHAR(255),
    role                user_role NOT NULL DEFAULT 'user',
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified         BOOLEAN NOT NULL DEFAULT FALSE,
    verification_token  TEXT,
    reset_token         TEXT,
    reset_token_expires TIMESTAMPTZ,
    avatar_url          TEXT,
    -- Profile / preferences stored as flexible JSONB
    profile             JSONB NOT NULL DEFAULT '{}'::JSONB,
    -- Job preferences: location, remote, salary range, etc.
    preferences         JSONB NOT NULL DEFAULT '{}'::JSONB,
    -- Subscription / feature flags
    subscription_tier   VARCHAR(50) NOT NULL DEFAULT 'free',
    subscription_ends   TIMESTAMPTZ,
    -- Timestamps
    last_login_at       TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_role  ON users (role);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users (is_active);
CREATE INDEX IF NOT EXISTS idx_users_profile   ON users USING GIN (profile);
CREATE INDEX IF NOT EXISTS idx_users_preferences ON users USING GIN (preferences);

DROP TRIGGER IF EXISTS set_users_updated_at ON users;
CREATE TRIGGER set_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- =============================================================================
--  TABLE: resumes
-- =============================================================================

CREATE TABLE IF NOT EXISTS resumes (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename            VARCHAR(500) NOT NULL,
    original_filename   VARCHAR(500) NOT NULL,
    file_path           TEXT NOT NULL,
    file_size_bytes     INTEGER,
    mime_type           VARCHAR(100),
    -- Extracted structured content
    extracted_text      TEXT,
    parsed_data         JSONB NOT NULL DEFAULT '{}'::JSONB,
    -- AI analysis results
    skills              JSONB NOT NULL DEFAULT '[]'::JSONB,
    experience_years    NUMERIC(4, 1),
    education_level     VARCHAR(100),
    job_titles          JSONB NOT NULL DEFAULT '[]'::JSONB,
    ai_summary          TEXT,
    ai_score            NUMERIC(4, 2),          -- Overall resume quality 0-100
    ats_score           NUMERIC(4, 2),           -- ATS compatibility score
    improvement_tips    JSONB NOT NULL DEFAULT '[]'::JSONB,
    -- ChromaDB embedding reference
    embedding_id        TEXT,
    is_primary          BOOLEAN NOT NULL DEFAULT FALSE,
    -- Timestamps
    analyzed_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resumes_user_id   ON resumes (user_id);
CREATE INDEX IF NOT EXISTS idx_resumes_is_primary ON resumes (user_id, is_primary);
CREATE INDEX IF NOT EXISTS idx_resumes_skills    ON resumes USING GIN (skills);
CREATE INDEX IF NOT EXISTS idx_resumes_parsed_data ON resumes USING GIN (parsed_data);

DROP TRIGGER IF EXISTS set_resumes_updated_at ON resumes;
CREATE TRIGGER set_resumes_updated_at
    BEFORE UPDATE ON resumes
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- =============================================================================
--  TABLE: jobs
-- =============================================================================

CREATE TABLE IF NOT EXISTS jobs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- External source tracking
    external_id         VARCHAR(500),
    source              job_source NOT NULL DEFAULT 'manual',
    source_url          TEXT,
    -- Core job info
    title               VARCHAR(500) NOT NULL,
    company             VARCHAR(500) NOT NULL,
    company_logo_url    TEXT,
    location            VARCHAR(500),
    is_remote           BOOLEAN NOT NULL DEFAULT FALSE,
    is_hybrid           BOOLEAN NOT NULL DEFAULT FALSE,
    job_type            job_type NOT NULL DEFAULT 'full_time',
    -- Compensation
    salary_min          INTEGER,
    salary_max          INTEGER,
    salary_currency     CHAR(3) DEFAULT 'USD',
    salary_period       VARCHAR(20) DEFAULT 'yearly',  -- 'yearly', 'monthly', 'hourly'
    -- Content
    description         TEXT NOT NULL,
    requirements        JSONB NOT NULL DEFAULT '[]'::JSONB,
    responsibilities    JSONB NOT NULL DEFAULT '[]'::JSONB,
    benefits            JSONB NOT NULL DEFAULT '[]'::JSONB,
    -- Taxonomy
    required_skills     JSONB NOT NULL DEFAULT '[]'::JSONB,
    preferred_skills    JSONB NOT NULL DEFAULT '[]'::JSONB,
    experience_level    VARCHAR(100),
    experience_years_min INTEGER,
    experience_years_max INTEGER,
    education_required  VARCHAR(100),
    department          VARCHAR(255),
    industry            VARCHAR(255),
    -- Metadata
    posted_at           TIMESTAMPTZ,
    expires_at          TIMESTAMPTZ,
    application_url     TEXT,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    -- Full-text search vector (auto-maintained by trigger)
    search_vector       TSVECTOR,
    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Unique constraint to avoid duplicate ingestion
    CONSTRAINT uq_jobs_external UNIQUE (source, external_id)
);

-- Standard indexes
CREATE INDEX IF NOT EXISTS idx_jobs_source      ON jobs (source);
CREATE INDEX IF NOT EXISTS idx_jobs_is_active   ON jobs (is_active);
CREATE INDEX IF NOT EXISTS idx_jobs_posted_at   ON jobs (posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_job_type    ON jobs (job_type);
CREATE INDEX IF NOT EXISTS idx_jobs_location    ON jobs (location);
CREATE INDEX IF NOT EXISTS idx_jobs_salary_min  ON jobs (salary_min);
CREATE INDEX IF NOT EXISTS idx_jobs_is_remote   ON jobs (is_remote);
-- JSONB indexes
CREATE INDEX IF NOT EXISTS idx_jobs_required_skills   ON jobs USING GIN (required_skills);
CREATE INDEX IF NOT EXISTS idx_jobs_preferred_skills  ON jobs USING GIN (preferred_skills);
-- Full-text search
CREATE INDEX IF NOT EXISTS idx_jobs_search_vector ON jobs USING GIN (search_vector);
-- Trigram index for fuzzy company/title search
CREATE INDEX IF NOT EXISTS idx_jobs_title_trgm   ON jobs USING GIN (title   gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_jobs_company_trgm ON jobs USING GIN (company gin_trgm_ops);

-- Trigger: maintain full-text search vector
CREATE OR REPLACE FUNCTION jobs_update_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.company, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.location, '')), 'D');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trig_jobs_search_vector ON jobs;
CREATE TRIGGER trig_jobs_search_vector
    BEFORE INSERT OR UPDATE OF title, company, description, location
    ON jobs
    FOR EACH ROW EXECUTE FUNCTION jobs_update_search_vector();

DROP TRIGGER IF EXISTS set_jobs_updated_at ON jobs;
CREATE TRIGGER set_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- =============================================================================
--  TABLE: job_matches
-- =============================================================================

CREATE TABLE IF NOT EXISTS job_matches (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id              UUID NOT NULL REFERENCES jobs(id)  ON DELETE CASCADE,
    resume_id           UUID REFERENCES resumes(id) ON DELETE SET NULL,
    -- Match quality scores (0.0 – 1.0)
    overall_score       NUMERIC(5, 4) NOT NULL DEFAULT 0,
    skills_score        NUMERIC(5, 4) NOT NULL DEFAULT 0,
    experience_score    NUMERIC(5, 4) NOT NULL DEFAULT 0,
    education_score     NUMERIC(5, 4) NOT NULL DEFAULT 0,
    location_score      NUMERIC(5, 4) NOT NULL DEFAULT 0,
    salary_score        NUMERIC(5, 4) NOT NULL DEFAULT 0,
    -- Detailed match breakdown
    matched_skills      JSONB NOT NULL DEFAULT '[]'::JSONB,
    missing_skills      JSONB NOT NULL DEFAULT '[]'::JSONB,
    match_explanation   TEXT,
    ai_recommendation   TEXT,
    -- User interaction
    is_dismissed        BOOLEAN NOT NULL DEFAULT FALSE,
    is_saved            BOOLEAN NOT NULL DEFAULT FALSE,
    viewed_at           TIMESTAMPTZ,
    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_job_match_user_job UNIQUE (user_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_job_matches_user_id      ON job_matches (user_id);
CREATE INDEX IF NOT EXISTS idx_job_matches_job_id       ON job_matches (job_id);
CREATE INDEX IF NOT EXISTS idx_job_matches_score        ON job_matches (user_id, overall_score DESC);
CREATE INDEX IF NOT EXISTS idx_job_matches_dismissed    ON job_matches (user_id, is_dismissed);
CREATE INDEX IF NOT EXISTS idx_job_matches_saved        ON job_matches (user_id, is_saved);
CREATE INDEX IF NOT EXISTS idx_job_matches_matched_skills ON job_matches USING GIN (matched_skills);
CREATE INDEX IF NOT EXISTS idx_job_matches_missing_skills ON job_matches USING GIN (missing_skills);

DROP TRIGGER IF EXISTS set_job_matches_updated_at ON job_matches;
CREATE TRIGGER set_job_matches_updated_at
    BEFORE UPDATE ON job_matches
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- =============================================================================
--  TABLE: applications
-- =============================================================================

CREATE TABLE IF NOT EXISTS applications (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
    job_id              UUID NOT NULL REFERENCES jobs(id)    ON DELETE CASCADE,
    resume_id           UUID         REFERENCES resumes(id)  ON DELETE SET NULL,
    -- Status tracking
    status              application_status NOT NULL DEFAULT 'saved',
    applied_at          TIMESTAMPTZ,
    -- Application details
    cover_letter        TEXT,
    custom_answers      JSONB NOT NULL DEFAULT '{}'::JSONB,
    application_url     TEXT,
    -- Tracking / notes
    recruiter_name      VARCHAR(255),
    recruiter_email     VARCHAR(320),
    notes               TEXT,
    salary_negotiated   INTEGER,
    -- Interview tracking
    interview_dates     JSONB NOT NULL DEFAULT '[]'::JSONB,
    -- Outcome
    rejection_reason    TEXT,
    offer_amount        INTEGER,
    offer_deadline      TIMESTAMPTZ,
    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_application_user_job UNIQUE (user_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_applications_user_id   ON applications (user_id);
CREATE INDEX IF NOT EXISTS idx_applications_job_id    ON applications (job_id);
CREATE INDEX IF NOT EXISTS idx_applications_status    ON applications (user_id, status);
CREATE INDEX IF NOT EXISTS idx_applications_applied_at ON applications (user_id, applied_at DESC);

DROP TRIGGER IF EXISTS set_applications_updated_at ON applications;
CREATE TRIGGER set_applications_updated_at
    BEFORE UPDATE ON applications
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- =============================================================================
--  TABLE: notifications
-- =============================================================================

CREATE TABLE IF NOT EXISTS notifications (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type                notification_type NOT NULL,
    title               VARCHAR(500) NOT NULL,
    message             TEXT NOT NULL,
    -- Optional links
    action_url          TEXT,
    action_label        VARCHAR(100),
    -- Related entities
    related_job_id      UUID REFERENCES jobs(id)         ON DELETE SET NULL,
    related_resume_id   UUID REFERENCES resumes(id)      ON DELETE SET NULL,
    related_app_id      UUID REFERENCES applications(id) ON DELETE SET NULL,
    -- State
    is_read             BOOLEAN NOT NULL DEFAULT FALSE,
    is_email_sent       BOOLEAN NOT NULL DEFAULT FALSE,
    is_push_sent        BOOLEAN NOT NULL DEFAULT FALSE,
    read_at             TIMESTAMPTZ,
    -- Metadata
    metadata            JSONB NOT NULL DEFAULT '{}'::JSONB,
    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id   ON notifications (user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read   ON notifications (user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_type      ON notifications (user_id, type);
CREATE INDEX IF NOT EXISTS idx_notifications_created   ON notifications (user_id, created_at DESC);

DROP TRIGGER IF EXISTS set_notifications_updated_at ON notifications;
CREATE TRIGGER set_notifications_updated_at
    BEFORE UPDATE ON notifications
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- =============================================================================
--  TABLE: user_skills
-- =============================================================================

CREATE TABLE IF NOT EXISTS user_skills (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_name          VARCHAR(255) NOT NULL,
    skill_category      VARCHAR(100),         -- 'programming', 'data', 'management', etc.
    proficiency         skill_proficiency NOT NULL DEFAULT 'intermediate',
    years_of_experience NUMERIC(4, 1),
    is_verified         BOOLEAN NOT NULL DEFAULT FALSE,
    verified_by         VARCHAR(100),         -- 'resume', 'assessment', 'linkedin', etc.
    last_used_at        TIMESTAMPTZ,
    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_skill UNIQUE (user_id, skill_name)
);

CREATE INDEX IF NOT EXISTS idx_user_skills_user_id      ON user_skills (user_id);
CREATE INDEX IF NOT EXISTS idx_user_skills_skill_name   ON user_skills (skill_name);
CREATE INDEX IF NOT EXISTS idx_user_skills_category     ON user_skills (skill_category);
CREATE INDEX IF NOT EXISTS idx_user_skills_proficiency  ON user_skills (proficiency);
-- Trigram for fuzzy skill search
CREATE INDEX IF NOT EXISTS idx_user_skills_trgm ON user_skills USING GIN (skill_name gin_trgm_ops);

DROP TRIGGER IF EXISTS set_user_skills_updated_at ON user_skills;
CREATE TRIGGER set_user_skills_updated_at
    BEFORE UPDATE ON user_skills
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- =============================================================================
--  TABLE: career_roadmaps
-- =============================================================================

CREATE TABLE IF NOT EXISTS career_roadmaps (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title               VARCHAR(500) NOT NULL,
    target_role         VARCHAR(500),
    target_industry     VARCHAR(255),
    current_role        VARCHAR(500),
    timeline_months     INTEGER,
    -- AI-generated roadmap content
    milestones          JSONB NOT NULL DEFAULT '[]'::JSONB,
    skill_gaps          JSONB NOT NULL DEFAULT '[]'::JSONB,
    recommended_courses JSONB NOT NULL DEFAULT '[]'::JSONB,
    recommended_certs   JSONB NOT NULL DEFAULT '[]'::JSONB,
    action_items        JSONB NOT NULL DEFAULT '[]'::JSONB,
    -- Progress tracking
    completion_pct      NUMERIC(5, 2) NOT NULL DEFAULT 0,
    completed_milestones JSONB NOT NULL DEFAULT '[]'::JSONB,
    -- State
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    ai_generated        BOOLEAN NOT NULL DEFAULT TRUE,
    -- Timestamps
    generated_at        TIMESTAMPTZ DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_career_roadmaps_user_id    ON career_roadmaps (user_id);
CREATE INDEX IF NOT EXISTS idx_career_roadmaps_is_active  ON career_roadmaps (user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_career_roadmaps_milestones ON career_roadmaps USING GIN (milestones);
CREATE INDEX IF NOT EXISTS idx_career_roadmaps_skill_gaps ON career_roadmaps USING GIN (skill_gaps);

DROP TRIGGER IF EXISTS set_career_roadmaps_updated_at ON career_roadmaps;
CREATE TRIGGER set_career_roadmaps_updated_at
    BEFORE UPDATE ON career_roadmaps
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- =============================================================================
--  TABLE: interview_sessions
-- =============================================================================

CREATE TABLE IF NOT EXISTS interview_sessions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id)        ON DELETE CASCADE,
    application_id      UUID         REFERENCES applications(id)  ON DELETE SET NULL,
    job_id              UUID         REFERENCES jobs(id)           ON DELETE SET NULL,
    -- Session metadata
    session_type        VARCHAR(100) NOT NULL DEFAULT 'practice', -- 'practice', 'mock', 'real'
    interview_type      VARCHAR(100),  -- 'behavioral', 'technical', 'case', 'panel'
    difficulty          VARCHAR(50) DEFAULT 'medium',
    -- Content
    questions           JSONB NOT NULL DEFAULT '[]'::JSONB,
    answers             JSONB NOT NULL DEFAULT '[]'::JSONB,
    -- AI feedback
    overall_score       NUMERIC(4, 2),
    strengths           JSONB NOT NULL DEFAULT '[]'::JSONB,
    weaknesses          JSONB NOT NULL DEFAULT '[]'::JSONB,
    ai_feedback         TEXT,
    improvement_areas   JSONB NOT NULL DEFAULT '[]'::JSONB,
    -- Session state
    status              VARCHAR(50) NOT NULL DEFAULT 'in_progress',  -- 'in_progress', 'completed', 'abandoned'
    started_at          TIMESTAMPTZ DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    duration_seconds    INTEGER,
    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_interview_sessions_user_id    ON interview_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_interview_sessions_app_id     ON interview_sessions (application_id);
CREATE INDEX IF NOT EXISTS idx_interview_sessions_status     ON interview_sessions (user_id, status);
CREATE INDEX IF NOT EXISTS idx_interview_sessions_type       ON interview_sessions (interview_type);
CREATE INDEX IF NOT EXISTS idx_interview_sessions_questions  ON interview_sessions USING GIN (questions);

DROP TRIGGER IF EXISTS set_interview_sessions_updated_at ON interview_sessions;
CREATE TRIGGER set_interview_sessions_updated_at
    BEFORE UPDATE ON interview_sessions
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- =============================================================================
--  TABLE: audit_logs
-- =============================================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- Actor
    user_id             UUID         REFERENCES users(id) ON DELETE SET NULL,
    actor_email         VARCHAR(320),
    actor_ip            INET,
    actor_user_agent    TEXT,
    -- Action
    action              VARCHAR(255) NOT NULL,
    entity_type         VARCHAR(100),
    entity_id           UUID,
    -- Before/after state (for mutations)
    old_values          JSONB,
    new_values          JSONB,
    -- Context
    request_id          UUID,
    status              VARCHAR(50) NOT NULL DEFAULT 'success',  -- 'success', 'failure', 'error'
    error_message       TEXT,
    metadata            JSONB NOT NULL DEFAULT '{}'::JSONB,
    -- Timestamp (no updated_at — audit log is append-only)
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Partition hint: in high-volume production, consider partitioning by created_at
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id     ON audit_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action      ON audit_logs (action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity      ON audit_logs (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at  ON audit_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_status      ON audit_logs (status);
CREATE INDEX IF NOT EXISTS idx_audit_logs_metadata    ON audit_logs USING GIN (metadata);

-- =============================================================================
--  VIEWS
-- =============================================================================

-- User dashboard summary view
CREATE OR REPLACE VIEW v_user_dashboard AS
SELECT
    u.id AS user_id,
    u.full_name,
    u.email,
    COUNT(DISTINCT r.id)  FILTER (WHERE r.id IS NOT NULL) AS resume_count,
    COUNT(DISTINCT a.id)  FILTER (WHERE a.status = 'applied')     AS active_applications,
    COUNT(DISTINCT a.id)  FILTER (WHERE a.status = 'interview')   AS in_interview,
    COUNT(DISTINCT a.id)  FILTER (WHERE a.status = 'offer')       AS offers_received,
    COUNT(DISTINCT jm.id) FILTER (WHERE jm.overall_score >= 0.75 AND NOT jm.is_dismissed) AS top_matches,
    COUNT(DISTINCT n.id)  FILTER (WHERE NOT n.is_read)            AS unread_notifications
FROM users u
LEFT JOIN resumes r       ON r.user_id = u.id AND r.is_primary = TRUE
LEFT JOIN applications a  ON a.user_id = u.id
LEFT JOIN job_matches jm  ON jm.user_id = u.id
LEFT JOIN notifications n ON n.user_id = u.id
GROUP BY u.id, u.full_name, u.email;

-- Job match leaderboard view
CREATE OR REPLACE VIEW v_top_job_matches AS
SELECT
    jm.user_id,
    j.id AS job_id,
    j.title,
    j.company,
    j.location,
    j.is_remote,
    j.salary_min,
    j.salary_max,
    jm.overall_score,
    jm.skills_score,
    jm.matched_skills,
    jm.missing_skills,
    jm.ai_recommendation,
    j.application_url,
    j.posted_at
FROM job_matches jm
JOIN jobs j ON j.id = jm.job_id
WHERE NOT jm.is_dismissed
  AND j.is_active = TRUE
ORDER BY jm.overall_score DESC;

-- =============================================================================
--  COMMENTS (documentation)
-- =============================================================================

COMMENT ON TABLE users              IS 'Platform user accounts with profile and preferences';
COMMENT ON TABLE resumes            IS 'Uploaded resumes with AI analysis results';
COMMENT ON TABLE jobs               IS 'Job listings aggregated from multiple external sources';
COMMENT ON TABLE job_matches        IS 'AI-computed match scores between users and jobs';
COMMENT ON TABLE applications       IS 'User job applications with full lifecycle tracking';
COMMENT ON TABLE notifications      IS 'In-app and email notification records';
COMMENT ON TABLE user_skills        IS 'User skill inventory extracted from resumes and self-reported';
COMMENT ON TABLE career_roadmaps    IS 'AI-generated personalized career development plans';
COMMENT ON TABLE interview_sessions IS 'AI-powered mock interview sessions and feedback';
COMMENT ON TABLE audit_logs         IS 'Immutable audit trail for all significant system actions';
