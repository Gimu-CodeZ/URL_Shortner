from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os
import redis
from fastapi import HTTPException

# Load environment variables from .env file
load_dotenv()

# Get MongoDB URI from environment variable
MONGODB_URI = os.getenv("MONGODB_URI")

try:
    # Create a new client and connect to the server
    client = MongoClient(MONGODB_URI, server_api=ServerApi('1'))
    #Access db
    db = client.url_shortner
    # Access collections
    collection_user = db.user
    collection_url = db.urls
    print("MongoDB connected successfully.")
except Exception as e:
    print("MongoDB connection failed:", e)
    collection_user = None
    collection_url = None

broker_url = os.getenv("REDIS_URL")
result_backend = broker_url

# # Initialize Redis client
# try:    
#     redis_client = redis.Redis.from_url(broker_url)
#     redis_client.ping() 
#     print("Redis connected successfully.")
# except Exception as e:
#     print("Redis connection failed:", e)
#     redis_client = None

_redis_client = None

def get_redis_client():
    global _redis_client
    if _redis_client is None:
        try:
            # Try to use Redis URL from environment if available
            if broker_url:
                try:
                    _redis_client = redis.Redis.from_url(
                        broker_url,
                        decode_responses=True,
                        socket_connect_timeout=5,
                        retry_on_timeout=True
                    )
                except Exception as url_error:
                    print(f"Failed to connect using REDIS_URL: {url_error}")
                    # Fallback to local connection
                    _redis_client = None

            # If broker_url failed or isn't set, try localhost
            if _redis_client is None:
                _redis_client = redis.Redis(
                    host='localhost',
                    port=6379,
                    db=0,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    retry_on_timeout=True
                )
            
            # Test the connection
            if not _redis_client.ping():
                raise redis.ConnectionError("Redis ping failed")
            print("Redis connected successfully.")
            
        except Exception as e:
            print(f"Redis connection failed: {str(e)}")
            _redis_client = None
            raise HTTPException(
                status_code=500,
                detail=f"Redis connection failed: {str(e)}"
            )
    
    # Verify connection is still alive before returning
    try:
        _redis_client.ping()
        return _redis_client
    except Exception as e:
        _redis_client = None
        raise HTTPException(
            status_code=500,
            detail="Redis connection lost"
        )
# try:
#     redis_client = redis.Redis(
#         host='localhost',  # or your Redis host
#         port=6379,        # default Redis port
#         db=0,            # default database
#         decode_responses=True
#     )
# except redis.ConnectionError as e:
#     print(f"Failed to connect to Redis: {e}")
#     redis_client = None