from future_bridge.config.config import settings
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import logging
from future_bridge.config.config import settings

client = None
cj_client=None
async def get_db():
    global client
    try:
        if client is None:
            if not settings.DATABASE_URL:
                logging.error("Database URL is not configured. Please check your environment variables.")
                raise ValueError("Database URL is not configured. Please check your environment variables.")
            
            logging.info(f"Connecting to MongoDB at {settings.DATABASE_URL}")
            try:
                client = AsyncIOMotorClient(settings.DATABASE_URL, serverSelectionTimeoutMS=5000)
                
                # Verify the connection
                await client.admin.command('ping')
                logging.info("Successfully connected to MongoDB")
                
                
            except ServerSelectionTimeoutError as e:
                logging.error(f"Could not connect to MongoDB server: {str(e)}")
                raise ConnectionFailure(f"Could not connect to MongoDB server: {str(e)}")
            
        return client[settings.DATABASE]
    except ConnectionFailure as e:
        logging.error(f"Failed to connect to MongoDB: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error while connecting to MongoDB: {str(e)}", exc_info=True)
        raise

async def get_cj_db():
    global cj_client
    try:
        if cj_client is None:
            if not settings.DATABASE_URL:
                logging.error("Database URL is not configured. Please check your environment variables.")
                raise ValueError("Database URL is not configured. Please check your environment variables.")
            
            logging.info(f"Connecting to MongoDB at {settings.DATABASE_URL}")
            try:
                cj_client = AsyncIOMotorClient(settings.DATABASE_URL, serverSelectionTimeoutMS=5000)
                
                # Verify the connection
                await cj_client.admin.command('ping')
                logging.info("Successfully connected to MongoDB")
                
            except ServerSelectionTimeoutError as e:
                logging.error(f"Could not connect to MongoDB server: {str(e)}")
                raise ConnectionFailure(f"Could not connect to MongoDB server: {str(e)}")
            
        return cj_client[settings.CJ_DATABASE]
    except ConnectionFailure as e:
        logging.error(f"Failed to connect to MongoDB: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error while connecting to MongoDB: {str(e)}", exc_info=True)
        raise