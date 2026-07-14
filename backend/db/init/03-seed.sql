-- Reference data for a fictional plant: 3 zones, 7 sensors across them.
-- ST_MakeEnvelope builds a rectangular polygon from (min_lon, min_lat, max_lon, max_lat, srid).
INSERT INTO zones (zone_id, name, boundary) VALUES
    (1, 'Compressor House', ST_MakeEnvelope(77.500, 13.000, 77.502, 13.002, 4326)),
    (2, 'Storage Tank Farm', ST_MakeEnvelope(77.505, 13.000, 77.508, 13.003, 4326)),
    (3, 'Pipeline Corridor', ST_MakeEnvelope(77.495, 13.003, 77.500, 13.006, 4326));

-- Keep the SERIAL sequence in sync with the explicit ids inserted above,
-- so future INSERTs without an explicit zone_id don't collide.
SELECT setval('zones_zone_id_seq', (SELECT MAX(zone_id) FROM zones));

INSERT INTO sensors (sensor_id, zone_id, sensor_type, unit, location) VALUES
    ('gas-01',      1, 'gas',         'ppm',     ST_SetSRID(ST_MakePoint(77.5008, 13.0008), 4326)),
    ('temp-01',     1, 'temperature', 'celsius', ST_SetSRID(ST_MakePoint(77.5012, 13.0011), 4326)),
    ('pressure-01', 1, 'pressure',    'bar',     ST_SetSRID(ST_MakePoint(77.5015, 13.0009), 4326)),
    ('gas-02',      2, 'gas',         'ppm',     ST_SetSRID(ST_MakePoint(77.5065, 13.0015), 4326)),
    ('temp-02',     2, 'temperature', 'celsius', ST_SetSRID(ST_MakePoint(77.5070, 13.0018), 4326)),
    ('gas-03',      3, 'gas',         'ppm',     ST_SetSRID(ST_MakePoint(77.4975, 13.0045), 4326)),
    ('pressure-02', 3, 'pressure',    'bar',     ST_SetSRID(ST_MakePoint(77.4980, 13.0048), 4326));
