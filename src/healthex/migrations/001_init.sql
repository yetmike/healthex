-- Baseline schema, generated from healthex.models.
-- Never edit an applied migration; add a new numbered file instead.

CREATE TABLE daily_hrv (
	id TEXT NOT NULL,
	user_id TEXT NOT NULL,
	hrv_date DATE NOT NULL,
	avg_hrv_ms NUMERIC(8, 3) NOT NULL,
	non_rem_bpm INTEGER,
	entropy NUMERIC(8, 4),
	deep_sleep_rmssd_ms NUMERIC(8, 3),
	source_platform TEXT,
	raw JSONB NOT NULL,
	ingested_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_hrv_user_date UNIQUE (user_id, hrv_date)
);

CREATE INDEX idx_hrv_user_date ON daily_hrv (user_id, hrv_date);

CREATE TABLE daily_rhr (
	id TEXT NOT NULL,
	user_id TEXT NOT NULL,
	rhr_date DATE NOT NULL,
	bpm INTEGER NOT NULL,
	calculation_method TEXT,
	source_platform TEXT,
	raw JSONB NOT NULL,
	ingested_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_rhr_user_date UNIQUE (user_id, rhr_date)
);

CREATE INDEX idx_rhr_user_date ON daily_rhr (user_id, rhr_date);

CREATE TABLE daily_steps (
	id TEXT NOT NULL,
	user_id TEXT NOT NULL,
	step_date DATE NOT NULL,
	steps INTEGER NOT NULL,
	source_platform TEXT,
	raw JSONB NOT NULL,
	ingested_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_steps_user_date UNIQUE (user_id, step_date)
);

CREATE INDEX idx_steps_user_date ON daily_steps (user_id, step_date);

CREATE TABLE sleep_sessions (
	id TEXT NOT NULL,
	user_id TEXT NOT NULL,
	civil_date DATE,
	start_time TIMESTAMP WITH TIME ZONE NOT NULL,
	end_time TIMESTAMP WITH TIME ZONE NOT NULL,
	sleep_type TEXT,
	duration_seconds INTEGER,
	minutes_asleep INTEGER,
	minutes_awake INTEGER,
	minutes_light INTEGER,
	minutes_deep INTEGER,
	minutes_rem INTEGER,
	efficiency NUMERIC(5, 2),
	sleep_score INTEGER,
	source_platform TEXT,
	raw JSONB NOT NULL,
	ingested_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_sleep_user_start UNIQUE (user_id, start_time)
);

CREATE INDEX idx_sleep_user_date ON sleep_sessions (user_id, civil_date);
