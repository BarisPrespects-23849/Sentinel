-- Work permits authorized for a zone. A permit being active doesn't
-- inherently mean danger -- it's dangerous specifically when it overlaps
-- with elevated sensor readings (e.g. hot work + a gas leak). That
-- cross-referencing happens in the Permit Agent, not here.
CREATE TABLE permits (
    permit_id SERIAL PRIMARY KEY,
    zone_id INTEGER NOT NULL REFERENCES zones(zone_id),
    permit_type TEXT NOT NULL CHECK (permit_type IN ('hot_work', 'confined_space', 'cold_work')),
    status TEXT NOT NULL CHECK (status IN ('active', 'expired', 'cancelled')),
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ NOT NULL,
    description TEXT
);

-- Calibration history per sensor. An overdue sensor's readings are less
-- trustworthy -- the Maintenance Agent surfaces this as a caveat on the
-- final explanation, not as a primary risk driver.
CREATE TABLE maintenance_records (
    record_id SERIAL PRIMARY KEY,
    sensor_id TEXT NOT NULL REFERENCES sensors(sensor_id),
    last_calibrated TIMESTAMPTZ NOT NULL,
    next_due TIMESTAMPTZ NOT NULL
);
