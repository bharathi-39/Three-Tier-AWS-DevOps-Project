# BGCV ServiceHub - EKS Fargate Implementation and Troubleshooting Record

## Purpose

This document records the implementation completed for BGCV ServiceHub up to the current checkpoint, including deployment order, component relationships, verification commands, issues encountered, root causes, and troubleshooting actions.

> All confidential values have been replaced with placeholders such as `xxx` and `yyy`. Never commit real passwords, private IP addresses, AWS account IDs, access keys, secret keys, or live Kubernetes Secrets to GitHub.

---

## 1. Current Architecture

```text
Developer / EC2 Administration Host
        |
        +--> AWS CLI
        +--> Docker
        +--> kubectl
        +--> eksctl
        +--> PostgreSQL Database

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
        +--> Frontend Deployment --> Frontend Pods
        |                             |
        |                             v
        |                        Frontend Service
        |
        +--> Backend Deployment --> Backend Pods
                                      |
                                      v
                                Backend Service
                                      |
                                      v
                         PostgreSQL on EC2 Private IP
```

### Application flow

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

---

## 2. Successful Milestones

The following work was completed successfully:

- Three-tier application ran locally using Docker Compose.
- React frontend, Flask backend, and PostgreSQL communicated locally.
- Frontend and backend Docker images were built separately.
- Two Amazon ECR repositories were created.
- Frontend and backend images were tagged and pushed to ECR.
- Amazon EKS cluster with Fargate support was created.
- A Fargate profile was created for the `bgcv-servicehub` namespace.
- Kubernetes Namespace, ConfigMap, Secret, Deployments, and Services were created.
- EKS Fargate successfully pulled both images from ECR.
- Frontend Pods reached `1/1 Running`.
- Backend containers started successfully using Gunicorn.
- PostgreSQL was installed on the EC2 administration host.
- PostgreSQL user, database, tables, and sample data were created.
- PostgreSQL was changed from localhost-only access to VPC network access.
- Backend Pods reached Running state after probe-related troubleshooting.
- Frontend responded through port-forward.
- Backend `/api/health/live` returned a successful response.

---

## 3. Required Repository Structure

```text
service-desk-portal/
├── frontend/
│   ├── Dockerfile
│   └── src/
├── backend/
│   ├── Dockerfile
│   └── app/
├── database/
│   ├── schema.sql
│   └── seed.sql
├── kubernetes/
│   ├── namespace.yaml
│   ├── config.yaml
│   ├── app.yaml
│   └── ingress.yaml
├── docs/
│   └── deployment/
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 4. Component Connections

### Namespace

```text
namespace.yaml
   |
   v
bgcv-servicehub namespace
```

Every Kubernetes application resource must use the same namespace.

### ConfigMap and Secret

```text
config.yaml
   |
   +--> ConfigMap: bgcv-config
   |
   +--> Secret: bgcv-secrets
```

The backend Deployment imports both resources using `envFrom`.

### Deployments and Services

```text
Backend Deployment
   |
   +--> ECR backend image
   +--> bgcv-config
   +--> bgcv-secrets
   +--> label: app=backend
                |
                v
         Backend Service selector

Frontend Deployment
   |
   +--> ECR frontend image
   +--> label: app=frontend
                |
                v
         Frontend Service selector
```

### Database connection

```text
Backend Pod
   |
   v
DATABASE_URL environment variable
   |
   v
EC2 private IP:5432
   |
   v
PostgreSQL database
```

The backend reads `DATABASE_URL` from its Kubernetes Secret. Its readiness endpoint executes a database query to verify connectivity.

---

## 5. Correct Deployment Order

Always use this order:

```text
1. AWS authentication
2. ECR repositories and images
3. EKS cluster
4. Fargate profile
5. PostgreSQL verification
6. Namespace
7. ConfigMap
8. Secret
9. Deployments and Services
10. Pod verification
11. Service testing
12. ALB Controller and Ingress
```

### Apply Kubernetes resources

```bash
kubectl apply -f namespace.yaml
kubectl apply -f config.yaml
kubectl apply --dry-run=client -f app.yaml
kubectl apply -f app.yaml
```

### Verify after each stage

```bash
kubectl get namespace bgcv-servicehub
kubectl get configmap -n bgcv-servicehub
kubectl get secret -n bgcv-servicehub
kubectl get deployments -n bgcv-servicehub
kubectl get pods -n bgcv-servicehub
kubectl get services -n bgcv-servicehub
kubectl get endpoints -n bgcv-servicehub
```

---

## 6. AWS and ECR Commands

### Configure and verify AWS CLI

```bash
aws configure
aws sts get-caller-identity
aws configure get region
```

Example reusable variables:

```bash
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=xxx
export CLUSTER_NAME=bgcv-cluster
export NAMESPACE=bgcv-servicehub
```

### ECR login

```bash
aws ecr get-login-password --region "$AWS_REGION" | \
  docker login \
  --username AWS \
  --password-stdin \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
```

The ECR username is always the literal value `AWS`. The password is generated by AWS CLI.

### Build images

```bash
docker build --platform linux/amd64 -t bgcv-frontend:v1 ./frontend
docker build --platform linux/amd64 -t bgcv-backend:v1 ./backend
```

### Tag images

```bash
docker tag bgcv-frontend:v1 \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/bgcv-frontend:v1"

docker tag bgcv-backend:v1 \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/bgcv-backend:v1"
```

### Push images

```bash
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/bgcv-frontend:v1"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/bgcv-backend:v1"
```

### Verify images

```bash
aws ecr describe-images \
  --repository-name bgcv-frontend \
  --region "$AWS_REGION"

aws ecr describe-images \
  --repository-name bgcv-backend \
  --region "$AWS_REGION"
```

---

## 7. EKS Fargate Commands

### Create cluster

```bash
eksctl create cluster \
  --name "$CLUSTER_NAME" \
  --region "$AWS_REGION" \
  --fargate
```

### Update kubeconfig

```bash
aws eks update-kubeconfig \
  --name "$CLUSTER_NAME" \
  --region "$AWS_REGION"
```

### Create application Fargate profile

```bash
eksctl create fargateprofile \
  --cluster "$CLUSTER_NAME" \
  --region "$AWS_REGION" \
  --name bgcv-profile \
  --namespace bgcv-servicehub
```

### Verify

```bash
kubectl cluster-info
kubectl get namespaces

eksctl get fargateprofile \
  --cluster "$CLUSTER_NAME" \
  --region "$AWS_REGION"
```

The Fargate profile selector must include the `bgcv-servicehub` namespace. Otherwise, the application Pods may remain Pending.

---

## 8. Sanitized ConfigMap and Secret Pattern

Do not commit a real password or database URL.

### Safe Git-tracked ConfigMap

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

`CORS_ORIGINS: "*"` is acceptable only for development testing. Restrict it to the final application origin before production use.

### Secret template for documentation only

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: bgcv-secrets
  namespace: bgcv-servicehub
type: Opaque
stringData:
  POSTGRES_PASSWORD: xxx
  DATABASE_URL: postgresql+psycopg2://bgcv:xxx@yyy:5432/bgcv_servicehub
```

Where:

```text
xxx = database password
yyy = PostgreSQL EC2 private IP or private DNS name
```

### Preferred Secret creation command

```bash
read -s DB_PASSWORD
printf '\n'

kubectl create secret generic bgcv-secrets \
  --namespace bgcv-servicehub \
  --from-literal=POSTGRES_PASSWORD="$DB_PASSWORD" \
  --from-literal=DATABASE_URL="postgresql+psycopg2://bgcv:${DB_PASSWORD}@yyy:5432/bgcv_servicehub" \
  --dry-run=client -o yaml | kubectl apply -f -

unset DB_PASSWORD
```

If the password contains URL-sensitive characters, URL-encode the password before inserting it into `DATABASE_URL`.

---

## 9. PostgreSQL on EC2

### Install PostgreSQL

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib -y
sudo systemctl enable --now postgresql
sudo systemctl status postgresql
```

### Create user and database

```bash
sudo -u postgres psql
```

```sql
CREATE USER bgcv WITH PASSWORD 'xxx';
CREATE DATABASE bgcv_servicehub OWNER bgcv;
GRANT ALL PRIVILEGES ON DATABASE bgcv_servicehub TO bgcv;
\q
```

If the role or database already exists, PostgreSQL returns an error stating that it already exists. Verify instead of recreating:

```bash
sudo -u postgres psql
```

```sql
\du
\l
\q
```

### Find active configuration files

```bash
sudo -u postgres psql -tAc "SHOW config_file;"
sudo -u postgres psql -tAc "SHOW hba_file;"
```

### Enable network listening

In `postgresql.conf`, change:

```text
#listen_addresses = 'localhost'
```

or:

```text
#listen_addresses = '*'
```

to:

```text
listen_addresses = '*'
```

The leading `#` must be removed because `#` means the setting is commented out.

### Permit the private network

In `pg_hba.conf`, use a narrow private CIDR appropriate for the VPC:

```text
host    bgcv_servicehub    bgcv    xxx.xxx.0.0/16    scram-sha-256
```

Do not use public access such as `0.0.0.0/0`.

### Restart and verify

```bash
sudo systemctl restart postgresql
sudo systemctl status postgresql
sudo ss -lntp | grep 5432
```

Expected:

```text
0.0.0.0:5432
```

A result showing only `127.0.0.1:5432` means EKS Fargate Pods cannot reach PostgreSQL.

### Verify database and tables

```bash
psql -h localhost -U bgcv -d bgcv_servicehub
```

```sql
\dt
```

Expected tables:

```text
users
tickets
comments
```

### Load schema and sample data when required

Run from the project root:

```bash
PGPASSWORD='xxx' psql \
  -h localhost \
  -U bgcv \
  -d bgcv_servicehub \
  -f database/schema.sql

PGPASSWORD='xxx' psql \
  -h localhost \
  -U bgcv \
  -d bgcv_servicehub \
  -f database/seed.sql
```

### EC2 security group

Allow PostgreSQL only from the required application network or approved security group:

```text
Protocol: TCP
Port: 5432
Source: private application network or approved security group
```

---

## 10. Kubernetes YAML Alignment Rules

Correct Deployment nesting:

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

Important checks:

- `containers` must be below `template.spec`.
- Deployment selectors must match Pod template labels.
- Service selectors must match Pod labels.
- Backend container port and Service target port must both be `5000`.
- Frontend container port and Service target port must both be `8080`.
- ECR image URI must include the correct repository and tag.
- ConfigMap and Secret names must exactly match `envFrom` references.
- All resources must use the same namespace.
- Use spaces, not tabs, in YAML.

Validate before applying:

```bash
kubectl apply --dry-run=client -f app.yaml
```

---

## 11. Issues Encountered and Fixes

### Issue 1: Password broke the local database URL

Symptom:

```text
could not translate host name "xxx@postgres" to address
```

Cause:

A URL-sensitive character in the password changed how the database URI was parsed.

Fix:

- Used a safe test password.
- Recreated the local environment.
- Recommended URL-encoding database credentials.

### Issue 2: ConfigMap not found

Symptom:

```text
CreateContainerConfigError
configmap "bgcv-config" not found
```

Cause:

The Deployment referenced a ConfigMap that did not exist in the namespace.

Fix:

```bash
kubectl apply -f namespace.yaml
kubectl apply -f config.yaml
kubectl apply -f app.yaml
```

### Issue 3: Frontend `ImagePullBackOff`

Cause:

The frontend image reference did not use the correct existing image tag.

Fix:

Updated the Deployment to use the complete ECR URI ending in `:v1`.

### Issue 4: Invalid YAML indentation

Cause:

`containers` was nested under `metadata` instead of `template.spec`.

Fix:

Corrected YAML nesting and validated with:

```bash
kubectl apply --dry-run=client -f app.yaml
```

### Issue 5: Non-root user validation failure

Symptom:

```text
container has runAsNonRoot and image has non-numeric user
```

Cause:

The image used a named user while Kubernetes was configured to verify a numeric non-root user.

Temporary fix:

Removed the conflicting Pod-level `runAsNonRoot` setting.

Permanent fix:

- Use a numeric UID such as `10001` in the Dockerfile.
- Rebuild the image using a new tag.
- Push the new image to ECR.
- Update the Deployment.

### Issue 6: Backend `0/1 Running` with readiness HTTP 503

Cause:

`/api/health/ready` checks database connectivity. PostgreSQL was unavailable or unreachable.

Fix:

- Installed PostgreSQL on EC2.
- Created the database and user.
- Loaded tables.
- Updated `DATABASE_URL`.
- Configured PostgreSQL to listen beyond localhost.

### Issue 7: PostgreSQL listened only on localhost

Symptom:

```text
127.0.0.1:5432
```

Cause:

`listen_addresses` was commented out, so PostgreSQL used the default localhost setting.

Fix:

```text
listen_addresses = '*'
```

After restart, verification showed:

```text
0.0.0.0:5432
```

### Issue 8: Probe timeouts and container restarts

Symptoms:

```text
Liveness probe failed: context deadline exceeded
Readiness probe failed: connection reset by peer
CrashLoopBackOff
```

Cause:

The probes repeatedly restarted the application while dependency troubleshooting was still in progress.

Temporary fix:

Removed the probes to confirm that frontend and backend containers could remain running.

Recommended final fix:

- Restore a lightweight liveness probe using `/api/health/live`.
- Keep database validation in readiness.
- Add a startup probe.
- Use suitable delay and timeout settings.
- Confirm database network connectivity before enabling strict readiness.

### Issue 9: `curl` missing in backend container

Cause:

The production image was minimal and did not include `curl`.

Fix:

Used port-forwarding from EC2 or a temporary debug Pod instead of expanding the production image.

### Issue 10: `kubectl get pods` showed no resources

Cause:

The command searched the `default` namespace.

Fix:

```bash
kubectl get pods -n bgcv-servicehub
```

### Issue 11: Fargate logging warning

Symptom:

```text
aws-logging configmap was not found
```

This warning did not prevent scheduling or container startup. CloudWatch/Fargate logging remains a later observability task.

---

## 12. Verification Commands

### Complete resource check

```bash
kubectl get all -n bgcv-servicehub
kubectl get endpoints -n bgcv-servicehub
```

### Pod status

```bash
kubectl get pods -n bgcv-servicehub -w
```

### Deployment rollout

```bash
kubectl rollout status deployment/backend -n bgcv-servicehub
kubectl rollout status deployment/frontend -n bgcv-servicehub
```

### Troubleshooting

```bash
kubectl describe pod <BACKEND_POD> -n bgcv-servicehub
kubectl logs <BACKEND_POD> -n bgcv-servicehub
kubectl logs <BACKEND_POD> -n bgcv-servicehub --previous
```

### Restart after Secret or ConfigMap change

```bash
kubectl rollout restart deployment/backend -n bgcv-servicehub
kubectl rollout status deployment/backend -n bgcv-servicehub
```

Environment variables from ConfigMaps and Secrets are loaded when a container starts, so existing Pods must be recreated after changes.

---

## 13. Service Testing

### Backend port-forward

```bash
kubectl port-forward service/backend 5000:5000 -n bgcv-servicehub
```

Run from a second EC2 SSH session:

```bash
curl http://localhost:5000/api/health/live
curl http://localhost:5000/api/health/ready
```

Confirmed result:

```text
/api/health/live returned success
```

The readiness endpoint still required further database-response investigation at the current checkpoint.

### Frontend port-forward

```bash
kubectl port-forward service/frontend 3000:80 -n bgcv-servicehub
```

Verify from EC2:

```bash
curl http://localhost:3000
```

Confirmed result:

```text
Frontend HTML and compiled assets were returned successfully.
```

When port-forwarding on a remote EC2 instance, `localhost` means the EC2 instance. Use an approved SSH tunnel or ALB for browser access from a personal computer.

---

## 14. Current Checkpoint

Confirmed:

```text
[✓] Local three-tier application worked through Docker Compose
[✓] Frontend image exists in ECR
[✓] Backend image exists in ECR
[✓] EKS Fargate cluster created
[✓] Fargate profile selected bgcv-servicehub
[✓] Namespace created
[✓] ConfigMap created
[✓] Secret created
[✓] Frontend Pods running
[✓] Backend Pods running after probe removal
[✓] PostgreSQL running on EC2
[✓] PostgreSQL listening on the private network
[✓] users, tickets, and comments tables exist
[✓] Frontend service responds through port-forward
[✓] Backend live endpoint responds through port-forward
[ ] Backend ready endpoint should return success consistently
[ ] Reintroduce production-style startup, liveness, and readiness probes
[ ] Install AWS Load Balancer Controller
[ ] Apply ALB Ingress
[ ] Test full ticket creation from the public application endpoint
```

---

## 15. Next Steps

1. Confirm backend-to-database connectivity from inside the cluster using a temporary diagnostic Pod.
2. Confirm `/api/health/ready` returns success consistently.
3. Reintroduce safe health probes.
4. Install AWS Load Balancer Controller.
5. Configure Ingress using ALB IP target mode for Fargate.
6. Obtain the ALB DNS name.
7. Restrict CORS to the real frontend origin.
8. Test dashboard, create incident, comments, status update, delete, and persistence.
9. Add CloudWatch/Fargate logging.
10. Add Prometheus and Grafana monitoring.
11. Automate build and deployment through Jenkins or GitHub Actions.
12. Replace the EC2-hosted database with Amazon RDS for a production-oriented design.

---

## 16. Confidential Data Checklist Before Git Commit

Search the repository before pushing:

```bash
grep -RniE 'password|secret|access[_-]?key|DATABASE_URL|172\.|314[0-9]+' . \
  --exclude-dir=.git \
  --exclude='*.md'
```

Confirm that the repository does not contain:

```text
[ ] Real AWS account ID
[ ] AWS access key
[ ] AWS secret access key
[ ] Real database password
[ ] Real DATABASE_URL
[ ] EC2 private or public IP where not required
[ ] SSH private key
[ ] Unencrypted Kubernetes Secret manifest
[ ] Terraform state files
[ ] .env file
```

Use placeholders:

```text
AWS Account ID: xxx
Database password: xxx
EC2 private IP: yyy
Database host: yyy
Access key: xxx
Secret key: xxx
```

Ensure `.gitignore` includes:

```gitignore
.env
*.pem
*.key
*.tfstate
*.tfstate.*
.terraform/
secrets.yaml
config-with-secret.yaml
```

---

## 17. Cost-Control Cleanup

Delete only the application namespace:

```bash
kubectl delete namespace bgcv-servicehub
```

Delete the EKS cluster:

```bash
eksctl delete cluster \
  --name "$CLUSTER_NAME" \
  --region "$AWS_REGION"
```

Verify:

```bash
aws eks list-clusters --region "$AWS_REGION"
```

ECR repositories remain after cluster deletion. Also check separately for EC2 instances, ALBs, target groups, NAT Gateways, Elastic IPs, and EBS volumes.

---

## 18. Suggested Git Location

Save this document at:

```text
docs/deployment/BGCV_EKS_FARGATE_IMPLEMENTATION_AND_TROUBLESHOOTING.md
```

Commit:

```bash
mkdir -p docs/deployment

git add docs/deployment/BGCV_EKS_FARGATE_IMPLEMENTATION_AND_TROUBLESHOOTING.md
git commit -m "docs: add sanitized EKS Fargate implementation record"
git push origin main
```
