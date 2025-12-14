"""
Redis-based distributed cache service for transcriptions and analysis.
Provides shared cache across all workers with TTL and compression.
"""

import hashlib
import logging
import pickle
import gzip
from typing import Optional, Any, Dict
from redis import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class CacheService:
    """
    Distributed cache service using Redis.
    Supports transcriptions, analysis, and generic caching with compression.
    """
    
    def __init__(self, redis_host: str = "redis", redis_port: int = 6379, redis_db: int = 1):
        """
        Initialize cache service.
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number (0 is used by RQ, we use 1)
        """
        try:
            self.redis = Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=False,  # We handle binary data
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis.ping()
            logger.info(f"✓ Cache service connected to Redis at {redis_host}:{redis_port} (db={redis_db})")
        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None
    
    def _get_file_hash(self, file_path: str) -> str:
        """
        Generate MD5 hash of file for cache key.
        Uses file metadata for speed (not content).
        
        Args:
            file_path: Path to file
            
        Returns:
            MD5 hash string
        """
        import os
        
        if not os.path.exists(file_path):
            return hashlib.md5(file_path.encode()).hexdigest()
        
        # Hash based on file path + size + mtime (fast)
        stat = os.stat(file_path)
        key_data = f"{file_path}_{stat.st_size}_{stat.st_mtime}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _compress(self, data: Any) -> bytes:
        """Compress data using gzip"""
        pickled = pickle.dumps(data)
        return gzip.compress(pickled, compresslevel=6)
    
    def _decompress(self, data: bytes) -> Any:
        """Decompress gzipped data"""
        decompressed = gzip.decompress(data)
        return pickle.loads(decompressed)
    
    # ========================================================================
    # TRANSCRIPTION CACHE
    # ========================================================================
    
    def get_transcription(self, file_path: str, options: Dict = None) -> Optional[Dict]:
        """
        Get cached transcription result.
        
        Args:
            file_path: Path to audio file
            options: Transcription options (model, language, etc.)
            
        Returns:
            Cached transcription dict or None
        """
        if not self.redis:
            return None
        
        try:
            # Generate cache key
            file_hash = self._get_file_hash(file_path)
            options_hash = hashlib.md5(str(sorted((options or {}).items())).encode()).hexdigest()[:8]
            cache_key = f"transcription:{file_hash}:{options_hash}"
            
            # Get from cache
            cached_data = self.redis.get(cache_key)
            if cached_data:
                result = self._decompress(cached_data)
                logger.info(f"✓ TRANSCRIPTION CACHE HIT: {file_path}")
                return result
            
            logger.debug(f"Transcription cache miss: {file_path}")
            return None
            
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None
    
    def set_transcription(self, file_path: str, result: Dict, options: Dict = None, ttl: int = 86400):
        """
        Cache transcription result.
        
        Args:
            file_path: Path to audio file
            result: Transcription result dict
            options: Transcription options used
            ttl: Time to live in seconds (default: 24h)
        """
        if not self.redis:
            return
        
        try:
            # Generate cache key
            file_hash = self._get_file_hash(file_path)
            options_hash = hashlib.md5(str(sorted((options or {}).items())).encode()).hexdigest()[:8]
            cache_key = f"transcription:{file_hash}:{options_hash}"
            
            # Compress and save
            compressed = self._compress(result)
            self.redis.setex(cache_key, ttl, compressed)
            
            # Log size savings
            original_size = len(pickle.dumps(result))
            compressed_size = len(compressed)
            ratio = (1 - compressed_size / original_size) * 100
            
            logger.info(
                f"✓ Cached transcription: {file_path} "
                f"(size: {original_size/1024:.1f}KB → {compressed_size/1024:.1f}KB, "
                f"saved {ratio:.1f}%)"
            )
            
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
    
    # ========================================================================
    # ANALYSIS CACHE
    # ========================================================================
    
    def get_analysis(self, text: str, rules: list = None) -> Optional[Dict]:
        """
        Get cached analysis result.
        
        Args:
            text: Text to analyze
            rules: Analysis rules used
            
        Returns:
            Cached analysis dict or None
        """
        if not self.redis:
            return None
        
        try:
            # Generate cache key from text + rules
            text_hash = hashlib.md5(text.encode()).hexdigest()
            rules_hash = hashlib.md5(str(sorted(rules or [])).encode()).hexdigest()[:8]
            cache_key = f"analysis:{text_hash}:{rules_hash}"
            
            # Get from cache
            cached_data = self.redis.get(cache_key)
            if cached_data:
                result = self._decompress(cached_data)
                logger.info(f"✓ ANALYSIS CACHE HIT (text length: {len(text)})")
                return result
            
            logger.debug(f"Analysis cache miss (text length: {len(text)})")
            return None
            
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None
    
    def set_analysis(self, text: str, result: Dict, rules: list = None, ttl: int = 604800):
        """
        Cache analysis result.
        
        Args:
            text: Text analyzed
            result: Analysis result dict
            rules: Analysis rules used
            ttl: Time to live in seconds (default: 7 days)
        """
        if not self.redis:
            return
        
        try:
            # Generate cache key
            text_hash = hashlib.md5(text.encode()).hexdigest()
            rules_hash = hashlib.md5(str(sorted(rules or [])).encode()).hexdigest()[:8]
            cache_key = f"analysis:{text_hash}:{rules_hash}"
            
            # Compress and save
            compressed = self._compress(result)
            self.redis.setex(cache_key, ttl, compressed)
            
            logger.info(f"✓ Cached analysis (text length: {len(text)}, size: {len(compressed)/1024:.1f}KB)")
            
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
    
    # ========================================================================
    # GENERIC CACHE
    # ========================================================================
    
    def get(self, key: str) -> Optional[Any]:
        """Generic cache get"""
        if not self.redis:
            return None
        
        try:
            cached_data = self.redis.get(f"generic:{key}")
            if cached_data:
                return self._decompress(cached_data)
            return None
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """Generic cache set"""
        if not self.redis:
            return
        
        try:
            compressed = self._compress(value)
            self.redis.setex(f"generic:{key}", ttl, compressed)
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
    
    # ========================================================================
    # CACHE MANAGEMENT
    # ========================================================================
    
    def clear_all(self):
        """Clear all cache entries"""
        if not self.redis:
            return
        
        try:
            # Get all keys in our database
            keys = self.redis.keys("*")
            if keys:
                self.redis.delete(*keys)
                logger.info(f"✓ Cleared {len(keys)} cache entries")
            else:
                logger.info("Cache already empty")
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
    
    def clear_transcriptions(self):
        """Clear only transcription cache"""
        if not self.redis:
            return
        
        try:
            keys = self.redis.keys("transcription:*")
            if keys:
                self.redis.delete(*keys)
                logger.info(f"✓ Cleared {len(keys)} transcription cache entries")
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
    
    def clear_analysis(self):
        """Clear only analysis cache"""
        if not self.redis:
            return
        
        try:
            keys = self.redis.keys("analysis:*")
            if keys:
                self.redis.delete(*keys)
                logger.info(f"✓ Cleared {len(keys)} analysis cache entries")
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        if not self.redis:
            return {"error": "Redis not connected"}
        
        try:
            # Count keys by type
            transcription_keys = len(self.redis.keys("transcription:*"))
            analysis_keys = len(self.redis.keys("analysis:*"))
            generic_keys = len(self.redis.keys("generic:*"))
            total_keys = transcription_keys + analysis_keys + generic_keys
            
            # Get memory usage
            info = self.redis.info("memory")
            used_memory_mb = info.get("used_memory", 0) / 1024 / 1024
            
            return {
                "total_keys": total_keys,
                "transcription_keys": transcription_keys,
                "analysis_keys": analysis_keys,
                "generic_keys": generic_keys,
                "used_memory_mb": round(used_memory_mb, 2),
                "connected": True
            }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {"error": str(e), "connected": False}


# Global cache instance
cache_service = CacheService()
