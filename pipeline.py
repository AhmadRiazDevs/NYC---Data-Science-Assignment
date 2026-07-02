import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent))

from src import config
from src import ingestion
from src import processing
import duckdb

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("pipeline.log")
    ]
)
logger = logging.getLogger("NYC_Pipeline")

def main():
    logger.info("Starting NYC Congestion Pricing Audit Pipeline...")
    
    # Phase 1: Ingestion
    logger.info(">>> Phase 1: Data Ingestion")
    ingestion.run_ingestion()
    
    
    # Phase 2: Processing & Fraud
    logger.info(">>> Phase 2: Data Processing & Fraud Detection")
    processing.run_processing()
    
    con = duckdb.connect(str(config.DB_PATH))
    from src import fraud
    fraud.detect_fraud(con)
    con.close()
    
    # Phase 3: Analysis
    logger.info(">>> Phase 3: Analysis")
    from src import analysis, weather
    
    # Run core analysis
    analysis.run_analysis()
    
    # Run weather analysis
    weather.run_weather_analysis()
    
    # Phase 4: Reporting
    logger.info(">>> Phase 4: Generating Reports")
    try:
        import report_generator
        report_generator.generate_pdf_report()
    except ImportError:
        logger.warning("Report generator not found or failed to import.")
    
    logger.info("Pipeline execution finished. Run 'streamlit run dashboard_app.py' to view the dashboard.")

if __name__ == "__main__":
    main()
