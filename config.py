import os
from pathlib import Path

# Project Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Data Directories
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
DB_DIR = DATA_DIR / "db"
OUTPUT_DIR = DATA_DIR / "output"

# Database path
DB_PATH = DB_DIR / "nyc_taxi.duckdb"

# TLC Data Source
TLC_BASE_URL = "https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page"

# Years/Months to process
TARGET_YEAR = 2025
HISTORICAL_YEARS = [2023, 2024] # For imputation and comparison

# Hardcoded schema mapping for normalization
COLUMN_MAPPING = {
    "tpep_pickup_datetime": "pickup_time",
    "lpep_pickup_datetime": "pickup_time",
    "tpep_dropoff_datetime": "dropoff_time",
    "lpep_dropoff_datetime": "dropoff_time",
    "PULocationID": "pickup_loc",
    "DOLocationID": "dropoff_loc",
    "trip_distance": "trip_distance",
    "fare_amount": "fare",
    "total_amount": "total_amount",
    "congestion_surcharge": "congestion_surcharge",
    "VendorID": "vendor_id",
    "passenger_count": "passenger_count"
}

# Fraud Thresholds
MAX_SPEED_MPH = 65
MIN_DURATION_MINUTES = 1
MAX_FARE = 1000 # Sanity check, user said > $20 for specific fraud rule but let's keep robust
MIN_FARE = 0

# Weather API
WEATHER_API_URL = "https://archive-api.open-meteo.com/v1/archive"
LATITUDE = 40.7831  # Central Park
LONGITUDE = -73.9712
