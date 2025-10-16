"""
Intelligent caching system for API responses
Reduces API calls and improves performance
"""

import json
import hashlib
import time
from pathlib import Path
from typing import Any, Optional, Callable
from datetime import datetime, timedelta
from functools import wraps
import pickle


class CacheManager:
    """
    Simple file-based cache with TTL (Time To Live)
    """
    
    def __init__(self, cache_dir: Path, ttl_hours: int = 24):
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_hours * 3600
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self.hits = 0
        self.misses = 0
    
    def _get_cache_key(self, key: str) -> str:
        """Generate cache filename from key"""
        # Use hash to avoid filesystem issues with special chars
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return f"{hash_key}.cache"
    
    def _get_cache_path(self, key: str) -> Path:
        """Get full path to cache file"""
        return self.cache_dir / self._get_cache_key(key)
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve cached value if exists and not expired
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            self.misses += 1
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                cache_data = pickle.load(f)
            
            # Check expiration
            cached_time = cache_data.get('timestamp', 0)
            if time.time() - cached_time > self.ttl_seconds:
                # Expired
                cache_path.unlink()  # Delete expired cache
                self.misses += 1
                return None
            
            # Valid cache hit
            self.hits += 1
            return cache_data.get('value')
            
        except Exception as e:
            # Corrupted cache, delete it
            cache_path.unlink(missing_ok=True)
            self.misses += 1
            return None
    
    def set(self, key: str, value: Any) -> None:
        """
        Store value in cache
        
        Args:
            key: Cache key
            value: Value to cache (must be picklable)
        """
        cache_path = self._get_cache_path(key)
        
        cache_data = {
            'timestamp': time.time(),
            'value': value,
            'key': key  # Store original key for debugging
        }
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
        except Exception as e:
            # If caching fails, just log and continue
            print(f"Cache write failed: {e}")
    
    def clear(self) -> int:
        """
        Clear all cache files
        
        Returns:
            Number of files deleted
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink()
            count += 1
        return count
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        # Count cache files
        cache_files = list(self.cache_dir.glob("*.cache"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.1f}%",
            'cached_items': len(cache_files),
            'total_size_mb': f"{total_size / 1024 / 1024:.2f}"
        }


# Global cache instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get or create global cache manager"""
    global _cache_manager
    
    if _cache_manager is None:
        from config import APIConfig
        _cache_manager = CacheManager(
            cache_dir=APIConfig.CACHE_DIR,
            ttl_hours=APIConfig.CACHE_TTL_HOURS
        )
    
    return _cache_manager


def cached(key_prefix: str = "", ttl_hours: Optional[int] = None):
    """
    Decorator to cache function results
    
    Args:
        key_prefix: Prefix for cache key
        ttl_hours: Override default TTL
        
    Example:
        @cached(key_prefix="pubmed_search")
        def search_pubmed(query: str):
            # expensive API call
            return results
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            from config import APIConfig
            
            # Skip caching if disabled
            if not APIConfig.ENABLE_CACHE:
                return func(*args, **kwargs)
            
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cache = get_cache_manager()
            cached_result = cache.get(cache_key)
            
            if cached_result is not None:
                return cached_result
            
            # Cache miss - execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            cache.set(cache_key, result)
            
            return result
        
        return wrapper
    return decorator


def clear_all_caches():
    """Clear all cached data"""
    cache = get_cache_manager()
    deleted = cache.clear()
    print(f"✅ Cleared {deleted} cache files")
    return deleted


def get_cache_stats() -> dict:
    """Get cache statistics"""
    cache = get_cache_manager()
    return cache.get_stats()


# Example usage
if __name__ == "__main__":
    # Test caching
    cache = get_cache_manager()
    
    # Set some values
    cache.set("test_key", {"data": "example"})
    cache.set("another_key", [1, 2, 3, 4, 5])
    
    # Retrieve
    value1 = cache.get("test_key")
    value2 = cache.get("another_key")
    value3 = cache.get("nonexistent")
    
    print(f"Retrieved: {value1}")
    print(f"Retrieved: {value2}")
    print(f"Not found: {value3}")
    
    # Stats
    stats = cache.get_stats()
    print(f"\nCache stats: {stats}")