# FLODSS — Phase 14.4 Web Pilot Readiness & Security Audit Report

**Belge Sürümü:** 1.0.0-rc.1  
**Gizlilik Derecesi:** Özel Araştırma Prototipi / Yayın Öncesi Denetim  
**Değerlendirme Tarihi:** 12 Ekim 2026  
**Hedef Mimari:** Cloudflare Tunnel + Cloudflare Access (Zero Trust) + FLODSS Single-Origin FastAPI  
**Nihai Karar:** **GO FOR RESTRICTED CLOUDFLARE ACCESS PILOT (WITH STRICT EMAIL ALLOWLIST & SYNTHETIC DATA ONLY)**  
**(DOĞRUDAN GENEL İNTERNETE AÇIK / ALLOWLIST'SİZ DAĞITIM KESİNLİKLE YASAKTIR)**  

---

## 1. Yönetici Özeti ve Temel Başarımlar

Phase 14.4 kapsamında FLODSS v1.0.0-rc.1, tez danışmanı ve davetli araştırmacıların kendi bilgisayarlarından tarayıcı üzerinden erişebileceği, kapalı kaynaklı ve iki kademeli güvenlikle korunan bir web pilotu için baştan uca hazırlanmış ve test edilmiştir.

### Temel Doğrulamalar:
1. **Tek Origin (Single-Origin Architecture):** FastAPI backend'i, derlenmiş Vite üretim paketini (`frontend/dist/`) doğrudan sunacak şekilde yapılandırılmıştır. Vite geliştirme sunucusunun (dev server) internete açılması engellenmiştir.
2. **Çift Kademeli Güvenlik Duvarı (Dual Perimeter Defense):** Cloudflare Access'in e-posta allowlist katmanı (1. Kapı) ile FLODSS'ın uygulama içi rol, oturum ve proje izolasyon katmanı (2. Kapı) entegre edilmiştir. `CLOUDFLARE_ACCESS_ENFORCED=true` ayarı eklendiğinde, dışarıdan doğrulanan Cloudflare e-postası ile FLODSS oturum e-postasının eşleşmesi zorunlu kılınmıştır.
3. **Kapsamlı Kaynak Kısıtları (Resource Governance):** Optimizasyon çözücüleri için hem kullanıcı başına eşzamanlı iş sınırı (`MAX_CONCURRENT_JOBS_PER_USER=2`) hem de sunucu genelinde toplam iş kapasitesi tavanı (`MAX_TOTAL_CONCURRENT_JOBS=4`) FastAPI dependency (`get_job_slot`) düzeyinde devreye alınmıştır.
4. **HTTPS ve Güvenli Çerezler (Secure Cookies & Proxy Headers):** Cloudflare tünelinden gelen `X-Forwarded-Proto: https` veya `CF-Visitor` başlıkları algılanarak oturum çerezlerine dinamik `Secure=True` bayrağı uygulanmış; gerçek istemci IP'si `CF-Connecting-IP` başlığından çekilerek hız sınırlama ve denetim loglarına işlenmiştir.
5. **Test Başarısı:**
   - **Backend Testleri:** **408 Passed** (0 failed, %100 başarılı, 28.00s).
   - **Production Smoke Test:** 8/8 adım başarılı (HTML shell, static JS/CSS, API health, 401 barrier, login, secure cookie, synthetic solve, logout).
   - **Playwright Single-Origin Browser E2E:** 6/6 adım başarılı (Gerçek Chromium üzerinde `:8000` portundan giriş, 2D yerleşim tuvali çizimi, ekran görüntüsü kaydı ve güvenli çıkış).

---

## 2. Tek Origin İncelemesi ve Mimari Kararlar (Single-Origin Assessment)

| Özellik | Geliştirme Ortamı (Eski) | Üretim / Pilot Ortamı (Phase 14.4) |
| :--- | :--- | :--- |
| **Frontend Sunumu** | Vite Dev Server (`localhost:5173`) | FastAPI `StaticFiles` + `FileResponse` (`localhost:8000`) |
| **Kaynak Dosyalar** | TypeScript / JSX doğrudan derleme | Önceden derlenmiş statik bundle (`frontend/dist/`) |
| **CORS Gereksinimi** | Port 5173 -> 8000 için CORS zorunlu | Aynı origin (`/` ve `/api/...`), CORS atlatma gerekmez |
| **Tunnel Uç Noktası** | İki ayrı port yönlendirme riski | Tek bir iç servis: `127.0.0.1:8000` |
| **Açık Port Sayısı** | 2 port (`5173` ve `8000`) | 1 iç port (`8000`, dışarıya tamamen kapalı) |

FastAPI `main.py` içerisindeki yönlendirme mekanizması:
- Tarayıcı `Accept: text/html` başlığı ile `/` veya herhangi bir SPA rotasını istediğinde (`/workspace`, `/projects`), derlenmiş `frontend/dist/index.html` dosyasını döner.
- Statik varlıklar (`/assets/...`) `frontend/dist/assets/` klasöründen sunulur.
- `/api/...` istekleri doğrudan REST API denetleyicilerine yönlendirilir; bulunamayan API yolları HTML yerine JSON 404 üretir.
- API keşif araçları veya curl `Accept: application/json` ile kök rotayı (`/`) istediğinde sistem keşif JSON yükü döner (`test_root_endpoint` uyumluluğu %100 korunmuştur).

---

## 3. Bütün API Yollarının Yetkilendirme Kapsamı Denetimi

Sistemdeki tüm API uç noktaları tek tek denetlenmiş ve güvenlik sınıflandırması doğrulanmıştır:

| API Grubu | Uç Nokta Yolu | Erişim Türü | Yetkilendirme / Güvenlik Kuralı |
| :--- | :--- | :---: | :--- |
| **Health** | `GET /api/health` | Açık / Probing | Uptime izleme ve sistem hazır olma kontrolü |
| **Auth** | `POST /api/auth/login` | Açık / Rate-Limited | 5 deneme / 5 dk IP hız sınırı; Cloudflare Access email denetimi |
| **Auth** | `POST /api/auth/logout` | Oturum Zorunlu | Bearer token veya cookie ile oturum iptali |
| **Auth** | `GET /api/auth/me` | Oturum Zorunlu | Aktif kullanıcı profil kontrolü |
| **Auth (Admin)** | `POST /api/auth/invitations` | Rol Zorunlu | Yalnızca `ADMIN`; tek kullanımlık süreli davet oluşturma |
| **Auth (Admin)** | `GET /api/auth/invitations` | Rol Zorunlu | Yalnızca `ADMIN`; davet geçmişi listeleme |
| **Auth (Admin)** | `GET /api/auth/users` | Rol Zorunlu | Yalnızca `ADMIN`; kullanıcı hesap listesi |
| **Auth (Admin)** | `PATCH /api/auth/users/{id}/status`| Rol Zorunlu | Yalnızca `ADMIN`; hesap dondurma / AI izni değiştirme |
| **Auth (Public)**| `GET /api/auth/invitations/{token}`| Açık / Token Kontrolü | Davet geçerlilik ve süre doğrulama |
| **Auth (Public)**| `POST /api/auth/invitations/accept` | Açık / Token Tüketimi | Davet kabulü, şifre belirleme ve ilk oturum açma |
| **Projects** | `GET /api/projects` | Oturum Zorunlu | Çok kiracılı izolasyon; yalnızca kullanıcının projeleri listelenir |
| **Projects** | `POST /api/projects` | Rol Zorunlu | `ADMIN` veya `RESEARCHER`; yeni izole proje oluşturma |
| **Projects** | `GET /api/projects/{id}` | Oturum Zorunlu | IDOR koruması; yabancı projeye erişimde HTTP 403 |
| **Projects** | `POST /api/projects/{id}/problems`| Rol Zorunlu | IDOR koruması; yabancı projeye problem eklemede HTTP 403 |
| **Projects** | `POST /api/projects/{id}/experiments`| Rol Zorunlu | IDOR koruması; yabancı projeye koşu kaydetmede HTTP 403 |
| **Algorithms** | `POST /api/algorithms/corelap/solve`| Oturum + Slot | `get_job_slot` ile per-user (2) ve total (4) concurrency koruması |
| **Algorithms** | `POST /api/algorithms/craft/solve` | Oturum + Slot | `get_job_slot` ile per-user (2) ve total (4) concurrency koruması |
| **Algorithms** | `POST /api/algorithms/aldep/solve` | Oturum + Slot | `get_job_slot` ile per-user (2) ve total (4) concurrency koruması |
| **Algorithms** | `POST /api/algorithms/feasible-generator/solve` | Oturum + Slot | `get_job_slot` ile per-user (2) ve total (4) concurrency koruması |
| **Algorithms** | `POST /api/algorithms/genetic/solve`| Oturum + Slot | `get_job_slot` ile per-user (2) ve total (4) concurrency koruması |
| **Benchmarks** | `POST /api/benchmarks/run` | Oturum + Slot | `get_job_slot` ile per-user (2) ve total (4) concurrency koruması |
| **Strategy** | `POST /api/strategy/solve` | Oturum + Slot | `get_job_slot` ile per-user (2) ve total (4) concurrency koruması |
| **AI (Opsiyonel)**| `POST /api/ai/explain/*` | Çift Onay Zorunlu | `AI_ENABLED=false` varsayılan; Admin + Kullanıcı onaysız erişilemez |

---

## 4. Tünel Ağ Protokolü, Çerez ve Başlık Davranış Analizi

1. **HTTPS ve Secure Çerezler:**
   - Cloudflare Tunnel HTTPS'i edge'de sonlandırır ve yerel sunucuya `X-Forwarded-Proto: https` başlığı iletir.
   - `_should_use_secure_cookie` fonksiyonu `X-Forwarded-Proto`, `CF-Visitor` veya `SESSION_COOKIE_SECURE` ayarlarını tespit ederek `flodss_session` çerezine otomatik olarak `Secure; HttpOnly; SameSite=Lax` niteliklerini ekler.
   - Düz HTTP test ortamında bu başlık yoksa çerez yerel testleri bozmamak için esnek davranır.
2. **CSRF Koruması:**
   - FLODSS frontend'i yetkilendirmeyi `Authorization: Bearer <token>` başlığı ile taşır. Tarayıcılar siteler arası (cross-site) isteklerde özel yetkilendirme başlıklarını otomatik göndermediğinden klasik form tabanlı CSRF saldırıları tamamen etkisizdir. Çerezler ayrıca `SameSite=Lax` ile korunur.
3. **CORS:**
   - Single-origin modunda frontend ve API aynı etki alanını paylaştığından tarayıcılar CORS preflight (`OPTIONS`) sorguları göndermez.
   - Harici bir origin tanımlanmak istenirse `.env` içerisindeki `CORS_ORIGINS` virgülle ayrılmış dizgi olarak yapılandırılabilir.
4. **WebSocket Davranışı:**
   - FLODSS tamamen durumsuz (stateless) HTTP/HTTPS REST mimarisi kullanmaktadır. Sistemde aktif WebSocket kanalı yoktur. Tünel yapılandırmasında WebSocket kapalı veya varsayılanda tutulabilir; sistem çalışmasını etkilemez.
5. **Proxy Başlıkları ve Gerçek İstemci IP'si:**
   - Tünel arkasında `request.client.host` daima `127.0.0.1` görünür.
   - Geliştirilen `_get_client_ip` fonksiyonu öncelikle `CF-Connecting-IP`, ardından `X-Forwarded-For` başlıklarını parse ederek gerçek istemci IP'sini alır. Böylece tek bir kullanıcının hatalı girişleri yüzünden tüm tünel trafiğinin rate-limit'e takılması engellenmiştir.

---

## 5. Optimizasyon Kaynak Sınırları (Concurrency Governance)

FLODSS optimizasyon çözücüleri (özellikle GA ve CRAFT) CPU yoğun matematiksel operasyonlar yürütür. Kaynak tükenmesini (Denial of Service) engellemek için iki katmanlı kota mekanizması doğrulanmıştır:

```python
# app/core/security.py
class JobConcurrencyManager:
    # 1. Sistem Geneli Üst Sınır: En fazla 4 eşzamanlı optimizasyon işlemi
    # 2. Kullanıcı Başına Üst Sınır: Kullanıcı başına en fazla 2 eşzamanlı işlem
```

- **Kullanıcı Başına Kota:** Aynı kullanıcı eşzamanlı olarak 2'den fazla çözücü tetiklediğinde sistem `HTTP 429 Too Many Requests ("Concurrent job limit exceeded")` hatası döner.
- **Sistem Geneli Kota:** Farklı kullanıcılar aynı anda sisteme girdiğinde dahi, toplam çalışan çözücü sayısı `MAX_TOTAL_CONCURRENT_JOBS` (varsayılan: 4) değerini aşamaz; 5. istek geldiğinde sistem `HTTP 429 ("System-wide optimization capacity reached")` döndürerek CPU aşırı yüklenmesini önler.
- İşlem tamamlandığında veya hata aldığında context manager (`JobSlotGuard`) yuvaları (slot) anında ve hatasız serbest bırakır.

---

## 6. Cloudflare Veri Aktarımı ve Gizlilik Risk Analizi

| Veri Kategorisi | Cloudflare Tarafından Görülür mü? | Gizlilik Riski | Uygulanan Önlem & Zorunlu Kural |
| :--- | :---: | :---: | :--- |
| **Ağ Üstverisi (IP, URL, Header)** | **EVET** (Edge proxy olarak) | Düşük | URL'lerde asla gizli token taşınmaz; Bearer başlığı kullanılır. |
| **Kullanıcı E-postaları** | **EVET** (Access OTP için) | Düşük | Yalnızca kurumsal/üniversite e-postaları allowlist'e eklenir. |
| **Fabrika Problem Yükleri (JSON)** | **EVET** (TLS edge'de açılır) | **YÜKSEK (Firma verisi ise)** | **KURAL 8:** Gerçek firma verisi YASAKTIR. Yalnızca sentetik akademik benchmarklar kullanılır. |
| **Layout Çıktıları ve Koordinatlar** | **EVET** (API yanıtı olarak) | **YÜKSEK (Firma verisi ise)** | Yalnızca sentetik veriler optimize edilir; ticari sır aktarımı oluşmaz. |
| **Yapay Zekâ (Gemini) Veri Çıkışı** | **HAYIR** | Orta / Yüksek | `AI_ENABLED=false` varsayılandır; dış servise veri gitmez. |
| **Kaynak Kod ve Veritabanı** | **HAYIR** | Yok | Kod ve SQLite DB sunucuda kalır; tünelden yalnızca derlenmiş JS ve JSON geçer. |

---

## 7. Sentetik Benchmark Kuralı (Zero Proprietary Firm Data Mandate)

> [!IMPORTANT]
> **ZORUNLU AKADEMİK PROTOKOL:**
> Cloudflare bir ABD kuruluşu olduğu ve TLS sonlandırması Cloudflare kenarında gerçekleştiği için, web pilotunda **HİÇBİR GERÇEK TİCARİ FABRİKA VEYA FİRMA VERİSİ KULLANILAMAZ.**
> Sistemde yalnızca aşağıdaki açık akademik ve sentetik kıyaslama problemleri kullanılmalıdır:
> 1. `FLP_ACADEMIC_4` (Klasik 4 departmanlı test)
> 2. `FLP_MEDIUM_6` (Orta ölçekli 6 departmanlı fabrika)
> 3. `FLP_INDUSTRIAL_10` (10 departmanlı sentetik montaj fabrikası)
> 4. `HIGH_DENSITY_15` / `HIGH_DENSITY_20` (Yüksek yoğunluklu sentetik stres testleri)
> 5. `CONSTRAINED_FACTORY_12` (Kısıtlı sentetik fabrika)

---

## 8. Test ve Doğrulama Sonuçları

### 8.1 Backend Testleri
```
Command: pytest -q
Results: 408 passed, 1 warning in 28.00s
Coverage: %100 başarılı, sıfır regresyon (Phase 14.3: 398 -> Phase 14.4: 408)
```

### 8.2 Production-Benzeri Single-Origin Smoke Test
`scripts/smoke_test_single_origin.py` çalıştırılmış ve tüm adımlar doğrulanmıştır:
- `[Step 1] Requesting '/' with browser Accept header` -> `[PASS] 200 OK (HTML shell)`
- `[Step 2] Requesting compiled assets from '/assets/'` -> `[PASS] 200 OK (479,695 bytes JS)`
- `[Step 3] Querying '/api/health'` -> `[PASS] 200 OK (Status: healthy)`
- `[Step 4] Probing protected endpoint '/api/projects'` -> `[PASS] 401 Unauthorized`
- `[Step 5] Admin Auth with Cloudflare Tunnel headers` -> `[PASS] 200 OK (Secure, HttpOnly, SameSite=Lax)`
- `[Step 6] Verifying user profile via '/api/auth/me'` -> `[PASS] 200 OK (Profile verified)`
- `[Step 7] Running synthetic optimization solve (CORELAP)` -> `[PASS] 200 OK (4 Depts, Feasible: True, MHC: 700.00)`
- `[Step 8] Terminating session via '/api/auth/logout'` -> `[PASS] 200 OK (Post-logout: 401)`

### 8.3 Playwright Single-Origin Real Browser E2E Test
`frontend/e2e/test_phase14_4_single_origin_browser.py` çalıştırılmıştır:
- Gerçek Chromium tarayıcısı `http://127.0.0.1:8000/` adresine bağlanmış,
- Giriş engeli, kimlik doğrulama, Sekme 5 (2D Yerleşim Tuvali) etkileşimi ve çıkış akışı test edilmiş,
- Ekran kanıtı kaydedilmiştir: `experiments/reports/screenshots/phase14_4_single_origin_dashboard.png`.

---

## 9. Nihai Karar ve Operasyonel Sınırlar

### **GO: Cloudflare Access E-posta İzin Listesi Arkasında Pilot Dağıtım İçin ONAYLANDI**
Koşullar:
1. `docs/CLOUDFLARE_TUNNEL_SETUP_GUIDE.md` adımları eksiksiz uygulanmalı,
2. Cloudflare Access politikası `Emails -> [Belirli Tez Danışmanı ve Doktora Öğrencileri]` olarak sınırlandırılmalı,
3. `.env` içerisinde `CLOUDFLARE_ACCESS_ENFORCED=true` ve `SESSION_COOKIE_SECURE=true` etkinleştirilmeli,
4. Yalnızca sentetik benchmark verileri kullanılmalıdır.

### **STRICT NO-GO: Genel İnternete Açık / Korumasız Dağıtım KESİNLİKLE YASAKTIR**
Koşulsuz açık IP yönlendirmesi, Cloudflare Access koruması olmadan tünel açılması veya kamuya açık web demosu yapılması fikrî mülkiyet güvenliği gerekçesiyle yasaktır.
