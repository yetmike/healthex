-- models.py used server_default="now()" (a plain string), which SQLAlchemy
-- emitted as the literal DEFAULT 'now()' — evaluated once at CREATE TABLE and
-- frozen. Every row inserted without an explicit ingested_at therefore carried
-- the table's creation time rather than the insert time.
--
-- Existing rows are left alone: their true ingestion time is not recoverable.
ALTER TABLE sleep_sessions ALTER COLUMN ingested_at SET DEFAULT now();
ALTER TABLE daily_steps    ALTER COLUMN ingested_at SET DEFAULT now();
ALTER TABLE daily_rhr      ALTER COLUMN ingested_at SET DEFAULT now();
ALTER TABLE daily_hrv      ALTER COLUMN ingested_at SET DEFAULT now();
