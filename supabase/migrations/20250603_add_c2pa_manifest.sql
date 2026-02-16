-- =============================================================
-- Add c2pa_manifest JSONB column to images table
-- =============================================================

ALTER TABLE public.images
    ADD COLUMN IF NOT EXISTS c2pa_manifest jsonb;
