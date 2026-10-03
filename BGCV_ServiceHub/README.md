# BGCV ServiceHub

> Simplifying IT. Resolving Faster.

BGCV ServiceHub is a production-style 3-Tier Service Desk and Incident Management Application built using React, Flask, PostgreSQL, Docker, and Docker Compose.

The project simulates a real-world enterprise IT Service Management (ITSM) platform where users can create incidents, track issues, update ticket status, and manage ticket lifecycles.

---

# Architecture

## High-Level Architecture

```text
Browser
   │
   ▼
React Frontend
   │
   ▼
Flask REST API
   │
   ▼
PostgreSQL Database
```

---

## Deployment Architecture

```text
Docker Compose
      │
      ├── Frontend Container
      │
      ├── Backend Container
      │
      └── PostgreSQL Container
```

---

# Technology Stack

## Frontend

- React.js
- React Router
- Axios
- Recharts

## Backend

- Python
- Flask
- SQLAlchemy
- Gunicorn

## Database

- PostgreSQL

## DevOps

- Docker
- Docker Compose
- Git
- GitHub

## Future Integrations

- Kubernetes
- AWS EKS
- Amazon ECR
- Terraform
- Jenkins
- Prometheus
- Grafana

---

# Features

## Dashboard

- Total Tickets
- Open Tickets
- Resolved Tickets
- Critical Tickets
- Ticket Status Distribution
- Priority Analysis
- Incident Trends

## Incident Management

- Create Incident
- View Incident
- Update Incident
- Change Status
- Add Comments
- Delete Incident

## Database Features

- Relational Database Design
- Foreign Key Relationships
- Indexed Fields
- Sample Seed Data

## API Features

```http
GET /api/health

GET /api/health/live

GET /api/health/ready

GET /api/tickets

GET /api/tickets/{id}

POST /api/tickets

PUT /api/tickets/{id}

DELETE /api/tickets/{id}

POST /api/tickets/{id}/comments

GET /api/dashboard/stats
```

---

# Project Structure

```text
service-desk-portal/

├── frontend/
│
├── backend/
│
├── database/
│   ├── schema.sql
│   └── seed.sql
│
├── docker-compose.yml
│
├── kubernetes/
│
├── terraform/
│
├── ansible/
│
├── jenkins/
│
├── monitoring/
│
├── docs/
│
├── .env.example
│
└── README.md
```

---

# Database Design

## Users

```sql
id
name
email
role
created_at
```

## Tickets

```sql
id
ticket_number
title
description
priority
status
created_by
created_at
updated_at
```

## Comments

```sql
id
ticket_id
comment
created_at
```

---

# Sample Incidents

```text
INC0001 - VPN Not Connecting

INC0002 - Outlook Not Syncing

INC0003 - Laptop Unable to Connect to WiFi

INC0004 - Production Application Unavailable

INC0005 - Microsoft Teams Audio Issue
```

---

# Running the Application

## Clone Repository

```bash
git clone <repository-url>

cd BGCV-ServiceHub
```

---

## Create Environment File

```bash
cp .env.example .env
```

Update:

```env
POSTGRES_DB=bgcv_servicehub
POSTGRES_USER=bgcv
POSTGRES_PASSWORD=StrongPassword123
```

---

## Build and Start Containers

```bash
docker compose up --build
```

---

## Verify Running Containers

```bash
docker ps
```

Expected:

```text
frontend
backend
postgres
```

---

# Access Application

## Frontend

```text
http://localhost:3000
```

## Backend API

```text
http://localhost:5000/api
```

## Health Endpoint

```text
http://localhost:5000/api/health
```

## Readiness Endpoint

```text
http://localhost:5000/api/health/ready
```

---

# Container Details

## Frontend Container

Responsibilities:

- User Interface
- Dashboard Views
- Incident Management Screens
- API Communication

## Backend Container

Responsibilities:

- REST APIs
- Business Logic
- Input Validation
- Database Interaction

## PostgreSQL Container

Responsibilities:

- Persistent Storage
- Ticket Management Data
- User Data
- Comments Data

---

# Docker Compose Workflow

```text
docker compose up --build
            │
            ▼
Frontend Container
            │
            ▼
Backend Container
            │
            ▼
PostgreSQL Container
```

---

# DevOps Learning Outcomes

This project demonstrates:

✅ 3-Tier Architecture

✅ REST API Design

✅ Containerization with Docker

✅ Multi-Container Deployment using Docker Compose

✅ Environment Variable Management

✅ Database Integration

✅ Service-to-Service Communication

✅ Health Checks

✅ Persistent Storage

✅ Enterprise Project Structure

---

# Future Roadmap

## Container Registry

- Docker Hub
- Amazon ECR

## Kubernetes

- Deployments
- Services
- Ingress
- ConfigMaps
- Secrets

## AWS

- EKS
- RDS PostgreSQL
- ALB Ingress Controller

## Infrastructure as Code

- Terraform
- VPC
- Subnets
- Security Groups
- IAM Roles

## CI/CD

- Jenkins
- GitHub Actions

## Monitoring

- Prometheus
- Grafana
- AWS CloudWatch

---

# Screenshots

Add screenshots after deployment:

- Dashboard
- Incident List Page
- Create Incident Page
- Incident Details Page
- Docker Containers
- Kubernetes Deployment
- Grafana Dashboard

---

# Resume Description

Built and deployed a production-style 3-tier Service Desk application using React, Flask, and PostgreSQL. Containerized services using Docker and orchestrated deployment with Docker Compose. Implemented REST APIs, persistent database storage, service-to-service communication, and environment-based configuration. Designed the project as a foundation for Kubernetes, AWS EKS, Terraform, Jenkins CI/CD, and Prometheus-Grafana monitoring.

---

# Author

**Bharathi Ganesh Sankarapandi**

Cloud Support Engineer | Aspiring DevOps Engineer

Skills:

- Linux
- AWS
- Git
- Docker
- Docker Compose
- Kubernetes
- Terraform
- Jenkins
- Prometheus
- Grafana
- Python

---
