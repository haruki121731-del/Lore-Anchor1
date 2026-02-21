-- Weekly KPI: Flow Completion = downloads / uploads
WITH weekly_uploads AS (
  SELECT
    date_trunc('week', created_at) AS week,
    COUNT(*)::int AS upload_success_count
  FROM public.images
  WHERE status != 'deleted'
  GROUP BY 1
),
weekly_downloads AS (
  SELECT
    date_trunc('week', created_at) AS week,
    COALESCE(SUM(download_count), 0)::int AS download_click_count
  FROM public.images
  WHERE status != 'deleted'
  GROUP BY 1
)
SELECT
  u.week,
  u.upload_success_count,
  d.download_click_count,
  CASE
    WHEN u.upload_success_count = 0 THEN 0
    ELSE ROUND((d.download_click_count::numeric / u.upload_success_count::numeric) * 100, 2)
  END AS flow_completion_percent
FROM weekly_uploads u
JOIN weekly_downloads d ON d.week = u.week
ORDER BY u.week DESC;
