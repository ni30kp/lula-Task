from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Enum, ForeignKey, DECIMAL, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import logging
from datetime import datetime
from typing import Generator
import redis
import pymysql

from app.core.config import settings, get_database_url, get_redis_url

# Configure logging
logger = logging.getLogger(__name__)

# Database engine configuration
engine = create_engine(
    get_database_url(),
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Redis connection
redis_client = redis.from_url(get_redis_url(), decode_responses=True)

def get_db() -> Generator[Session, None, None]:
    """
    Database dependency for FastAPI.
    Provides a database session and ensures proper cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def get_redis() -> redis.Redis:
    """
    Redis connection dependency.
    """
    return redis_client

# Database Models
class Customer(Base):
    """Customer model for storing customer information"""
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    company = Column(String(255))
    vip_status = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    total_issues = Column(Integer, default=0)
    avg_resolution_time = Column(DECIMAL(10, 2))  # in hours

class Issue(Base):
    """Issue model for storing support issues"""
    __tablename__ = "issues"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100))
    severity = Column(Enum("LOW", "NORMAL", "HIGH", name="severity_enum"), default="NORMAL")
    status = Column(Enum("OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED", name="status_enum"), default="OPEN")
    priority = Column(String(50))
    assigned_to = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime)
    resolution_time = Column(DECIMAL(10, 2))  # in hours
    ai_confidence_score = Column(DECIMAL(3, 2))  # 0.00 to 1.00

class Conversation(Base):
    """Conversation model for storing issue conversations"""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    sender_type = Column(Enum("CUSTOMER", "SUPPORT", name="sender_enum"), nullable=False)
    sender_id = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    sentiment_score = Column(DECIMAL(3, 2))  # -1.0 to 1.0

class Recommendation(Base):
    """Recommendation model for storing AI-generated recommendations"""
    __tablename__ = "recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False, index=True)
    template_text = Column(Text, nullable=False)
    message_type = Column(String(50))  # greeting, solution, follow-up
    tone = Column(String(50))  # professional, friendly, urgent
    confidence_score = Column(DECIMAL(3, 2), nullable=False)
    reasoning = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    used_count = Column(Integer, default=0)

class ConversationSummary(Base):
    """Conversation summary model for storing AI-generated summaries"""
    __tablename__ = "conversation_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    key_points = Column(Text)  # JSON array of key points
    action_items = Column(Text)  # JSON array of action items
    sentiment = Column(String(50))
    processing_status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

class SimilarIssue(Base):
    """Similar issue model for storing issue similarity relationships"""
    __tablename__ = "similar_issues"
    
    id = Column(Integer, primary_key=True, index=True)
    source_issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False, index=True)
    similar_issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False, index=True)
    similarity_score = Column(DECIMAL(3, 2), nullable=False)
    similarity_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    """User model for support executives"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="support_executive")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)

class AuditLog(Base):
    """Audit log model for tracking system activities"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50))  # issue, customer, conversation
    resource_id = Column(Integer)
    details = Column(Text)  # JSON object with action details
    ip_address = Column(String(45))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

# Database initialization
def init_db():
    """Initialize database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        raise

def check_db_connection():
    """Check database connectivity"""
    try:
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False

def check_redis_connection():
    """Check Redis connectivity"""
    try:
        redis_client.ping()
        logger.info("Redis connection successful")
        return True
    except Exception as e:
        logger.error(f"Redis connection failed: {str(e)}")
        return False

# Database utilities
def get_issue_by_id(db: Session, issue_id: int):
    """Get issue by ID with customer information"""
    return db.query(Issue).filter(Issue.id == issue_id).first()

def get_customer_by_id(db: Session, customer_id: int):
    """Get customer by ID with issue count"""
    return db.query(Customer).filter(Customer.id == customer_id).first()

def get_conversations_by_issue_id(db: Session, issue_id: int):
    """Get all conversations for an issue"""
    return db.query(Conversation).filter(Conversation.issue_id == issue_id).order_by(Conversation.created_at).all()

def get_recommendations_by_issue_id(db: Session, issue_id: int):
    """Get all recommendations for an issue"""
    return db.query(Recommendation).filter(Recommendation.issue_id == issue_id).order_by(Recommendation.confidence_score.desc()).all()

# Cache utilities
def cache_set(key: str, value: str, ttl: int = 300):
    """Set cache value with TTL"""
    try:
        redis_client.setex(key, ttl, value)
    except Exception as e:
        logger.error(f"Cache set error: {str(e)}")

def cache_get(key: str) -> str:
    """Get cache value"""
    try:
        return redis_client.get(key)
    except Exception as e:
        logger.error(f"Cache get error: {str(e)}")
        return None

def cache_delete(key: str):
    """Delete cache value"""
    try:
        redis_client.delete(key)
    except Exception as e:
        logger.error(f"Cache delete error: {str(e)}") 