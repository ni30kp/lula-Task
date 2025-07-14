"""
Support Copilot API Examples

This file contains example code snippets demonstrating how to use the Support Copilot API
for various use cases including issue analysis, recommendation generation, and conversation management.
"""

import requests
import json
from datetime import datetime
from typing import Dict, Any, List

# API Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "support-copilot-api-key-2024"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

class SupportCopilotClient:
    """Client for interacting with Support Copilot API"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def analyze_new_issue(self, customer_id: int, title: str, description: str, 
                         category: str = None, priority: str = None) -> Dict[str, Any]:
        """
        Analyze a new support issue and get AI-powered insights.
        
        Example:
        >>> client = SupportCopilotClient(BASE_URL, API_KEY)
        >>> analysis = client.analyze_new_issue(
        ...     customer_id=1,
        ...     title="Login authentication failed",
        ...     description="Unable to login to the application. Getting error 401 unauthorized.",
        ...     category="Authentication",
        ...     priority="High"
        ... )
        >>> print(f"Severity: {analysis['severity_assessment']}")
        >>> print(f"Confidence: {analysis['confidence_score']}")
        """
        
        payload = {
            "customer_id": customer_id,
            "title": title,
            "description": description,
            "category": category,
            "priority": priority
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/issues/analyze",
            headers=self.headers,
            json=payload,
            timeout=15
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API Error: {response.status_code} - {response.text}")
    
    def get_recommendations(self, issue_id: int, context: str, 
                           message_type: str = "greeting", tone: str = "professional") -> Dict[str, Any]:
        """
        Get AI-generated message recommendations for support executives.
        
        Example:
        >>> recommendations = client.get_recommendations(
        ...     issue_id=123,
        ...     context="Customer reported login issues",
        ...     message_type="greeting",
        ...     tone="professional"
        ... )
        >>> for rec in recommendations['recommendations']:
        ...     print(f"Template: {rec['template']}")
        ...     print(f"Confidence: {rec['confidence_score']}")
        """
        
        payload = {
            "context": context,
            "message_type": message_type,
            "tone": tone
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/issues/{issue_id}/recommend",
            headers=self.headers,
            json=payload,
            timeout=15
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API Error: {response.status_code} - {response.text}")
    
    def get_customer_history(self, customer_id: int) -> Dict[str, Any]:
        """
        Get comprehensive customer history and analytics.
        
        Example:
        >>> history = client.get_customer_history(customer_id=1)
        >>> print(f"Total Issues: {history['total_issues']}")
        >>> print(f"Avg Resolution Time: {history['avg_resolution_time']}")
        >>> print(f"Critical Issues: {history['critical_issues']}")
        """
        
        response = requests.get(
            f"{self.base_url}/api/v1/customers/{customer_id}/history",
            headers=self.headers,
            timeout=15
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API Error: {response.status_code} - {response.text}")
    
    def get_critical_issues(self) -> List[Dict[str, Any]]:
        """
        Get all critical issues that require immediate attention.
        
        Example:
        >>> critical_issues = client.get_critical_issues()
        >>> for issue in critical_issues:
        ...     print(f"Issue {issue['issue_id']}: {issue['title']}")
        ...     print(f"Customer: {issue['customer_name']}")
        ...     print(f"VIP Status: {issue['vip_status']}")
        """
        
        response = requests.get(
            f"{self.base_url}/api/v1/issues/critical",
            headers=self.headers,
            timeout=15
        )
        
        if response.status_code == 200:
            return response.json()["critical_issues"]
        else:
            raise Exception(f"API Error: {response.status_code} - {response.text}")
    
    def update_issue_status(self, issue_id: int, new_status: str) -> bool:
        """
        Update issue status and trigger notifications.
        
        Example:
        >>> success = client.update_issue_status(issue_id=123, new_status="RESOLVED")
        >>> print(f"Status updated: {success}")
        """
        
        response = requests.put(
            f"{self.base_url}/api/v1/issues/{issue_id}/status?status={new_status}",
            headers=self.headers,
            timeout=15
        )
        
        return response.status_code == 200
    
    def summarize_conversation(self, conversation_id: int) -> Dict[str, Any]:
        """
        Generate conversation summary for knowledge base.
        
        Example:
        >>> summary = client.summarize_conversation(conversation_id=456)
        >>> print(f"Summary: {summary['summary']}")
        >>> print(f"Key Points: {summary['key_points']}")
        >>> print(f"Action Items: {summary['action_items']}")
        """
        
        response = requests.post(
            f"{self.base_url}/api/v1/conversations/{conversation_id}/summarize",
            headers=self.headers,
            timeout=15
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API Error: {response.status_code} - {response.text}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get system performance metrics.
        
        Example:
        >>> metrics = client.get_performance_metrics()
        >>> print(f"Avg Response Time: {metrics['api_response_time_avg']}s")
        >>> print(f"Active Issues: {metrics['active_issues']}")
        >>> print(f"Critical Issues: {metrics['critical_issues']}")
        """
        
        response = requests.get(
            f"{self.base_url}/api/v1/metrics",
            headers=self.headers,
            timeout=15
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API Error: {response.status_code} - {response.text}")

# Example usage scenarios
def example_issue_analysis():
    """Example: Analyze a new critical issue"""
    client = SupportCopilotClient(BASE_URL, API_KEY)
    
    # Analyze new issue
    analysis = client.analyze_new_issue(
        customer_id=1,
        title="Payment processing error",
        description="Credit card payments are being declined incorrectly. This is affecting our business operations.",
        category="Payment",
        priority="Critical"
    )
    
    print("=== Issue Analysis ===")
    print(f"Issue ID: {analysis['issue_id']}")
    print(f"Severity: {analysis['severity_assessment']}")
    print(f"Confidence: {analysis['confidence_score']:.2f}")
    print(f"Processing Time: {analysis['processing_time']:.2f}s")
    
    print("\nCustomer History:")
    history = analysis['customer_history']
    print(f"  Total Issues: {history['total_issues']}")
    print(f"  VIP Status: {history['vip_status']}")
    print(f"  Avg Resolution Time: {history['avg_resolution_time']}")
    
    print("\nSimilar Issues:")
    for similar in analysis['similar_issues'][:3]:
        print(f"  - Issue {similar['issue_id']}: {similar['similarity_score']:.2f} similarity")
    
    print("\nCritical Flags:")
    for flag in analysis['critical_flags']:
        print(f"  - {flag}")
    
    print("\nRecommended Actions:")
    for action in analysis['recommended_actions']:
        print(f"  - {action}")

def example_recommendation_generation():
    """Example: Generate message recommendations"""
    client = SupportCopilotClient(BASE_URL, API_KEY)
    
    # Get recommendations for different message types
    issue_id = 123
    context = "Customer reported login authentication issues. They are a VIP customer."
    
    # Greeting recommendation
    greeting_recs = client.get_recommendations(
        issue_id=issue_id,
        context=context,
        message_type="greeting",
        tone="professional"
    )
    
    print("=== Greeting Recommendations ===")
    for i, rec in enumerate(greeting_recs['recommendations'], 1):
        print(f"{i}. {rec['template']}")
        print(f"   Confidence: {rec['confidence_score']:.2f}")
        print()
    
    # Solution recommendation
    solution_recs = client.get_recommendations(
        issue_id=issue_id,
        context=context,
        message_type="solution",
        tone="helpful"
    )
    
    print("=== Solution Recommendations ===")
    for i, rec in enumerate(solution_recs['recommendations'], 1):
        print(f"{i}. {rec['template']}")
        print(f"   Confidence: {rec['confidence_score']:.2f}")
        print()

def example_customer_analytics():
    """Example: Customer history and analytics"""
    client = SupportCopilotClient(BASE_URL, API_KEY)
    
    # Get customer history
    customer_id = 1
    history = client.get_customer_history(customer_id)
    
    print("=== Customer Analytics ===")
    print(f"Customer ID: {history['customer_id']}")
    print(f"Total Issues: {history['total_issues']}")
    print(f"Resolved Issues: {history['resolved_issues']}")
    print(f"Critical Issues: {history['critical_issues']}")
    print(f"Avg Resolution Time: {history['avg_resolution_time']}")
    print(f"Customer Satisfaction: {history['customer_satisfaction']}")
    
    print("\nRecent Issues:")
    for issue in history['recent_issues'][:3]:
        print(f"  - Issue {issue['issue_id']}: {issue['title']}")
        print(f"    Status: {issue['status']}, Severity: {issue['severity']}")
    
    print("\nIssue Patterns:")
    for pattern in history['issue_patterns']:
        print(f"  - {pattern}")

def example_critical_issues_monitoring():
    """Example: Monitor critical issues"""
    client = SupportCopilotClient(BASE_URL, API_KEY)
    
    # Get critical issues
    critical_issues = client.get_critical_issues()
    
    print("=== Critical Issues Alert ===")
    print(f"Total Critical Issues: {len(critical_issues)}")
    
    for issue in critical_issues:
        print(f"\nIssue {issue['issue_id']}: {issue['title']}")
        print(f"  Customer: {issue['customer_name']}")
        print(f"  VIP Status: {issue['vip_status']}")
        print(f"  Severity: {issue['severity']}")
        print(f"  Status: {issue['status']}")
        print(f"  Time Since Creation: {issue['time_since_creation']:.1f} hours")
        
        if issue['vip_status']:
            print("  ⚠️  VIP CUSTOMER - PRIORITY ESCALATION REQUIRED")

def example_conversation_summarization():
    """Example: Conversation summarization"""
    client = SupportCopilotClient(BASE_URL, API_KEY)
    
    # Summarize conversation
    conversation_id = 456
    summary = client.summarize_conversation(conversation_id)
    
    print("=== Conversation Summary ===")
    print(f"Conversation ID: {summary['conversation_id']}")
    print(f"Summary: {summary['summary']}")
    print(f"Sentiment: {summary['sentiment']}")
    print(f"Message Count: {summary['message_count']}")
    
    print("\nKey Points:")
    for point in summary['key_points']:
        print(f"  - {point}")
    
    print("\nAction Items:")
    for item in summary['action_items']:
        print(f"  - {item}")

def example_performance_monitoring():
    """Example: System performance monitoring"""
    client = SupportCopilotClient(BASE_URL, API_KEY)
    
    # Get performance metrics
    metrics = client.get_performance_metrics()
    
    print("=== System Performance Metrics ===")
    print(f"API Response Time (Avg): {metrics['api_response_time_avg']:.2f}s")
    print(f"Active Issues: {metrics['active_issues']}")
    print(f"Resolved Today: {metrics['resolved_today']}")
    print(f"Critical Issues: {metrics['critical_issues']}")
    print(f"System Health: {metrics['system_health']}")

# Main execution
if __name__ == "__main__":
    print("Support Copilot API Examples")
    print("=" * 50)
    
    try:
        # Run examples
        example_issue_analysis()
        print("\n" + "=" * 50)
        
        example_recommendation_generation()
        print("\n" + "=" * 50)
        
        example_customer_analytics()
        print("\n" + "=" * 50)
        
        example_critical_issues_monitoring()
        print("\n" + "=" * 50)
        
        example_conversation_summarization()
        print("\n" + "=" * 50)
        
        example_performance_monitoring()
        
    except Exception as e:
        print(f"Error running examples: {str(e)}")
        print("Make sure the Support Copilot API is running on localhost:8000") 