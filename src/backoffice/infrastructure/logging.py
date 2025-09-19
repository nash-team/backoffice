import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            RotatingFileHandler(f"{log_dir}/app.log", maxBytes=10485760, backupCount=5),  # 10MB
            logging.StreamHandler(),
        ],
    )
