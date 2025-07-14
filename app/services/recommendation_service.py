import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.core.database import Issue, Customer, Conversation, Recommendation
from app.models.schemas import RecommendationRequest, RecommendationResponse
from app.services.ai_service import AIService
from app.core.cache import cache_set, cache_get, cache_delete

logger = logging.getLogger(__name__)

class RecommendationService:
    """
    Recommendation Service for generating message templates and recommendations.
    
    Features:
    - Message template generation
    - Context-aware recommendations
    - Historical recommendation tracking
    - Performance optimization
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIService()
    
    async def generate_recommendations(self, issue_id: int, context: str, ai_service: AIService) -> RecommendationResponse:
        """
        Generate comprehensive recommendations for support executives.
        
        Args:
            issue_id: Issue ID
            context: Current conversation context
            ai_service: AI service instance
            
        Returns:
            Recommendation response with templates and reasoning
        """
        try:
            # Get issue details
            issue = self.db.query(Issue).filter(Issue.id == issue_id).first()
            if not issue:
                raise ValueError(f"Issue {issue_id} not found")
            
            # Get customer information
            customer = self.db.query(Customer).filter(Customer.id == issue.customer_id).first()
            
            # Get conversation history
            conversations = self.db.query(Conversation).filter(
                Conversation.issue_id == issue_id
            ).order_by(Conversation.created_at).all()
            
            # Generate different types of recommendations
            greeting_recommendations = await self._generate_greeting_recommendations(
                issue, customer, context, ai_service
            )
            
            solution_recommendations = await self._generate_solution_recommendations(
                issue, customer, conversations, ai_service
            )
            
            follow_up_recommendations = await self._generate_follow_up_recommendations(
                issue, customer, conversations, ai_service
            )
            
            # Combine all recommendations
            all_recommendations = []
            confidence_scores = []
            
            all_recommendations.extend(greeting_recommendations)
            all_recommendations.extend(solution_recommendations)
            all_recommendations.extend(follow_up_recommendations)
            
            confidence_scores.extend([rec["confidence_score"] for rec in greeting_recommendations])
            confidence_scores.extend([rec["confidence_score"] for rec in solution_recommendations])
            confidence_scores.extend([rec["confidence_score"] for rec in follow_up_recommendations])
            
            # Generate reasoning
            reasoning = self._generate_recommendation_reasoning(
                issue, customer, conversations, all_recommendations
            )
            
            # Store recommendations in database
            await self._store_recommendations(issue_id, all_recommendations)
            
            return RecommendationResponse(
                issue_id=issue_id,
                recommendations=all_recommendations,
                confidence_scores=confidence_scores,
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            raise
    
    async def _generate_greeting_recommendations(self, issue: Issue, customer: Customer, 
                                               context: str, ai_service: AIService) -> List[Dict[str, Any]]:
        """Generate greeting message recommendations"""
        try:
            # Prepare context for greeting
            greeting_context = f"Issue: {issue.title}. Customer: {customer.name}. {context}"
            
            recommendations = await ai_service.generate_recommendations(
                issue.id, greeting_context, "greeting", "professional"
            )
            
            # Add customer-specific customization
            for rec in recommendations:
                if customer.vip_status:
                    rec["template"] = rec["template"].replace(
                        "Thank you for reaching out",
                        "Thank you for reaching out to our VIP support team"
                    )
                    rec["confidence_score"] = min(0.95, rec["confidence_score"] + 0.1)
                
                # Add issue-specific context
                if issue.severity == "HIGH":
                    rec["template"] = rec["template"].replace(
                        "I'm here to help",
                        "I understand this is urgent and I'm here to help immediately"
                    )
            
            return recommendations[:2]  # Return top 2 greeting recommendations
            
        except Exception as e:
            logger.error(f"Error generating greeting recommendations: {str(e)}")
            return self._get_fallback_greeting_recommendations(issue, customer)
    
    async def _generate_solution_recommendations(self, issue: Issue, customer: Customer,
                                               conversations: List[Conversation], 
                                               ai_service: AIService) -> List[Dict[str, Any]]:
        """Generate solution message recommendations"""
        try:
            # Analyze conversation context
            conversation_text = " ".join([conv.message for conv in conversations])
            
            # Get similar issues for solution patterns
            similar_issues = await ai_service.find_similar_issues(
                f"{issue.title} {issue.description}", self.db
            )
            
            # Prepare solution context
            solution_context = f"Issue: {issue.title}. Description: {issue.description}. "
            solution_context += f"Conversation: {conversation_text[:500]}. "
            
            if similar_issues:
                solution_context += f"Similar resolved issues found: {len(similar_issues)}"
            
            recommendations = await ai_service.generate_recommendations(
                issue.id, solution_context, "solution", "helpful"
            )
            
            # Enhance with similar issue solutions
            if similar_issues:
                for rec in recommendations:
                    # Add solution hints from similar issues
                    best_similar = similar_issues[0]
                    if best_similar.get("resolution_time") and best_similar["resolution_time"] < 2:
                        rec["template"] += " Based on similar cases, this should be resolved quickly."
                    elif best_similar.get("resolution_time") and best_similar["resolution_time"] > 4:
                        rec["template"] += " This may require some time to resolve completely."
            
            return recommendations[:3]  # Return top 3 solution recommendations
            
        except Exception as e:
            logger.error(f"Error generating solution recommendations: {str(e)}")
            return self._get_fallback_solution_recommendations(issue)
    
    async def _generate_follow_up_recommendations(self, issue: Issue, customer: Customer,
                                                conversations: List[Conversation], 
                                                ai_service: AIService) -> List[Dict[str, Any]]:
        """Generate follow-up message recommendations"""
        try:
            # Analyze conversation sentiment
            conversation_text = " ".join([conv.message for conv in conversations])
            
            # Determine follow-up tone based on conversation
            tone = "professional"
            if any(word in conversation_text.lower() for word in ["thank", "great", "excellent"]):
                tone = "positive"
            elif any(word in conversation_text.lower() for word in ["frustrated", "angry", "disappointed"]):
                tone = "empathetic"
            
            # Prepare follow-up context
            follow_up_context = f"Issue: {issue.title}. Conversation length: {len(conversations)} messages. "
            follow_up_context += f"Current status: {issue.status}. Tone: {tone}"
            
            recommendations = await ai_service.generate_recommendations(
                issue.id, follow_up_context, "follow-up", tone
            )
            
            # Customize based on issue status
            for rec in recommendations:
                if issue.status == "RESOLVED":
                    rec["template"] += " Is there anything else I can help you with?"
                elif issue.status == "IN_PROGRESS":
                    rec["template"] += " I'll keep you updated on the progress."
            
            return recommendations[:2]  # Return top 2 follow-up recommendations
            
        except Exception as e:
            logger.error(f"Error generating follow-up recommendations: {str(e)}")
            return self._get_fallback_follow_up_recommendations(issue)
    
    def _generate_recommendation_reasoning(self, issue: Issue, customer: Customer,
                                         conversations: List[Conversation], 
                                         recommendations: List[Dict[str, Any]]) -> str:
        """Generate reasoning for recommendations"""
        reasoning_parts = []
        
        # Customer-based reasoning
        if customer.vip_status:
            reasoning_parts.append("VIP customer - enhanced service level")
        
        if customer.total_issues > 10:
            reasoning_parts.append("Experienced customer - familiar with process")
        
        # Issue-based reasoning
        if issue.severity == "HIGH":
            reasoning_parts.append("High severity issue - urgent attention required")
        
        if len(conversations) > 5:
            reasoning_parts.append("Extended conversation - detailed context available")
        
        # Recommendation-based reasoning
        high_confidence_count = len([r for r in recommendations if r["confidence_score"] > 0.8])
        if high_confidence_count > 2:
            reasoning_parts.append("High confidence recommendations based on similar cases")
        
        if not reasoning_parts:
            reasoning_parts.append("Standard support recommendations")
        
        return ". ".join(reasoning_parts) + "."
    
    async def _store_recommendations(self, issue_id: int, recommendations: List[Dict[str, Any]]):
        """Store recommendations in database for tracking"""
        try:
            for rec in recommendations:
                db_recommendation = Recommendation(
                    issue_id=issue_id,
                    template_text=rec["template"],
                    message_type=rec.get("type", "general"),
                    tone=rec.get("tone", "professional"),
                    confidence_score=rec["confidence_score"],
                    reasoning=rec.get("reasoning", ""),
                    created_at=datetime.utcnow()
                )
                self.db.add(db_recommendation)
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error storing recommendations: {str(e)}")
            self.db.rollback()
    
    def _get_fallback_greeting_recommendations(self, issue: Issue, customer: Customer) -> List[Dict[str, Any]]:
        """Get fallback greeting recommendations"""
        templates = [
            "Thank you for reaching out to our support team. I understand you're experiencing an issue and I'm here to help.",
            "Hello! I see you're having trouble with our service. Let me assist you in resolving this quickly."
        ]
        
        if customer.vip_status:
            templates[0] = "Thank you for reaching out to our VIP support team. I understand you're experiencing an issue and I'm here to help."
        
        if issue.severity == "HIGH":
            templates[0] += " I understand this is urgent and I'm here to help immediately."
        
        return [
            {
                "template": template,
                "type": "greeting",
                "tone": "professional",
                "confidence_score": 0.6
            }
            for template in templates
        ]
    
    def _get_fallback_solution_recommendations(self, issue: Issue) -> List[Dict[str, Any]]:
        # Remove fallback logic; implement real solution logic as needed
        return []

    def _get_fallback_follow_up_recommendations(self, issue: Issue) -> List[Dict[str, Any]]:
        # Remove fallback logic; implement real follow-up logic as needed
        return []
    
    async def get_recommendation_history(self, issue_id: int) -> List[Dict[str, Any]]:
        """
        Get historical recommendations for an issue.
        
        Args:
            issue_id: Issue ID
            
        Returns:
            List of historical recommendations
        """
        try:
            recommendations = self.db.query(Recommendation).filter(
                Recommendation.issue_id == issue_id
            ).order_by(desc(Recommendation.created_at)).all()
            
            return [
                {
                    "id": rec.id,
                    "template": rec.template_text,
                    "type": rec.message_type,
                    "tone": rec.tone,
                    "confidence_score": float(rec.confidence_score),
                    "used_count": rec.used_count,
                    "created_at": rec.created_at.isoformat()
                }
                for rec in recommendations
            ]
            
        except Exception as e:
            logger.error(f"Error getting recommendation history: {str(e)}")
            return []
    
    async def mark_recommendation_used(self, recommendation_id: int):
        """
        Mark a recommendation as used.
        
        Args:
            recommendation_id: Recommendation ID
        """
        try:
            recommendation = self.db.query(Recommendation).filter(
                Recommendation.id == recommendation_id
            ).first()
            
            if recommendation:
                recommendation.used_count += 1
                self.db.commit()
                
        except Exception as e:
            logger.error(f"Error marking recommendation as used: {str(e)}")
            self.db.rollback()
    
    async def get_popular_recommendations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most popular recommendations across all issues.
        
        Args:
            limit: Maximum number of recommendations to return
            
        Returns:
            List of popular recommendations
        """
        try:
            popular_recommendations = self.db.query(Recommendation).filter(
                Recommendation.used_count > 0
            ).order_by(desc(Recommendation.used_count)).limit(limit).all()
            
            return [
                {
                    "id": rec.id,
                    "template": rec.template_text,
                    "type": rec.message_type,
                    "tone": rec.tone,
                    "used_count": rec.used_count,
                    "confidence_score": float(rec.confidence_score)
                }
                for rec in popular_recommendations
            ]
            
        except Exception as e:
            logger.error(f"Error getting popular recommendations: {str(e)}")
            return []
    
    async def get_recommendation_analytics(self) -> Dict[str, Any]:
        """
        Get analytics about recommendation usage.
        
        Returns:
            Recommendation analytics
        """
        try:
            total_recommendations = self.db.query(Recommendation).count()
            used_recommendations = self.db.query(Recommendation).filter(
                Recommendation.used_count > 0
            ).count()
            
            # Get average confidence score
            avg_confidence = self.db.query(func.avg(Recommendation.confidence_score)).scalar()
            
            # Get recommendations by type
            greeting_count = self.db.query(Recommendation).filter(
                Recommendation.message_type == "greeting"
            ).count()
            
            solution_count = self.db.query(Recommendation).filter(
                Recommendation.message_type == "solution"
            ).count()
            
            follow_up_count = self.db.query(Recommendation).filter(
                Recommendation.message_type == "follow-up"
            ).count()
            
            return {
                "total_recommendations": total_recommendations,
                "used_recommendations": used_recommendations,
                "usage_rate": round(used_recommendations / total_recommendations * 100, 2) if total_recommendations > 0 else 0,
                "avg_confidence_score": round(float(avg_confidence), 2) if avg_confidence else 0,
                "by_type": {
                    "greeting": greeting_count,
                    "solution": solution_count,
                    "follow_up": follow_up_count
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting recommendation analytics: {str(e)}")
            return {} 