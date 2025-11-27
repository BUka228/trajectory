CREATE TABLE IF NOT EXISTS users_raw (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    name VARCHAR(255),
    email VARCHAR(255),
    event_time TIMESTAMPTZ,
    password_hash VARCHAR(128),
    country VARCHAR(128),
    city VARCHAR(128),
    phone_number VARCHAR(64),
    job VARCHAR(255),
    company VARCHAR(255),
    ipv4 VARCHAR(45),
    raw_payload JSONB,
    error TEXT
);
