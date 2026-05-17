"""
============================================================
 MACHINE HEALTH & MAINTENANCE DASHBOARD
 Python Backend  ·  Data Pipeline + Analysis + Export
============================================================
 Covers:
   1. Data models (dataclasses)
   2. Seed / load data (mirrors dashboard hardcoded arrays)
   3. Database layer  (SQLite via SQLAlchemy – swap URL for Postgres)
   4. KPI calculations
   5. Filtering helpers  (plant, date range)
   6. Risk classification
   7. Alert engine
   8. CSV export
   9. Chart-ready data builders (dict output → JSON for any frontend)
  10. CLI demo
============================================================
"""

import sqlite3
import csv
import json
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Optional
from statistics import mean

# ──────────────────────────────────────────────────────────
# 1. DATA MODELS
# ──────────────────────────────────────────────────────────

@dataclass
class MonthlySummary:
    month: str           # "Jan 2025"
    defects: int
    maint: int
    temp: float          # avg °C
    vib: float           # avg mm/s
    pres: float          # avg PSI
    plant: Optional[str] = None   # None = all plants combined


@dataclass
class Machine:
    id: str              # "MX-132"
    defects: int
    maint: int
    vib: float           # avg mm/s
    plant: str = "Unknown"


@dataclass
class Alert:
    machine_id: str
    plant: str
    defects: int
    level: str           # "Critical" | "High Risk" | "Warning"
    message: str


@dataclass
class KPIResult:
    total_defects: int
    total_maint_events: int
    avg_vibration: float
    avg_temperature: float
    months_count: int
    date_range: str
    critical_alerts: int


# ──────────────────────────────────────────────────────────
# 2. SEED DATA  (mirrors the dashboard JS arrays exactly)
# ──────────────────────────────────────────────────────────

MONTHLY_DATA: list[MonthlySummary] = [
    MonthlySummary("Jan 2025", 2174, 73,  70.6, 5.03, 29.9),
    MonthlySummary("Feb 2025", 2108, 81,  70.1, 4.95, 30.0),
    MonthlySummary("Mar 2025", 2267, 71,  70.3, 4.93, 30.3),
    MonthlySummary("Apr 2025", 2213, 79,  70.0, 4.99, 29.9),
    MonthlySummary("May 2025", 2327, 89,  69.9, 4.96, 29.9),
    MonthlySummary("Jun 2025", 2065, 72,  69.7, 5.02, 29.9),
    MonthlySummary("Jul 2025", 2185, 80,  69.9, 4.95, 30.0),
    MonthlySummary("Aug 2025", 2272, 76,  69.8, 4.92, 30.2),
    MonthlySummary("Sep 2025", 2163, 78,  69.5, 4.93, 29.8),
    MonthlySummary("Oct 2025", 2301, 67,  69.7, 5.02, 29.9),
    MonthlySummary("Nov 2025", 2164, 54,  70.2, 5.03, 30.1),
    MonthlySummary("Dec 2025", 2148, 74,  69.8, 4.90, 30.1),
    MonthlySummary("Jan 2026", 2163, 78,  70.2, 5.01, 29.8),
    MonthlySummary("Feb 2026", 2012, 57,  69.7, 5.00, 29.9),
    MonthlySummary("Mar 2026", 2189, 68,  69.9, 5.05, 29.9),
    MonthlySummary("Apr 2026", 2065, 71,  69.5, 4.99, 30.0),
    MonthlySummary("May 2026", 2183, 91,  69.9, 4.98, 30.0),
    MonthlySummary("Jun 2026", 2095, 71,  70.2, 5.05, 30.1),
    MonthlySummary("Jul 2026", 2304, 76,  70.3, 5.03, 30.0),
    MonthlySummary("Aug 2026", 2278, 70,  70.1, 5.03, 30.3),
    MonthlySummary("Sep 2026", 2216, 71,  70.2, 4.99, 30.1),
    MonthlySummary("Oct 2026", 2131, 95,  70.4, 5.01, 29.7),
    MonthlySummary("Nov 2026", 2110, 74,  70.1, 5.11, 29.8),
    MonthlySummary("Dec 2026", 2307, 65,  69.7, 5.00, 29.8),
    MonthlySummary("Jan 2027", 2230, 75,  69.1, 5.00, 29.8),
    MonthlySummary("Feb 2027", 1958, 63,  69.7, 5.00, 30.2),
    MonthlySummary("Mar 2027", 2237, 80,  70.1, 4.98, 30.0),
    MonthlySummary("Apr 2027", 1006, 33,  70.0, 4.99, 30.4),
]

MACHINE_DATA: list[Machine] = [
    Machine("MX-132", 1391, 47, 5.04, "Plant B"),
    Machine("MX-100", 1383, 49, 4.97, "Plant A"),
    Machine("MX-137", 1341, 44, 5.05, "Plant C"),
    Machine("MX-118", 1319, 38, 5.08, "Plant B"),
    Machine("MX-125", 1289, 32, 4.95, "Plant A"),
    Machine("MX-121", 1286, 33, 5.08, "Plant C"),
    Machine("MX-119", 1281, 35, 4.91, "Plant A"),
    Machine("MX-123", 1279, 39, 5.05, "Plant B"),
    Machine("MX-112", 1276, 43, 4.95, "Plant C"),
    Machine("MX-103", 1276, 39, 4.95, "Plant A"),
]

PLANT_DEFECTS = {"Plant A": 19735, "Plant B": 20647, "Plant C": 19489}

_MONTH_ORDER = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
    "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
    "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


# ──────────────────────────────────────────────────────────
# 3. DATABASE LAYER  (SQLite — swap URL for Postgres)
# ──────────────────────────────────────────────────────────

class Database:
    """Lightweight SQLite wrapper for the dashboard data."""

    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._seed()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS monthly_summary (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                plant       TEXT,                  -- NULL = all plants
                month       TEXT    NOT NULL,
                defects     INTEGER NOT NULL,
                maint       INTEGER NOT NULL,
                temp        REAL,
                vib         REAL,
                pres        REAL
            );

            CREATE TABLE IF NOT EXISTS machines (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_code TEXT   NOT NULL UNIQUE,
                plant        TEXT   NOT NULL,
                defects      INTEGER NOT NULL,
                maint        INTEGER NOT NULL,
                vib          REAL
            );

            CREATE INDEX IF NOT EXISTS idx_monthly_plant  ON monthly_summary(plant);
            CREATE INDEX IF NOT EXISTS idx_monthly_month  ON monthly_summary(month);
            CREATE INDEX IF NOT EXISTS idx_machine_plant  ON machines(plant);
        """)
        self.conn.commit()

    def _seed(self):
        # Only seed once
        if self.conn.execute("SELECT COUNT(*) FROM monthly_summary").fetchone()[0] > 0:
            return

        self.conn.executemany(
            "INSERT INTO monthly_summary (plant, month, defects, maint, temp, vib, pres) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(None, m.month, m.defects, m.maint, m.temp, m.vib, m.pres)
             for m in MONTHLY_DATA]
        )
        self.conn.executemany(
            "INSERT OR IGNORE INTO machines (machine_code, plant, defects, maint, vib) "
            "VALUES (?, ?, ?, ?, ?)",
            [(m.id, m.plant, m.defects, m.maint, m.vib) for m in MACHINE_DATA]
        )
        self.conn.commit()

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchall()

    def close(self):
        self.conn.close()


# ──────────────────────────────────────────────────────────
# 4. HELPER: MONTH PARSING & COMPARISON
# ──────────────────────────────────────────────────────────

def month_to_sortable(month_str: str) -> str:
    """'Jan 2025' → '2025-01'  (sortable string for date comparisons)"""
    parts = month_str.split()
    m = _MONTH_ORDER.get(parts[0], 0)
    return f"{parts[1]}-{m:02d}"


def in_date_range(
    month_str: str,
    from_month: Optional[str],
    to_month: Optional[str],
) -> bool:
    """
    Return True if month_str falls within [from_month, to_month].
    Both bounds are inclusive and can be None (= no limit).
    Format: 'Jan 2025'
    """
    val = month_to_sortable(month_str)
    if from_month and val < month_to_sortable(from_month):
        return False
    if to_month and val > month_to_sortable(to_month):
        return False
    return True


# ──────────────────────────────────────────────────────────
# 5. FILTERING HELPERS
# ──────────────────────────────────────────────────────────

def filter_monthly(
    data: list[MonthlySummary],
    plant: Optional[str] = None,
    from_month: Optional[str] = None,
    to_month: Optional[str] = None,
) -> list[MonthlySummary]:
    """
    Filter monthly summary rows.

    Args:
        plant:      'Plant A' | 'Plant B' | 'Plant C' | None (all)
        from_month: 'Jan 2025'  (inclusive)
        to_month:   'Dec 2026'  (inclusive)
    """
    result = data
    if plant:
        result = [r for r in result if r.plant == plant]
    if from_month or to_month:
        result = [r for r in result if in_date_range(r.month, from_month, to_month)]
    return result


def filter_machines(
    machines: list[Machine],
    plant: Optional[str] = None,
) -> list[Machine]:
    if plant:
        return [m for m in machines if m.plant == plant]
    return machines


# ──────────────────────────────────────────────────────────
# 6. RISK CLASSIFICATION
# ──────────────────────────────────────────────────────────

def risk_level(defects: int) -> str:
    """Mirrors the JS riskLevel() function in the dashboard."""
    if defects >= 1380:
        return "Critical"
    if defects >= 1310:
        return "High Risk"
    if defects >= 1280:
        return "Warning"
    return "Normal"


# ──────────────────────────────────────────────────────────
# 7. KPI CALCULATIONS
# ──────────────────────────────────────────────────────────

def compute_kpis(
    monthly: list[MonthlySummary],
    machines: list[Machine],
) -> KPIResult:
    if not monthly:
        return KPIResult(0, 0, 0.0, 0.0, 0, "No data", 0)

    total_def  = sum(r.defects for r in monthly)
    total_mnt  = sum(r.maint   for r in monthly)
    avg_vib    = round(mean(r.vib  for r in monthly), 2)
    avg_temp   = round(mean(r.temp for r in monthly), 1)
    n_months   = len(monthly)
    date_range = f"{monthly[0].month} – {monthly[-1].month}"
    criticals  = sum(1 for m in machines if risk_level(m.defects) == "Critical")

    return KPIResult(
        total_defects=total_def,
        total_maint_events=total_mnt,
        avg_vibration=avg_vib,
        avg_temperature=avg_temp,
        months_count=n_months,
        date_range=date_range,
        critical_alerts=criticals,
    )


# ──────────────────────────────────────────────────────────
# 8. ALERT ENGINE
# ──────────────────────────────────────────────────────────

ALERT_THRESHOLDS = {
    "Critical":  1380,
    "High Risk": 1310,
    "Warning":   1280,
}


def generate_alerts(machines: list[Machine]) -> list[Alert]:
    """Return Alert objects for every machine above Warning threshold."""
    alerts = []
    for m in sorted(machines, key=lambda x: x.defects, reverse=True):
        level = risk_level(m.defects)
        if level == "Normal":
            continue
        threshold = ALERT_THRESHOLDS[level]
        alerts.append(Alert(
            machine_id=m.id,
            plant=m.plant,
            defects=m.defects,
            level=level,
            message=(
                f"[{level.upper()}] {m.id} ({m.plant}): "
                f"{m.defects:,} defects — exceeds {threshold:,} threshold"
            ),
        ))
    return alerts


# ──────────────────────────────────────────────────────────
# 9. CHART-READY DATA BUILDERS



def build_trend_chart_data(
    monthly: list[MonthlySummary],
    metric: str = "defects",
) -> dict:
    """
    Returns labels + values list ready to plug into Chart.js.
    metric: 'defects' | 'maint' | 'temp' | 'vib' | 'pres'
    """
    valid = {"defects", "maint", "temp", "vib", "pres"}
    if metric not in valid:
        raise ValueError(f"metric must be one of {valid}")

    return {
        "labels": [r.month for r in monthly],
        "values": [getattr(r, metric) for r in monthly],
        "metric": metric,
    }


def build_plant_donut_data(plant_filter: Optional[str] = None) -> dict:
    """Donut chart: defects per plant."""
    if plant_filter:
        plants = [plant_filter]
    else:
        plants = list(PLANT_DEFECTS.keys())

    total = sum(PLANT_DEFECTS[p] for p in plants)
    return {
        "labels": plants,
        "values": [PLANT_DEFECTS[p] for p in plants],
        "pct": [round(PLANT_DEFECTS[p] / total * 100, 1) for p in plants],
    }


def build_bar_race_data(machines: list[Machine], top_n: int = 10) -> list[dict]:
    """Bar-race data for top N machines."""
    ranked = sorted(machines, key=lambda m: m.defects, reverse=True)[:top_n]
    max_def = ranked[0].defects if ranked else 1
    return [
        {
            "id":      m.id,
            "plant":   m.plant,
            "defects": m.defects,
            "maint":   m.maint,
            "vib":     m.vib,
            "pct":     round(m.defects / max_def * 100, 1),
            "risk":    risk_level(m.defects),
        }
        for m in ranked
    ]


def build_risk_table_data(machines: list[Machine]) -> list[dict]:
    ranked = sorted(machines, key=lambda m: m.defects, reverse=True)
    return [
        {
            "rank":    i + 1,
            "id":      m.id,
            "plant":   m.plant,
            "defects": m.defects,
            "maint":   m.maint,
            "vib":     m.vib,
            "risk":    risk_level(m.defects),
        }
        for i, m in enumerate(ranked)
    ]


def build_full_dashboard_payload(
    plant: Optional[str] = None,
    from_month: Optional[str] = None,
    to_month: Optional[str] = None,
) -> dict:
    """
    Single function that returns everything the dashboard needs as JSON.
    Used as an API endpoint response in Flask / FastAPI.
    """
    monthly  = filter_monthly(MONTHLY_DATA, plant, from_month, to_month)
    machines = filter_machines(MACHINE_DATA, plant)
    kpis     = compute_kpis(monthly, machines)
    alerts   = generate_alerts(machines)

    return {
        "kpis":        asdict(kpis),
        "trend_chart": build_trend_chart_data(monthly, "defects"),
        "plant_donut": build_plant_donut_data(plant),
        "bar_race":    build_bar_race_data(machines),
        "risk_table":  build_risk_table_data(machines),
        "alerts":      [asdict(a) for a in alerts],
        "filters": {
            "plant":      plant or "All",
            "from_month": from_month,
            "to_month":   to_month,
        },
    }


# ──────────────────────────────────────────────────────────
# 10. CSV EXPORT


def export_monthly_csv(
    monthly: list[MonthlySummary],
    filepath: str = "monthly_summary.csv",
) -> None:
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["month", "defects", "maint", "temp", "vib", "pres", "plant"]
        )
        writer.writeheader()
        writer.writerows(asdict(r) for r in monthly)
    print(f"✅ Exported {len(monthly)} rows → {filepath}")


def export_machines_csv(
    machines: list[Machine],
    filepath: str = "machines.csv",
) -> None:
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "plant", "defects", "maint", "vib", "risk"])
        writer.writeheader()
        for m in machines:
            row = asdict(m)
            row["risk"] = risk_level(m.defects)
            writer.writerow(row)
    print(f"✅ Exported {len(machines)} machines → {filepath}")


def export_dashboard_json(
    payload: dict,
    filepath: str = "dashboard_data.json",
) -> None:
    with open(filepath, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"✅ Dashboard payload saved → {filepath}")


# ──────────────────────────────────────────────────────────
# 11. OPTIONAL: FLASK API SKELETON

# Uncomment and run `pip install flask` to expose a REST API
# that the dashboard HTML can call instead of using hardcoded data.

# from flask import Flask, jsonify, request
#
# app = Flask(__name__)
#
# @app.route("/api/dashboard")
# def dashboard():
#     plant      = request.args.get("plant")           # ?plant=Plant+A
#     from_month = request.args.get("from")            # ?from=Jan+2025
#     to_month   = request.args.get("to")              # ?to=Dec+2026
#     payload    = build_full_dashboard_payload(plant, from_month, to_month)
#     return jsonify(payload)
#
# @app.route("/api/alerts")
# def alerts():
#     plant    = request.args.get("plant")
#     machines = filter_machines(MACHINE_DATA, plant)
#     return jsonify([asdict(a) for a in generate_alerts(machines)])
#
# if __name__ == "__main__":
#     app.run(debug=True, port=5000)


# ──────────────────────────────────────────────────────────
# 12. CLI DEMO


if __name__ == "__main__":
    print("=" * 60)
    print("  MACHINE HEALTH DASHBOARD — Python Backend Demo")
    print("=" * 60)

    # --- KPIs: all plants, full period ---
    kpis = compute_kpis(MONTHLY_DATA, MACHINE_DATA)
    print("\n📊 KPIs (All Plants · Full Period)")
    print(f"   Total Defects       : {kpis.total_defects:,}")
    print(f"   Maintenance Events  : {kpis.total_maint_events:,}")
    print(f"   Avg Vibration       : {kpis.avg_vibration} mm/s")
    print(f"   Avg Temperature     : {kpis.avg_temperature} °C")
    print(f"   Date Range          : {kpis.date_range}")
    print(f"   Critical Alerts     : {kpis.critical_alerts}")

    # --- KPIs filtered: Plant A, 2025 only ---
    filtered = filter_monthly(MONTHLY_DATA, plant="Plant A",
                               from_month="Jan 2025", to_month="Dec 2025")
    # Plant A gets ~33% of all-plant totals
    plant_a_monthly = [
        MonthlySummary(r.month, round(r.defects * 0.33), round(r.maint * 0.33),
                        r.temp, r.vib, r.pres, "Plant A")
        for r in filter_monthly(MONTHLY_DATA, from_month="Jan 2025", to_month="Dec 2025")
    ]
    plant_a_machines = filter_machines(MACHINE_DATA, plant="Plant A")
    kpis_a = compute_kpis(plant_a_monthly, plant_a_machines)
    print("\n📊 KPIs (Plant A · 2025 Only)")
    print(f"   Total Defects       : {kpis_a.total_defects:,}")
    print(f"   Maintenance Events  : {kpis_a.total_maint_events:,}")
    print(f"   Months              : {kpis_a.months_count}")

    # --- Alerts ---
    alerts = generate_alerts(MACHINE_DATA)
    print(f"\n🚨 Active Alerts ({len(alerts)} machines above threshold)")
    for a in alerts[:5]:
        print(f"   {a.message}")

    # --- Top 5 machines ---
    bar_data = build_bar_race_data(MACHINE_DATA, top_n=5)
    print("\n🏆 Top 5 Machines by Defects")
    for row in bar_data:
        print(f"   {row['id']:8s}  {row['plant']:8s}  {row['defects']:,} defects  [{row['risk']}]")

    # --- Trend chart data (first 3 months) ---
    trend = build_trend_chart_data(MONTHLY_DATA[:3], "defects")
    print(f"\n📈 Trend Chart (first 3 months, defects)")
    for lbl, val in zip(trend["labels"], trend["values"]):
        print(f"   {lbl}: {val:,}")

    # --- Plant donut ---
    donut = build_plant_donut_data()
    print("\n🍩 Plant Donut")
    for lbl, val, pct in zip(donut["labels"], donut["values"], donut["pct"]):
        print(f"   {lbl}: {val:,}  ({pct}%)")

    # --- DB query demo ---
    db = Database()
    rows = db.query(
        "SELECT plant, SUM(defects) as total FROM machines GROUP BY plant ORDER BY total DESC"
    )
    print("\n🗄️  DB — Defects by Plant")
    for row in rows:
        print(f"   {row['plant']}: {row['total']:,}")
    db.close()

    # --- Exports ---
    export_monthly_csv(MONTHLY_DATA)
    export_machines_csv(MACHINE_DATA)
    payload = build_full_dashboard_payload()
    export_dashboard_json(payload)

    print("\n✅ Done.")
