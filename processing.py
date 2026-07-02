import duckdb
import pandas as pd
import logging
from pathlib import Path
from . import config

logger = logging.getLogger(__name__)

def init_db():
    """Initializes the DuckDB database and extensions."""
    logger.info(f"Initializing DuckDB at {config.DB_PATH}")
    con = duckdb.connect(str(config.DB_PATH))
    con.execute("INSTALL spatial;")
    con.execute("LOAD spatial;")
    con.close()

def impute_december_data():
    """
    Imputes December 2025 data using 30% of Dec 2023 and 70% of Dec 2024.
    Ref: '30% weight from Dec 2023, 70% weight from Dec 2024'
    """
    logger.info("Imputing December 2025 data...")
    
    # Define paths
    dec_23_path = config.RAW_DATA_DIR / "yellow_tripdata_2023-12.parquet"
    dec_24_path = config.RAW_DATA_DIR / "yellow_tripdata_2024-12.parquet"
    output_path = config.RAW_DATA_DIR / "yellow_tripdata_2025-12.parquet"
    
    if output_path.exists():
        logger.info("Imputed file already exists.")
        return

    # Check existence
    if not dec_23_path.exists() or not dec_24_path.exists():
        logger.warning("Historical data for imputation missing. Skipping imputation.")
        return

    try:
        # Load using DuckDB for efficiency, then convert result to Pandas for sampling if needed, 
        # or just sample in SQL.
        
        # We need to shift dates to 2025.
        # SQL logic: 
        # 1. Select * from 2023, sample 30%, shift year to 2025
        # 2. Select * from 2024, sample 70%, shift year to 2025
        # 3. Union and export
        
        con = duckdb.connect()
        
        query = f"""
        COPY (
            SELECT 
                * REPLACE(
                    tpep_pickup_datetime + INTERVAL (2025 - 2023) YEAR AS tpep_pickup_datetime,
                    tpep_dropoff_datetime + INTERVAL (2025 - 2023) YEAR AS tpep_dropoff_datetime
                )
            FROM '{dec_23_path}'
            USING SAMPLE 30%
            
            UNION ALL
            
            SELECT 
                * REPLACE(
                    tpep_pickup_datetime + INTERVAL (2025 - 2024) YEAR AS tpep_pickup_datetime,
                    tpep_dropoff_datetime + INTERVAL (2025 - 2024) YEAR AS tpep_dropoff_datetime
                )
            FROM '{dec_24_path}'
            USING SAMPLE 70%
        ) TO '{output_path}' (FORMAT 'parquet');
        """
        
        con.execute(query)
        logger.info(f"Generated imputed file: {output_path}")
        
    except Exception as e:
        logger.error(f"Imputation failed: {e}")

def create_normalized_schema(con):
    """Creates the normalized schema in DuckDB."""
    logger.info("Creating normalized schema...")
    
    # We create a view or table that unifies yellow and green taxi data
    # and maps columns to our standard schema.
    
    # First, list all parquet files for 2025
    raw_pattern = str(config.RAW_DATA_DIR / "*2025*.parquet")
    
    # Depending on file availability, we might need to be dynamic.
    # For now, let's assume we can read all matching 2025 files.
    
    # Prefer reading yellow and green files separately to avoid schema mismatches
    yellow_pattern = str(config.RAW_DATA_DIR / "*yellow*2025*.parquet")
    green_pattern = str(config.RAW_DATA_DIR / "*green*2025*.parquet")

    # Create or replace table from yellow files if present
    try:
        con.execute(f"CREATE OR REPLACE TABLE raw_trips AS\n"
                    f"SELECT\n"
                    f"    tpep_pickup_datetime AS pickup_time,\n"
                    f"    tpep_dropoff_datetime AS dropoff_time,\n"
                    f"    PULocationID AS pickup_loc,\n"
                    f"    DOLocationID AS dropoff_loc,\n"
                    f"    trip_distance,\n"
                    f"    fare_amount AS fare,\n"
                    f"    total_amount,\n"
                    f"    congestion_surcharge,\n"
                    f"    VendorID AS vendor_id,\n"
                    f"    'yellow' AS taxi_type\n"
                    f"FROM read_parquet('{yellow_pattern}')")
        logger.info("Loaded yellow taxi files into raw_trips.")
    except Exception as e:
        logger.warning(f"No yellow files loaded or error reading yellow files: {e}")

    # Append green files if present (green uses lpep_* column names)
    try:
        con.execute(f"INSERT INTO raw_trips\n"
                    f"SELECT\n"
                    f"    lpep_pickup_datetime AS pickup_time,\n"
                    f"    lpep_dropoff_datetime AS dropoff_time,\n"
                    f"    PULocationID AS pickup_loc,\n"
                    f"    DOLocationID AS dropoff_loc,\n"
                    f"    trip_distance,\n"
                    f"    fare_amount AS fare,\n"
                    f"    total_amount,\n"
                    f"    congestion_surcharge,\n"
                    f"    VendorID AS vendor_id,\n"
                    f"    'green' AS taxi_type\n"
                    f"FROM read_parquet('{green_pattern}')")
        logger.info("Appended green taxi files into raw_trips.")
    except Exception as e:
        logger.info(f"No green files appended (may be missing): {e}")

    logger.info("Schema normalization complete.")

def run_processing():
    """Main processing logic."""
    init_db()
    impute_december_data()
    
    con = duckdb.connect(str(config.DB_PATH))
    create_normalized_schema(con)
    con.close()
    
if __name__ == "__main__":
    run_processing()
