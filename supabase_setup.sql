-- TrendIQ Database Setup
-- Ye SQL Supabase ke SQL Editor mein paste karo

CREATE TABLE IF NOT EXISTS trendiq_data (
  id            BIGSERIAL PRIMARY KEY,
  fetched_at    TIMESTAMPTZ DEFAULT NOW(),
  topics        JSONB DEFAULT '[]',
  recommendations JSONB DEFAULT '[]',
  trending_audios JSONB DEFAULT '[]',
  stats         JSONB DEFAULT '{}'
);

-- Public read access do (dashboard ke liye zaroori hai)
ALTER TABLE trendiq_data ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read allowed"
  ON trendiq_data FOR SELECT
  USING (true);

-- Index for fast queries
CREATE INDEX idx_fetched_at ON trendiq_data(fetched_at DESC);
