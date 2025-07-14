from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# Enums
class SeverityLevel(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"

class IssueStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

class SenderType(str, Enum):
    CUSTOMER = "CUSTOMER"
    SUPPORT = "SUPPORT"

# Base Models
class BaseResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Issue Models
class IssueCreate(BaseModel):
    customer_id: int = Field(..., description="Customer ID")
    title: str = Field(..., min_length=1, max_length=500, description="Issue title")
    description: str = Field(..., min_length=10, description="Issue description")
    category: Optional[str] = Field(None, description="Issue category")
    priority: Optional[str] = Field(None, description="Customer priority level")
    
    @validator('title')
    def validate_title(cls, v):
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()
    
    @validator('description')
    def validate_description(cls, v):
        if len(v.strip()) < 10:
            raise ValueError('Description must be at least 10 characters')
        return v.strip()

class IssueResponse(BaseModel):
    id: int
    customer_id: int
    title: str
    description: str
    severity: SeverityLevel
    status: IssueStatus
    category: Optional[str]
    priority: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class IssueAnalysis(BaseModel):
    issue_id: int
    severity_assessment: SeverityLevel
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    customer_history: Dict[str, Any]
    similar_issues: List[Dict[str, Any]]
    critical_flags: List[str]
    recommended_actions: List[str]
    processing_time: float
    
    class Config:
        json_schema_extra = {
            "example": {
                "issue_id": 12345,
                "severity_assessment": "HIGH",
                "confidence_score": 0.85,
                "customer_history": {
                    "total_issues": 15,
                    "avg_resolution_time": "2.5 hours",
                    "critical_issues": 2
                },
                "similar_issues": [
                    {
                        "issue_id": 12340,
                        "similarity_score": 0.92,
                        "resolution": "Updated firewall settings"
                    }
                ],
                "critical_flags": [
                    "VIP customer",
                    "Similar issue unresolved for 48h"
                ],
                "recommended_actions": [
                    "Assign to senior support engineer",
                    "Escalate to technical team"
                ],
                "processing_time": 0.8
            }
        }

# Recommendation Models
class RecommendationRequest(BaseModel):
    context: str = Field(..., description="Current conversation context")
    message_type: str = Field(..., description="Type of message (greeting, solution, follow-up)")
    tone: Optional[str] = Field("professional", description="Desired tone of message")
    
    @validator('context')
    def validate_context(cls, v):
        if not v.strip():
            raise ValueError('Context cannot be empty')
        return v.strip()

class RecommendationResponse(BaseModel):
    issue_id: int
    recommendations: List[Dict[str, Any]]
    confidence_scores: List[float]
    reasoning: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "issue_id": 12345,
                "recommendations": [
                    {
                        "template": "Thank you for reaching out. I understand you're experiencing [issue]. Let me help you resolve this quickly.",
                        "type": "greeting",
                        "tone": "professional"
                    },
                    {
                        "template": "Based on similar cases, this issue can be resolved by [solution]. Would you like me to guide you through the steps?",
                        "type": "solution",
                        "tone": "helpful"
                    }
                ],
                "confidence_scores": [0.92, 0.88],
                "reasoning": "High confidence due to similar resolved issues in database"
            }
        }

# Conversation Models
class ConversationMessage(BaseModel):
    id: int
    issue_id: int
    message: str
    sender_type: SenderType
    created_at: datetime
    
    class Config:
        from_attributes = True

class ConversationSummary(BaseModel):
    conversation_id: int
    summary: str
    key_points: List[str]
    action_items: List[str]
    sentiment: str
    processing_status: str = "completed"
    
    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": 12345,
                "summary": "Customer reported login issues. Support provided step-by-step troubleshooting. Issue resolved by clearing browser cache.",
                "key_points": [
                    "Login authentication problem",
                    "Browser cache clearing required",
                    "Issue resolved successfully"
                ],
                "action_items": [
                    "Document solution for knowledge base",
                    "Follow up with customer in 24h"
                ],
                "sentiment": "positive",
                "processing_status": "completed"
            }
        }

# Customer Models
class CustomerHistory(BaseModel):
    customer_id: int
    total_issues: int
    resolved_issues: int
    avg_resolution_time: str
    critical_issues: int
    recent_issues: List[Dict[str, Any]]
    issue_patterns: List[str]
    customer_satisfaction: Optional[float]
    
    class Config:
        json_schema_extra = {
            "example": {
                "customer_id": 1001,
                "total_issues": 15,
                "resolved_issues": 14,
                "avg_resolution_time": "2.5 hours",
                "critical_issues": 2,
                "recent_issues": [
                    {
                        "issue_id": 12345,
                        "title": "Login authentication failed",
                        "status": "RESOLVED",
                        "resolution_time": "1.5 hours"
                    }
                ],
                "issue_patterns": [
                    "Authentication issues",
                    "Browser compatibility"
                ],
                "customer_satisfaction": 4.2
            }
        }

# Performance Models
class PerformanceMetrics(BaseModel):
    api_response_time_avg: float
    active_issues: int
    resolved_today: int
    critical_issues: int
    system_health: str
    uptime_percentage: float
    error_rate: float

# Error Models
class ErrorResponse(BaseModel):
    success: bool = False
    error_code: str
    error_message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Authentication Models
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class UserLogin(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    
    class Config:
        from_attributes = True

# Webhook Models
class WebhookPayload(BaseModel):
    event_type: str
    issue_id: int
    customer_id: int
    timestamp: datetime
    data: Dict[str, Any]

# Search Models
class SearchFilters(BaseModel):
    severity: Optional[SeverityLevel] = None
    status: Optional[IssueStatus] = None
    customer_id: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    category: Optional[str] = None

class SearchResponse(BaseModel):
    issues: List[IssueResponse]
    total_count: int
    page: int
    page_size: int
    filters_applied: SearchFilters 