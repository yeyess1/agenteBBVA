-- ============================================================
-- Metrics table for RAG Assistant
-- Run once in Supabase SQL Editor to create the schema.
-- ============================================================

CREATE TABLE IF NOT EXISTS metrics_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- ── Identity ──────────────────────────────────────────
    user_id             VARCHAR(255) NOT NULL,
    session_id          VARCHAR(50),

    -- ── Request metadata ──────────────────────────────────
    query_length        INT          DEFAULT 0,
    answer_length       INT          DEFAULT 0,
    total_latency_ms    FLOAT,
    success             BOOLEAN      DEFAULT TRUE,
    error_message       TEXT,

    -- ── Retrieval metrics ─────────────────────────────────
    retrieval_latency_ms        FLOAT,
    retrieval_candidate_count   INT     DEFAULT 0,   -- docs before threshold filter
    retrieval_document_count    INT     DEFAULT 0,   -- docs after threshold + MMR
    retrieval_threshold_filtered INT    DEFAULT 0,   -- docs removed by threshold
    retrieval_avg_score         FLOAT   DEFAULT 0,
    retrieval_top_score         FLOAT   DEFAULT 0,
    context_quality             VARCHAR(20) DEFAULT 'none',  -- high|medium|low|none
    mmr_applied                 BOOLEAN DEFAULT FALSE,

    -- ── Generation metrics ────────────────────────────────
    generation_latency_ms   FLOAT,
    input_tokens            INT     DEFAULT 0,
    output_tokens           INT     DEFAULT 0,
    total_tokens            INT     DEFAULT 0,
    model_used              VARCHAR(100),
    estimated_cost_usd      FLOAT   DEFAULT 0,

    -- ── Timestamps ────────────────────────────────────────
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at  TIMESTAMPTZ          DEFAULT NOW()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_metrics_user_id
    ON metrics_requests (user_id);

CREATE INDEX IF NOT EXISTS idx_metrics_timestamp
    ON metrics_requests (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_metrics_user_ts
    ON metrics_requests (user_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_metrics_context_quality
    ON metrics_requests (context_quality);

-- Optional: enable Row Level Security
-- ALTER TABLE metrics_requests ENABLE ROW LEVEL SECURITY;
