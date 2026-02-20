-- =============================================================
-- images table  –  stores metadata for uploaded / protected images
-- =============================================================
-- Run this in the Supabase SQL Editor (https://supabase.com/dashboard → SQL Editor)
-- or via `supabase db push` if using the Supabase CLI.
-- =============================================================

-- 1. Create the table (idempotent)
CREATE TABLE IF NOT EXISTS public.images (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid NOT NULL,
    original_url   text NOT NULL,
    protected_url  text,
    watermark_id   text,
    status      text NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

-- 2. Enable RLS (required by Supabase best-practice)
ALTER TABLE public.images ENABLE ROW LEVEL SECURITY;

-- 3. Policy: allow the service_role key to do everything (backend API)
--    service_role automatically bypasses RLS, so this is a safety net.
DROP POLICY IF EXISTS "service_role_full_access" ON public.images;
CREATE POLICY "service_role_full_access"
    ON public.images
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- 4. Policy: authenticated users can SELECT their own rows
DROP POLICY IF EXISTS "users_select_own" ON public.images;
CREATE POLICY "users_select_own"
    ON public.images
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

-- 5. Policy: authenticated users can INSERT rows for themselves
DROP POLICY IF EXISTS "users_insert_own" ON public.images;
CREATE POLICY "users_insert_own"
    ON public.images
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

-- 6. Index for fast lookups by user
CREATE INDEX IF NOT EXISTS idx_images_user_id ON public.images (user_id);

-- 7. Auto-update updated_at on row modification
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_images_updated_at ON public.images;
CREATE TRIGGER trg_images_updated_at
    BEFORE UPDATE ON public.images
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();
