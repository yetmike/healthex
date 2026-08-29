-- Minutes from the start of a sleep session to the first non-AWAKE stage.
-- Derived at ingest: summary.minutesToFallAsleep exists in the API but reports
-- 0 on some devices, so the stage timeline is the reliable source.
ALTER TABLE sleep_sessions ADD COLUMN IF NOT EXISTS sleep_latency_minutes INTEGER;

-- Backfill from the stored payload, so history is not lost. Sessions without a
-- stage timeline (CLASSIC) keep NULL.
WITH first_asleep AS (
    SELECT
        s.id,
        MIN((st ->> 'startTime')::timestamptz)
            FILTER (WHERE upper(st ->> 'type') <> 'AWAKE') AS asleep_at
    FROM sleep_sessions s,
         LATERAL jsonb_array_elements(s.raw -> 'sleep' -> 'stages') st
    GROUP BY s.id
)
UPDATE sleep_sessions s
SET sleep_latency_minutes =
        GREATEST(ROUND(EXTRACT(EPOCH FROM f.asleep_at - s.start_time) / 60)::int, 0)
FROM first_asleep f
WHERE f.id = s.id
  AND f.asleep_at IS NOT NULL
  AND s.sleep_latency_minutes IS NULL;
