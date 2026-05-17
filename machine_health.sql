-- ============================================================
--  MACHINE HEALTH & MAINTENANCE DASHBOARD
--  SQL Schema + Queries
--  Database: PostgreSQL (compatible with MySQL / SQLite with
--            minor adjustments noted inline)
-- ============================================================


-- ============================================================
--  1. SCHEMA
-- ============================================================

-- Plants / sites
CREATE TABLE plants (
    plant_id   SERIAL PRIMARY KEY,
    plant_code VARCHAR(20)  NOT NULL UNIQUE,   -- 'Plant A', 'Plant B', 'Plant C'
    city       VARCHAR(100),
    country    VARCHAR(100) DEFAULT 'USA'
);

-- Machine master list
CREATE TABLE machines (
    machine_id   SERIAL PRIMARY KEY,
    machine_code VARCHAR(20)  NOT NULL UNIQUE,  -- 'MX-132', 'MX-100', …
    plant_id     INT          NOT NULL REFERENCES plants(plant_id),
    machine_type VARCHAR(100),
    installed_at DATE,
    is_active    BOOLEAN DEFAULT TRUE
);

-- Raw sensor readings (one row per machine per timestamp)
CREATE TABLE sensor_readings (
    reading_id   BIGSERIAL PRIMARY KEY,
    machine_id   INT          NOT NULL REFERENCES machines(machine_id),
    recorded_at  TIMESTAMP    NOT NULL,
    temperature  NUMERIC(6,2),   -- °C
    vibration    NUMERIC(6,3),   -- mm/s
    pressure     NUMERIC(6,2)    -- PSI
);

-- Defect events (one row per defect detected)
CREATE TABLE defect_events (
    defect_id    BIGSERIAL PRIMARY KEY,
    machine_id   INT       NOT NULL REFERENCES machines(machine_id),
    detected_at  TIMESTAMP NOT NULL,
    defect_type  VARCHAR(100),
    severity     VARCHAR(20) CHECK (severity IN ('low','medium','high','critical')),
    resolved_at  TIMESTAMP
);

-- Maintenance events
CREATE TABLE maintenance_events (
    maint_id     BIGSERIAL PRIMARY KEY,
    machine_id   INT       NOT NULL REFERENCES machines(machine_id),
    triggered_at TIMESTAMP NOT NULL,
    maint_type   VARCHAR(100),  -- 'preventive', 'corrective', 'emergency'
    completed_at TIMESTAMP,
    technician   VARCHAR(100)
);

-- Pre-aggregated monthly snapshot (mirrors the dashboard's `monthly` array)
-- Populate via the INSERT below or refresh with a scheduled job
CREATE TABLE monthly_summary (
    summary_id   SERIAL PRIMARY KEY,
    plant_id     INT     REFERENCES plants(plant_id),  -- NULL = all plants
    month_start  DATE    NOT NULL,   -- always 1st of the month
    total_defects     INT     NOT NULL DEFAULT 0,
    total_maint_events INT   NOT NULL DEFAULT 0,
    avg_temperature  NUMERIC(6,2),
    avg_vibration    NUMERIC(6,3),
    avg_pressure     NUMERIC(6,2),
    UNIQUE (plant_id, month_start)
);

-- Indexes for common query patterns
CREATE INDEX idx_sensor_machine_time  ON sensor_readings  (machine_id, recorded_at DESC);
CREATE INDEX idx_defect_machine_time  ON defect_events    (machine_id, detected_at DESC);
CREATE INDEX idx_maint_machine_time   ON maintenance_events (machine_id, triggered_at DESC);
CREATE INDEX idx_monthly_month        ON monthly_summary  (month_start);


-- ============================================================
--  2. SEED DATA  (mirrors the dashboard's hardcoded arrays)
-- ============================================================

INSERT INTO plants (plant_code, city) VALUES
    ('Plant A', 'Detroit'),
    ('Plant B', 'Chicago'),
    ('Plant C', 'Houston');

INSERT INTO machines (machine_code, plant_id, machine_type) VALUES
    ('MX-132', (SELECT plant_id FROM plants WHERE plant_code='Plant B'), 'CNC Mill'),
    ('MX-100', (SELECT plant_id FROM plants WHERE plant_code='Plant A'), 'Press'),
    ('MX-137', (SELECT plant_id FROM plants WHERE plant_code='Plant C'), 'Lathe'),
    ('MX-118', (SELECT plant_id FROM plants WHERE plant_code='Plant B'), 'CNC Mill'),
    ('MX-125', (SELECT plant_id FROM plants WHERE plant_code='Plant A'), 'Conveyor'),
    ('MX-121', (SELECT plant_id FROM plants WHERE plant_code='Plant C'), 'Press'),
    ('MX-119', (SELECT plant_id FROM plants WHERE plant_code='Plant A'), 'Lathe'),
    ('MX-123', (SELECT plant_id FROM plants WHERE plant_code='Plant B'), 'Conveyor'),
    ('MX-112', (SELECT plant_id FROM plants WHERE plant_code='Plant C'), 'CNC Mill'),
    ('MX-103', (SELECT plant_id FROM plants WHERE plant_code='Plant A'), 'Press');

-- Monthly all-plant summary (plant_id = NULL means aggregated)
INSERT INTO monthly_summary (plant_id, month_start, total_defects, total_maint_events, avg_temperature, avg_vibration, avg_pressure)
VALUES
    (NULL, '2025-01-01', 2174, 73,  70.6, 5.03, 29.9),
    (NULL, '2025-02-01', 2108, 81,  70.1, 4.95, 30.0),
    (NULL, '2025-03-01', 2267, 71,  70.3, 4.93, 30.3),
    (NULL, '2025-04-01', 2213, 79,  70.0, 4.99, 29.9),
    (NULL, '2025-05-01', 2327, 89,  69.9, 4.96, 29.9),
    (NULL, '2025-06-01', 2065, 72,  69.7, 5.02, 29.9),
    (NULL, '2025-07-01', 2185, 80,  69.9, 4.95, 30.0),
    (NULL, '2025-08-01', 2272, 76,  69.8, 4.92, 30.2),
    (NULL, '2025-09-01', 2163, 78,  69.5, 4.93, 29.8),
    (NULL, '2025-10-01', 2301, 67,  69.7, 5.02, 29.9),
    (NULL, '2025-11-01', 2164, 54,  70.2, 5.03, 30.1),
    (NULL, '2025-12-01', 2148, 74,  69.8, 4.90, 30.1),
    (NULL, '2026-01-01', 2163, 78,  70.2, 5.01, 29.8),
    (NULL, '2026-02-01', 2012, 57,  69.7, 5.00, 29.9),
    (NULL, '2026-03-01', 2189, 68,  69.9, 5.05, 29.9),
    (NULL, '2026-04-01', 2065, 71,  69.5, 4.99, 30.0),
    (NULL, '2026-05-01', 2183, 91,  69.9, 4.98, 30.0),
    (NULL, '2026-06-01', 2095, 71,  70.2, 5.05, 30.1),
    (NULL, '2026-07-01', 2304, 76,  70.3, 5.03, 30.0),
    (NULL, '2026-08-01', 2278, 70,  70.1, 5.03, 30.3),
    (NULL, '2026-09-01', 2216, 71,  70.2, 4.99, 30.1),
    (NULL, '2026-10-01', 2131, 95,  70.4, 5.01, 29.7),
    (NULL, '2026-11-01', 2110, 74,  70.1, 5.11, 29.8),
    (NULL, '2026-12-01', 2307, 65,  69.7, 5.00, 29.8),
    (NULL, '2027-01-01', 2230, 75,  69.1, 5.00, 29.8),
    (NULL, '2027-02-01', 1958, 63,  69.7, 5.00, 30.2),
    (NULL, '2027-03-01', 2237, 80,  70.1, 4.98, 30.0),
    (NULL, '2027-04-01', 1006, 33,  70.0, 4.99, 30.4);


-- ============================================================
--  3. DASHBOARD QUERIES
-- ============================================================

-- ── 3a. KPI STRIP ──────────────────────────────────────────

-- Total Defects (all plants, full period)
SELECT SUM(total_defects) AS total_defects
FROM monthly_summary
WHERE plant_id IS NULL;

-- KPIs for a custom date range  (e.g. 2025-01 to 2026-12)
SELECT
    SUM(total_defects)      AS total_defects,
    SUM(total_maint_events) AS total_maint_events,
    ROUND(AVG(avg_temperature), 1) AS avg_temp_c,
    ROUND(AVG(avg_vibration),  2)  AS avg_vib_mms,
    ROUND(AVG(avg_pressure),   1)  AS avg_pressure_psi,
    COUNT(*)                       AS months_in_range
FROM monthly_summary
WHERE plant_id IS NULL
  AND month_start BETWEEN '2025-01-01' AND '2026-12-01';

-- KPIs filtered by plant
SELECT
    p.plant_code,
    SUM(ms.total_defects)          AS total_defects,
    SUM(ms.total_maint_events)     AS total_maint_events,
    ROUND(AVG(ms.avg_temperature), 1) AS avg_temp_c,
    ROUND(AVG(ms.avg_vibration),   2) AS avg_vib_mms
FROM monthly_summary ms
JOIN plants p ON p.plant_id = ms.plant_id
WHERE ms.plant_id IS NOT NULL
GROUP BY p.plant_code
ORDER BY p.plant_code;


-- ── 3b. MONTHLY TREND CHART ────────────────────────────────

-- All metrics by month (all plants)
SELECT
    TO_CHAR(month_start, 'Mon YYYY')  AS month,
    total_defects,
    total_maint_events                AS maint,
    avg_temperature                   AS temp,
    avg_vibration                     AS vib,
    avg_pressure                      AS pres
FROM monthly_summary
WHERE plant_id IS NULL
ORDER BY month_start;

-- Defect trend for a specific plant + date range
SELECT
    TO_CHAR(ms.month_start, 'Mon YYYY') AS month,
    ms.total_defects
FROM monthly_summary ms
JOIN plants p ON p.plant_id = ms.plant_id
WHERE p.plant_code = 'Plant A'
  AND ms.month_start BETWEEN '2025-01-01' AND '2026-12-01'
ORDER BY ms.month_start;


-- ── 3c. DEFECTS BY PLANT (donut chart) ─────────────────────

SELECT
    p.plant_code,
    p.city,
    SUM(ms.total_defects)                                          AS total_defects,
    ROUND(SUM(ms.total_defects) * 100.0 /
          SUM(SUM(ms.total_defects)) OVER (), 1)                   AS pct_of_total
FROM monthly_summary ms
JOIN plants p ON p.plant_id = ms.plant_id
WHERE ms.plant_id IS NOT NULL
GROUP BY p.plant_code, p.city
ORDER BY total_defects DESC;


-- ── 3d. TOP MACHINES BY DEFECTS (bar race) ─────────────────

-- From raw events (most accurate)
SELECT
    m.machine_code,
    p.plant_code,
    COUNT(*)                        AS total_defects,
    -- risk tier matching the dashboard logic
    CASE
        WHEN COUNT(*) >= 1380 THEN 'Critical'
        WHEN COUNT(*) >= 1310 THEN 'High Risk'
        WHEN COUNT(*) >= 1280 THEN 'Warning'
        ELSE 'Normal'
    END                             AS risk_level
FROM defect_events de
JOIN machines m ON m.machine_id = de.machine_id
JOIN plants   p ON p.plant_id   = m.plant_id
GROUP BY m.machine_code, p.plant_code
ORDER BY total_defects DESC
LIMIT 10;

-- Same query filtered to one plant
SELECT
    m.machine_code,
    COUNT(*)  AS total_defects,
    CASE
        WHEN COUNT(*) >= 1380 THEN 'Critical'
        WHEN COUNT(*) >= 1310 THEN 'High Risk'
        WHEN COUNT(*) >= 1280 THEN 'Warning'
        ELSE 'Normal'
    END AS risk_level
FROM defect_events de
JOIN machines m ON m.machine_id = de.machine_id
JOIN plants   p ON p.plant_id   = m.plant_id
WHERE p.plant_code = 'Plant B'
GROUP BY m.machine_code
ORDER BY total_defects DESC
LIMIT 10;


-- ── 3e. RISK TABLE (top-risk machines) ────────────────────

SELECT
    ROW_NUMBER() OVER (ORDER BY d.total_defects DESC) AS rank,
    m.machine_code,
    p.plant_code,
    d.total_defects,
    me.total_maint,
    ROUND(sr.avg_vib, 2) AS avg_vibration_mms,
    CASE
        WHEN d.total_defects >= 1380 THEN 'Critical'
        WHEN d.total_defects >= 1310 THEN 'High Risk'
        WHEN d.total_defects >= 1280 THEN 'Warning'
        ELSE 'Normal'
    END AS risk_level
FROM machines m
JOIN plants p ON p.plant_id = m.plant_id

-- defect count per machine
LEFT JOIN (
    SELECT machine_id, COUNT(*) AS total_defects
    FROM defect_events
    GROUP BY machine_id
) d ON d.machine_id = m.machine_id

-- maintenance count per machine
LEFT JOIN (
    SELECT machine_id, COUNT(*) AS total_maint
    FROM maintenance_events
    GROUP BY machine_id
) me ON me.machine_id = m.machine_id

-- avg vibration per machine
LEFT JOIN (
    SELECT machine_id, AVG(vibration) AS avg_vib
    FROM sensor_readings
    GROUP BY machine_id
) sr ON sr.machine_id = m.machine_id

ORDER BY d.total_defects DESC NULLS LAST
LIMIT 15;


-- ── 3f. SENSOR MINI-CHARTS (temp / vibration / pressure) ──

-- Monthly averages for all three sensors
SELECT
    TO_CHAR(DATE_TRUNC('month', recorded_at), 'Mon YYYY') AS month,
    ROUND(AVG(temperature), 2) AS avg_temp_c,
    ROUND(AVG(vibration),   3) AS avg_vib_mms,
    ROUND(AVG(pressure),    2) AS avg_pressure_psi
FROM sensor_readings sr
JOIN machines m ON m.machine_id = sr.machine_id
-- optional plant filter: JOIN plants p ON p.plant_id = m.plant_id WHERE p.plant_code = 'Plant A'
GROUP BY DATE_TRUNC('month', recorded_at)
ORDER BY DATE_TRUNC('month', recorded_at);


-- ── 3g. MAINTENANCE EVENTS BAR CHART ─────────────────────

-- Monthly count, flagging high-activity months (>85 matches dashboard highlight)
SELECT
    TO_CHAR(DATE_TRUNC('month', triggered_at), 'Mon YYYY') AS month,
    COUNT(*) AS maint_events,
    CASE WHEN COUNT(*) > 85 THEN 'high' ELSE 'normal' END  AS activity_level
FROM maintenance_events
GROUP BY DATE_TRUNC('month', triggered_at)
ORDER BY DATE_TRUNC('month', triggered_at);


-- ── 3h. CRITICAL ALERTS ───────────────────────────────────

-- Machines currently at critical defect level (real-time)
SELECT
    m.machine_code,
    p.plant_code,
    COUNT(de.defect_id) AS total_defects,
    MAX(de.detected_at) AS last_defect_at
FROM defect_events de
JOIN machines m ON m.machine_id = de.machine_id
JOIN plants   p ON p.plant_id   = m.plant_id
GROUP BY m.machine_code, p.plant_code
HAVING COUNT(de.defect_id) >= 1380
ORDER BY total_defects DESC;

-- Unresolved defects in the last 24 hours
SELECT
    m.machine_code,
    p.plant_code,
    de.defect_type,
    de.severity,
    de.detected_at
FROM defect_events de
JOIN machines m ON m.machine_id = de.machine_id
JOIN plants   p ON p.plant_id   = m.plant_id
WHERE de.resolved_at IS NULL
  AND de.detected_at >= NOW() - INTERVAL '24 hours'
ORDER BY de.detected_at DESC;


-- ============================================================
--  4. MATERIALIZED VIEW  (refresh daily for the dashboard)
-- ============================================================

CREATE MATERIALIZED VIEW mv_monthly_kpis AS
SELECT
    p.plant_code,
    DATE_TRUNC('month', de.detected_at)::DATE         AS month_start,
    COUNT(DISTINCT de.defect_id)                       AS total_defects,
    COUNT(DISTINCT me.maint_id)                        AS total_maint_events,
    ROUND(AVG(sr.temperature), 2)                      AS avg_temperature,
    ROUND(AVG(sr.vibration),   3)                      AS avg_vibration,
    ROUND(AVG(sr.pressure),    2)                      AS avg_pressure
FROM machines m
JOIN plants p ON p.plant_id = m.plant_id
LEFT JOIN defect_events      de ON de.machine_id = m.machine_id
LEFT JOIN maintenance_events me ON me.machine_id = m.machine_id
    AND DATE_TRUNC('month', me.triggered_at) = DATE_TRUNC('month', de.detected_at)
LEFT JOIN sensor_readings    sr ON sr.machine_id = m.machine_id
    AND DATE_TRUNC('month', sr.recorded_at)  = DATE_TRUNC('month', de.detected_at)
GROUP BY p.plant_code, DATE_TRUNC('month', de.detected_at)
ORDER BY p.plant_code, month_start;

-- Refresh command (run on schedule):
-- REFRESH MATERIALIZED VIEW mv_monthly_kpis;
