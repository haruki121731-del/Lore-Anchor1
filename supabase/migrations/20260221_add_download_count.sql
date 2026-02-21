-- Add download_count to images so Flow Completion KPI can be tracked.
ALTER TABLE public.images
ADD COLUMN download_count integer NOT NULL DEFAULT 0;
