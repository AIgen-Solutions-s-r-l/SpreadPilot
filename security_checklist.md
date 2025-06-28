# 🔒 SpreadPilot Security Checklist

> 🛡️ **Comprehensive security checklist** for SpreadPilot platform - enforcing best practices across all services and deployments

This checklist ensures that security best practices are followed throughout the development, deployment, and operation of SpreadPilot. All items must be verified before each release.

---

## 📋 Pre-Deployment Security Checklist

### 🔍 1. Dependency Scanning

- [ ] **Run Trivy dependency scan** on all Docker images
  ```bash
  ./trivy_scan.sh
  ```
- [ ] **No HIGH or CRITICAL vulnerabilities** in production dependencies
- [ ] **All npm/pip packages** are from trusted sources
- [ ] **License compliance** verified for all dependencies
- [ ] **SBOM (Software Bill of Materials)** generated and stored

### 🐳 2. Container Security

- [ ] **All containers run as non-root user**
  - Trading Bot: ✅ (UID 1000)
  - Admin API: ✅ (UID 1000)
  - Report Worker: ✅ (UID 1000)
  - Alert Router: ✅ (UID 1000)
  - Frontend: ✅ (nginx user)
  - Admin Dashboard: ✅ (nginx user)
- [ ] **Minimal base images** used (alpine/slim variants)
- [ ] **No secrets in Docker images** or build args
- [ ] **Health checks** configured for all containers
- [ ] **Resource limits** set (CPU/Memory)
- [ ] **Read-only root filesystem** where possible

### 🌐 3. CSP Headers & Web Security

- [ ] **Content Security Policy (CSP)** headers configured:
  ```
  Content-Security-Policy: default-src 'self'; 
    script-src 'self' 'unsafe-inline' 'unsafe-eval'; 
    style-src 'self' 'unsafe-inline'; 
    img-src 'self' data: https:; 
    font-src 'self' data:; 
    connect-src 'self' wss: https:;
  ```
- [ ] **Security headers** implemented:
  - X-Frame-Options: DENY
  - X-Content-Type-Options: nosniff
  - X-XSS-Protection: 1; mode=block
  - Referrer-Policy: strict-origin-when-cross-origin
  - Permissions-Policy: geolocation=(), microphone=(), camera=()
- [ ] **HSTS (HTTP Strict Transport Security)** enabled
- [ ] **CORS** properly configured with specific origins

### 🔐 4. Database Security (DB-TLS)

- [ ] **MongoDB TLS/SSL** enabled in production:
  ```
  mongodb://username:password@host:port/database?tls=true&tlsCAFile=/path/to/ca.pem
  ```
- [ ] **PostgreSQL SSL mode** set to 'require' or 'verify-full':
  ```
  postgresql://user:pass@host/db?sslmode=require
  ```
- [ ] **Connection strings** use environment variables
- [ ] **Database credentials** stored in Secret Manager
- [ ] **Encryption at rest** enabled for databases
- [ ] **Network isolation** via VPC/private subnets

### 👤 5. IAM & Least Privilege

- [ ] **Service accounts** follow least-privilege principle:
  - Trading Bot: Read sheets, write to DB
  - Admin API: Read/write DB, no cloud resources
  - Report Worker: Read DB, write to GCS bucket only
  - Alert Router: Pub/Sub publish only
- [ ] **No wildcard permissions** (*) in IAM policies
- [ ] **Separate service accounts** per service
- [ ] **Regular IAM audit** scheduled (quarterly)
- [ ] **MFA required** for admin accounts
- [ ] **API keys rotated** every 90 days

### 🔑 6. PIN Verification (0312)

- [ ] **PIN verification** implemented for dangerous endpoints:
  ```python
  DANGEROUS_ENDPOINTS = [
      "/api/v1/followers/*/delete",
      "/api/v1/positions/close-all",
      "/api/v1/settings/reset",
      "/api/v1/trading/emergency-stop"
  ]
  ```
- [ ] **PIN stored securely** (hashed with bcrypt)
- [ ] **Rate limiting** on PIN attempts (3 attempts per 15 minutes)
- [ ] **Audit logging** for all PIN-protected actions
- [ ] **PIN complexity** enforced (6+ digits, not sequential)
- [ ] **PIN expiration** after 90 days

### 🔒 7. Authentication & Authorization

- [ ] **JWT tokens** with appropriate expiration (24h max)
- [ ] **Refresh tokens** stored securely with rotation
- [ ] **Password policy** enforced:
  - Minimum 12 characters
  - Mix of uppercase, lowercase, numbers, symbols
  - No common passwords (NIST list)
- [ ] **Account lockout** after 5 failed attempts
- [ ] **Session management** with secure cookies
- [ ] **RBAC (Role-Based Access Control)** implemented

### 📡 8. Network Security

- [ ] **TLS 1.2+** enforced for all connections
- [ ] **Firewall rules** restrict unnecessary ports
- [ ] **Private subnets** for internal services
- [ ] **WAF (Web Application Firewall)** for public endpoints
- [ ] **DDoS protection** enabled
- [ ] **VPN required** for admin access

### 🔍 9. Logging & Monitoring

- [ ] **Security events** logged:
  - Authentication attempts
  - Authorization failures
  - PIN verification attempts
  - Configuration changes
  - Data access patterns
- [ ] **Log retention** policy (90 days minimum)
- [ ] **SIEM integration** for security alerts
- [ ] **Anomaly detection** configured
- [ ] **Real-time alerts** for security events

### 🚨 10. Incident Response

- [ ] **Incident response plan** documented
- [ ] **Security contacts** list maintained
- [ ] **Automated security alerts** configured
- [ ] **Backup and recovery** procedures tested
- [ ] **Security patches** applied within 48 hours
- [ ] **Penetration testing** performed annually

---

## 🤖 CI/CD Security Integration

### Pipeline Security Checks

```yaml
security-scan:
  stage: security
  script:
    - ./trivy_scan.sh
    - python security_audit.py
    - npm audit --production
    - pip-audit
  artifacts:
    reports:
      - trivy-report.json
      - security-audit.json
```

### Pre-commit Hooks

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    hooks:
      - id: detect-private-key
      - id: check-yaml
      - id: check-json
  - repo: https://github.com/trufflesecurity/trufflehog
    hooks:
      - id: trufflehog
```

---

## 📊 Security Metrics

Track these KPIs monthly:

| Metric | Target | Current |
|--------|--------|---------|
| Days since last security incident | > 365 | - |
| Vulnerability scan frequency | Weekly | - |
| Time to patch critical vulns | < 48h | - |
| % containers running as non-root | 100% | - |
| Failed authentication attempts | < 1% | - |
| Security training completion | 100% | - |

---

## 🔄 Review Schedule

- **Daily**: Monitor security alerts and logs
- **Weekly**: Run vulnerability scans
- **Monthly**: Review security metrics and checklist
- **Quarterly**: IAM audit and credential rotation
- **Annually**: Penetration testing and security assessment

---

## 📞 Security Contacts

- **Security Lead**: security@spreadpilot.com
- **Incident Response**: incident@spreadpilot.com
- **24/7 Hotline**: +1-XXX-XXX-XXXX

---

<div align="center">

**🛡️ Security is everyone's responsibility**

Last Updated: 2025-06-28 | Version: 1.0.0

</div>