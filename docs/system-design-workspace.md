# System Design Workspace & Component Stencils

## 1. Overview
The **System Design Workspace** turns InterviewOS into an interactive environment for assessing large-scale system architecture and distributed systems engineering.

It provides candidate and interviewer participants with standard cloud engineering iconography, templates, and diagramming primitives.

---

## 2. Stencils Catalog

The stencil palette is categorized into 4 core architectural tiers:

### Compute Tier
- **API Gateway** (`#8b5cf6`): Entry point handling SSL termination, rate limiting, routing, and JWT validation.
- **Load Balancer** (`#3b82f6`): Layer 4 (TCP) and Layer 7 (HTTP) traffic balancing (ALB, NGINX, HAProxy).
- **Application Server** (`#6366f1`): Stateless application tier executing business logic.
- **Microservice** (`#06b6d4`): Autonomous domain service with independent persistence.
- **Async Worker** (`#10b981`): Asynchronous background job worker (Celery, BullMQ, Go routines).

### Storage Tier
- **SQL Database (PostgreSQL)** (`#0ea5e9`): Relational primary database with ACID guarantees and read-replica replication.
- **Redis In-Memory Cache** (`#ef4444`): High-throughput, sub-millisecond key-value cache and distributed lock store.
- **Object Storage (S3)** (`#f59e0b`): Scalable blob storage for assets, backups, and user uploads.
- **Search Cluster (Elasticsearch)** (`#14b8a6`): Inverted index for distributed full-text search and analytical log ingestion.

### Infrastructure Tier
- **Edge CDN (Cloudflare)** (`#f97316`): Global edge caching for static assets, SSR caching, and DDoS mitigation.
- **Message Queue (Kafka / RabbitMQ)** (`#ec4899`): Distributed log streaming and pub/sub message broker.

### Clients Tier
- **Web Client / SPA** (`#64748b`): Modern browser application (React, Next.js).
- **Mobile Client** (`#64748b`): Native mobile application (iOS, Android).
- **3rd-Party External API** (`#94a3b8`): Payment processors (Stripe), SMS gateways (Twilio), OAuth IDPs.

---

## 3. Architecture Templates

Interviewers can load standard architecture templates to kickstart system design rounds:
1. **3-Tier Scalable Web Application**:
   - `Client` -> `CDN (Cloudflare)` -> `Load Balancer` -> `App Cluster` -> `Redis Cache` & `PostgreSQL DB`
2. **Event-Driven Microservices**:
   - `Clients` -> `API Gateway` -> `Order/Payment Services` -> `Kafka Broker` -> `Notification/Analytics Workers`
3. **URL Shortener (TinyURL)**:
   - `Browser` -> `Load Balancer` -> `Shortener Service (Base62)` -> `Redis (Top 20%)` -> `Distributed NoSQL DB`
