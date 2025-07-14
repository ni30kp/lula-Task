# Technical Architecture - Support Copilot

## 1. System Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Support       │    │   API Gateway   │    │   Load Balancer │
│   Portal        │───▶│   (FastAPI)     │───▶│   (ALB)         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Issue         │    │   AI Analysis   │    │   Message       │
│   Management    │◀──▶│   Service       │◀──▶│   Queue         │
│   Service       │    │   (ML Models)   │    │   (RabbitMQ)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MySQL         │    │   Redis Cache   │    │   CloudWatch    │
│   Database      │    │   (Session)     │    │   (Monitoring)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 2. Component Details

### 2.1 API Gateway (FastAPI)
**Purpose**: Single entry point for all external requests
**Technology**: FastAPI with Uvicorn
**Features**:
- Request routing and load balancing
- Authentication and authorization
- Rate limiting and throttling
- Request/response logging
- CORS handling

**Response Time**: <15 seconds guaranteed

### 2.2 Issue Management Service
**Purpose**: Core business logic for issue processing
**Responsibilities**:
- Issue intake and validation
- Customer history retrieval
- Similar issue search
- Severity assessment
- Critical issue flagging

**Key Algorithms**:
- TF-IDF for similar issue detection
- Rule-based severity classification
- Time-based criticality assessment

### 2.3 AI Analysis Service
**Purpose**: ML-powered analysis and recommendations
**Components**:
- **Text Classification Model**: Severity assessment
- **Recommendation Engine**: Message template generation
- **Summarization Model**: Conversation summarization
- **Similarity Engine**: Issue similarity detection

**ML Models Used**:
- BERT for text understanding
- Sentence Transformers for similarity
- GPT-3.5 for template generation
- T5 for summarization

### 2.4 Database Layer
**MySQL Schema**:
```sql
-- Core tables for issue management
CREATE TABLE customers (
    id BIGINT PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    name VARCHAR(255),
    created_at TIMESTAMP,
    total_issues INT DEFAULT 0
);

CREATE TABLE issues (
    id BIGINT PRIMARY KEY,
    customer_id BIGINT,
    title VARCHAR(500),
    description TEXT,
    severity ENUM('LOW', 'NORMAL', 'HIGH'),
    status ENUM('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE conversations (
    id BIGINT PRIMARY KEY,
    issue_id BIGINT,
    message TEXT,
    sender_type ENUM('CUSTOMER', 'SUPPORT'),
    created_at TIMESTAMP,
    FOREIGN KEY (issue_id) REFERENCES issues(id)
);

CREATE TABLE recommendations (
    id BIGINT PRIMARY KEY,
    issue_id BIGINT,
    template_text TEXT,
    confidence_score DECIMAL(3,2),
    created_at TIMESTAMP,
    FOREIGN KEY (issue_id) REFERENCES issues(id)
);
```

**Redis Usage**:
- Session storage
- API response caching
- Real-time issue status
- Customer history cache

### 2.5 Message Queue (RabbitMQ)
**Purpose**: Asynchronous processing for heavy operations
**Queues**:
- `issue_analysis` - New issue processing
- `recommendation_generation` - Template generation
- `conversation_summarization` - Summary creation
- `notification` - Alert notifications

## 3. Data Flow Diagrams

### 3.1 Issue Intake Flow
```
1. Support Portal → API Gateway
2. API Gateway → Issue Management Service
3. Issue Service → Database (Customer History)
4. Issue Service → AI Service (Severity Analysis)
5. AI Service → Database (Store Analysis)
6. Issue Service → Message Queue (Async Processing)
7. Response → Support Portal (<15s)
```

### 3.2 Recommendation Generation Flow
```
1. Support Executive Request → API Gateway
2. API Gateway → Issue Management Service
3. Issue Service → Database (Issue Details)
4. Issue Service → AI Service (Template Generation)
5. AI Service → Database (Similar Issues)
6. AI Service → Recommendation Engine
7. Response → Support Executive (<15s)
```

### 3.3 Conversation Summarization Flow
```
1. Conversation End → API Gateway
2. API Gateway → Message Queue (Async)
3. Message Queue → AI Service
4. AI Service → Summarization Model
5. AI Service → Database (Store Summary)
6. Notification → Support Portal
```

## 4. Performance Considerations

### 4.1 Response Time Optimization
- **Caching Strategy**: Redis for frequently accessed data
- **Database Indexing**: Optimized indexes on customer_id, issue_id
- **Async Processing**: Heavy operations moved to background
- **Connection Pooling**: Database and external service connections

### 4.2 Scalability Features
- **Horizontal Scaling**: Stateless services
- **Load Balancing**: Multiple service instances
- **Database Sharding**: Customer-based sharding
- **CDN Integration**: Static content delivery

## 5. Security Architecture

### 5.1 Authentication & Authorization
- JWT-based token authentication
- Role-based access control (RBAC)
- API key management for external integrations

### 5.2 Data Protection
- Encryption at rest (AES-256)
- Encryption in transit (TLS 1.3)
- GDPR compliance measures
- Data anonymization for ML training

### 5.3 API Security
- Rate limiting per client
- Input validation and sanitization
- SQL injection prevention
- XSS protection

## 6. Monitoring & Observability

### 6.1 Metrics Collection
- API response times
- Error rates and types
- Database query performance
- Queue processing times

### 6.2 Logging Strategy
- Structured logging (JSON)
- Log aggregation (ELK Stack)
- Error tracking and alerting
- Audit trail for compliance

### 6.3 Health Checks
- Service health endpoints
- Database connectivity
- External service dependencies
- ML model availability

## 7. Deployment Architecture

### 7.1 AWS Infrastructure
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Route 53      │    │   Application   │    │   Auto Scaling  │
│   (DNS)         │───▶│   Load Balancer │───▶│   Group         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   ECS Fargate   │    │   RDS MySQL    │    │   ElastiCache   │
│   (Services)    │◀──▶│   (Database)   │◀──▶│   (Redis)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   S3            │    │   CloudWatch    │    │   SQS           │
│   (Logs)        │    │   (Monitoring)  │    │   (Queue)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 7.2 Container Strategy
- **Microservices**: Each component in separate containers
- **Docker Images**: Optimized for size and security
- **Orchestration**: ECS Fargate for serverless containers
- **Service Discovery**: Internal load balancing

## 8. Disaster Recovery

### 8.1 Backup Strategy
- **Database**: Automated daily backups with point-in-time recovery
- **Application**: Container images in ECR
- **Configuration**: Infrastructure as Code (Terraform)

### 8.2 High Availability
- **Multi-AZ Deployment**: Services across availability zones
- **Failover Mechanisms**: Automatic failover for database
- **Circuit Breakers**: External service dependency protection

## 9. Cost Optimization

### 9.1 Resource Management
- **Auto Scaling**: Based on CPU/memory usage
- **Spot Instances**: For non-critical workloads
- **Reserved Instances**: For predictable workloads
- **Data Lifecycle**: Automated data archival

### 9.2 Performance vs Cost
- **Caching**: Reduce database calls
- **CDN**: Reduce bandwidth costs
- **Compression**: Reduce data transfer
- **Monitoring**: Prevent resource waste 