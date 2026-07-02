import requests
import duckdb
import pandas as pd
import logging
from . import config

logger = logging.getLogger(__name__)

def fetch_weather_data():
    """
    Fetches daily precipitation sum for 2025 from Open-Meteo.
    """
    logger.info("Fetching Weather Data...")
    
    params = {
        "latitude": config.LATITUDE,
        "longitude": config.LONGITUDE,
        "start_date": f"{config.TARGET_YEAR}-01-01",
        "end_date": f"{config.TARGET_YEAR}-12-31",
        "daily": "precipitation_sum",
        "timezone": "America/New_York"
    }
    
    try:
        response = requests.get(config.WEATHER_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        df = pd.DataFrame({
            "date": pd.to_datetime(data["daily"]["time"]),
            "precipitation": data["daily"]["precipitation_sum"]
        })
        
        # Save to DuckDB/Parquet
        df.to_parquet(config.OUTPUT_DIR / "weather_2025.parquet")
        logger.info("Weather data saved.")
        return df
        
    except Exception as e:
        logger.error(f"Failed to fetch weather data: {e}")
        return None

def compute_rain_elasticity(con):
    """
    Computes Rain Elasticity: Correlation between Daily Trip Count and Rainfall.
    """
    logger.info("Computing Rain Elasticity...")
    
    # Ensure weather data is loaded
    weather_path = config.OUTPUT_DIR / "weather_2025.parquet"
    if not weather_path.exists():
        logger.warning("Weather data not found. Skipping elasticity.")
        return

    # Daily Trip Counts
    con.execute(f"""
        CREATE OR REPLACE TABLE daily_trips AS
        SELECT
            CAST(pickup_time AS DATE) as date,
            COUNT(*) as trip_count
        FROM processed_trips
        WHERE is_fraud = 0
        GROUP BY 1
    """)
    
    # Join
    con.execute(f"""
        CREATE OR REPLACE TABLE weather_trips AS
        SELECT 
            t.date,
            t.trip_count,
            w.precipitation
        FROM daily_trips t
        JOIN read_parquet('{weather_path}') w ON t.date = w.date
    """)
    
    # Calculate Correlation
    res = con.execute("""
        SELECT corr(trip_count, precipitation) 
        FROM weather_trips
    """).fetchone()
    
    correlation = res[0] if res else 0
    logger.info(f"Rain Elasticity (Correlation): {correlation}")
    
    with open(config.OUTPUT_DIR / "rain_elasticity.txt", "w") as f:
        f.write(f"Rain Elasticity Score: {correlation}\n")

def run_weather_analysis():
    fetch_weather_data()
    con = duckdb.connect(str(config.DB_PATH))
    compute_rain_elasticity(con)
    con.close()
