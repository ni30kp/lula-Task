import json
import logging
from typing import Optional, Any, Dict
import redis
from datetime import datetime

from app.core.config import get_redis_url

logger = logging.getLogger(__name__)

# Redis client
redis_client = redis.from_url(get_redis_url(), decode_responses=True)

def cache_set(key: str, value: str, ttl: int = 300) -> bool:
    """
    Set cache value with TTL.
    
    Args:
        key: Cache key
        value: Value to cache (string)
        ttl: Time to live in seconds
        
    Returns:
        True if successful, False otherwise
    """
    try:
        redis_client.setex(key, ttl, value)
        return True
    except Exception as e:
        logger.error(f"Cache set error for key {key}: {str(e)}")
        return False

def cache_get(key: str) -> Optional[str]:
    """
    Get cache value.
    
    Args:
        key: Cache key
        
    Returns:
        Cached value or None if not found
    """
    try:
        return redis_client.get(key)
    except Exception as e:
        logger.error(f"Cache get error for key {key}: {str(e)}")
        return None

def cache_delete(key: str) -> bool:
    """
    Delete cache value.
    
    Args:
        key: Cache key
        
    Returns:
        True if successful, False otherwise
    """
    try:
        redis_client.delete(key)
        return True
    except Exception as e:
        logger.error(f"Cache delete error for key {key}: {str(e)}")
        return False

def cache_set_json(key: str, value: Dict[str, Any], ttl: int = 300) -> bool:
    """
    Set JSON cache value with TTL.
    
    Args:
        key: Cache key
        value: Dictionary to cache
        ttl: Time to live in seconds
        
    Returns:
        True if successful, False otherwise
    """
    try:
        json_value = json.dumps(value)
        return cache_set(key, json_value, ttl)
    except Exception as e:
        logger.error(f"Cache set JSON error for key {key}: {str(e)}")
        return False

def cache_get_json(key: str) -> Optional[Dict[str, Any]]:
    """
    Get JSON cache value.
    
    Args:
        key: Cache key
        
    Returns:
        Cached dictionary or None if not found
    """
    try:
        value = cache_get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.error(f"Cache get JSON error for key {key}: {str(e)}")
        return None

def cache_exists(key: str) -> bool:
    """
    Check if cache key exists.
    
    Args:
        key: Cache key
        
    Returns:
        True if key exists, False otherwise
    """
    try:
        return redis_client.exists(key) > 0
    except Exception as e:
        logger.error(f"Cache exists error for key {key}: {str(e)}")
        return False

def cache_ttl(key: str) -> int:
    """
    Get remaining TTL for cache key.
    
    Args:
        key: Cache key
        
    Returns:
        Remaining TTL in seconds, -1 if key doesn't exist, -2 if key has no TTL
    """
    try:
        return redis_client.ttl(key)
    except Exception as e:
        logger.error(f"Cache TTL error for key {key}: {str(e)}")
        return -1

def cache_increment(key: str, amount: int = 1, ttl: int = 300) -> Optional[int]:
    """
    Increment cache value (useful for counters).
    
    Args:
        key: Cache key
        amount: Amount to increment
        ttl: Time to live in seconds
        
    Returns:
        New value or None if error
    """
    try:
        # Use Redis pipeline for atomic operation
        pipe = redis_client.pipeline()
        pipe.incr(key, amount)
        pipe.expire(key, ttl)
        result = pipe.execute()
        return result[0]
    except Exception as e:
        logger.error(f"Cache increment error for key {key}: {str(e)}")
        return None

def cache_set_hash(key: str, mapping: Dict[str, str], ttl: int = 300) -> bool:
    """
    Set hash cache value.
    
    Args:
        key: Cache key
        mapping: Dictionary to store as hash
        ttl: Time to live in seconds
        
    Returns:
        True if successful, False otherwise
    """
    try:
        pipe = redis_client.pipeline()
        pipe.hset(key, mapping=mapping)
        pipe.expire(key, ttl)
        pipe.execute()
        return True
    except Exception as e:
        logger.error(f"Cache set hash error for key {key}: {str(e)}")
        return False

def cache_get_hash(key: str) -> Optional[Dict[str, str]]:
    """
    Get hash cache value.
    
    Args:
        key: Cache key
        
    Returns:
        Hash dictionary or None if not found
    """
    try:
        return redis_client.hgetall(key)
    except Exception as e:
        logger.error(f"Cache get hash error for key {key}: {str(e)}")
        return None

def cache_delete_pattern(pattern: str) -> int:
    """
    Delete cache keys matching pattern.
    
    Args:
        pattern: Redis pattern (e.g., "user:*")
        
    Returns:
        Number of keys deleted
    """
    try:
        keys = redis_client.keys(pattern)
        if keys:
            return redis_client.delete(*keys)
        return 0
    except Exception as e:
        logger.error(f"Cache delete pattern error for pattern {pattern}: {str(e)}")
        return 0

def cache_clear_all() -> bool:
    """
    Clear all cache (use with caution).
    
    Returns:
        True if successful, False otherwise
    """
    try:
        redis_client.flushdb()
        return True
    except Exception as e:
        logger.error(f"Cache clear all error: {str(e)}")
        return False

def cache_get_stats() -> Dict[str, Any]:
    """
    Get cache statistics.
    
    Returns:
        Dictionary with cache statistics
    """
    try:
        info = redis_client.info()
        return {
            "total_keys": info.get("db0", {}).get("keys", 0),
            "memory_used": info.get("used_memory_human", "0B"),
            "connected_clients": info.get("connected_clients", 0),
            "uptime_seconds": info.get("uptime_in_seconds", 0),
            "redis_version": info.get("redis_version", "unknown")
        }
    except Exception as e:
        logger.error(f"Cache stats error: {str(e)}")
        return {}

# Cache key generators
def generate_issue_cache_key(issue_id: int) -> str:
    """Generate cache key for issue data"""
    return f"issue:{issue_id}"

def generate_customer_cache_key(customer_id: int) -> str:
    """Generate cache key for customer data"""
    return f"customer:{customer_id}"

def generate_user_cache_key(user_id: int) -> str:
    """Generate cache key for user data"""
    return f"user:{user_id}"

def generate_analysis_cache_key(issue_id: int, timestamp: float) -> str:
    """Generate cache key for issue analysis"""
    return f"analysis:{issue_id}:{timestamp}"

def generate_recommendation_cache_key(issue_id: int) -> str:
    """Generate cache key for recommendations"""
    return f"recommendations:{issue_id}"

def generate_conversation_cache_key(conversation_id: int) -> str:
    """Generate cache key for conversation data"""
    return f"conversation:{conversation_id}"

# Cache utilities for specific use cases
def cache_issue_data(issue_id: int, issue_data: Dict[str, Any], ttl: int = 1800) -> bool:
    """Cache issue data"""
    key = generate_issue_cache_key(issue_id)
    return cache_set_json(key, issue_data, ttl)

def get_cached_issue_data(issue_id: int) -> Optional[Dict[str, Any]]:
    """Get cached issue data"""
    key = generate_issue_cache_key(issue_id)
    return cache_get_json(key)

def cache_customer_data(customer_id: int, customer_data: Dict[str, Any], ttl: int = 3600) -> bool:
    """Cache customer data"""
    key = generate_customer_cache_key(customer_id)
    return cache_set_json(key, customer_data, ttl)

def get_cached_customer_data(customer_id: int) -> Optional[Dict[str, Any]]:
    """Get cached customer data"""
    key = generate_customer_cache_key(customer_id)
    return cache_get_json(key)

def cache_user_session(user_id: int, session_data: Dict[str, Any], ttl: int = 1800) -> bool:
    """Cache user session data"""
    key = f"session:user:{user_id}"
    return cache_set_json(key, session_data, ttl)

def get_cached_user_session(user_id: int) -> Optional[Dict[str, Any]]:
    """Get cached user session data"""
    key = f"session:user:{user_id}"
    return cache_get_json(key)

def cache_api_response(endpoint: str, params: Dict[str, Any], response: Dict[str, Any], ttl: int = 300) -> bool:
    """Cache API response"""
    # Create a hash of the endpoint and parameters for the cache key
    import hashlib
    param_str = json.dumps(params, sort_keys=True)
    key_hash = hashlib.md5(f"{endpoint}:{param_str}".encode()).hexdigest()
    key = f"api:{endpoint}:{key_hash}"
    return cache_set_json(key, response, ttl)

def get_cached_api_response(endpoint: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Get cached API response"""
    import hashlib
    param_str = json.dumps(params, sort_keys=True)
    key_hash = hashlib.md5(f"{endpoint}:{param_str}".encode()).hexdigest()
    key = f"api:{endpoint}:{key_hash}"
    return cache_get_json(key)

def cache_rate_limit(key: str, limit: int, window: int) -> bool:
    """Cache rate limit counter"""
    return cache_increment(key, 1, window) is not None

def get_rate_limit_count(key: str) -> int:
    """Get current rate limit count"""
    count = cache_get(key)
    return int(count) if count else 0

def is_rate_limited(key: str, limit: int) -> bool:
    """Check if request is rate limited"""
    count = get_rate_limit_count(key)
    return count >= limit

# Cache cleanup utilities
def cleanup_expired_cache():
    """Clean up expired cache entries (Redis handles this automatically)"""
    try:
        # Redis automatically removes expired keys
        # This function can be used for additional cleanup logic
        logger.info("Cache cleanup completed")
        return True
    except Exception as e:
        logger.error(f"Cache cleanup error: {str(e)}")
        return False

def clear_user_cache(user_id: int):
    """Clear all cache entries for a specific user"""
    try:
        pattern = f"*user:{user_id}*"
        deleted_count = cache_delete_pattern(pattern)
        logger.info(f"Cleared {deleted_count} cache entries for user {user_id}")
        return deleted_count
    except Exception as e:
        logger.error(f"Error clearing user cache: {str(e)}")
        return 0

def clear_issue_cache(issue_id: int):
    """Clear all cache entries for a specific issue"""
    try:
        pattern = f"*issue:{issue_id}*"
        deleted_count = cache_delete_pattern(pattern)
        logger.info(f"Cleared {deleted_count} cache entries for issue {issue_id}")
        return deleted_count
    except Exception as e:
        logger.error(f"Error clearing issue cache: {str(e)}")
        return 0 