import logging
import os

def setup_logger():
    logger = logging.getLogger("KellysCreepyDeathDiggerMachine")
    logger.setLevel(logging.DEBUG)
    
    # Create AppData directory for logs
    app_data_dir = os.path.join(
        os.getenv("APPDATA", os.path.expanduser("~")),
        "KellysCreepyDeathDiggerMachine"
    )
    os.makedirs(app_data_dir, exist_ok=True)
    log_path = os.path.join(app_data_dir, "app.log")
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # File handler (Targeting writable AppData)
    try:
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to initialize file logger: {e}")
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logger()
