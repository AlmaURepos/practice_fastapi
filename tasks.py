from celery_config import app as celery_app
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@celery_app.task
def send_mock_msg():
    time.sleep(10)
    logger.info("Celery logging is working")