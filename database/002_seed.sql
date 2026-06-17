-- =============================================================================
--  FUTURE VIP — Seed Data
--  Migration: 002_seed.sql
--  Description: Initial data for development/demo environments
--  Idempotent: uses INSERT ... ON CONFLICT DO NOTHING
-- =============================================================================

-- =============================================================================
--  ADMIN USER
--  Password: FutureVIP@Admin2025!
--  Hash generated with: python3 -c "import bcrypt; print(bcrypt.hashpw(b'FutureVIP@Admin2025!', bcrypt.gensalt(12)).decode())"
-- =============================================================================

INSERT INTO users (
    id,
    email,
    hashed_password,
    full_name,
    role,
    is_active,
    is_verified,
    profile,
    preferences,
    subscription_tier
) VALUES (
    '00000000-0000-0000-0000-000000000001',
    'admin@futurevip.ai',
    '$2b$12$LQv3c1yqBwlVHpPjrC/oneFlFETRdkONKFTXUHiZ5DWwMBmzfqoIa',
    'FutureVIP Admin',
    'admin',
    TRUE,
    TRUE,
    '{"bio": "Platform administrator", "company": "FutureVIP", "title": "Platform Admin"}',
    '{"remote": true, "job_types": ["full_time"], "salary_min": 100000}',
    'enterprise'
)
ON CONFLICT (email) DO NOTHING;

-- =============================================================================
--  DEMO USER
--  Password: DemoUser@2025!
-- =============================================================================

INSERT INTO users (
    id,
    email,
    hashed_password,
    full_name,
    role,
    is_active,
    is_verified,
    profile,
    preferences,
    subscription_tier
) VALUES (
    '00000000-0000-0000-0000-000000000002',
    'demo@futurevip.ai',
    '$2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWEHB',
    'Alex Johnson',
    'premium',
    TRUE,
    TRUE,
    '{"bio": "Senior software engineer with 7 years of experience", "location": "San Francisco, CA", "title": "Senior Software Engineer", "linkedin": "https://linkedin.com/in/alexjohnson"}',
    '{"remote": true, "hybrid": true, "job_types": ["full_time"], "salary_min": 150000, "preferred_locations": ["San Francisco", "New York", "Austin"], "industries": ["technology", "fintech", "ai"]}',
    'premium'
)
ON CONFLICT (email) DO NOTHING;

-- =============================================================================
--  SAMPLE SKILLS FOR DEMO USER
-- =============================================================================

INSERT INTO user_skills (id, user_id, skill_name, skill_category, proficiency, years_of_experience, is_verified, verified_by)
VALUES
    (uuid_generate_v4(), '00000000-0000-0000-0000-000000000002', 'Python',          'programming',  'expert',        7.0, TRUE,  'resume'),
    (uuid_generate_v4(), '00000000-0000-0000-0000-000000000002', 'JavaScript',      'programming',  'advanced',      5.0, TRUE,  'resume'),
    (uuid_generate_v4(), '00000000-0000-0000-0000-000000000002', 'TypeScript',      'programming',  'advanced',      4.0, TRUE,  'resume'),
    (uuid_generate_v4(), '00000000-0000-0000-0000-000000000002', 'React',           'frontend',     'advanced',      4.0, TRUE,  'resume'),
    (uuid_generate_v4(), '00000000-0000-0000-0000-000000000002', 'FastAPI',         'backend',      'expert',        3.0, TRUE,  'resume'),
    (uuid_generate_v4(), '00000000-0000-0000-0000-000000000002', 'PostgreSQL',      'database',     'advanced',      5.0, TRUE,  'resume'),
    (uuid_generate_v4(), '00000000-0000-0000-0000-000000000002', 'Docker',          'devops',       'intermediate',  3.0, TRUE,  'resume'),
    (uuid_generate_v4(), '00000000-0000-0000-0000-000000000002', 'Kubernetes',      'devops',       'intermediate',  2.0, FALSE, 'resume'),
    (uuid_generate_v4(), '00000000-0000-0000-0000-000000000002', 'Machine Learning','ai_ml',        'intermediate',  2.0, FALSE, 'resume'),
    (uuid_generate_v4(), '00000000-0000-0000-0000-000000000002', 'AWS',             'cloud',        'advanced',      4.0, TRUE,  'resume')
ON CONFLICT (user_id, skill_name) DO NOTHING;

-- =============================================================================
--  SAMPLE JOBS (10 listings from various sources)
-- =============================================================================

INSERT INTO jobs (
    id, external_id, source, source_url,
    title, company, company_logo_url, location, is_remote, is_hybrid,
    job_type, salary_min, salary_max, salary_currency,
    description, required_skills, preferred_skills,
    experience_level, experience_years_min, experience_years_max,
    education_required, industry, department, posted_at, is_active, application_url
) VALUES

-- Job 1: Senior Python Engineer
(
    '10000000-0000-0000-0000-000000000001',
    'adzuna-py-001', 'adzuna', 'https://www.adzuna.com/jobs/details/py-001',
    'Senior Python Engineer', 'Stripe', 'https://stripe.com/favicon.ico',
    'San Francisco, CA', TRUE, FALSE, 'full_time', 170000, 230000, 'USD',
    'Join Stripe as a Senior Python Engineer to build the financial infrastructure of the internet. You will work on high-throughput payment processing systems, design RESTful APIs, and contribute to our core platform serving millions of businesses worldwide. We value clean code, rigorous testing, and thoughtful system design.',
    '["Python", "FastAPI", "PostgreSQL", "Redis", "AWS", "Docker"]',
    '["Kubernetes", "Celery", "gRPC", "Go", "Kafka"]',
    'senior', 5, 10, 'bachelor', 'fintech', 'Platform Engineering',
    NOW() - INTERVAL '2 days', TRUE, 'https://stripe.com/jobs/py-001'
),

-- Job 2: ML Engineer
(
    '10000000-0000-0000-0000-000000000002',
    'jsearch-ml-002', 'jsearch', 'https://jsearch.io/jobs/ml-002',
    'Machine Learning Engineer', 'OpenAI', 'https://openai.com/favicon.ico',
    'San Francisco, CA', TRUE, TRUE, 'full_time', 200000, 300000, 'USD',
    'OpenAI is looking for an ML Engineer to help build and deploy large-scale language models. You will work on model training pipelines, fine-tuning strategies, inference optimization, and evaluation frameworks. This role requires deep expertise in PyTorch and distributed training.',
    '["Python", "PyTorch", "Machine Learning", "CUDA", "Distributed Systems"]',
    '["Transformers", "RLHF", "vLLM", "Triton", "C++"]',
    'senior', 4, 8, 'master', 'ai', 'Research Engineering',
    NOW() - INTERVAL '1 day', TRUE, 'https://openai.com/careers/ml-002'
),

-- Job 3: Full Stack Developer
(
    '10000000-0000-0000-0000-000000000003',
    'adzuna-fs-003', 'adzuna', 'https://www.adzuna.com/jobs/details/fs-003',
    'Senior Full Stack Developer', 'Airbnb', 'https://airbnb.com/favicon.ico',
    'New York, NY', FALSE, TRUE, 'full_time', 160000, 200000, 'USD',
    'Airbnb is hiring a Senior Full Stack Developer to work on host-facing products. You will build React frontends, Node.js/Python backends, and contribute to our design system. We prioritize developer experience, performance, and accessibility.',
    '["React", "TypeScript", "Python", "PostgreSQL", "GraphQL"]',
    '["Next.js", "Apollo", "Redis", "AWS Lambda", "Figma"]',
    'senior', 5, 9, 'bachelor', 'technology', 'Host Products',
    NOW() - INTERVAL '3 days', TRUE, 'https://airbnb.com/careers/fs-003'
),

-- Job 4: DevOps / Platform Engineer
(
    '10000000-0000-0000-0000-000000000004',
    'jsearch-devops-004', 'jsearch', 'https://jsearch.io/jobs/devops-004',
    'Senior DevOps / Platform Engineer', 'Netflix', 'https://netflix.com/favicon.ico',
    'Los Angeles, CA', TRUE, FALSE, 'full_time', 180000, 250000, 'USD',
    'Netflix is looking for a Platform Engineer to improve developer experience and platform reliability at massive scale. You will work on container orchestration, CI/CD pipelines, observability, and infrastructure automation supporting our global streaming platform.',
    '["Kubernetes", "Docker", "Terraform", "AWS", "Python", "Prometheus"]',
    '["Spinnaker", "Argo CD", "Datadog", "Go", "Linux"]',
    'senior', 6, 12, 'bachelor', 'technology', 'Platform Engineering',
    NOW() - INTERVAL '4 days', TRUE, 'https://netflix.com/jobs/devops-004'
),

-- Job 5: Data Scientist
(
    '10000000-0000-0000-0000-000000000005',
    'adzuna-ds-005', 'adzuna', 'https://www.adzuna.com/jobs/details/ds-005',
    'Lead Data Scientist', 'Spotify', 'https://spotify.com/favicon.ico',
    'New York, NY', FALSE, TRUE, 'full_time', 155000, 195000, 'USD',
    'Join Spotify as a Lead Data Scientist driving recommendations and personalization. You will analyze petabyte-scale listening data, build ML models for discovery features, and partner with product teams to deliver measurable impact for 600M+ users.',
    '["Python", "Machine Learning", "SQL", "Spark", "Statistics"]',
    '["Scala", "Hadoop", "A/B Testing", "Deep Learning", "Causal Inference"]',
    'lead', 5, 10, 'master', 'technology', 'Personalization',
    NOW() - INTERVAL '5 days', TRUE, 'https://spotify.com/careers/ds-005'
),

-- Job 6: Backend Engineer (Go)
(
    '10000000-0000-0000-0000-000000000006',
    'jsearch-go-006', 'jsearch', 'https://jsearch.io/jobs/go-006',
    'Senior Backend Engineer (Go)', 'Uber', 'https://uber.com/favicon.ico',
    'Austin, TX', FALSE, TRUE, 'full_time', 165000, 215000, 'USD',
    'Uber is hiring a Backend Engineer to build the distributed services powering the Uber platform. You will design high-availability microservices in Go, optimize for sub-millisecond latency, and contribute to our engineering culture of reliability and scale.',
    '["Go", "Microservices", "gRPC", "Kafka", "MySQL", "Kubernetes"]',
    '["Python", "Java", "Prometheus", "Jaeger", "Redis"]',
    'senior', 5, 10, 'bachelor', 'technology', 'Core Platform',
    NOW() - INTERVAL '6 days', TRUE, 'https://uber.com/careers/go-006'
),

-- Job 7: AI/LLM Product Engineer
(
    '10000000-0000-0000-0000-000000000007',
    'adzuna-ai-007', 'adzuna', 'https://www.adzuna.com/jobs/details/ai-007',
    'AI Product Engineer (LLMs)', 'Anthropic', 'https://anthropic.com/favicon.ico',
    'San Francisco, CA', TRUE, FALSE, 'full_time', 200000, 280000, 'USD',
    'Anthropic is building AI systems that are safe, beneficial, and understandable. As an AI Product Engineer, you will integrate Claude into products, build agentic workflows, optimize prompts at scale, and create evaluation frameworks to measure AI quality.',
    '["Python", "LLMs", "FastAPI", "TypeScript", "Prompt Engineering"]',
    '["Constitutional AI", "RAG", "LangChain", "Vector Databases", "React"]',
    'senior', 4, 8, 'bachelor', 'ai', 'Product Engineering',
    NOW() - INTERVAL '1 day', TRUE, 'https://anthropic.com/careers/ai-007'
),

-- Job 8: Frontend Engineer (React)
(
    '10000000-0000-0000-0000-000000000008',
    'jsearch-fe-008', 'jsearch', 'https://jsearch.io/jobs/fe-008',
    'Senior Frontend Engineer', 'Figma', 'https://figma.com/favicon.ico',
    'San Francisco, CA', FALSE, TRUE, 'full_time', 155000, 200000, 'USD',
    'Figma is looking for a Senior Frontend Engineer to build the collaborative design tools used by millions of designers. You will work on canvas rendering, real-time collaboration, plugin APIs, and our React-based UI layer.',
    '["React", "TypeScript", "JavaScript", "WebGL", "CSS"]',
    '["Rust", "WebAssembly", "GraphQL", "Canvas API", "Node.js"]',
    'senior', 5, 9, 'bachelor', 'technology', 'Editor Experience',
    NOW() - INTERVAL '7 days', TRUE, 'https://figma.com/careers/fe-008'
),

-- Job 9: Government / Federal Tech Lead
(
    '10000000-0000-0000-0000-000000000009',
    'usajobs-gov-009', 'usajobs', 'https://www.usajobs.gov/job/gov-009',
    'IT Specialist (Application Software)', 'U.S. Digital Service', NULL,
    'Washington, D.C.', TRUE, FALSE, 'full_time', 122000, 158000, 'USD',
    'The U.S. Digital Service is recruiting an IT Specialist to modernize critical government systems. You will work alongside federal agencies to replace legacy systems, improve digital service delivery, and apply modern software development practices to public-sector challenges.',
    '["Python", "JavaScript", "PostgreSQL", "Docker", "REST APIs"]',
    '["AWS GovCloud", "FedRAMP", "React", "Node.js", "Agile"]',
    'mid', 3, 7, 'bachelor', 'government', 'Technology Modernization',
    NOW() - INTERVAL '10 days', TRUE, 'https://www.usajobs.gov/apply/gov-009'
),

-- Job 10: Startup CTO / Tech Lead
(
    '10000000-0000-0000-0000-000000000010',
    'manual-cto-010', 'manual', NULL,
    'CTO / VP of Engineering', 'StealthAI Startup', NULL,
    'Remote', TRUE, FALSE, 'full_time', 160000, 220000, 'USD',
    'Series A AI startup is looking for a founding CTO / VP of Engineering to build and lead engineering from scratch. You will define the technical architecture, hire the first 10 engineers, and ship a production AI product from 0 to 1. Significant equity package available.',
    '["Python", "AWS", "Machine Learning", "System Design", "Team Leadership"]',
    '["FastAPI", "React", "Kubernetes", "LLMs", "Product Thinking"]',
    'executive', 8, 20, 'bachelor', 'ai', 'Executive',
    NOW() - INTERVAL '0 days', TRUE, 'mailto:cto@stealthai.example.com'
)

ON CONFLICT (source, external_id) DO NOTHING;

-- =============================================================================
--  SAMPLE JOB MATCHES FOR DEMO USER
-- =============================================================================

INSERT INTO job_matches (
    id, user_id, job_id,
    overall_score, skills_score, experience_score, education_score, location_score, salary_score,
    matched_skills, missing_skills, match_explanation, ai_recommendation
) VALUES
(
    uuid_generate_v4(),
    '00000000-0000-0000-0000-000000000002',
    '10000000-0000-0000-0000-000000000001',
    0.8900, 0.9200, 0.8500, 0.9000, 0.8000, 0.8900,
    '["Python", "FastAPI", "PostgreSQL", "Redis", "AWS", "Docker"]',
    '["Kubernetes", "Kafka"]',
    'Excellent match. Alex has all 6 required skills and 7 years of Python experience, exceeding the 5-year minimum.',
    'Apply immediately. Your Python/FastAPI/PostgreSQL stack is a perfect fit. Highlight your experience with high-throughput systems.'
),
(
    uuid_generate_v4(),
    '00000000-0000-0000-0000-000000000002',
    '10000000-0000-0000-0000-000000000007',
    0.8200, 0.8700, 0.8000, 0.8500, 0.9500, 0.7800,
    '["Python", "FastAPI", "TypeScript"]',
    '["LLMs", "Prompt Engineering", "RAG"]',
    'Strong match. Core stack aligns well. Developing LLM/prompt engineering experience would maximize fit.',
    'Consider taking a fast course on LangChain and RAG before applying. Your Python/FastAPI foundation is exactly what they need.'
),
(
    uuid_generate_v4(),
    '00000000-0000-0000-0000-000000000002',
    '10000000-0000-0000-0000-000000000003',
    0.7500, 0.8000, 0.7500, 0.9000, 0.7000, 0.8200,
    '["React", "TypeScript", "Python", "PostgreSQL"]',
    '["GraphQL", "Apollo", "Next.js"]',
    'Good match with room to grow. Frontend skills are strong; GraphQL experience would improve your candidacy.',
    'Apply with confidence on the backend requirements. Briefly mention your React experience; lead with Python/PostgreSQL.'
)
ON CONFLICT (user_id, job_id) DO NOTHING;

-- =============================================================================
--  SAMPLE NOTIFICATIONS FOR DEMO USER
-- =============================================================================

INSERT INTO notifications (
    id, user_id, type, title, message, action_url, action_label,
    related_job_id, is_read, is_email_sent
) VALUES
(
    uuid_generate_v4(),
    '00000000-0000-0000-0000-000000000002',
    'job_match',
    'New Top Match: Senior Python Engineer at Stripe',
    'We found a new job that matches 89% of your profile. Stripe is hiring a Senior Python Engineer — your Python and FastAPI experience is an excellent fit.',
    '/jobs/10000000-0000-0000-0000-000000000001',
    'View Job',
    '10000000-0000-0000-0000-000000000001',
    FALSE, TRUE
),
(
    uuid_generate_v4(),
    '00000000-0000-0000-0000-000000000002',
    'job_match',
    'Hot Match: AI Product Engineer at Anthropic',
    'Anthropic is looking for AI engineers with your exact Python/FastAPI stack. 82% match score — do not miss this one!',
    '/jobs/10000000-0000-0000-0000-000000000007',
    'View Job',
    '10000000-0000-0000-0000-000000000007',
    FALSE, TRUE
),
(
    uuid_generate_v4(),
    '00000000-0000-0000-0000-000000000002',
    'system',
    'Welcome to FUTURE VIP!',
    'Your account is set up and ready. Upload your resume to unlock AI-powered job matching, career roadmaps, and interview prep.',
    '/dashboard/resume',
    'Upload Resume',
    NULL,
    TRUE, TRUE
),
(
    uuid_generate_v4(),
    '00000000-0000-0000-0000-000000000002',
    'weekly_digest',
    'Your Weekly Career Intelligence Report',
    'This week: 10 new job matches found, 3 top opportunities identified. Your Python skills are trending up 12% in demand. View your full report.',
    '/dashboard/insights',
    'View Report',
    NULL,
    FALSE, TRUE
),
(
    uuid_generate_v4(),
    '00000000-0000-0000-0000-000000000002',
    'career_milestone',
    'Career Insight: ML is Your Next Frontier',
    'Based on your profile and market trends, adding Machine Learning to your skill set could increase your salary potential by 15-25%. We''ve prepared a personalized learning roadmap.',
    '/dashboard/roadmap',
    'View Roadmap',
    NULL,
    FALSE, FALSE
)
ON CONFLICT DO NOTHING;

-- =============================================================================
--  AUDIT LOG ENTRY for seeding
-- =============================================================================

INSERT INTO audit_logs (action, entity_type, status, metadata)
VALUES (
    'database.seed',
    'system',
    'success',
    '{"migration": "002_seed.sql", "records": {"users": 2, "jobs": 10, "user_skills": 10, "job_matches": 3, "notifications": 5}}'
);
