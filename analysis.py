import duckdb
import logging
from . import config

logger = logging.getLogger(__name__)

def analyze_zone_leakage(con):
    """
    Leakage Audit:
    - Compute Surcharge Compliance Rate (Trips entering zone vs Paid Surcharge)
    - Top 3 pickup locations missing surcharge
    """
    logger.info("Analyzing Zone Leakage...")
    
    # Assuming Congestion Zone is Manhattan South of 60th St.
    # We would need a shapefile or list of LocationIDs for accurate checking.
    # For this exercise, let's assume specific LocationIDs correspond to the zone.
    # Ref: Manhattan Yellow Zone IDs (approximate list for demo)
    zone_ids = [261, 262, 263, 237, 236, 230, 249, 231, 246, 161, 162, 163, 164, 186, 170, 107, 113, 114, 79, 4, 24, 151, 238, 239, 142, 143, 144, 148, 140, 141, 229, 233, 137]
    zone_ids_str = ",".join(map(str, zone_ids))
    
    # Logic: If Dropoff OR Pickup is in Zone (simplified rule for demonstration), surcharge should apply.
    # Current rule: Trips starting in or entering the zone.
    
    con.execute(f"""
        CREATE OR REPLACE TABLE zone_trips AS
        SELECT * FROM processed_trips
        WHERE (pickup_loc IN ({zone_ids_str}) OR dropoff_loc IN ({zone_ids_str}))
        AND is_fraud = 0
    """)
    
    # Compliance Rate
    con.execute(f"""
        CREATE OR REPLACE TABLE leakage_stats AS
        SELECT
            COUNT(*) as total_zone_trips,
            SUM(CASE WHEN congestion_surcharge > 0 THEN 1 ELSE 0 END) as compliant_trips,
            (SUM(CASE WHEN congestion_surcharge > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as compliance_rate
        FROM zone_trips
    """)
    
    # Top Missing Locations
    con.execute(f"""
        CREATE OR REPLACE TABLE top_missing_surcharge_locs AS
        SELECT 
            pickup_loc,
            COUNT(*) as missing_count
        FROM zone_trips
        WHERE congestion_surcharge <= 0
        GROUP BY pickup_loc
        ORDER BY missing_count DESC
        LIMIT 3
    """)
    
    # Export for dashboard
    con.execute(f"COPY leakage_stats TO '{config.OUTPUT_DIR}/leakage_stats.parquet' (FORMAT 'parquet')")
    con.execute(f"COPY top_missing_surcharge_locs TO '{config.OUTPUT_DIR}/top_missing_surcharge_locs.parquet' (FORMAT 'parquet')")

def analyze_decline(con):
    """
    Yellow vs Green Decline:
    Compare Q1 2024 vs Q1 2025 (Trips entering congestion zone)
    """
    logger.info("Analyzing Trip Decline...")
    
    con.execute(f"""
        CREATE OR REPLACE TABLE yearly_comparison AS
        SELECT
            YEAR(pickup_time) as year,
            MONTH(pickup_time) as month,
            taxi_type,
            COUNT(*) as trip_count
        FROM processed_trips
        WHERE is_fraud = 0
          AND (YEAR(pickup_time) = 2024 OR YEAR(pickup_time) = 2025)
          AND MONTH(pickup_time) BETWEEN 1 AND 3
        GROUP BY 1, 2, 3
    """)
    
    con.execute(f"COPY yearly_comparison TO '{config.OUTPUT_DIR}/yearly_comparison.parquet' (FORMAT 'parquet')")

def analyze_border_effect(con):
    """
    Border Effect: Changes in drop-offs just outside the zone.
    Hypothesis: Raiders drop off just outside toll zone.
    """
    logger.info("Analyzing Border Effect...")
    
    # Assume border zones are those adjacent to the main zone list. 
    # For demo, we define a set of 'Border IDs'.
    border_ids = [238, 239, 142, 143] # Placeholder IDs
    border_ids_str = ",".join(map(str, border_ids))

    con.execute(f"""
        CREATE OR REPLACE TABLE border_stats AS
        SELECT
            dropoff_loc,
            YEAR(pickup_time) as year,
            COUNT(*) as dropoff_count
        FROM processed_trips
        WHERE dropoff_loc IN ({border_ids_str})
        AND is_fraud = 0
        GROUP BY 1, 2
    """)
    
    con.execute(f"COPY border_stats TO '{config.OUTPUT_DIR}/border_stats.parquet' (FORMAT 'parquet')")

def analyze_velocity(con):
    """
    Congestion Velocity Heatmaps: Hour vs Day of Week
    """
    logger.info("Analyzing Velocity...")
    
    con.execute(f"""
        CREATE OR REPLACE TABLE velocity_heatmap AS
        SELECT
            DAYOFWEEK(pickup_time) as dow,
            HOUR(pickup_time) as hour,
            AVG(speed_mph) as avg_speed
        FROM processed_trips
        WHERE is_fraud = 0
        GROUP BY 1, 2
    """)
    
    con.execute(f"COPY velocity_heatmap TO '{config.OUTPUT_DIR}/velocity_heatmap.parquet' (FORMAT 'parquet')")

def analyze_tips(con):
    """
    Tip Crowding-Out Analysis
    """
    logger.info("Analyzing Tips...")
    
    con.execute(f"""
        CREATE OR REPLACE TABLE tip_stats AS
        SELECT
            MONTH(pickup_time) as month,
            AVG(congestion_surcharge) as avg_surcharge,
            AVG(fare) as avg_fare,
            AVG(CASE WHEN total_amount > 0 THEN (total_amount - fare - congestion_surcharge) / NULLIF(fare,0) ELSE 0 END) * 100 as tip_pct
        FROM processed_trips
        WHERE is_fraud = 0
        GROUP BY 1
    """)
    
    con.execute(f"COPY tip_stats TO '{config.OUTPUT_DIR}/tip_stats.parquet' (FORMAT 'parquet')")

def run_analysis():
    con = duckdb.connect(str(config.DB_PATH))
    analyze_zone_leakage(con)
    analyze_decline(con)
    analyze_border_effect(con)
    analyze_velocity(con)
    analyze_tips(con)
    con.close()
