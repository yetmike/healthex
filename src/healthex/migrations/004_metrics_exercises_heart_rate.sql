-- Long-format daily values (activity rollups, SpO2, breathing rate, skin
-- temperature, VO2 max, weight, ...). Metric names are "<data_type>.<field>",
-- units as the API names them. One table, so a new data type needs no migration.
CREATE TABLE IF NOT EXISTS daily_metrics (
    user_id     TEXT NOT NULL,
    metric_date DATE NOT NULL,
    metric      TEXT NOT NULL,
    value       DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (user_id, metric_date, metric)
);

CREATE TABLE IF NOT EXISTS heart_rate (
    user_id      TEXT NOT NULL,
    bucket_start TIMESTAMPTZ NOT NULL,
    bpm_avg      DOUBLE PRECISION NOT NULL,
    bpm_min      DOUBLE PRECISION,
    bpm_max      DOUBLE PRECISION,
    PRIMARY KEY (user_id, bucket_start)
);

CREATE TABLE IF NOT EXISTS exercises (
    user_id             TEXT NOT NULL,
    start_time          TIMESTAMPTZ NOT NULL,
    end_time            TIMESTAMPTZ,
    civil_date          DATE,
    exercise_type       TEXT,
    display_name        TEXT,
    active_seconds      DOUBLE PRECISION,
    calories_kcal       DOUBLE PRECISION,
    distance_m          DOUBLE PRECISION,
    steps               INTEGER,
    avg_bpm             INTEGER,
    active_zone_minutes INTEGER,
    elevation_gain_m    DOUBLE PRECISION,
    raw                 JSONB NOT NULL,
    PRIMARY KEY (user_id, start_time)
);
