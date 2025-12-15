"""
Secure Secrets Management
Reads secrets from Docker secrets or environment variables
"""
import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def read_secret(name: str, default: Optional[str] = None) -> str:
    """
    Read secret from Docker secrets (/run/secrets/) or environment variable.
    
    Priority:
    1. Docker secret file (/run/secrets/{name})
    2. Environment variable ({NAME})
    3. Default value
    
    Args:
        name: Secret name (e.g., 'db_password')
        default: Default value if secret not found
        
    Returns:
        Secret value as string
        
    Raises:
        ValueError: If secret not found and no default provided
    """
    # Try Docker secret first
    secret_path = Path(f"/run/secrets/{name}")
    if secret_path.exists():
        try:
            value = secret_path.read_text().strip()
            logger.info(f"✅ Loaded secret '{name}' from Docker secrets")
            return value
        except Exception as e:
            logger.warning(f"⚠️ Failed to read secret '{name}' from {secret_path}: {e}")
    
    # Fallback to environment variable
    env_name = name.upper()
    value = os.getenv(env_name)
    if value:
        logger.info(f"✅ Loaded secret '{name}' from environment variable")
        return value
    
    # Use default if provided
    if default is not None:
        logger.warning(f"⚠️ Using default value for secret '{name}'")
        return default
    
    # No secret found
    raise ValueError(
        f"❌ Secret '{name}' not found in Docker secrets or environment variables. "
        f"Please create /run/secrets/{name} or set {env_name} environment variable."
    )


def get_database_url() -> str:
    """Build database URL with secure password handling"""
    db_user = os.getenv("DB_USER", "careca")
    db_name = os.getenv("DB_NAME", "carecadb")
    db_host = os.getenv("DB_HOST", "db")
    db_port = os.getenv("DB_PORT", "5432")
    
    try:
        db_password = read_secret("db_password")
    except ValueError:
        logger.error("❌ Database password not configured!")
        raise
    
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def get_redis_url() -> str:
    """Build Redis URL with secure password handling"""
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = os.getenv("REDIS_PORT", "6379")
    redis_db = os.getenv("REDIS_DB", "0")
    
    try:
        redis_password = read_secret("redis_password")
    except ValueError:
        logger.error("❌ Redis password not configured!")
        raise
    
    return f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"


# Export commonly used secrets
def get_secret_key() -> str:
    """Get application secret key"""
    return read_secret("secret_key")


def get_admin_password() -> str:
    """Get admin password"""
    return read_secret("admin_password")
