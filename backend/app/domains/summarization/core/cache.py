import redis.asyncio as redis
from typing import Optional

from ..config import settings

redis_pool: Optional[redis.ConnectionPool] = None

def init_redis_pool():
    """Initializes the Redis connection pool."""
    global redis_pool
    try:
        print(f"Initializing Redis connection pool for {settings.redis_host}:{settings.redis_port}")
        redis_pool = redis.ConnectionPool(
            host=settings.redis_host,
            port=settings.redis_port,
            # password=settings.redis_password, # Uncomment if password is set
            db=0, # Default Redis DB
            decode_responses=True # Decode keys/values from bytes to str
        )
        # Optional: Ping to check connection early
        # client = redis.Redis(connection_pool=redis_pool)
        # asyncio.run(client.ping()) # This won't work directly here, needs async context
        print("Redis connection pool initialized.")
    except Exception as e:
        print(f"Failed to initialize Redis connection pool: {e}")
        redis_pool = None # Ensure pool is None if init fails

async def get_redis_client() -> Optional[redis.Redis]:
    """Gets a Redis client instance from the pool."""
    if redis_pool is None:
        print("Redis pool not initialized. Cannot get client.")
        return None
    # Using Redis.from_pool is recommended for async
    return redis.Redis.from_pool(redis_pool)

# Initialize the pool when this module is imported
# In FastAPI, you might call this from a startup event (lifespan)
init_redis_pool()

# Optional: Close pool on shutdown (needs lifespan event in FastAPI)
# async def close_redis_pool():
#     if redis_pool:
#         print("Closing Redis connection pool...")
#         await redis_pool.disconnect()
#         print("Redis connection pool closed.") 