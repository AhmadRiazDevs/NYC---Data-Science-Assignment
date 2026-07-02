import duckdb
import logging
from . import config

logger = logging.getLogger(__name__)

def detect_fraud(con):
    """
    Detects and logs suspicious trips into a separate audit table.
    Rules:
    - Avg Speed > 65 MPH
    - Duration < 1 minute
    - Distance = 0 AND Fare > 0
    - Fare > $MAX_FARE (Sanity check)
    """
    logger.info("Running Fraud Detection...")
    
    # Define duration in minutes and speed in mph
    # Note: DuckDB's date_diff returns integer units. For seconds we need precision.
    # epoch(dropoff) - epoch(pickup) gives seconds.
    
    con.execute(f"""
        CREATE OR REPLACE TABLE trips_with_metrics AS 
        SELECT 
            *,
            (epoch(dropoff_time) - epoch(pickup_time)) / 60.0 AS duration_minutes,
            CASE 
                WHEN (epoch(dropoff_time) - epoch(pickup_time)) = 0 THEN 0
                ELSE trip_distance / ((epoch(dropoff_time) - epoch(pickup_time)) / 3600.0) 
            END AS speed_mph
        FROM raw_trips
    """)

    # Identify Fraud
    con.execute(f"""
        CREATE OR REPLACE TABLE fraud_audit AS
        SELECT *
        FROM trips_with_metrics
        WHERE 
            speed_mph > {config.MAX_SPEED_MPH}
            OR duration_minutes < {config.MIN_DURATION_MINUTES}
            OR (trip_distance = 0 AND fare > 0)
            OR fare > {config.MAX_FARE}
    """)
   
    con.execute(f"""
        CREATE OR REPLACE TABLE processed_trips AS
        SELECT 
            *,
            CASE
                WHEN speed_mph > {config.MAX_SPEED_MPH} THEN 1
                WHEN duration_minutes < {config.MIN_DURATION_MINUTES} THEN 1
                WHEN (trip_distance = 0 AND fare > 0) THEN 1
                WHEN fare > {config.MAX_FARE} THEN 1
                ELSE 0
            END AS is_fraud,
            CASE
                WHEN speed_mph > {config.MAX_SPEED_MPH} THEN 'Impossible Speed'
                WHEN duration_minutes < {config.MIN_DURATION_MINUTES} THEN 'Short Duration'
                WHEN (trip_distance = 0 AND fare > 0) THEN 'Stationary Ride'
                WHEN fare > {config.MAX_FARE} THEN 'High Fare'
                ELSE NULL
            END AS fraud_reason
        FROM trips_with_metrics
    """)
    
    # Export Fraud Log
    fraud_count = con.execute("SELECT count(*) FROM processed_trips WHERE is_fraud = 1").fetchone()[0]
    logger.info(f"Fraud detection complete. Found {fraud_count} suspicious trips.")
    
    # Save fraud report
    con.execute(f"""
        COPY (SELECT * FROM processed_trips WHERE is_fraud = 1) 
        TO '{config.OUTPUT_DIR}/fraud_audit.csv' (HEADER, DELIMITER ',')
    """)

def run_fraud_check():
    con = duckdb.connect(str(config.DB_PATH))
    detect_fraud(con)
    con.close()
