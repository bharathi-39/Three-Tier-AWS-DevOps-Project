# BGCV ServiceHub - 3 Tier Application

BGCV ServiceHub is a production-style 3-tier web application developed to demonstrate end-to-end application deployment and DevOps practices.

The project follows a standard enterprise architecture consisting of a frontend, backend, and database layer, all containerized using Docker and orchestrated using Docker Compose.

---

## Architecture

```text
Frontend (React)
       ↓
Backend (Flask REST API)
       ↓
Database (PostgreSQL)
```

---

## Project Components

### Frontend

- React.js
- User Interface
- Dashboard
- Incident Management Screens

### Backend

- Python Flask
- REST APIs
- Business Logic
- Database Connectivity

### Database

- PostgreSQL
- Incident Records
- User Data
- Comments Data

---

## Technology Stack

- React.js
- Python Flask
- PostgreSQL
- Docker
- Docker Compose
- Git
- GitHub

---

## Deployment Architecture

```text
Docker Compose
       │
       ├── Frontend Container
       ├── Backend Container
       └── PostgreSQL Container
```

---

## Features

- Create Incidents
- View Incidents
- Update Incidents
- Delete Incidents
- Add Comments
- Dashboard Statistics
- REST APIs
- Persistent Data Storage

---

## Run Application

```bash
cp .env.example .env

docker compose up --build
```

Access:

```text
Frontend : http://localhost:3000

Backend  : http://localhost:5000/api
```

---

## DevOps Concepts Demonstrated

- 3-Tier Architecture
- Docker Containerization
- Docker Compose Orchestration
- Environment Variable Management
- Service-to-Service Communication
- Database Integration
- Health Checks
- Application Deployment

---

## Future Enhancements

- Kubernetes
- AWS EKS
- Amazon ECR
- Terraform
- Jenkins CI/CD
- Prometheus
- Grafana
- AWS CloudWatch

---

## Learning Outcome

This project demonstrates how a modern 3-tier application can be developed, containerized, deployed, and managed using industry-standard DevOps tools and practices.

