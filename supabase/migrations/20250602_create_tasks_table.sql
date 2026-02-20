-- =============================================================
-- tasks table  –  tracks GPU worker processing per image
-- =============================================================

CREATE TABLE IF NOT EXISTS public.tasks (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id      uuid NOT NULL REFERENCES public.images (id),
    worker_id     text,
    started_at    timestamptz,
    completed_at  timestamptz,
    error_log     text
);

-- RLS: authenticated users can SELECT tasks linked to their own images
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own tasks" ON public.tasks;
CREATE POLICY "Users can view own tasks"
    ON public.tasks
    FOR SELECT
    TO authenticated
    USING (
        image_id IN (
            SELECT id FROM public.images WHERE user_id = auth.uid()
        )
    );

-- service_role bypasses RLS automatically, but add explicit policy for clarity
DROP POLICY IF EXISTS "service_role_full_access" ON public.tasks;
CREATE POLICY "service_role_full_access"
    ON public.tasks
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Index for fast lookups by image_id
CREATE INDEX IF NOT EXISTS idx_tasks_image_id ON public.tasks (image_id);
