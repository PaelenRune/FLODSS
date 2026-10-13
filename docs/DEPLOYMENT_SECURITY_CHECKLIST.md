# FLODSS — Deployment Security & Hardening Checklist (Phase 14.1)

## 1. Scope & Objective

This document outlines the mandatory operational and cryptographic security requirements for transitioning FLODSS from local pair-programming execution to a **private, on-premise institutional research server** or dedicated laboratory workstation.

> **CRITICAL DIRECTIVE**: FLODSS is a proprietary research prototype subject to ongoing intellectual property and patent feasibility evaluation. It MUST NEVER be deployed to a public cloud, exposed to the open internet, or uploaded to a public repository.

---

## 2. Infrastructure & Network Perimeter Hardening

- [ ] **Interface Binding**: Bind backend (`uvicorn`) and frontend servers strictly to `127.0.0.1` (loopback) or a private virtual interface. Never expose `0.0.0.0` directly to public networks.
- [ ] **Reverse Proxy Termination**: Place Nginx, Caddy, or Apache in front of FLODSS to manage TLS termination, request buffering, and static file delivery.
- [ ] **TLS 1.3 Encryption**: Mandate TLS 1.3 with strong cipher suites. Reject unencrypted HTTP (port 80 redirect to 443).
- [ ] **Access Restriction**: Restrict access to laboratory subnets or require institutional VPN (WireGuard/OpenVPN) for remote access by thesis advisors.
- [ ] **Firewall Rules**: Configure `ufw` or Windows Advanced Firewall to drop all inbound traffic except authorized proxy and VPN ports.
- [ ] **Outbound Filtering**: Block all egress traffic except DNS and authorized Gemini API endpoints (if external AI explanations are explicitly enabled).

---

## 3. Environment & Secrets Management

- [ ] **Admin Password Override**: Change `DEFAULT_ADMIN_PASSWORD` immediately from the default bootstrap value to a strong random passphrase (minimum 16 characters).
- [ ] **Session Secret Entropy**: Ensure `SECRET_KEY` is populated with high-entropy cryptographic random bytes:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(48))"
  ```
- [ ] **Environment File Protection**: Set file permissions on `.env` or systemd service environment definitions to `600` (readable only by the service runner user).
- [ ] **Disable Insecure Debug Modes**: Verify `FASTAPI_DEBUG=false` and disable automatic API interactive documentation (`/docs`, `/redoc`) if external viewer access is permitted.

---

## 4. Database Hardening & Backup Continuity

- [ ] **File Permissions**: Set filesystem permissions on `data/flodss_research.db` and WAL files (`-wal`, `-shm`) to `chmod 600` owned by `flodss:flodss`.
- [ ] **WAL Mode Verification**: Confirm Write-Ahead Logging is active (`PRAGMA journal_mode = WAL;`) for non-blocking concurrent operations.
- [ ] **Automated Backup Protocol**: Schedule daily encrypted backups using the SQLite online backup API:
  ```bash
  sqlite3 data/flodss_research.db ".backup 'backups/flodss_$(date +%Y%m%d_%H%M%S).db'"
  ```
- [ ] **Disaster Recovery**: Verify that backup files can be restored and migrations validated on a standby workstation.

---

## 5. Application & Session Security

- [ ] **Cookie / Header Security**: Verify HTTP response security headers are actively delivered on all routes:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`
- [ ] **Brute-Force Protection**: Ensure the sliding-window rate limiter is operational (`MAX_LOGIN_ATTEMPTS = 5/min`). Connect Fail2ban or Nginx `limit_req` for persistent IP banning.
- [ ] **Job Resource Quotas**: Maintain the global maximum of 2 concurrent optimization jobs (`MAX_CONCURRENT_JOBS = 2`) to prevent CPU exhaustion on shared laboratory compute nodes.
- [ ] **Payload Limits**: Ensure reverse proxy and FastAPI limit request bodies to 10MB maximum.

---

## 6. Research Privacy & Third-Party Audit

- [ ] **Default AI State**: Verify `AI_ENABLED=false` remains the default. External AI reasoning must require dual opt-in (Administrator enablement + Researcher session consent).
- [ ] **Multi-Tenant Audit**: Review SQLite audit logs regularly (`SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 100;`) to detect anomalous authentication or project access attempts.
- [ ] **Non-Disclosure**: Ensure all participating thesis advisors, researchers, and students execute institutional Non-Disclosure Agreements (NDAs) prior to receiving invitation tokens.
