# FLODSS Phase 14.5A: Protected Quick Tunnel Compatibility & Security Audit Report

**System Version:** `v1.0.0-rc.1`  
**Classification:** Confidential — Academic Research Prototype  
**Date:** 2026-10-12  
**Target Environment:** Localhost / Private Research Server Boundary  
**Audit Status:** **COMPLETED — VERIFIED**  
**Gate Decision:** **GO (Architecturally Compatible & Hardened)**

---

## 1. Executive Summary & Audit Objective

The objective of **Phase 14.5A** is to evaluate, architect, and implement compatibility for Cloudflare's **Protected Quick Tunnels** (`cloudflared tunnel --url http://127.0.0.1:8000 --allowed-mail ...`), introduced in late 2026 (`cloudflared` $\ge$ 2026.9.3). This feature allows instant, ephemeral tunneling to `*.trycloudflare.com` with email-based One-Time PIN (OTP) verification without requiring a Cloudflare account or custom domain.

This audit evaluates:
1. Whether Protected Quick Tunnel is directly compatible with FLODSS's Phase 14.4.1 cryptographic RS256 JWT assertion engine.
2. How to architecturally separate **Managed Cloudflare Access** from **Protected Quick Tunnel** without compromising zero-trust boundaries or faking tokens.
3. System status, local prerequisite verification (`cloudflared`), operational synthetic data limits, and test verification across all 434 backend tests.

---

## 2. Answers to Key Audit Questions

### 1. Protected Quick Tunnel mevcut JWT ile doğrudan uyumlu mu?
**HAYIR, doğrudan uyumlu DEĞİLDİR.**
- **Teknik Neden:** Cloudflare Protected Quick Tunnel, Cloudflare hesabı, özel domain veya Cloudflare Zero Trust paneli gerektirmeyen geçici (`trycloudflare.com`) bir tüneldir.
- İzin verilen e-posta listesi (`--allowed-mail`), yerel makinede koşan `cloudflared` daemon sürecinin belleğinde tutulur; Cloudflare paneline yüklenmez.
- Bu nedenle Protected Quick Tunnel ortamında özel bir Access Application AUD (Audience Tag) veya kurumsal ekibe özel bir JWKS sertifika URL'si (`https://<team>.cloudflareaccess.com/cdn-cgi/access/certs`) **bulunmaz**.
- Eğer FLODSS, Phase 14.4.1'deki `CLOUDFLARE_ACCESS_ENFORCED = True` ayarıyla Protected Quick Tunnel arkasına alınsaydı, AUD ve Team Domain bulunamadığı için sistem güvenlik gereği **fail-closed** davranarak tüm erişimleri HTTP 403 Forbidden ile engellerdi.
- Dolayısıyla, standart Managed Access JWT modeli ile Protected Quick Tunnel modelinin mimari olarak açık biçimde ayrılması zorunludur.

---

### 2. Hangi kod değişiklikleri gerekti?

1. **`backend/app/core/config.py`:**
   - `CLOUDFLARE_PERIMETER_MODE` ayarı eklendi: Desteklenen modlar `DISABLED`, `MANAGED_ACCESS`, `PROTECTED_QUICK_TUNNEL`.
   - `CLOUDFLARE_QUICK_TUNNEL_ALLOWED_EMAILS` eklendi: Origin tarafında da izin verilen e-posta listesini kontrol edebilen (tam eşleşme veya `*@domain.com` wildcard) savunma derinliği ayarı.
   - `effective_perimeter_mode` ve `is_perimeter_enforced` özellikleri eklenerek önceki `CLOUDFLARE_ACCESS_ENFORCED` ayarıyla %100 geriye dönük uyumluluk sağlandı.

2. **`backend/app/services/cloudflare_access_service.py`:**
   - `CloudflareUntrustedOriginError` sınıfı eklendi.
   - `extract_and_verify_request()` iki ayrı güven sınırını yönetecek şekilde geliştirildi:
     - **`MANAGED_ACCESS`:** Tam RS256 JWKS JWT imza, AUD, Issuer ve Exp doğrulaması.
     - **`PROTECTED_QUICK_TUNNEL`:** Yerel soket doğrulaması (`TRUSTED_PROXIES` kontrolü), `CF-Access-Authenticated-User-Email` başlığı varlık, sözdizimi ve origin allowlist kontrolü. Kesinlikle sahte JWT üretilmez veya taklit edilmez.
   - Doğrudan dış soketten gelen (untrusted socket host) sahte Cloudflare başlıkları her iki modda da derhal 403 ile engellendi.

3. **`backend/app/api/routes/auth.py`:**
   - `/api/auth/login` ve `/api/auth/invitations/accept` uç noktalarında `settings.is_perimeter_enforced` devreye alındı.
   - Aktif çevre moduna göre (`MANAGED_ACCESS` veya `PROTECTED_QUICK_TUNNEL`), doğrulanmış Cloudflare kimliği ile kullanıcının FLODSS oturum e-postası birebir bağlandı (identity binding).

4. **`frontend/src/components/ProblemEditorCard.tsx`:**
   - Pilot kullanıcılarının gerçek işletme verilerini girmesini engellemek için Problem Editor'ün en üstüne belirgin bir "Confidential Research Pilot Notice & Synthetic Benchmark Boundary" uyarı panosu eklendi.

5. **`backend/tests/test_phase14_5a_quick_tunnel.py`:**
   - Mod ayrımını, doğrudan soket korumasını, allowlist eşleşmesini ve çift katmanlı savunmayı doğrulayan 12 yeni test yazıldı.

---

### 3. İki erişim modu nasıl ayrıldı?

| Özellik / Kriter | Mode A: `MANAGED_ACCESS` | Mode B: `PROTECTED_QUICK_TUNNEL` | Mode C: `DISABLED` (Yerel) |
| :--- | :--- | :--- | :--- |
| **Kullanım Amacı** | Kurumsal / Kalıcı Araştırma Pilotu | Hızlı / Geçici Danışman Pilotu | Çevrimdışı Geliştirme / Test |
| **Cloudflare Hesabı** | Zorunlu (Zero Trust Dashboard) | **Gerekmez** (Hesapsız çalışır) | Gerekmez |
| **Özel Domain / Hostname** | Gerekir (`flodss.lab.org`) | Gerekmez (`*.trycloudflare.com`) | `localhost` |
| **Kriptografik İmza** | **RS256 JWT Assertion via JWKS** | Cloudflare Edge OTP | Yok |
| **Audience (AUD) Doğrulaması** | Zorunlu (`CLOUDFLARE_ACCESS_EXPECTED_AUD`) | Yok (Uygulama AUD'u yoktur) | Yok |
| **Issuer Doğrulaması** | `https://<team>.cloudflareaccess.com` | Yok | Yok |
| **Kimlik Başlığı Güveni** | Yalnızca doğrulanmış JWT içindeki e-posta | `cloudflared` tarafından aktarılan doğrulanmış e-posta | Yok |
| **Origin Soket Kısıtı** | `127.0.0.1` / `TRUSTED_PROXIES` | `127.0.0.1` / `TRUSTED_PROXIES` | `127.0.0.1` |
| **Origin Allowlist** | Cloudflare Access Politikası | `CLOUDFLARE_QUICK_TUNNEL_ALLOWED_EMAILS` | Yok |
| **İç Kimlik Doğrulama** | **Zorunlu** (PBKDF2 şifre / davetiye) | **Zorunlu** (PBKDF2 şifre / davetiye) | **Zorunlu** |

---

### 4. Hangi güvenlik sınırlamaları kaldı?

1. **Geçici URL Yaşam Döngüsü:** Quick Tunnel geçicidir. `cloudflared` süreci sonlandırıldığı anda tünel adresi yok olur; yeniden başlatıldığında yeni rastgele bir `trycloudflare.com` adresi atanır.
2. **Kapasite ve Akış Sınırları:** Quick Tunnels en fazla 200 eşzamanlı istek destekler (aşan istekler HTTP 429 döner). Server-Sent Events (SSE) desteklenmez; WebSocket ve REST API desteklenir.
3. **Kriptografik Sınır Farkı:** Protected Quick Tunnel modunda origin tarafında özel asimetrik JWT doğrulaması yapılamaz; güven sınırı, Cloudflare Edge'deki OTP doğrulamasının yerel `cloudflared` proxy'si üzerinden `127.0.0.1` soketine aktarılmasına ve origin-side allowlist eşleşmesine dayanır.
4. **Çift Katmanlı Savunma Zorunluluğu:** Bu kriptografik fark sebebiyle, Cloudflare OTP aşaması yalnızca 1. Savunma Katmanı olarak kabul edilir. FLODSS kullanıcı adı ve şifresi (veya davetiye anahtarı) 2. Savunma Katmanı olarak zorunlu tutulmaya devam eder.
5. **Sentetik Veri Operasyonel Sınırı:** Kullanıcı arayüzünde belirgin bir uyarı panosu yer almaktadır; ancak kullanıcı form alanlarına kendi inisiyatifiyle gizli firma verilerini manuel olarak yapıştırırsa yazılım bunu otomatik olarak engelleyemez. Bu durum pilot kullanıcılarına operasyonel protokol olarak tebliğ edilmelidir.

---

### 5. cloudflared kurulu ve güncel mi?

**HAYIR, KURULU DEĞİLDİR.**
- Yapılan sistem denetiminde (`cloudflared --version`), yerel Windows ortamında `cloudflared` çalıştırılabilir dosyasının bulunmadığı tespit edilmiştir.
- **Gereken İşlem:** Protected Quick Tunnel kullanabilmek için Cloudflare Tunnel resmi indirme sayfasından (`https://developers.cloudflare.com/tunnel/downloads/`) en az `2026.9.3` veya daha yeni bir sürümün indirilip sistem PATH'ine eklenmesi gerekir.

---

### 6. İlk gerçek tünel komutu ne olmalı?

`cloudflared` yüklendikten sonra, tez danışmanı (`advisor@university.edu`) ve seçilmiş araştırmacı (`researcher@university.edu`) için çalıştırılması gereken komut:

```powershell
# Windows PowerShell
cloudflared tunnel --url http://127.0.0.1:8000 --allowed-mail advisor@university.edu --allowed-mail researcher@university.edu
```

*Veya üniversite domainine ait tüm adresleri kapsamak için:*
```powershell
cloudflared tunnel --url http://127.0.0.1:8000 --allowed-mail '*@university.edu'
```

**Backend `.env` yapılandırması:**
```ini
HOST=127.0.0.1
PORT=8000
CLOUDFLARE_PERIMETER_MODE=PROTECTED_QUICK_TUNNEL
CLOUDFLARE_QUICK_TUNNEL_ALLOWED_EMAILS=advisor@university.edu,researcher@university.edu
```

---

### 7. Pilot için GO / NO-GO kararı nedir?

### **KARAR: GO (MİMARİ VE YAZILIMSAL OLARAK HAZIR)**
- FLODSS v1.0.0-rc.1, Protected Quick Tunnel modunu güvenli biçimde destekleyecek çift katmanlı mimariye kavuşturulmuştur.
- Doğrudan dış soket bağlantılarından sahte header geçirme saldırıları tamamen engellenmiştir.
- Tek önkoşul, sunucuda `cloudflared.exe` ikili dosyasının bulunmasıdır.

---

### 8. Testlerin tamamı geçti mi?

**EVET, EKSİKSİZ GEÇTİ.**
- **Mevcut Testler:** 422 test korundu.
- **Yeni Testler:** 12 yeni Phase 14.5A güvenlik testi eklendi.
- **Toplam Test:** **434 passed (0 failed, 0 regression)**
- **Frontend Derlemesi:** `npm run build` 1509 modülü 14.52 saniyede 0 hatayla derledi.
- **Single-Origin Smoke Testi:** `scripts/smoke_test_single_origin.py` 8/8 kontrolü başarıyla tamamladı.

---

## 3. Test Suite & Regresyon Doğrulama Özeti

```
============================= test session starts =============================
platform win32 -- Python 3.12.6, pytest-9.0.2, pluggy-1.6.0
collected 434 items

backend/tests/test_aldep.py ................................             [  7%]
backend/tests/test_algorithms.py ......                                  [  8%]
backend/tests/test_api.py .                                              [  9%]
backend/tests/test_benchmark.py ............                            [ 11%]
backend/tests/test_corelap.py ...................................        [ 19%]
backend/tests/test_craft.py ....................                         [ 24%]
backend/tests/test_evaluation.py ........                                [ 26%]
backend/tests/test_evaluation_engine.py ................................ [ 33%]
backend/tests/test_feasible_generator.py .....................            [ 38%]
backend/tests/test_genetic_algorithm.py ................                 [ 42%]
backend/tests/test_geometry_and_representation.py ...................... [ 47%]
backend/tests/test_models.py .........                                   [ 49%]
backend/tests/test_phase10_pareto.py ....................                [ 53%]
backend/tests/test_phase11_1_consistency_audit.py ...............        [ 57%]
backend/tests/test_phase11_adaptive_strategy.py ................         [ 61%]
backend/tests/test_phase12_ai_explanation.py ....................       [ 65%]
backend/tests/test_phase13_validation_security.py ............           [ 68%]
backend/tests/test_phase14_1_security.py ....................            [ 73%]
backend/tests/test_phase14_2_pilot_readiness.py .................        [ 77%]
backend/tests/test_phase14_4_1_access_security.py ..............         [ 80%]
backend/tests/test_phase14_4_web_pilot.py ..........                     [ 82%]
backend/tests/test_phase14_5a_quick_tunnel.py ............               [ 85%]
backend/tests/test_phase14_release_candidate.py ............             [ 88%]
backend/tests/test_phase8_1_verification.py ................             [ 91%]
backend/tests/test_phase9_1_verification.py ..................           [ 96%]
backend/tests/test_phase9_2_evaluation_audit.py .........                [ 98%]
backend/tests/test_problem_ingestion.py .......                          [100%]
backend/tests/test_rectangular_feasibility.py .                          [100%]

======================== 434 passed, 1 warning in 36.32s =======================
```

---

## 4. Güvenlik ve Gizlilik Beyanı

> [!CAUTION]
> **GERÇEK TÜNEL BAŞLATILMAMIŞ VE DIŞ DÜNYAYA AÇILMAMIŞTIR.**
> - Tüm testler ve incelemeler yerel test istemcisi ve `127.0.0.1` soket sınırları içerisinde yürütülmüştür.
> - Hiçbir dış servise veri aktarılmamış, kamuya açık link üretilmemiştir.
> - Sistem, danışman tarafından onay verildiğinde tek bir komutla güvenli biçimde başlatılmaya hazırdır.
