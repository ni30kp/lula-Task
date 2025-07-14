import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.core.database import Issue, Customer, Conversation, Recommendation, ConversationSummary, SimilarIssue
from app.models.schemas import IssueCreate, IssueAnalysis, CustomerHistory, SeverityLevel, IssueStatus
from app.services.ai_service import AIService
from app.core.cache import cache_set, cache_get, cache_delete

logger = logging.getLogger(__name__)

class IssueService:
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIService()

    async def analyze_new_issue(self, issue_data: IssueCreate, ai_service: AIService) -> IssueAnalysis:
        try:
            start_time = datetime.utcnow()
            customer_history = await self._get_customer_history(issue_data.customer_id)
            issue_text = f"{issue_data.title} {issue_data.description}"
            severity_analysis = await ai_service.assess_severity(issue_text, customer_history)
            similar_issues = await ai_service.find_similar_issues(issue_text, self.db)
            critical_patterns = await ai_service.detect_critical_patterns(issue_data.customer_id, self.db)
            recommended_actions = self._generate_recommended_actions(
                severity_analysis, customer_history, similar_issues, critical_patterns
            )
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            analysis = IssueAnalysis(
                issue_id=issue_data.customer_id,
                severity_assessment=severity_analysis["severity"],
                confidence_score=severity_analysis["confidence_score"],
                customer_history=customer_history,
                similar_issues=similar_issues,
                critical_flags=critical_patterns,
                recommended_actions=recommended_actions,
                processing_time=processing_time
            )
            cache_key = f"issue_analysis:{issue_data.customer_id}:{datetime.utcnow().timestamp()}"
            cache_set(cache_key, json.dumps(analysis.dict()), ttl=3600)
            logger.info(f"Issue analysis completed in {processing_time}s")
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing new issue: {str(e)}")
            raise

    async def _get_customer_history(self, customer_id: int) -> Dict[str, Any]:
        """
        Get comprehensive customer history with caching.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            Customer history data
        """
        try:
            # Check cache first
            cache_key = f"customer_history:{customer_id}"
            cached_data = cache_get(cache_key)
            
            if cached_data:
                return json.loads(cached_data)
            
            # Get customer data
            customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
            if not customer:
                return self._get_default_customer_history()
            
            # Get recent issues
            recent_issues = self.db.query(Issue).filter(
                Issue.customer_id == customer_id,
                Issue.created_at >= datetime.utcnow() - timedelta(days=30)
            ).all()
            
            # Calculate metrics
            total_issues = len(recent_issues)
            resolved_issues = len([i for i in recent_issues if i.status in ["RESOLVED", "CLOSED"]])
            critical_issues = len([i for i in recent_issues if i.severity == "HIGH"])
            
            # Calculate average resolution time
            resolved_with_time = [i for i in recent_issues if i.resolution_time and i.status in ["RESOLVED", "CLOSED"]]
            avg_resolution_time = sum(i.resolution_time for i in resolved_with_time) / len(resolved_with_time) if resolved_with_time else 0
            
            # Get recent issue details
            recent_issue_details = []
            for issue in recent_issues[-5:]:  # Last 5 issues
                recent_issue_details.append({
                    "issue_id": issue.id,
                    "title": issue.title,
                    "status": issue.status,
                    "severity": issue.severity,
                    "resolution_time": float(issue.resolution_time) if issue.resolution_time else None,
                    "created_at": issue.created_at.isoformat()
                })
            
            # Detect issue patterns
            issue_patterns = self._detect_issue_patterns(recent_issues)
            
            history = {
                "total_issues": total_issues,
                "resolved_issues": resolved_issues,
                "critical_issues": critical_issues,
                "avg_resolution_time": f"{avg_resolution_time:.1f} hours",
                "vip_status": customer.vip_status,
                "recent_issues": recent_issue_details,
                "issue_patterns": issue_patterns,
                "customer_satisfaction": self._calculate_satisfaction_score(customer_id)
            }
            
            # Cache the result
            cache_set(cache_key, json.dumps(history), ttl=1800)  # 30 minutes
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting customer history: {str(e)}")
            return self._get_default_customer_history()
    
    def _get_default_customer_history(self) -> Dict[str, Any]:
        """Return default customer history for new customers"""
        return {
            "total_issues": 0,
            "resolved_issues": 0,
            "critical_issues": 0,
            "avg_resolution_time": "0.0 hours",
            "vip_status": False,
            "recent_issues": [],
            "issue_patterns": [],
            "customer_satisfaction": None
        }
    
    def _detect_issue_patterns(self, issues: List[Issue]) -> List[str]:
        """Detect patterns in customer issues"""
        patterns = []
        
        if not issues:
            return patterns
        
        # Check for repeated categories
        categories = [issue.category for issue in issues if issue.category]
        category_counts = {}
        for category in categories:
            category_counts[category] = category_counts.get(category, 0) + 1
        
        repeated_categories = [cat for cat, count in category_counts.items() if count > 1]
        if repeated_categories:
            patterns.append(f"Repeated categories: {', '.join(repeated_categories)}")
        
        # Check for severity patterns
        high_severity_count = len([i for i in issues if i.severity == "HIGH"])
        if high_severity_count > 2:
            patterns.append("Multiple high-severity issues")
        
        # Check for timing patterns
        if len(issues) >= 3:
            # Check if issues are clustered in time
            sorted_issues = sorted(issues, key=lambda x: x.created_at)
            for i in range(len(sorted_issues) - 2):
                time_diff1 = (sorted_issues[i+1].created_at - sorted_issues[i].created_at).total_seconds() / 3600
                time_diff2 = (sorted_issues[i+2].created_at - sorted_issues[i+1].created_at).total_seconds() / 3600
                if time_diff1 < 24 and time_diff2 < 24:  # Issues within 24 hours
                    patterns.append("Issues clustered in time")
                    break
        
        return patterns
    
    def _calculate_satisfaction_score(self, customer_id: int) -> Optional[float]:
        # Placeholder for real satisfaction score logic
        return None
    
    def _generate_recommended_actions(self, severity_analysis: Dict[str, Any], 
                                    customer_history: Dict[str, Any], 
                                    similar_issues: List[Dict[str, Any]], 
                                    critical_patterns: List[str]) -> List[str]:
        """Generate recommended actions based on analysis"""
        actions = []
        
        # Severity-based actions
        if severity_analysis["severity"] == SeverityLevel.HIGH:
            actions.append("Assign to senior support engineer")
            actions.append("Escalate to technical team")
            if customer_history.get("vip_status", False):
                actions.append("Notify account manager")
        
        # Pattern-based actions
        if "Multiple issues in short time period" in critical_patterns:
            actions.append("Schedule customer success review")
        
        if "Repeated categories" in critical_patterns:
            actions.append("Provide proactive training on affected areas")
        
        # Similar issue-based actions
        if similar_issues:
            avg_resolution_time = sum(i.get("resolution_time", 0) for i in similar_issues if i.get("resolution_time"))
            if avg_resolution_time > 4:  # More than 4 hours average
                actions.append("Prepare for extended resolution time")
        
        # Customer history-based actions
        if customer_history.get("total_issues", 0) > 10:
            actions.append("Consider VIP status upgrade")
        
        if not actions:
            actions.append("Standard support process")
        
        return actions
    
    async def get_customer_history(self, customer_id: int) -> CustomerHistory:
        """
        Get comprehensive customer history for API response.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            Customer history response
        """
        try:
            # Get cached history
            history_data = await self._get_customer_history(customer_id)
            
            # Convert to response format
            return CustomerHistory(
                customer_id=customer_id,
                total_issues=history_data["total_issues"],
                resolved_issues=history_data["resolved_issues"],
                avg_resolution_time=history_data["avg_resolution_time"],
                critical_issues=history_data["critical_issues"],
                recent_issues=history_data["recent_issues"],
                issue_patterns=history_data["issue_patterns"],
                customer_satisfaction=history_data["customer_satisfaction"]
            )
            
        except Exception as e:
            logger.error(f"Error getting customer history: {str(e)}")
            raise
    
    async def get_critical_issues(self) -> List[Dict[str, Any]]:
        """
        Get all critical issues that require immediate attention.
        
        Returns:
            List of critical issues
        """
        try:
            # Get issues that meet critical criteria
            critical_issues = self.db.query(Issue).filter(
                and_(
                    or_(
                        Issue.severity == "HIGH",
                        and_(
                            Issue.status.in_(["OPEN", "IN_PROGRESS"]),
                            Issue.created_at <= datetime.utcnow() - timedelta(hours=24)
                        )
                    ),
                    Issue.status.in_(["OPEN", "IN_PROGRESS"])
                )
            ).all()
            
            critical_issue_list = []
            for issue in critical_issues:
                # Get customer info
                customer = self.db.query(Customer).filter(Customer.id == issue.customer_id).first()
                
                critical_issue_list.append({
                    "issue_id": issue.id,
                    "title": issue.title,
                    "severity": issue.severity,
                    "status": issue.status,
                    "created_at": issue.created_at.isoformat(),
                    "customer_id": issue.customer_id,
                    "customer_name": customer.name if customer else "Unknown",
                    "vip_status": customer.vip_status if customer else False,
                    "time_since_creation": (datetime.utcnow() - issue.created_at).total_seconds() / 3600
                })
            
            # Sort by priority (VIP customers first, then by creation time)
            critical_issue_list.sort(key=lambda x: (not x["vip_status"], x["time_since_creation"]), reverse=True)
            
            return critical_issue_list
            
        except Exception as e:
            logger.error(f"Error getting critical issues: {str(e)}")
            return []
    
    async def update_issue_status(self, issue_id: int, new_status: str) -> bool:
        """
        Update issue status and trigger relevant notifications.
        
        Args:
            issue_id: Issue ID
            new_status: New status
            
        Returns:
            Success status
        """
        try:
            issue = self.db.query(Issue).filter(Issue.id == issue_id).first()
            if not issue:
                return False
            
            old_status = issue.status
            issue.status = new_status
            issue.updated_at = datetime.utcnow()
            
            # Calculate resolution time if resolving
            if new_status in ["RESOLVED", "CLOSED"] and old_status not in ["RESOLVED", "CLOSED"]:
                issue.resolved_at = datetime.utcnow()
                if issue.created_at:
                    resolution_time = (issue.resolved_at - issue.created_at).total_seconds() / 3600
                    issue.resolution_time = resolution_time
            
            self.db.commit()
            
            # Clear related caches
            cache_delete(f"customer_history:{issue.customer_id}")
            cache_delete(f"issue_analysis:{issue_id}")
            
            # Log the status change
            logger.info(f"Issue {issue_id} status changed from {old_status} to {new_status}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating issue status: {str(e)}")
            self.db.rollback()
            return False
    
    async def process_async_analysis(self, issue_id: int, analysis: IssueAnalysis):
        """
        Process additional analysis asynchronously.
        
        Args:
            issue_id: Issue ID
            analysis: Initial analysis results
        """
        try:
            # Store analysis results in database
            # This would typically involve storing the analysis results
            # and triggering additional background processes
            
            logger.info(f"Async analysis completed for issue {issue_id}")
            
        except Exception as e:
            logger.error(f"Error in async analysis: {str(e)}")
    
    def get_issue_statistics(self) -> Dict[str, Any]:
        """
        Get system-wide issue statistics.
        
        Returns:
            Issue statistics
        """
        try:
            # Get total issues
            total_issues = self.db.query(Issue).count()
            
            # Get issues by status
            open_issues = self.db.query(Issue).filter(Issue.status == "OPEN").count()
            in_progress_issues = self.db.query(Issue).filter(Issue.status == "IN_PROGRESS").count()
            resolved_issues = self.db.query(Issue).filter(Issue.status == "RESOLVED").count()
            closed_issues = self.db.query(Issue).filter(Issue.status == "CLOSED").count()
            
            # Get issues by severity
            high_severity = self.db.query(Issue).filter(Issue.severity == "HIGH").count()
            normal_severity = self.db.query(Issue).filter(Issue.severity == "NORMAL").count()
            low_severity = self.db.query(Issue).filter(Issue.severity == "LOW").count()
            
            # Get average resolution time
            resolved_with_time = self.db.query(Issue).filter(
                and_(
                    Issue.status.in_(["RESOLVED", "CLOSED"]),
                    Issue.resolution_time.isnot(None)
                )
            ).all()
            
            avg_resolution_time = 0
            if resolved_with_time:
                avg_resolution_time = sum(i.resolution_time for i in resolved_with_time) / len(resolved_with_time)
            
            return {
                "total_issues": total_issues,
                "open_issues": open_issues,
                "in_progress_issues": in_progress_issues,
                "resolved_issues": resolved_issues,
                "closed_issues": closed_issues,
                "high_severity_issues": high_severity,
                "normal_severity_issues": normal_severity,
                "low_severity_issues": low_severity,
                "avg_resolution_time_hours": round(avg_resolution_time, 2),
                "resolution_rate": round((resolved_issues + closed_issues) / total_issues * 100, 2) if total_issues > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting issue statistics: {str(e)}")
            return {}
    
    def search_issues(self, filters: Dict[str, Any], page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        Search issues with filters and pagination.
        
        Args:
            filters: Search filters
            page: Page number
            page_size: Items per page
            
        Returns:
            Search results with pagination
        """
        try:
            query = self.db.query(Issue)
            
            # Apply filters
            if filters.get("customer_id"):
                query = query.filter(Issue.customer_id == filters["customer_id"])
            
            if filters.get("severity"):
                query = query.filter(Issue.severity == filters["severity"])
            
            if filters.get("status"):
                query = query.filter(Issue.status == filters["status"])
            
            if filters.get("category"):
                query = query.filter(Issue.category == filters["category"])
            
            if filters.get("date_from"):
                query = query.filter(Issue.created_at >= filters["date_from"])
            
            if filters.get("date_to"):
                query = query.filter(Issue.created_at <= filters["date_to"])
            
            # Get total count
            total_count = query.count()
            
            # Apply pagination
            offset = (page - 1) * page_size
            issues = query.offset(offset).limit(page_size).all()
            
            return {
                "issues": issues,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }
            
        except Exception as e:
            logger.error(f"Error searching issues: {str(e)}")
            return {"issues": [], "total_count": 0, "page": page, "page_size": page_size, "total_pages": 0} 