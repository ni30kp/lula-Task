from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer
import uvicorn
import logging
from datetime import datetime
from typing import List, Optional
import json

from app.core.config import settings
from app.core.database import get_db
from app.core.auth import get_current_user, authenticate_user, create_access_token
from app.models.schemas import (
    IssueCreate, IssueResponse, IssueAnalysis, 
    RecommendationRequest, RecommendationResponse,
    ConversationSummary, CustomerHistory, UserLogin, Token
)
from app.services.issue_service import IssueService
from app.services.ai_service import AIService
from app.services.recommendation_service import RecommendationService
from sqlalchemy.orm import Session
from fastapi import Body

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Support Copilot API",
    description="AI-powered support issue lifecycle management system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Security
security = HTTPBearer()

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancer"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

# Issue Analysis Endpoint
@app.post("/api/v1/issues/analyze", response_model=IssueAnalysis)
async def analyze_issue(
    issue: IssueCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Analyze a new support issue and provide insights.
    
    This endpoint:
    1. Retrieves customer history
    2. Searches for similar issues
    3. Assesses severity
    4. Flags critical issues
    5. Returns analysis within 15 seconds
    """
    try:
        issue_service = IssueService(db)
        ai_service = AIService()
        
        # Start timing for performance monitoring
        start_time = datetime.utcnow()
        
        # Core analysis (synchronous for <15s response)
        analysis = await issue_service.analyze_new_issue(issue, ai_service)
        
        # Background tasks for heavy processing
        background_tasks.add_task(
            issue_service.process_async_analysis, 
            issue.id, 
            analysis
        )
        
        # Log performance metrics
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Issue analysis completed in {processing_time}s")
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error analyzing issue: {str(e)}")
        raise HTTPException(status_code=500, detail="Issue analysis failed")

# Recommendation Generation Endpoint
@app.post("/api/v1/issues/{issue_id}/recommend", response_model=RecommendationResponse)
async def get_recommendations(
    issue_id: int,
    request: RecommendationRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Generate recommended message templates for support executives.
    
    Considers:
    - Issue description and context
    - Customer history
    - Similar past issues and resolutions
    - Severity and criticality tags
    """
    try:
        recommendation_service = RecommendationService(db)
        ai_service = AIService()
        
        recommendations = await recommendation_service.generate_recommendations(
            issue_id, 
            request.context, 
            ai_service
        )
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail="Recommendation generation failed")

# Conversation Summarization Endpoint
@app.post("/api/v1/conversations/{conversation_id}/summarize", response_model=ConversationSummary)
async def summarize_conversation(
    conversation_id: int,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Generate a concise summary of the entire conversation.
    
    Used for:
    - Historical review
    - Knowledge base updates
    - Training data for ML models
    """
    try:
        ai_service = AIService()
        
        # Process summarization in background
        background_tasks.add_task(
            ai_service.summarize_conversation_async,
            conversation_id,
            db
        )
        
        return {"message": "Summarization started", "conversation_id": conversation_id}
        
    except Exception as e:
        logger.error(f"Error starting summarization: {str(e)}")
        raise HTTPException(status_code=500, detail="Summarization failed")

# Customer History Endpoint
@app.get("/api/v1/customers/{customer_id}/history", response_model=CustomerHistory)
async def get_customer_history(
    customer_id: int,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Retrieve comprehensive customer history including:
    - Total number of issues
    - Issue patterns and trends
    - Resolution times
    - Critical issues
    """
    try:
        issue_service = IssueService(db)
        history = await issue_service.get_customer_history(customer_id)
        return history
        
    except Exception as e:
        logger.error(f"Error retrieving customer history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve customer history")

# Issue Status Update Endpoint
@app.put("/api/v1/issues/{issue_id}/status")
async def update_issue_status(
    issue_id: int,
    status: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update issue status and trigger relevant notifications"""
    try:
        issue_service = IssueService(db)
        await issue_service.update_issue_status(issue_id, status)
        return {"message": "Status updated successfully"}
        
    except Exception as e:
        logger.error(f"Error updating issue status: {str(e)}")
        raise HTTPException(status_code=500, detail="Status update failed")

# Critical Issues Alert Endpoint
@app.get("/api/v1/issues/critical")
async def get_critical_issues(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Get all critical issues that require immediate attention.
    
    Criteria:
    - High severity issues
    - Issues unattended for >24 hours
    - Issues from VIP customers
    """
    try:
        issue_service = IssueService(db)
        critical_issues = await issue_service.get_critical_issues()
        return {"critical_issues": critical_issues}
        
    except Exception as e:
        logger.error(f"Error retrieving critical issues: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve critical issues")

# Performance Metrics Endpoint
@app.get("/api/v1/metrics")
async def get_performance_metrics(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    try:
        metrics = {
            "api_response_time_avg": 0.8,
            "active_issues": 150,
            "resolved_today": 45,
            "critical_issues": 3,
            "system_health": "healthy"
        }
        return metrics
    except Exception as e:
        logger.error(f"Error retrieving metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")

@app.post("/api/v1/auth/login", response_model=Token)
async def login(
    payload: UserLogin = Body(...),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    access_token = create_access_token({"sub": user.id})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 60 * 30  # 30 minutes
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 