# BGCV ServiceHub - ECR and EKS Fargate Deployment Progress

## Session Summary

This document records the work completed while moving the BGCV ServiceHub three-tier application from local Docker Compose deployment to Amazon ECR and Amazon EKS Fargate.

> Security note: passwords, AWS account details, database secrets, and private endpoints are intentionally excluded from this document. Never commit real credentials to GitHub.

---

## Application Architecture

```text
Browser
   |
   v
React Frontend
   |
   v
Flask Backend API
   |
   v
PostgreSQL Database
```

Target AWS architecture:

```text
Internet
   |
   v
AWS Application Load Balancer
   |
   v
Kubernetes Ingress
   |
   +--> Frontend Service --> Frontend Pods on EKS Fargate
   |
   +--> Backend Service  --> Backend Pods on EKS Fargate
                                |
                                v
                         PostgreSQL Database
```

---

## Work Completed Successfully

### 1. Local Three-Tier Application

The complete application was tested locally using Docker Compose.

Services:

- React frontend
- Flask backend
- PostgreSQL database

Validated locally:

- Dashboard loaded successfully
- Frontend communicated with the backend API
- Incidents could be created and viewed
- PostgreSQL stored application data
- Docker Compose successfully started all three services

### 2. Docker Images

Two separate Docker images were created:

```text
bgcv-frontend:v1
bgcv-backend:v1
```

The frontend and backend were kept as separate images because they have different runtimes and can be built, versioned, deployed, and scaled independently.

### 3. Amazon ECR

Two private ECR repositories were created:

```text
bgcv-frontend
bgcv-backend
```

The frontend and backend images were tagged and pushed to ECR with the `v1` tag.

Validated:

- AWS CLI authentication worked
- Docker authenticated to ECR
- Both images were uploaded successfully
- EKS Fargate successfully pulled the backend and frontend images

### 4. Amazon EKS Fargate

An EKS cluster and Fargate profile were created.

The Fargate profile selected the following namespace:

```text
bgcv-servicehub
```

Validated:

- `kubectl` connected to the EKS cluster
- Pods were scheduled on Fargate
- ECR images were successfully pulled
- Frontend containers started successfully
- Backend container started successfully

### 5. Kubernetes Resources

The following resources were created through YAML manifests:

```text
Namespace
ConfigMap
Secret
Backend Deployment
Backend Service
Frontend Deployment
Frontend Service
```

Kubernetes deployment order used:

```text
namespace.yaml
      |
      v
config.yaml
      |
      v
app.yaml
```

---

## Kubernetes File Connections

### `namespace.yaml`

Creates the isolated Kubernetes namespace:

```text
bgcv-servicehub
```

All application resources are deployed inside this namespace.

### `config.yaml`

Creates:

- `bgcv-config` ConfigMap for non-sensitive configuration
- `bgcv-secrets` Secret for sensitive database configuration

The backend Deployment references both resources through `envFrom`.

### `app.yaml`

Creates:

- Backend Deployment
- Backend ClusterIP Service
- Frontend Deployment
- Frontend ClusterIP Service

Connections:

```text
Backend Deployment
   |
   +--> bgcv-config
   |
   +--> bgcv-secrets
   |
   +--> Backend ECR image

Frontend Deployment
   |
   +--> Frontend ECR image

Frontend Service --> Frontend Pods
Backend Service  --> Backend Pods
```

---

## Troubleshooting Performed

### Issue 1: Database password broke the connection string

Error:

```text
could not translate host name "...@postgres" to address
```

Cause:

A special character in the database password changed how the database URL was parsed.

Resolution:

- Used a test password without URL-sensitive characters
- Recreated the local Docker Compose environment

Long-term improvement:

- URL-encode database credentials before placing them in a connection URI
- Store production secrets in a managed secret system

### Issue 2: ConfigMap not found

Error:

```text
configmap "bgcv-config" not found
```

Cause:

The Deployment was applied before its required ConfigMap existed in the namespace.

Resolution:

Applied resources in the correct order:

```bash
kubectl apply -f namespace.yaml
kubectl apply -f config.yaml
kubectl apply -f app.yaml
```

### Issue 3: Frontend image pull failure

Status:

```text
ImagePullBackOff
```

Cause:

The frontend image URI did not include the expected `v1` tag.

Resolution:

Updated the frontend Deployment to use the complete ECR image URI with `:v1`.

### Issue 4: Invalid Deployment YAML indentation

Cause:

`containers` was incorrectly placed under `metadata` instead of under the Pod template `spec`.

Correct structure:

```yaml
spec:
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
        - name: backend
```

Resolution:

Corrected the structure of both frontend and backend Deployments.

### Issue 5: Non-root user validation failure

Error:

```text
container has runAsNonRoot and image has non-numeric user
```

Cause:

The image used a named user such as `appuser`, while the Kubernetes security context required Kubernetes to verify a numeric non-root UID.

Temporary resolution:

Removed the conflicting Pod-level `runAsNonRoot` setting so the existing image could start.

Recommended permanent fix:

- Keep the non-root user in the image
- Use a numeric UID such as `10001`
- Configure the container security context with the matching numeric UID
- Rebuild and push a new immutable image tag

### Issue 6: Backend readiness probe returned HTTP 503

Observed state:

```text
Backend container: Started
Gunicorn: Listening on port 5000
Readiness probe: HTTP 503
```

Cause:

The readiness endpoint validates database connectivity. The configured database host did not point to a working PostgreSQL server.

Current result:

- Backend image pull succeeded
- Backend container started
- Flask/Gunicorn started
- Backend was not Ready because PostgreSQL was unavailable

Required fix:

Create a PostgreSQL database reachable from the Fargate Pods and update `DATABASE_URL` with the real database username, password, private host, port, and database name.

### Issue 7: `curl` not available inside backend container

Error:

```text
exec: "curl": executable file not found in $PATH
```

Cause:

The minimal backend image does not contain the `curl` utility.

Alternative test methods:

- Use `kubectl port-forward` and run `curl` from the EC2 administration host
- Use a temporary diagnostic Pod containing network tools
- Keep the application image minimal rather than installing debugging utilities in production

### Informational warning: Fargate logging ConfigMap missing

Warning:

```text
LoggingDisabled: aws-logging configmap was not found
```

This did not prevent the Pods from being scheduled or the containers from starting. Fargate logging can be configured separately when CloudWatch logging is implemented.

---

## Last Confirmed Workload State

Confirmed successful:

```text
Frontend replicas: Running and Ready
Backend container: Running
Backend image: Pulled successfully from ECR
Backend readiness: Failing because database is unavailable
```

The EKS cluster deletion was discussed for cost control. Confirm the current AWS state before resuming:

```bash
eksctl get cluster --region us-east-1
aws eks list-clusters --region us-east-1
```

---

## Database Decision

For the lab environment, PostgreSQL was planned on the existing EC2 administration instance to reduce additional service cost.

Lab design:

```text
EKS Fargate Backend
        |
        v
PostgreSQL on existing EC2 private IP
```

Production recommendation:

```text
EKS Fargate Backend
        |
        v
Amazon RDS for PostgreSQL
```

The database security group should permit TCP port `5432` only from the required application network or security group. Do not expose PostgreSQL to the public internet.

---

## Secure Database URL Format

Use this pattern only after PostgreSQL is ready:

```text
postgresql+psycopg2://<DB_USER>:<URL_ENCODED_PASSWORD>@<PRIVATE_DB_HOST>:5432/<DB_NAME>
```

Example placeholder:

```text
postgresql+psycopg2://bgcv:<PASSWORD>@<EC2_PRIVATE_IP>:5432/bgcv_servicehub
```

Do not commit the real value to GitHub.

---

## Next Implementation Steps

1. Confirm whether the previous EKS cluster still exists.
2. If required, recreate the EKS cluster and Fargate profile.
3. Install and configure PostgreSQL on the selected EC2 instance.
4. Create the `bgcv` database user and `bgcv_servicehub` database.
5. Apply `database/schema.sql` and `database/seed.sql` to PostgreSQL.
6. Restrict PostgreSQL access using the EC2 security group and `pg_hba.conf`.
7. Create the Kubernetes Secret directly from the CLI or an external secret manager.
8. Apply the Namespace, ConfigMap/Secret, and application manifests.
9. Confirm both frontend and backend Deployments are Ready.
10. Install AWS Load Balancer Controller.
11. Apply ALB Ingress with IP target mode for Fargate.
12. Test the complete incident workflow through the ALB endpoint.
13. Add CloudWatch/Fargate logging and monitoring.

---

## Useful Validation Commands

```bash
kubectl get namespaces
kubectl get all -n bgcv-servicehub
kubectl get pods -n bgcv-servicehub
kubectl get services -n bgcv-servicehub
kubectl get configmap -n bgcv-servicehub
kubectl get secret -n bgcv-servicehub
```

```bash
kubectl describe pod <POD_NAME> -n bgcv-servicehub
kubectl logs <POD_NAME> -n bgcv-servicehub
kubectl rollout status deployment/backend -n bgcv-servicehub
kubectl rollout status deployment/frontend -n bgcv-servicehub
```

```bash
kubectl port-forward service/backend 5000:5000 -n bgcv-servicehub
curl http://localhost:5000/api/health/live
curl http://localhost:5000/api/health/ready
```

---

## Recommended Repository Documentation Structure

```text
```

---

## Git Commands

From the project root:

```bash
mkdir -p docs/deployment
cp /path/to/EKS_FARGATE_DEPLOYMENT_PROGRESS.md docs/deployment/

git add docs/deployment/EKS_FARGATE_DEPLOYMENT_PROGRESS.md
git commit -m "docs: add ECR and EKS Fargate deployment progress"
git push origin main
```

---

## Key Learning Outcomes

- Docker Compose provides simple service discovery on one local Docker network.
- EKS requires explicit Deployments, Services, configuration, secrets, scheduling, and health checks.
- ECR stores container images; EKS Fargate pulls and runs those images.
- ConfigMaps and Secrets must exist in the same namespace before dependent Pods can start.
- Kubernetes Services connect stable names to changing Pods through labels and selectors.
- Liveness proves that the process is alive; readiness proves that the application can serve traffic.
- A backend may be running but not Ready when a required dependency such as PostgreSQL is unavailable.
- Databases require additional persistence, identity, network access, schema initialization, and security controls.
