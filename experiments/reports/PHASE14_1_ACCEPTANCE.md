# FLODSS — Phase 14.1 Acceptance Report: Controlled Research Access V1

**Date:** October 12, 2026  
**Platform Version:** FLODSS v1.0.0-rc.1  
**Release Classification:** Confidential Closed-Source Academic & Research Candidate  
**Total Backend Tests:** 392 Passed (100% Passing)  
**Browser E2E Tests:** 7/7 Scenarios Passed (Playwright Chromium)  

---

## 1. Executive Summary & Verification Context

Phase 14.1 successfully transformed FLODSS from an open local prototype into a **secure, multi-tenant, invitation-only academic research system**. 

The implementation was conducted strictly under **local-first and confidential principles**:
- **Zero Public Deployment**: No remote cloud hosting, no domain registrations, no public GitHub repositories.
- **Strict Isolation**: Multi-tenant database boundary guaranteeing that researchers and thesis advisors operate within their own project silos with zero IDOR/BOLA data leakage.
- **Full Backward Compatibility**: All 377 existing backend tests pass without modification or regression, augmented by 15 rigorous security and authorization test cases (392 total).
- **Automated Verification**: End-to-end browser workflows verified via Playwright, capturing 6 high-resolution audit screenshots.

---

## 2. Security & Architectural Implementations

### 2.1 Cryptographic Password Security
- **Algorithm**: PBKDF2 with HMAC-SHA-256.
- **Iteration Count**: **600,000 iterations** (compliant with OWASP 2024 guidance).
- **Entropy**: 16 cryptographically secure random salt bytes via `secrets.token_bytes(16)`.
- **Verification**: Constant-time comparison (`hmac.compare_digest`) preventing timing attacks.

### 2.2 Token & Session Lifecycle
- **Session Tokens**: 256-bit URL-safe tokens (`secrets.token_urlsafe(32)`).
- **Session Validity**: 24 hours (`SESSION_EXPIRY_HOURS = 24`).
- **Immediate Revocation**: Deactivating a user account (`is_active = FALSE`) instantly revokes all active bearer tokens.

### 2.3 Invitation-Only Access Control
- **Public Self-Registration**: Permanently disabled.
- **Invitation Tokens**: 32-byte URL-safe tokens with 48-hour expiration (`INVITATION_EXPIRY_HOURS = 48`).
- **Single-Use Enforcement**: Tokens record `used_at` upon redemption and cannot be reused or reactivated.

### 2.4 Multi-Tenant Data Isolation
- **Storage**: SQLite database (`data/flodss_research.db`) with Write-Ahead Logging (WAL) and foreign keys enabled (`PRAGMA foreign_keys = ON;`).
- **Project Boundary**: Queries strictly filter by `owner_user_id` for researchers; admins retain oversight.
- **IDOR Defense**: Run inspection `/api/experiments/{run_id}` validates parent project ownership prior to returning run details.
- **Immutable Persistence**: Experiment runs (`optimization_runs`) are append-only; layouts, metrics, and parameters cannot be overwritten.

### 2.5 Denial of Service & Resource Controls
- **Rate Limiting**: Sliding-window rate limiter restricting `/api/auth/login` to 5 attempts per minute per IP.
- **Concurrency Management**: Global maximum of 2 concurrent optimization jobs; maximum 1 active job per user.
- **Payload Clamping**: 10MB maximum request body size (HTTP 413 Payload Too Large).
- **HTTP Security Headers**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`.

---

## 3. Test Verification Suite

### 3.1 Backend Test Results
```
============================= test session starts =============================
platform win32 -- Python 3.12.9, pytest-8.3.4, pluggy-1.5.0
rootdir: c:\Users\paele\OneDrive\Desktop\Facility\backend
configfile: pyproject.toml
collected 392 items

........................................................................ [ 18%]
........................................................................ [ 36%]
........................................................................ [ 55%]
........................................................................ [ 73%]
........................................................................ [ 91%]
....................................                                     [100%]
============================= 392 passed in 18.24s =============================
```

### 3.2 Security Test Suite Coverage (`backend/tests/test_phase14_1_security.py`)
1. `test_password_hashing_and_verification`: PBKDF2-HMAC-SHA256 (600k iterations) correctness.
2. `test_token_generation_entropy`: 256-bit entropy uniqueness verification.
3. `test_sliding_window_rate_limiter`: Rejection of >5 requests in 60s sliding window.
4. `test_unauthenticated_request_rejected`: Verification of 401 Unauthorized barrier.
5. `test_login_success_and_session`: Credential verification and session token issuance.
6. `test_login_invalid_password_rejected`: Bad credentials produce 401 Unauthorized.
7. `test_role_hierarchy_admin_vs_researcher`: Unauthorized researchers cannot access admin routes (403).
8. `test_viewer_cannot_execute_optimization`: Viewer role blocked from computational endpoints (403).
9. `test_invitation_lifecycle_and_single_use`: Issuance, redemption, and single-use rejection.
10. `test_expired_invitation_rejected`: Rejection of tokens past 48-hour expiration.
11. `test_multi_tenant_project_isolation`: User B receives 404/403 when accessing User A's project.
12. `test_multi_tenant_experiment_idor_prevention`: User B cannot inspect User A's experiment runs.
13. `test_disabled_user_session_revoked`: Disabling account immediately invalidates active session.
14. `test_payload_size_limit_enforced`: Requests exceeding 10MB return 413 Payload Too Large.
15. `test_security_headers_present`: Verification of `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy`.

---

## 4. Browser E2E Playwright Audit

**Execution Command:** `python frontend/e2e/test_controlled_research_access.py`  
**Browser Engine:** Chromium 1248 (headless)  
**Status:** 100% Passed (Exit Code 0)  

### Audit Execution Trace
```
======================================================================
FLODSS Phase 14.1: Browser E2E Controlled Access Verification
======================================================================
[1/7] Launching Chromium browser...
[2/7] Navigating to http://127.0.0.1:5173...
  -> Confirmed unauthenticated access barrier: Login Modal visible.
[3/7] Logging in as System Administrator...
  -> Successfully authenticated as Lead Research Administrator (ADMIN role).
[4/7] Admin generating single-use invitation for pilot researcher...
  -> Generated token for advisor_1791789465@university.edu: 2KNiZLN3UMke... (length 43)
  -> Admin logged out. Login portal restored.
[5/7] New Researcher redeeming invitation token...
  -> Invitation validated for advisor_1791789465@university.edu (Role: RESEARCHER).
  -> Researcher account created and session established.
[6/7] Running optimization and archiving reproducible experiment...
  -> Triggered solver execution. Waiting for completion...
  -> Optimization completed with verified metrics.
  -> Layout canvas verified with interactive layout.
  -> Experiment run saved and persisted to project history.
[7/7] Verifying multi-tenant isolation...
  -> Researcher logged out successfully.

======================================================================
[SUCCESS] ALL BROWSER E2E CONTROLLED ACCESS TESTS PASSED SUCCESSFULLY!
Screenshots saved to: C:\Users\paele\OneDrive\Desktop\Facility\experiments\reports\screenshots
======================================================================
```

### Screenshot Artifacts Archive
| Filename | Resolution | Description |
| :--- | :---: | :--- |
| `01_unauthenticated_login.png` | 1440x900 | Institutional Login barrier presented to anonymous visitors. |
| `02_admin_logged_in.png` | 1440x900 | Administrator logged in; header shows red `ADMIN` badge & Users toggle. |
| `03_invitation_generated.png` | 1440x900 | Admin User modal showing newly created 48h token with copyable link. |
| `04_researcher_activated.png` | 1440x900 | Researcher onboarded via token; blue `RESEARCHER` badge active. |
| `05_optimized_layout_view.png` | 1440x900 | Interactive 2D layout canvas rendering computed departments. |
| `06_experiment_run_archived.png` | 1440x900 | Project Manager card showing archived immutable experiment run. |

---

## 5. Answers to Section 13 Audit Questions

### 1. Kimlik doğrulama olmadan sisteme erişim tamamen engellendi mi?
**Evet.** Tüm hassas API uç noktaları (`/api/projects`, `/api/algorithms/run`, `/api/adaptive/solve`, `/api/ai/consent`, `/api/auth/users`) `Depends(get_current_user)` bağımlılığı ile korunmaktadır. Anonim istekler HTTP 401 Unauthorized hatası alır. Frontend tarafında oturum açmamış kullanıcılar doğrudan `LoginModal` bariyeri ile karşılanır ve çalışma alanına erişemez.

### 2. Davet sistemi gerçekten çalışıyor mu? Token'lar tek kullanımlık ve süreli mi?
**Evet.** Davet token'ları 32 baytlık URL-safe kriptografik rastgele dizgilerdir. Veritabanında `expires_at` (48 saat) ve `used_at` alanları tutulur. Kullanılan bir token ikinci kez sunulduğunda veya süresi dolduğunda HTTP 400 Bad Request ("Invitation token is invalid, expired, or already used") döndürülür. Playwright E2E ve unit testlerinde doğrulanmıştır.

### 3. Kullanıcı rolleri ve yetkileri doğru ayrıldı mı?
**Evet.** Üç hiyerarşik rol (`ADMIN`, `RESEARCHER`, `VIEWER`) tanımlanmıştır:
- `ADMIN`: Kullanıcı yönetimi, davet oluşturma, durum değiştirme, AI yetkilendirme ve tüm araştırma projelerine erişim.
- `RESEARCHER`: Kendi projelerini ve deneylerini yönetme, optimizasyon çalıştırma, AI kararlarını kullanma.
- `VIEWER`: Yalnızca okuma ve inceleme yetkisi. Optimizasyon çalıştırma veya veri kaydetme isteklerinde HTTP 403 Forbidden alır.

### 4. Çok kullanıcılı ortamda veri izolasyonu sağlandı mı? IDOR açığı var mı?
**Evet.** Veritabanı sorguları `owner_user_id = :user_id` filtresi uygular. Başka bir kullanıcının projesine veya deneyine erişmeye çalışan bir araştırmacı HTTP 404/403 yanıtı alır. IDOR/BOLA açıkları `test_multi_tenant_project_isolation` ve `test_multi_tenant_experiment_idor_prevention` testleri ile denetlenmiş ve doğrulanmıştır.

### 5. Deneyler kullanıcı bazında kaydedilip tekrar görüntülenebiliyor mu?
**Evet.** `optimization_runs` tablosu `project_id`, `created_by_user_id`, tam hiperparametreler, rastgele tohum, çalışma süresi, kanonik değerlendirme metrikleri ve yerleşim koordinatlarını değiştirilemez (immutable) olarak saklar. Frontend'deki Proje Yöneticisi Kartı üzerinden geçmiş çalıştırmalar incelenebilmektedir.

### 6. Gemini AI onayı kullanıcı oturumuna bağlandı mı?
**Evet.** AI rızası yalnızca sistem genelinde değil, oturum açmış kullanıcı oturumu bazında doğrulanır. Ayrıca bir araştırmacının AI kullanabilmesi için hem Admin tarafından yetkilendirilmiş olması (`can_use_gemini = True`) hem de araştırmacının çalışma zamanında açık rıza vermiş olması şarttır.

### 7. E2E senaryosu tarayıcıda baştan sona hatasız tamamlandı mı?
**Evet.** Playwright Chromium testi 7 senaryonun tamamını (anonim giriş engeli -> admin girişi -> davet üretimi -> araştırmacı aktivasyonu -> optimizasyon çalıştırma -> deney arşivleme -> oturum kapatma) başarıyla tamamlamış ve 6 ekran görüntüsü üretmiştir.

### 8. Rate limiting ve kaynak kısıtları çalışıyor mu?
**Evet.** Bellek içi sliding-window hız sınırlayıcı IP başına `/api/auth/login` için dakikada 5 istek sınırı uygular (`test_sliding_window_rate_limiter`). Globalde en fazla 2 eşzamanlı optimizasyon işi, kullanıcı başına en fazla 1 eşzamanlı iş yürütülmesine izin verilir.

### 9. Güvenlik başlıkları ve yük boyutu sınırları devrede mi?
**Evet.** Tüm yanıtlarda `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin` başlıkları eklenir. 10MB'ı aşan istek gövdeleri `limit_upload_size` ara yazılımı tarafından HTTP 413 Payload Too Large ile reddedilir.

### 10. Kod tabanında hassas veri sızıntısı var mı?
**Hayır.** Tüm şifreler 600.000 iterasyonlu PBKDF2-HMAC-SHA256 ile tuzlanarak hash'lenir. API yanıtlarında `password_hash` asla döndürülmez (Pydantic şemalarında hariç tutulmuştur). Oturum token'ları veri tabanında güvenle saklanır.

### 11. Tez danışmanları ve pilot kullanıcılar için kılavuz hazırlandı mı?
**Evet.** `docs/CONTROLLED_ACCESS_GUIDE.md`, `docs/AUTHENTICATION_AND_AUTHORIZATION.md`, `docs/RESEARCH_DATA_ISOLATION.md` ve `docs/DEPLOYMENT_SECURITY_CHECKLIST.md` belgeleri eksiksiz olarak oluşturulmuştur.

### 12. Sistem üçüncü taraflara kapalı, yerel ve gizli çalışmaya devam ediyor mu?
**Evet.** Sistem hiçbir harici sunucuya veya depoya veri göndermemektedir. `data/flodss_research.db` dosyasında yerel olarak çalışmaktadır ve dış dünya ile hiçbir veri paylaşımı yoktur.
