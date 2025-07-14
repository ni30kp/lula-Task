from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "Support Copilot"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Support Copilot API"
    
    # Security Settings
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS Settings
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "https://support-portal.example.com"
    ]
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # Database Settings
    DATABASE_URL: str = "mysql+pymysql://user:password@localhost/support_copilot"
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "support_user"
    MYSQL_PASSWORD: str = "support_password"
    MYSQL_DATABASE: str = "support_copilot"
    
    # Redis Settings
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # RabbitMQ Settings
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    
    # AI/ML Settings
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    HUGGINGFACE_API_KEY: str = ""
    
    # AWS Settings
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: str = "support-copilot-logs"
    
    # Monitoring Settings
    CLOUDWATCH_LOG_GROUP: str = "/aws/ecs/support-copilot"
    METRICS_NAMESPACE: str = "SupportCopilot"
    
    # Performance Settings
    MAX_RESPONSE_TIME: int = 15  # seconds
    CACHE_TTL: int = 300  # 5 minutes
    RATE_LIMIT_PER_MINUTE: int = 100
    
    # Feature Flags
    ENABLE_AI_ANALYSIS: bool = True
    ENABLE_RECOMMENDATIONS: bool = True
    ENABLE_SUMMARIZATION: bool = True
    ENABLE_CRITICAL_ALERTS: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()

# Database URL construction
def get_database_url() -> str:
    """Construct database URL from individual components"""
    return f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"

# Redis URL construction
def get_redis_url() -> str:
    """Construct Redis URL from individual components"""
    return f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"

# RabbitMQ URL construction
def get_rabbitmq_url() -> str:
    """Construct RabbitMQ URL from individual components"""
    return f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/" 