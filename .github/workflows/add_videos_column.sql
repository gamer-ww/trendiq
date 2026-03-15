-- Ye SQL Supabase SQL Editor mein run karo
-- youtube_videos column add karne ke liye

ALTER TABLE trendiq_data ADD COLUMN IF NOT EXISTS youtube_videos JSONB DEFAULT '{}';
