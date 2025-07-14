# Support Copilot - Issue Lifecycle Management System

## Project Overview

The Support Copilot is an AI-powered system that assists support executives throughout the entire issue lifecycle. It provides intelligent analysis, automated recommendations, and real-time guidance to ensure efficient issue resolution.

## Key Features

- **Issue Intake & Analysis**: Automatic severity assessment and customer history analysis
- **Support Executive Guidance**: AI-generated message templates and recommendations
- **Conversation Summarization**: Automatic conversation summaries for knowledge base
- **Real-time API Integration**: RESTful APIs with <15 second response times
- **Cloud Deployment**: AWS-hosted scalable solution

## Architecture Overview

### System Components

1. **API Gateway** - Entry point for all external requests
2. **Issue Management Service** - Core business logic for issue processing
3. **AI Analysis Service** - ML-powered issue analysis and recommendations
4. **Database Layer** - MySQL for structured data, Redis for caching
5. **Message Queue** - RabbitMQ for asynchronous processing
6. **Monitoring & Logging** - CloudWatch integration

### Data Flow

```
Support Portal → API Gateway → Issue Service → AI Service → Database
                ↓
            Response (≤15s)
```

## Quick Start

1. **Prerequisites**
   - Python 3.9+
   - Docker & Docker Compose
   - AWS CLI configured

2. **Installation**
   ```bash
   git clone <repository>
   cd support-copilot
   docker-compose up -d
   ```

3. **API Documentation**
   - Swagger UI: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## API Endpoints

- `POST /api/v1/issues/analyze` - Analyze new issue
- `POST /api/v1/issues/{id}/recommend` - Get recommendations
- `POST /api/v1/conversations/{id}/summarize` - Generate summary
- `GET /api/v1/customers/{id}/history` - Customer history

## Security & Compliance

- JWT-based authentication
- GDPR-compliant data handling
- Encrypted data transmission
- Role-based access control 

## How to Test Authentication and Protected Endpoints

1. **Login to get a JWT token:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "support_user", "password": "support_password"}'
   ```
   This will return a JSON response with an `access_token`.

2. **Use the token to call a protected endpoint:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/issues/analyze \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <access_token>" \
     -d '{
       "customer_id": 1001,
       "title": "Cannot login to portal",
       "description": "I am unable to login to the support portal with my credentials. It says invalid password.",
       "category": "Authentication",
       "priority": "High"
     }'
   ```
   Replace `<access_token>` with the value from the login response. 