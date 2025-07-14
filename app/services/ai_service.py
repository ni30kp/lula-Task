import logging
import json
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import openai
from transformers import pipeline, AutoTokenizer, AutoModel
import torch
from sentence_transformers import SentenceTransformer
import re

from app.core.config import settings
from app.core.database import get_db, Issue, Customer, Conversation, Recommendation, ConversationSummary
from app.models.schemas import SeverityLevel

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.openai_client = None
        self.severity_classifier = None
        self.sentence_transformer = None
        self.summarizer = None
        self.sentiment_analyzer = None
        self._initialize_models()

    def _initialize_models(self):
        try:
            if settings.OPENAI_API_KEY:
                openai.api_key = settings.OPENAI_API_KEY
                self.openai_client = openai
            self.severity_classifier = self._create_severity_classifier()
            self.sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
            self.summarizer = pipeline("summarization", model="t5-small")
            self.sentiment_analyzer = pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment")
            logger.info("AI models initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing AI models: {str(e)}")
            self.severity_classifier = True
            self.sentence_transformer = None
            self.summarizer = None
            self.sentiment_analyzer = None

    def _create_severity_classifier(self):
        self.critical_keywords = [
            'urgent', 'critical', 'emergency', 'down', 'broken', 'failed',
            'error', 'crash', 'not working', 'cannot access', 'blocked',
            'security', 'breach', 'hack', 'data loss', 'outage'
        ]
        self.high_severity_keywords = [
            'important', 'priority', 'issue', 'problem', 'trouble',
            'difficulty', 'challenge', 'concern', 'matter', 'situation'
        ]
        return True

    async def assess_severity(self, issue_text: str, customer_history: Dict[str, Any]) -> Dict[str, Any]:
        try:
            full_text = issue_text.lower()
            severity_score = 0
            reasoning = []
            critical_count = sum(1 for keyword in self.critical_keywords if keyword in full_text)
            if critical_count > 0:
                severity_score += 3
                reasoning.append(f"Contains {critical_count} critical keywords")
            high_count = sum(1 for keyword in self.high_severity_keywords if keyword in full_text)
            if high_count > 0:
                severity_score += 2
                reasoning.append(f"Contains {high_count} high-severity keywords")
            if customer_history.get('vip_status', False):
                severity_score += 1
                reasoning.append("VIP customer")
            recent_critical = customer_history.get('recent_critical_issues', 0)
            if recent_critical > 0:
                severity_score += 1
                reasoning.append(f"{recent_critical} recent critical issues")
            if severity_score >= 5:
                severity = SeverityLevel.HIGH
                confidence = 0.9
            elif severity_score >= 3:
                severity = SeverityLevel.NORMAL
                confidence = 0.7
            else:
                severity = SeverityLevel.LOW
                confidence = 0.5
            return {
                "severity": severity,
                "confidence_score": confidence,
                "reasoning": "; ".join(reasoning)
            }
        except Exception as e:
            logger.error(f"Error in severity assessment: {str(e)}")
            return {"severity": SeverityLevel.NORMAL, "confidence_score": 0.5, "reasoning": "Fallback"}

    async def find_similar_issues(self, issue_text: str, db_session, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            resolved_issues = db_session.query(Issue).filter(
                Issue.status.in_(["RESOLVED", "CLOSED"])
            ).all()
            if not resolved_issues:
                return []
            issue_texts = [issue.title + " " + issue.description for issue in resolved_issues]
            issue_texts.append(issue_text)
            vectorizer = TfidfVectorizer(max_features=1000, stop_words='english', ngram_range=(1, 2))
            tfidf_matrix = vectorizer.fit_transform(issue_texts)
            similarities = cosine_similarity(tfidf_matrix[-1:], tfidf_matrix[:-1])[0]
            similar_indices = np.argsort(similarities)[::-1][:limit]
            similar_issues = []
            for idx in similar_indices:
                issue = resolved_issues[idx]
                similar_issues.append({
                    "issue_id": issue.id,
                    "similarity_score": float(similarities[idx]),
                    "resolution": getattr(issue, "resolution", None),
                    "resolution_time": getattr(issue, "resolution_time", None)
                })
            return similar_issues
        except Exception as e:
            logger.error(f"Error finding similar issues: {str(e)}")
            return []

    async def generate_recommendations(self, issue_id: int, context: str, message_type: str, tone: str = "professional") -> List[Dict[str, Any]]:
        try:
            if not self.openai_client:
                return []
            prompt = self._create_recommendation_prompt(context, message_type, tone)
            response = self.openai_client.ChatCompletion.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful support assistant. Generate professional, empathetic message templates."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7,
                n=3
            )
            recommendations = []
            for choice in response.choices:
                template = choice.message.content.strip()
                if template:
                    recommendations.append({
                        "template": template,
                        "type": message_type,
                        "tone": tone,
                        "confidence_score": 0.85
                    })
            return recommendations
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return []

    def _create_recommendation_prompt(self, context: str, message_type: str, tone: str) -> str:
        prompts = {
            "greeting": f"Generate a {tone} greeting message for a support issue. Context: {context}",
            "solution": f"Generate a {tone} solution message for a support issue. Context: {context}",
            "follow-up": f"Generate a {tone} follow-up message for a support issue. Context: {context}"
        }
        return prompts.get(message_type, f"Generate a {tone} message for a support issue. Context: {context}")

    async def summarize_conversation(self, conversation_id: int, db_session) -> Dict[str, Any]:
        try:
            messages = db_session.query(Conversation).filter(
                Conversation.issue_id == conversation_id
            ).order_by(Conversation.created_at).all()
            if not messages:
                return {"error": "No messages found for conversation"}
            full_conversation = " ".join([msg.message for msg in messages])
            if len(full_conversation) > 1000:
                full_conversation = full_conversation[:1000] + "..."
            if self.summarizer:
                summary_result = self.summarizer(full_conversation, max_length=150, min_length=50)
                summary = summary_result[0]['summary_text']
            else:
                summary = full_conversation[:150] + "..."
            return {
                "summary": summary,
                "key_points": [],
                "action_items": [],
                "sentiment": "neutral",
                "message_count": len(messages)
            }
        except Exception as e:
            logger.error(f"Error summarizing conversation: {str(e)}")
            return {
                "summary": "Error generating summary",
                "key_points": [],
                "action_items": [],
                "sentiment": "neutral",
                "message_count": 0
            }
    
    def _fallback_summarization(self, text: str) -> str:
        """Fallback summarization when ML model is unavailable"""
        sentences = text.split('.')
        if len(sentences) <= 3:
            return text
        
        # Simple extractive summarization
        important_sentences = []
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in ['issue', 'problem', 'resolved', 'fixed', 'error']):
                important_sentences.append(sentence)
        
        if important_sentences:
            return '. '.join(important_sentences[:3]) + '.'
        else:
            return '. '.join(sentences[:2]) + '.'
    
    def _extract_key_points(self, text: str) -> List[str]:
        """Extract key points from conversation"""
        key_points = []
        
        # Simple keyword-based extraction
        keywords = ['issue', 'problem', 'error', 'resolved', 'fixed', 'solution', 'help']
        
        sentences = text.split('.')
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in keywords):
                key_points.append(sentence.strip())
        
        return key_points[:5]  # Limit to 5 key points
    
    def _extract_action_items(self, text: str) -> List[str]:
        """Extract action items from conversation"""
        action_items = []
        
        # Look for action-oriented phrases
        action_phrases = [
            'need to', 'should', 'must', 'will', 'going to',
            'follow up', 'check', 'verify', 'test', 'update'
        ]
        
        sentences = text.split('.')
        for sentence in sentences:
            if any(phrase in sentence.lower() for phrase in action_phrases):
                action_items.append(sentence.strip())
        
        return action_items[:3]  # Limit to 3 action items
    
    async def _analyze_sentiment(self, text: str) -> str:
        """Analyze sentiment of conversation"""
        try:
            if self.sentiment_analyzer:
                result = self.sentiment_analyzer(text[:500])  # Limit text length
                label = result[0]['label']
                
                # Map sentiment labels
                sentiment_map = {
                    'LABEL_0': 'negative',
                    'LABEL_1': 'neutral',
                    'LABEL_2': 'positive'
                }
                
                return sentiment_map.get(label, 'neutral')
            else:
                # Simple rule-based sentiment analysis
                positive_words = ['thank', 'great', 'good', 'excellent', 'resolved', 'fixed', 'helpful']
                negative_words = ['bad', 'terrible', 'awful', 'broken', 'error', 'problem', 'issue']
                
                text_lower = text.lower()
                positive_count = sum(1 for word in positive_words if word in text_lower)
                negative_count = sum(1 for word in negative_words if word in text_lower)
                
                if positive_count > negative_count:
                    return 'positive'
                elif negative_count > positive_count:
                    return 'negative'
                else:
                    return 'neutral'
                    
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return 'neutral'
    
    async def analyze_customer_sentiment(self, customer_id: int, db_session) -> Dict[str, Any]:
        """
        Analyze overall customer sentiment based on recent conversations.
        
        Args:
            customer_id: Customer ID
            db_session: Database session
            
        Returns:
            Sentiment analysis results
        """
        try:
            # Get recent conversations for customer
            recent_issues = db_session.query(Issue).filter(
                Issue.customer_id == customer_id,
                Issue.created_at >= datetime.utcnow() - timedelta(days=30)
            ).all()
            
            all_sentiments = []
            for issue in recent_issues:
                conversations = db_session.query(Conversation).filter(
                    Conversation.issue_id == issue.id
                ).all()
                
                for conv in conversations:
                    sentiment = await self._analyze_sentiment(conv.message)
                    all_sentiments.append(sentiment)
            
            if not all_sentiments:
                return {"overall_sentiment": "neutral", "sentiment_score": 0.0}
            
            # Calculate overall sentiment
            sentiment_counts = {
                'positive': all_sentiments.count('positive'),
                'neutral': all_sentiments.count('neutral'),
                'negative': all_sentiments.count('negative')
            }
            
            total = len(all_sentiments)
            sentiment_score = (sentiment_counts['positive'] - sentiment_counts['negative']) / total
            
            # Determine overall sentiment
            if sentiment_score > 0.1:
                overall_sentiment = 'positive'
            elif sentiment_score < -0.1:
                overall_sentiment = 'negative'
            else:
                overall_sentiment = 'neutral'
            
            return {
                "overall_sentiment": overall_sentiment,
                "sentiment_score": sentiment_score,
                "total_conversations": total,
                "sentiment_breakdown": sentiment_counts
            }
            
        except Exception as e:
            logger.error(f"Error analyzing customer sentiment: {str(e)}")
            return {"overall_sentiment": "neutral", "sentiment_score": 0.0}
    
    async def detect_critical_patterns(self, customer_id: int, db_session) -> List[str]:
        """
        Detect critical patterns in customer issues.
        
        Args:
            customer_id: Customer ID
            db_session: Database session
            
        Returns:
            List of critical patterns detected
        """
        try:
            patterns = []
            
            # Get customer's recent issues
            recent_issues = db_session.query(Issue).filter(
                Issue.customer_id == customer_id,
                Issue.created_at >= datetime.utcnow() - timedelta(days=7)
            ).all()
            
            if len(recent_issues) >= 3:
                patterns.append("Multiple issues in short time period")
            
            # Check for unresolved critical issues
            critical_unresolved = db_session.query(Issue).filter(
                Issue.customer_id == customer_id,
                Issue.severity == "HIGH",
                Issue.status.in_(["OPEN", "IN_PROGRESS"]),
                Issue.created_at <= datetime.utcnow() - timedelta(hours=24)
            ).count()
            
            if critical_unresolved > 0:
                patterns.append(f"{critical_unresolved} critical issues unresolved for >24h")
            
            # Check for repeated issues
            issue_categories = [issue.category for issue in recent_issues if issue.category]
            if len(set(issue_categories)) < len(issue_categories):
                patterns.append("Repeated issue categories detected")
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error detecting critical patterns: {str(e)}")
            return [] 