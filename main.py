import logging, os
from src.ingestionpipeline import IngestionPipeline
from dotenv import load_dotenv
os.environ["DB_NAME"] = "rating_warehouse"
os.environ["DB_USER"] = "rating_warehouse_user"
os.environ["DB_PASSWORD"] = "your_secure_password"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] =  "5432"
 
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, 
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logger = logging.getLogger("MainOrchestrator")
    
    logger.info("Initializing multi-entity file ingestion suite...")
    try:
        logger.info("Pipe Creation Started")
        pipeline = IngestionPipeline()
        pipeline.run_pipe()


        logger.info("Batch execution sequence finished successfully. %s ",pipeline.datapath )
    except Exception as e:
        logger.critical("Batch sequence halted due to an unhandled exception: %s", e)
        
        