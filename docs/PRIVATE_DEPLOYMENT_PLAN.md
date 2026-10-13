# Controlled Private Research Deployment Plan
## FLODSS: Facility Layout Optimization & Decision Support System (`v1.0.0-rc.1`)

> [!CAUTION]
> **RESTRICTED RESEARCH INFRASTRUCTURE**  
> This architectural specification is designed strictly for **private institutional laboratories, internal university intranets, or secure air-gapped corporate research networks**. Public internet hosting or multi-tenant commercial deployment is strictly out of scope.

---

## 1. Deployment Architecture Overview

To provide multi-researcher access while maintaining strict data confidentiality and computational isolation, FLODSS employs a three-tier local server architecture:

```
                      +─────────────────────────────────────────+
                      |       Institutional Private LAN / VPN   |
                      |   (Authorized Research Workstations)    |
                      +────────────────────┬────────────────────+
                                           │
                                     HTTPS (TLS 1.3)
                                           ▼
                      +─────────────────────────────────────────+
                      |         Reverse Proxy & Gateway         |
                      |         (Nginx / Caddy + TLS)           |
                      +───────────┬─────────────────┬───────────+
                                  │                 │
                           Static Assets       REST API Calls
                                  │                 │
                                  ▼                 ▼
                      +───────────────────+ +───────────────────+
                      | Frontend (React)  | | Backend (FastAPI) |
                      | Static Nginx Host | | Python 3.12 Engine|
                      +───────────────────+ +─────────┬─────────+
                                                      │
                                                      ▼
                                            +───────────────────+
                                            | Local Persistence |
                                            | (PostgreSQL /     |
                                            |  Encrypted Disk)  |
                                            +───────────────────+
```

---

## 2. Infrastructure & Network Security

### 2.1 Network Segmentation & Access Control
- **Private Subnet Only:** The server should bind only to internal corporate/campus IP subnets (e.g., `10.x.x.x` or `192.168.x.x`) or be accessible solely via an authenticated WireGuard / OpenVPN tunnel.
- **Firewall Policy:** All external inbound traffic blocked. Inbound ports restricted to `443` (HTTPS) and `22` (SSH via SSH keys only).
- **DNS:** Internal DNS resolution (e.g., `flodss.lab.local`).

### 2.2 Reverse Proxy (Nginx) Configuration
A hardened Nginx reverse proxy handles TLS termination, request rate-limiting, and routing between static frontend assets and the FastAPI application server:

```nginx
server {
    listen 443 ssl http2;
    server_name flodss.lab.local;

    ssl_certificate /etc/ssl/certs/flodss_internal.crt;
    ssl_certificate_key /etc/ssl/private/flodss_internal.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header X-Frame-Options "DENY";
    add_header X-Content-Type-Options "nosniff";
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';";

    # Frontend Single-Page Application
    location / {
        root /var/www/flodss/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API Routing
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 300s; # Accommodates long-running GA batches
    }
}
```

---

## 3. Computational Resource Isolation & Sandboxing

Facility layout optimization—especially stochastic Genetic Algorithms with large populations ($N \ge 200$) and multi-generational slicing tree decodings—is computationally intensive.

### 3.1 Docker Containerization
Deploy services in separate containerized environments:
- **`flodss-frontend`:** Alpine-based Nginx serving production Vite build (`dist/`).
- **`flodss-backend`:** Python 3.12-slim running Uvicorn with worker processes:
  ```dockerfile
  FROM python:3.12-slim
  WORKDIR /app
  RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
  COPY pyproject.toml .
  RUN pip install --no-cache-dir .
  COPY app/ app/
  CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
  ```

### 3.2 CPU & Memory Capping
In `docker-compose.yml`, enforce hard resource quotas to prevent solver processes from starving other laboratory workloads:
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '4.00'
          memory: 4096M
        reservations:
          cpus: '1.00'
          memory: 1024M
```

---

## 4. User Authentication & Role-Based Access Control (RBAC)

For multi-user research groups, access control should follow three hierarchical roles:

1. **Viewer (Student / Observer):**
   - Read-only access to preloaded benchmark problems.
   - Run layout visualizations, inspect 2D canvas, review Pareto frontier.
   - Cannot overwrite shared problem templates.
2. **Researcher (Graduate Student / Postdoc):**
   - Full access to Problem Editor, Flow Matrix, Constraints, and Solvers.
   - Save custom problems, execute optimization runs, export thesis data.
3. **Administrator (Principal Investigator / Lab Director):**
   - System diagnostics, user provisioning, global configuration, backup management.

Authentication will utilize lightweight **JSON Web Tokens (JWT)** with HTTP-only, Secure, SameSite cookies to protect against cross-site scripting (XSS).

---

## 5. Data Persistence & Backup Policy

### 5.1 Storage Layout
- **Relational Data:** PostgreSQL 16 database storing problem specifications, matrix values, user profiles, and experiment runs.
- **File System Volumes:** Dedicated encrypted volume mount `/data/exports` storing exported JSON, CSV, and SVG bundles.

### 5.2 Automated Disaster Recovery Routine
- **Daily Automated Backup:** Encrypted PostgreSQL dump run via `cron` at 02:00 UTC:
  ```bash
  pg_dump -U flodss_user -Fc flodss_db | gpg --encrypt --recipient lab_pi@institution.edu > /backups/flodss_$(date +%Y%m%d).dump.gpg
  ```
- **Retention Schedule:** Retain daily backups for 30 days; weekly snapshots for 6 months.
- **Integrity Check:** Automated monthly test restoration into an isolated staging container.
