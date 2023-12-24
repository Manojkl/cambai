from fastapi import FastAPI, HTTPException, Depends, status
from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table
from sqlalchemy.orm import sessionmaker
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
import aioredis
from sqlalchemy.orm import Session

# FastAPI app initialization
app = FastAPI()

# Database Configuration
DATABASE_URL = "postgresql://welcome:welcome@postgresql-service:5432/my_database"  # Replace with your PostgreSQL connection details
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
metadata = MetaData()

# Define the users table
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("user_id", String, index=True),
    Column("key", String, index=True),
    Column("value", Integer),
)

metadata.create_all(bind=engine)
# Connect to Redis
async def get_redis():
    redis = aioredis.from_url("redis://redis-service:6379/")
    yield redis
    redis.close()
    await redis.wait_closed()

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize FastAPI Cache with RedisBackend
redis = aioredis.from_url("redis://redis-service:6379/")
redis_backend = RedisBackend(redis)
FastAPICache.init(redis_backend, prefix="fastapi_cache")

# Endpoint to create a new record in PostgreSQL and Redis
@app.post("/create-record/")
async def create_record(user_id: str, key: str, value: int, db: Session = Depends(get_db), redis: aioredis.Redis = Depends(get_redis)):
    db.execute(users.insert().values(user_id=user_id, key=key, value=value))
    db.commit()

    # Update or add to Redis cache
    await redis.set(f"{user_id}:{key}", str(value))

    return {"user_id": user_id, "key": key, "value": value}

# Endpoint to retrieve a record from PostgreSQL and Redis based on user_id and key
@app.get("/get-record/")
async def get_record(user_id: str, key: str, db: Session = Depends(get_db), redis: aioredis.Redis = Depends(get_redis)):
    # Check if data is in Redis
    cached_value = await redis.get(f"{user_id}:{key}")
    
    if cached_value is not None:
        return {"user_id": user_id, "key": key, "value": int(cached_value), "source": "cache_hit"}

    # If not in Redis, fetch from PostgreSQL and update Redis
    result = db.execute(users.select().where(users.c.user_id == user_id, users.c.key == key)).fetchone()
    if result is None:
        raise HTTPException(status_code=404, detail="Record not found")

    value = result["value"]
    await redis.set(f"{user_id}:{key}", str(value))
    return {"user_id": user_id, "key": key, "value": value, "source": "cache_miss"}

# Endpoint to delete a record from PostgreSQL and Redis based on user_id and key
@app.delete("/delete-record/")
async def delete_record(user_id: str, key: str, db: Session = Depends(get_db), redis: aioredis.Redis = Depends(get_redis)):
    # Delete from PostgreSQL
    db.execute(users.delete().where(users.c.user_id == user_id, users.c.key == key))
    db.commit()

    # Delete from Redis
    await redis.delete(f"{user_id}:{key}")
    return {"message": "Record deleted successfully"}

# Endpoint to increment the value by x in PostgreSQL and Redis based on user_id and key
@app.post("/increment-value/")
async def increment_value(user_id: str, key: str, x: int, db: Session = Depends(get_db), redis: aioredis.Redis = Depends(get_redis)):
    # Increment in PostgreSQL
    db.execute(users.update().where(users.c.user_id == user_id, users.c.key == key).values(value=users.c.value + x))
    db.commit()

    # Update Redis cache
    cached_value = await redis.get(f"{user_id}:{key}")
    if cached_value:
        updated_value = int(cached_value) + x
        await redis.set(f"{user_id}:{key}", str(updated_value))

    return {"message": "Value incremented successfully"}

# Endpoint to decrement the value by x in PostgreSQL and Redis based on user_id and key
@app.post("/decrement-value/")
async def decrement_value(user_id: str, key: str, x: int, db: Session = Depends(get_db), redis: aioredis.Redis = Depends(get_redis)):
    # Decrement in PostgreSQL
    db.execute(users.update().where(users.c.user_id == user_id, users.c.key == key).values(value=users.c.value - x))
    db.commit()

    # Update Redis cache
    cached_value = await redis.get(f"{user_id}:{key}")
    if cached_value:
        updated_value = int(cached_value) - x
        await redis.set(f"{user_id}:{key}", str(updated_value))

    return {"message": "Value decremented successfully"}

# Steps to deploy the application in Minikube:
# 1. Create Dockerfiles for FastAPI, PostgreSQL, and Redis services.
# 2. Build Docker images for each service.
# 3. Create Kubernetes deployment files (Deployment, Service, ConfigMap) for each service.
# 4. Deploy the services using `kubectl apply -f <deployment-file.yaml>` for each service.
# 5. Expose the FastAPI service using `kubectl expose deployment fastapi-service --type=NodePort` or use an Ingress.
# 6. Access the application using the Minikube IP and the assigned NodePort.

# This is a basic setup, and /you may need to adjust it based on your specific requirements and production considerations.
