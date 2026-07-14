-- Compressor House: a hot-work (welding) permit active right now.
-- Deliberately in the same zone as gas-01 for a rich compound scenario:
-- gas leak + active ignition source permit + an overdue-calibration
-- sensor, all in one zone.
INSERT INTO permits (zone_id, permit_type, status, valid_from, valid_until, description) VALUES
    (1, 'hot_work', 'active', now() - interval '2 hours', now() + interval '4 hours',
     'Welding repair on compressor housing'),
    (2, 'confined_space', 'expired', now() - interval '2 days', now() - interval '1 day',
     'Tank interior inspection (completed)');
-- Pipeline Corridor (zone 3) intentionally has no permits, to prove the
-- system handles "no permit data for this zone" without error.

INSERT INTO maintenance_records (sensor_id, last_calibrated, next_due) VALUES
    ('gas-01',      now() - interval '400 days', now() - interval '40 days'),  -- overdue
    ('temp-01',     now() - interval '60 days',  now() + interval '300 days'),
    ('pressure-01', now() - interval '60 days',  now() + interval '300 days'),
    ('gas-02',      now() - interval '60 days',  now() + interval '300 days'),
    ('temp-02',     now() - interval '60 days',  now() + interval '300 days'),
    ('gas-03',      now() - interval '60 days',  now() + interval '300 days'),
    ('pressure-02', now() - interval '60 days',  now() + interval '300 days');
