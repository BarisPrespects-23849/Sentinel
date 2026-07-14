-- Physical areas of the plant. Polygon boundaries let us later ask
-- "is this permit/equipment inside this zone" with real spatial queries.
CREATE TABLE zones (
    zone_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    boundary GEOMETRY(Polygon, 4326) NOT NULL
);

-- One row per physical sensor. Metadata only -- no readings here, so this
-- table stays tiny and fast to join against, no matter how much time-series
-- data accumulates in sensor_readings.
CREATE TABLE sensors (
    sensor_id TEXT PRIMARY KEY,
    zone_id INTEGER NOT NULL REFERENCES zones(zone_id),
    sensor_type TEXT NOT NULL CHECK (sensor_type IN ('gas', 'temperature', 'pressure')),
    unit TEXT NOT NULL,
    location GEOMETRY(Point, 4326) NOT NULL
);

-- The actual time-series stream. Deliberately narrow (3 columns) since
-- this is the table that grows forever -- every sensor, every few seconds.
CREATE TABLE sensor_readings (
    ts TIMESTAMPTZ NOT NULL,
    sensor_id TEXT NOT NULL REFERENCES sensors(sensor_id),
    value DOUBLE PRECISION NOT NULL
);

-- Converts sensor_readings from a plain table into a TimescaleDB hypertable,
-- auto-partitioned into time-based chunks under the hood. Application code
-- still just sees an ordinary table.
SELECT create_hypertable('sensor_readings', 'ts');

CREATE INDEX idx_sensor_readings_sensor_id ON sensor_readings (sensor_id, ts DESC);
