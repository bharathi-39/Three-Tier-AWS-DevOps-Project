# BGCV ServiceHub - ECR to EKS Fargate Deployment Runbook

## Purpose

This runbook documents the correct deployment order, required commands, YAML relationships, validation checks, and troubleshooting actions for running the BGCV ServiceHub frontend and backend on Amazon EKS Fargate using images stored in Amazon ECR.

> Never commit AWS credentials, database passwords, private keys, real Kubernetes Secrets, or sensitive endpoints to GitHub.

---

## 1. Target Architecture

```text
GitHub Source Code
        |
        v
Docker Build
        |
        v
Amazon ECR
        |
        v
Amazon EKS Fargate
        |
        +--> Frontend Deployment --> Frontend Service
        |
        +--> Backend Deployment  --> Backend Service
                                      |
                                      v
                               PostgreSQL Database

Internet --> ALB Ingress --> Frontend Service
```

---

## 2. Required Tools

Check each tool before deployment:

```bash
aws --version
docker --version
kubectl version --client
eksctl version
```

Confirm AWS authentication:

```bash
aws sts get-caller-identity
```

Confirm the configured region:

```bash
aws configure get region
```

Set reusable shell variables:

```bash
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export CLUSTER_NAME=bgcv-cluster
export NAMESPACE=bgcv-servicehub
```

Validate:

```bash
echo "$AWS_REGION"
echo "$AWS_ACCOUNT_ID"
echo "$CLUSTER_NAME"
echo "$NAMESPACE"
```

---

## 3. Required Repository Structure

```text
service-desk-portal/
├── frontend/
│   └── Dockerfile
├── backend/
│   └── Dockerfile
├── database/
│   ├── schema.sql
│   └── seed.sql
├── kubernetes/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── app.yaml
│   └── ingress.yaml
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 4. Local Validation Before AWS

Start the local application:

```bash
cp .env.example .env
docker compose up --build -d
```

Check services:

```bash
docker compose ps
docker compose logs backend --tail=100
docker compose logs frontend --tail=100
docker compose logs postgres --tail=100
```

Test:

```bash
curl http://localhost:5000/api/health/live
curl http://localhost:5000/api/health/ready
curl -I http://localhost:3000
```

Stop locally:

```bash
docker compose down
```

Reset local database only when necessary:

```bash
docker compose down -v
```

---

## 5. Create ECR Repositories

Create repositories once:

```bash
aws ecr create-repository \
  --repository-name bgcv-frontend \
  --region "$AWS_REGION"

aws ecr create-repository \
  --repository-name bgcv-backend \
  --region "$AWS_REGION"
```

Verify:

```bash
aws ecr describe-repositories --region "$AWS_REGION"
```

Authenticate Docker to ECR:

```bash
aws ecr get-login-password --region "$AWS_REGION" | \
  docker login \
  --username AWS \
  --password-stdin \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
```

Expected result:

```text
Login Succeeded
```

The ECR Docker username is always the literal value `AWS`. The password is generated and passed automatically by AWS CLI.

---

## 6. Build, Tag, and Push Images

Run from the project root.

Build:

```bash
docker build --platform linux/amd64 -t bgcv-frontend:v1 ./frontend
docker build --platform linux/amd64 -t bgcv-backend:v1 ./backend
```

Verify local images:

```bash
docker images | grep bgcv
```

Tag:

```bash
docker tag bgcv-frontend:v1 \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/bgcv-frontend:v1"

docker tag bgcv-backend:v1 \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/bgcv-backend:v1"
```

Push:

```bash
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/bgcv-frontend:v1"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/bgcv-backend:v1"
```

Verify ECR images:

```bash
aws ecr describe-images \
  --repository-name bgcv-frontend \
  --region "$AWS_REGION"

aws ecr describe-images \
  --repository-name bgcv-backend \
  --region "$AWS_REGION"
```

---

## 7. EKS Fargate Cluster

Create a Fargate-enabled cluster when required:

```bash
eksctl create cluster \
  --name "$CLUSTER_NAME" \
  --region "$AWS_REGION" \
  --fargate
```

Update kubeconfig:

```bash
aws eks update-kubeconfig \
  --name "$CLUSTER_NAME" \
  --region "$AWS_REGION"
```

Verify:

```bash
kubectl cluster-info
kubectl get namespaces
eksctl get cluster --region "$AWS_REGION"
```

Create a Fargate profile for the application namespace if one does not exist:

```bash
eksctl create fargateprofile \
  --cluster "$CLUSTER_NAME" \
  --region "$AWS_REGION" \
  --name bgcv-profile \
  --namespace "$NAMESPACE"
```

Verify:

```bash
eksctl get fargateprofile \
  --cluster "$CLUSTER_NAME" \
  --region "$AWS_REGION"
```

The profile namespace must match `bgcv-servicehub`. Otherwise, application Pods can remain Pending.

---

## 8. Kubernetes YAML Relationship and Correct Order

```text
namespace.yaml
      |
      v
configmap.yaml
      |
      v
app.yaml
      |
      v
ingress.yaml
```

### Relationship

```text
Namespace
  ├── ConfigMap: bgcv-config
  ├── Secret: bgcv-secrets
  ├── Backend Deployment
  │     ├── reads bgcv-config
  │     ├── reads bgcv-secrets
  │     └── uses backend ECR image
  ├── Backend Service
  │     └── selects Pods with label app=backend
  ├── Frontend Deployment
  │     └── uses frontend ECR image
  ├── Frontend Service
  │     └── selects Pods with label app=frontend
  └── Ingress
        └── routes ALB traffic to Services
```

---

## 9. Namespace YAML

File: `kubernetes/namespace.yaml`

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: bgcv-servicehub
```

Apply and verify:

```bash
kubectl apply -f kubernetes/namespace.yaml
kubectl get namespace bgcv-servicehub
```

---

## 10. ConfigMap and Secret

Do not store a real Secret value in a Git-tracked YAML file.

File: `kubernetes/configmap.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: bgcv-config
  namespace: bgcv-servicehub
data:
  POSTGRES_DB: bgcv_servicehub
  POSTGRES_USER: bgcv
  CORS_ORIGINS: "*"
```

Apply:

```bash
kubectl apply -f kubernetes/configmap.yaml
```

Create the Secret from the CLI after the real database is available:

```bash
read -s DB_PASSWORD
printf '\n'

kubectl create secret generic bgcv-secrets \
  --namespace bgcv-servicehub \
  --from-literal=POSTGRES_PASSWORD="$DB_PASSWORD" \
  --from-literal=DATABASE_URL="postgresql+psycopg2://bgcv:${DB_PASSWORD}@<PRIVATE_DB_HOST>:5432/bgcv_servicehub" \
  --dry-run=client -o yaml | kubectl apply -f -

unset DB_PASSWORD
```

If the password contains URL-sensitive characters, URL-encode the password before constructing `DATABASE_URL`.

Verify resource names only:

```bash
kubectl get configmap -n bgcv-servicehub
kubectl get secret -n bgcv-servicehub
```

Never print decoded production secrets in terminal recordings or GitHub documentation.

---

## 11. Application YAML Alignment

File: `kubernetes/app.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: bgcv-servicehub
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
        - name: backend
          image: <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/bgcv-backend:v1
          ports:
            - containerPort: 5000
          envFrom:
            - configMapRef:
                name: bgcv-config
            - secretRef:
                name: bgcv-secrets
          readinessProbe:
            httpGet:
              path: /api/health/ready
              port: 5000
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /api/health/live
              port: 5000
            initialDelaySeconds: 15
            periodSeconds: 20
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: bgcv-servicehub
spec:
  selector:
    app: backend
  ports:
    - port: 5000
      targetPort: 5000
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: bgcv-servicehub
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
        - name: frontend
          image: <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/bgcv-frontend:v1
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              cpu: 250m
              memory: 256Mi
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: bgcv-servicehub
spec:
  selector:
    app: frontend
  ports:
    - port: 80
      targetPort: 8080
```

Replace `<AWS_ACCOUNT_ID>` and `<AWS_REGION>` before applying.

### Alignment checklist

- `metadata.namespace` must be `bgcv-servicehub`.
- Deployment selector must match Pod template labels.
- Service selector must match Pod labels.
- `containers` must be under `template.spec`, not `template.metadata`.
- Frontend image URI must include the existing tag, such as `:v1`.
- Backend service `targetPort` must match container port `5000`.
- Frontend service `targetPort` must match container port `8080`.
- ConfigMap and Secret names must exactly match `envFrom` references.
- YAML consistently uses spaces, not tabs.

Validate locally before applying:

```bash
kubectl apply --dry-run=client -f kubernetes/app.yaml
```

Apply:

```bash
kubectl apply -f kubernetes/app.yaml
```

---

## 12. Deployment Verification Order

Run checks in this order:

```bash
kubectl get namespace bgcv-servicehub
kubectl get configmap -n bgcv-servicehub
kubectl get secret -n bgcv-servicehub
kubectl get deployments -n bgcv-servicehub
kubectl get replicasets -n bgcv-servicehub
kubectl get pods -n bgcv-servicehub
kubectl get services -n bgcv-servicehub
kubectl get endpoints -n bgcv-servicehub
```

Watch Pods:

```bash
kubectl get pods -n bgcv-servicehub -w
```

Check rollout:

```bash
kubectl rollout status deployment/backend -n bgcv-servicehub
kubectl rollout status deployment/frontend -n bgcv-servicehub
```

Expected final state:

```text
backend    2/2 Ready
frontend   2/2 Ready
```

---

## 13. Health Testing

Port-forward backend from the administration EC2 instance:

```bash
kubectl port-forward service/backend 5000:5000 -n bgcv-servicehub
```

Keep that command running. From a second SSH session:

```bash
curl http://localhost:5000/api/health/live
curl http://localhost:5000/api/health/ready
```

Port-forward frontend:

```bash
kubectl port-forward service/frontend 3000:80 -n bgcv-servicehub
```

From the EC2 instance:

```bash
curl -I http://localhost:3000
```

When operating from a remote EC2 instance, `localhost` refers to the EC2 instance, not the personal laptop. Browser access requires SSH tunneling, an external load balancer, or another approved exposure method.

---

## 14. Troubleshooting Decision Guide

### Pod is `Pending`

Run:

```bash
kubectl describe pod <POD_NAME> -n bgcv-servicehub
```

Check the Events section for:

- Fargate profile namespace mismatch
- Scheduling failure
- Unsupported volume configuration
- Resource sizing problem

Verify:

```bash
eksctl get fargateprofile \
  --cluster "$CLUSTER_NAME" \
  --region "$AWS_REGION"
```

### `ImagePullBackOff` or `ErrImagePull`

Run:

```bash
kubectl describe pod <POD_NAME> -n bgcv-servicehub
```

Check:

```bash
aws ecr describe-images \
  --repository-name bgcv-frontend \
  --region "$AWS_REGION"

aws ecr describe-images \
  --repository-name bgcv-backend \
  --region "$AWS_REGION"
```

Validate:

- Correct AWS account ID
- Correct ECR region
- Correct repository name
- Correct image tag
- Fargate Pod execution role has ECR pull access

### `CreateContainerConfigError`

Run:

```bash
kubectl describe pod <POD_NAME> -n bgcv-servicehub
kubectl get configmap -n bgcv-servicehub
kubectl get secret -n bgcv-servicehub
```

Typical causes:

- Missing ConfigMap
- Missing Secret
- Wrong namespace
- Resource name mismatch
- Invalid security context

### Non-root image error

Error pattern:

```text
container has runAsNonRoot and image has non-numeric user
```

Temporary action:

- Remove the conflicting `runAsNonRoot` setting from the Pod manifest.

Permanent action:

- Use a numeric non-root UID in the Docker image.
- Set `USER 10001` in the Dockerfile.
- Rebuild with a new tag.
- Push the new image to ECR.
- Update the Deployment image.

### `CrashLoopBackOff`

Run:

```bash
kubectl logs <POD_NAME> -n bgcv-servicehub
kubectl logs <POD_NAME> -n bgcv-servicehub --previous
kubectl describe pod <POD_NAME> -n bgcv-servicehub
```

Check:

- Startup command
- Missing dependency
- Invalid environment variable
- Database connection failure
- Port mismatch

### Pod is `Running` but `0/1 Ready`

Run:

```bash
kubectl describe pod <POD_NAME> -n bgcv-servicehub
kubectl logs <POD_NAME> -n bgcv-servicehub
```

If readiness returns HTTP `503`, verify the dependency checked by `/api/health/ready`. In BGCV ServiceHub, this endpoint checks database connectivity.

Check service endpoints:

```bash
kubectl get endpoints backend -n bgcv-servicehub
```

A backend Pod that is not Ready is normally excluded from the Service endpoints.

### `curl` missing inside the container

Do not modify the production image only for basic debugging. Use port-forward or a diagnostic Pod:

```bash
kubectl run network-debug \
  --rm -it \
  --restart=Never \
  --namespace bgcv-servicehub \
  --image=curlimages/curl \
  -- sh
```

Inside the diagnostic Pod:

```sh
curl http://backend:5000/api/health/live
curl http://backend:5000/api/health/ready
```

### ConfigMap or Secret changed but Pod still uses old values

Environment variables are loaded when the container starts. Restart the Deployment:

```bash
kubectl rollout restart deployment/backend -n bgcv-servicehub
kubectl rollout status deployment/backend -n bgcv-servicehub
```

### `kubectl get pods` shows no resources

The command defaults to the `default` namespace. Use:

```bash
kubectl get pods -n bgcv-servicehub
```

Or set the current namespace:

```bash
kubectl config set-context --current --namespace=bgcv-servicehub
```

### Fargate logging warning

Warning pattern:

```text
aws-logging configmap was not found
```

This warning does not by itself prove that the application failed. Check the container status and other Pod Events. Configure Fargate logging separately when CloudWatch logging is added.

---

## 15. PostgreSQL on EC2 Checklist

For a cost-conscious lab, PostgreSQL may run on the existing EC2 administration instance. This is not the recommended production design.

Install:

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib -y
sudo systemctl enable --now postgresql
sudo systemctl status postgresql
```

Create database and user interactively:

```bash
sudo -u postgres psql
```

Inside PostgreSQL, replace the password placeholder:

```sql
CREATE USER bgcv WITH PASSWORD '<STRONG_PASSWORD>';
CREATE DATABASE bgcv_servicehub OWNER bgcv;
GRANT ALL PRIVILEGES ON DATABASE bgcv_servicehub TO bgcv;
\q
```

Find the active configuration files:

```bash
sudo -u postgres psql -tAc "SHOW config_file;"
sudo -u postgres psql -tAc "SHOW hba_file;"
```

Set PostgreSQL to listen on the EC2 network interface in `postgresql.conf`:

```text
listen_addresses = '*'
```

Restrict `pg_hba.conf` to the actual private CIDR used by the EKS/Fargate Pods. Example placeholder:

```text
host    bgcv_servicehub    bgcv    <VPC_PRIVATE_CIDR>    scram-sha-256
```

Restart and verify:

```bash
sudo systemctl restart postgresql
sudo systemctl status postgresql
sudo ss -lntp | grep 5432
```

Load schema and seed data:

```bash
PGPASSWORD='<STRONG_PASSWORD>' psql \
  -h 127.0.0.1 \
  -U bgcv \
  -d bgcv_servicehub \
  -f database/schema.sql

PGPASSWORD='<STRONG_PASSWORD>' psql \
  -h 127.0.0.1 \
  -U bgcv \
  -d bgcv_servicehub \
  -f database/seed.sql
```

Security-group requirement:

```text
Protocol: TCP
Port: 5432
Source: only the required EKS/Fargate application network or approved security group
```

Do not use `0.0.0.0/0` for PostgreSQL.

Test locally on EC2:

```bash
psql -h 127.0.0.1 -U bgcv -d bgcv_servicehub
```

Test from a temporary Kubernetes Pod after network access is configured:

```bash
kubectl run pg-debug \
  --rm -it \
  --restart=Never \
  --namespace bgcv-servicehub \
  --image=postgres:16-alpine \
  --env="PGPASSWORD=<STRONG_PASSWORD>" \
  -- psql -h <EC2_PRIVATE_IP> -U bgcv -d bgcv_servicehub -c "SELECT 1;"
```

After successful connectivity, update the Kubernetes Secret and restart the backend.

---

## 16. Safe Redeployment Sequence

```bash
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/configmap.yaml
```

Create or update the Secret securely, then:

```bash
kubectl apply --dry-run=client -f kubernetes/app.yaml
kubectl apply -f kubernetes/app.yaml
kubectl rollout status deployment/backend -n bgcv-servicehub
kubectl rollout status deployment/frontend -n bgcv-servicehub
kubectl get all -n bgcv-servicehub
```

Do not apply Ingress until frontend and backend Pods are healthy and their Services have endpoints.

---

## 17. Cleanup and Cost Control

Delete only application resources:

```bash
kubectl delete namespace bgcv-servicehub
```

Delete the whole cluster:

```bash
eksctl delete cluster \
  --name "$CLUSTER_NAME" \
  --region "$AWS_REGION"
```

Verify:

```bash
aws eks list-clusters --region "$AWS_REGION"
```

ECR repositories are not automatically removed with the EKS cluster.

List ECR repositories:

```bash
aws ecr describe-repositories --region "$AWS_REGION"
```

Delete an ECR repository only when the images are no longer required:

```bash
aws ecr delete-repository \
  --repository-name bgcv-frontend \
  --force \
  --region "$AWS_REGION"
```

Check separately for other chargeable resources such as ALBs, target groups, NAT Gateways, Elastic IPs, EC2 instances, and storage volumes.

---

## 18. Recommended Git Documentation Structure

```text
docs/
├── deployment/
│   ├── EKS_FARGATE_DEPLOYMENT_PROGRESS.md
│   └── EKS_FARGATE_COMMANDS_AND_TROUBLESHOOTING.md
└── troubleshooting/
    └── README.md
```

Add this runbook:

```bash
mkdir -p docs/deployment
cp EKS_FARGATE_COMMANDS_AND_TROUBLESHOOTING.md docs/deployment/

git add docs/deployment/EKS_FARGATE_COMMANDS_AND_TROUBLESHOOTING.md
git commit -m "docs: add EKS Fargate deployment runbook"
git push origin main
```

---

## 19. Quick Command Checklist

```bash
# AWS identity
aws sts get-caller-identity

# ECR
aws ecr describe-images --repository-name bgcv-frontend --region "$AWS_REGION"
aws ecr describe-images --repository-name bgcv-backend --region "$AWS_REGION"

# Cluster
kubectl cluster-info
eksctl get fargateprofile --cluster "$CLUSTER_NAME" --region "$AWS_REGION"

# Apply in order
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/app.yaml

# Validate
kubectl get all -n bgcv-servicehub
kubectl get endpoints -n bgcv-servicehub
kubectl describe pod <POD_NAME> -n bgcv-servicehub
kubectl logs <POD_NAME> -n bgcv-servicehub

# Restart after configuration changes
kubectl rollout restart deployment/backend -n bgcv-servicehub
kubectl rollout status deployment/backend -n bgcv-servicehub

# Cleanup
kubectl delete namespace bgcv-servicehub
```

---

## 20. Success Criteria

The deployment is ready for ALB Ingress only when all of the following are true:

```text
[ ] Frontend image exists in ECR
[ ] Backend image exists in ECR
[ ] Fargate profile selects bgcv-servicehub
[ ] ConfigMap exists
[ ] Secret exists
[ ] Frontend Pods are Ready
[ ] Backend Pods are Ready
[ ] Frontend Service has endpoints
[ ] Backend Service has endpoints
[ ] Liveness endpoint returns success
[ ] Readiness endpoint returns success
[ ] Database schema and seed data are loaded
[ ] No credentials are committed to GitHub
```
