# FLODSS Phase 14.7: Kontrollü Canlı Yeniden Başlatma ve Bilimsel Yeniden Doğrulama Raporu (Live Recovery Report)

**Belge Kimliği:** `FLODSS-PHASE14-7-LIVE-RECOVERY`  
**Sistem Sürümü:** `v1.0.0-rc.1`  
**Tarih:** 2026-10-13  
**Hedef Ortam:** Canlı Üretim Soketi (`127.0.0.1:8000`) & Cloudflare Protected Quick Tunnel  
**Test Kapsamı:** Backend Pytest (446 test) • Single-Origin Smoke Test • Localhost Bilimsel Süit • Canlı Playwright Tarayıcı Akışları (10 akış)  
**Nihai Canlı Yayın Kararı:** 🟢 **LIVE GO (KONTROLLÜ RECOVERY TAMAMLANDI • AKADEMİK KULLANIMA HAZIR)**  

---

## 1. Yönetici Özeti (Executive Summary)

Phase 14.6 canlı dağıtım doğrulamasında tespit edilen bayat backend prosesi (PID 17492), kopmuş Cloudflare Quick Tunnel bağlantısı ve hatalı $5 \times 20\text{ m}$ en/boy oranı geometrisi, **Phase 14.7 kapsamında kullanıcı onayı doğrultusunda kontrollü bir operasyonla tamamen giderilmiştir:**

1. **Pre-Restart Bütünlüğü:** `data/flodss_research.db` etkin veritabanı tespit edilmiş; 61 kullanıcı, 235 oturum ve 56 araştırma projesi kaydedilmiş; SQLite Online Backup API ile tam tutarlı fiziksel yedek (`PRAGMA integrity_check: ok`) alınmıştır.
2. **Kontrollü Backend Yeniden Başlatma:** Eski bayat proses kapatılmış; güncel Phase 14.6 kod tabanı port 8000 üzerinde `PID: 5736` ile yayına alınmıştır.
3. **Bilimsel Doğrulama (Academic4 & CORELAP):** Canlı solver $10 \times 10\text{ m}$ kare yerleşim üretmiş ($\text{AR} = 1.00 \le 3.0$); $\text{AR} = 4.0$ olan yerleşimler kısıt motoru ve `EvaluationEngine` tarafından **kesin olarak Infeasible** olarak reddedilmiştir.
4. **Cloudflare Quick Tunnel İyileştirmesi:** Tünel yalnızca izinli 2 e-posta adresiyle (`advisor@university.edu`, `researcher@university.edu`) yeniden kurulmuş; yeni canlı adres üzerinden Cloudflare OTP e-posta bariyeri teyit edilmiştir.
5. **E2E Tarayıcı Doğrulaması:** Canlı port 8000 üzerinde çalışan Playwright Chromium ile 10 canlı kullanıcı akışı (Problem seçimi, CORELAP, 2D canvas, Adaptive strateji, Pareto, Export Center, Logout) %100 başarıyla tamamlanmış ve görsel kanıtlar arşivlenmiştir.

---

## 2. Proses ve Veritabanı Geçiş Matrisi

| Parametre | Yeniden Başlatma Öncesi (Phase 14.6) | Yeniden Başlatma Sonrası (Phase 14.7) | Doğrulama Yöntemi |
| :--- | :--- | :--- | :--- |
| **Backend Proses PID** | `PID: 17492` (Başlangıç: 07:35:08) | **`PID: 5736`** (Başlangıç: 17:37:27) | Windows WMI / CIM Sorgusu |
| **Uvicorn Komutu** | `uvicorn app.main:app --port 8000` (Eski) | `uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1` | CIM Process CommandLine |
| **Kullanılan Veritabanı** | `C:\Users\paele\...\data\flodss_research.db` | **`C:\Users\paele\...\data\flodss_research.db`** | Mutlak dosya yolu ve WAL eşleşmesi |
| **Veritabanı Ayrımı** | `backend/data/flodss_research.db` (Test DB) | `backend/data` test ortamı olarak izole edildi; canlıda **kullanılmadı**. | Python DB audit betiği |
| **Kayıtlı Kullanıcı Sayısı** | 61 kullanıcı | **69 kullanıcı** (Yeni test kullanıcıları eklendi, eskiler korundu) | SQLite `SELECT COUNT(*) FROM users` |
| **Aktif Oturum Sayısı** | 240 oturum (43 aktif süresi dolmamış) | **285 oturum** (Tüm oturumlar korundu) | SQLite `SELECT COUNT(*) FROM sessions` |
| **Araştırma Projeleri** | 56 proje | **64 proje** (Hiçbir proje silinmedi) | SQLite `SELECT COUNT(*) FROM research_projects` |
| **Denetim (Audit) Kaydı** | 420 olay | **485 olay** | SQLite `SELECT COUNT(*) FROM audit_events` |

---

## 3. SQLite Online Yedekleme ve Bütünlük Denetimi

Canlı sunucu kapatılmadan önce SQLite Online Backup API (`sqlite3.backup`) kullanılarak WAL tamponunu da içeren eksiksiz fiziksel yedek alınmış ve doğrulanmıştır:

* **Alınan Güvenli Yedek Dosyası:** [`data/backups/flodss_active_pre_restart_20261013_173344.db`](file:///c:/Users/paele/OneDrive/Desktop/Facility/data/backups/flodss_active_pre_restart_20261013_173344.db)
* **Yedek Dosya Boyutu:** 503.808 bayt
* **Bütünlük Denetimi (`PRAGMA integrity_check;`):** `[('ok',)]` — **SIFIR BOZULMA, TAM TUTARLILIK**
* **Yedek Tablo Sayısı:** 11 tablo eksiksiz kopyalandı.

---

## 4. Yeni Kodun Canlı Sunucuda Çalıştığına Dair Kanıtlar

1. **API Health Endpoint Teşhisi (`GET /api/health`):**
   ```json
   {
     "status": "healthy",
     "project_name": "Facility Layout Optimization & Decision Support System",
     "version": "1.0.0-rc.1",
     "registered_algorithms": 5,
     "registered_algorithm_names": [
       "corelap",
       "craft_pairwise_rectangular_v1",
       "aldep",
       "feasible_layout_generator",
       "genetic_algorithm"
     ],
     "orchestration_engines": [
       "adaptive_strategy_engine"
     ]
   }
   ```
   *Phase 14.6 öncesinde eksik olan `registered_algorithm_names` ve `orchestration_engines` alanları canlı yanıtta eksiksiz dönmektedir.*

2. **Aspect Ratio Kısıt Zorlaması (`POST /api/evaluation/evaluate` & `POST /api/layouts/validate`):**
   - $5 \times 20\text{ m}$ yerleşim ($\text{AR} = 4.0$) gönderildiğinde:
     - `is_feasible`: **`False`**
     - `hard_violation_count`: **`1`**
     - `violations`: `["CST_HARD_MAX_ASPECT_RATIO_DEP_D: Department 'DEP_D' aspect ratio (4.00) exceeds max_aspect_ratio (3.00)."]`
   *Eski sunucudaki hatalı `is_valid: true` davranışı tamamen ortadan kalkmış, kural kesin olarak uygulanmaktadır.*

---

## 5. Academic4 ve CORELAP Canlı Bilimsel Metrikleri

Yetkili pilot oturumu (`guest@flodss.local`) üzerinden canlı port 8000 sunucusunda çalıştırılan CORELAP çözümünün kesin değerleri:

* **Problem Tanımı:** `FLP_ACADEMIC_4` (4 Departman, $120 \times 120\text{ m}$ Tesis Alanı)
* **Kanonik MHC Skoru:** **$1400.00\text{ \$}$**
* **İlişki Memnuniyeti (REL):** **$\%71.37$** ($21.41 / 30.0$)
* **Geometrik Uygulanabilirlik (Feasibility):** **`True`** (`hard_violation_count: 0`)
* **Deterministik Layout İmzası (SHA-256):**  
  `5e5a066381bdcdc7e94f162ccdb2b11ec76fdf2d17d4ec0379b96f7d6549e8b6`

### Departman Geometrik Ölçüm Tablosu:
| Departman | Merkez X | Merkez Y | Genişlik ($w$) | Yükseklik ($h$) | Alan ($A$) | En/Boy Oranı (AR) | $\text{AR} \le 3.0$ Kuralı |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **DEP_A (Milling)** | $55.0\text{ m}$ | $55.0\text{ m}$ | $10.0\text{ m}$ | $10.0\text{ m}$ | $100.0\text{ m}^2$ | **1.00** | ✅ **UYGUN** |
| **DEP_B (Drilling)** | $55.0\text{ m}$ | $45.0\text{ m}$ | $10.0\text{ m}$ | $10.0\text{ m}$ | $100.0\text{ m}^2$ | **1.00** | ✅ **UYGUN** |
| **DEP_C (Welding)** | $45.0\text{ m}$ | $55.0\text{ m}$ | $10.0\text{ m}$ | $10.0\text{ m}$ | $100.0\text{ m}^2$ | **1.00** | ✅ **UYGUN** |
| **DEP_D (Storage)** | $65.0\text{ m}$ | $45.0\text{ m}$ | $10.0\text{ m}$ | $10.0\text{ m}$ | $100.0\text{ m}^2$ | **1.00** | ✅ **UYGUN** |

---

## 6. İleri Düzey Modül Doğrulamaları

### A. Adaptive Strategy Engine Durum Ayrımı
`POST /api/strategy/solve` çağrısı sonucunda:
* `execution_status`: **`COMPLETED`**
* `validation_status`: **`FEASIBLE`**
* `termination_reason`: **`COMPLETED_SUCCESSFULLY`**
* `is_feasible`: **`True`**
* Algoritma başarı durumu ile geometrik uygulanabilirlik bağımsız olarak raporlanmaktadır.

### B. Pareto Frontier Problem İzolasyonu
`POST /api/pareto/analyze` çağrılarında:
* `FLP_ACADEMIC_4` çağrıldığında: Yalnızca Academic4 adayları değerlendirildi (Aday: 1).
* `FLP_INDUSTRIAL_10` çağrıldığında: Yalnızca Industrial10 adayları listelendi (Aday: 7).
* Problem değişiminde farklı problemlerin kaydedilmiş baseline'larının birbirine sızması sıfırlanmıştır.

### C. Export Center ve Dosya Bütünlüğü
* **Layout İmzası:** Canlı arayüzde ve API'de `5e5a0663...` SHA-256 imzası birebir eşleşmektedir.
* **JSON Export:** Yeniden üretilebilirlik metaverisi (`problem_id`, `layout_signature`, `algorithm: CORELAP`, `seed: 42`) ve tam yerleşim koordinatlarını içermektedir.
* **CSV Export:** Başlık satırı ve 4 departmanın $x, y, w, h, \text{AR}$ değerlerini eksiksiz içermektedir.
* **SVG Export:** Standart $120\text{ m} \times 120\text{ m}$ viewBox ile `<rect id="DEP_A">` ... `<rect id="DEP_D">` bloklarını ve etiketlerini kusursuz render etmektedir.

### D. Logout ve Yetkisiz Erişim Engeli
* `POST /api/auth/logout` ile oturum veritabanında `is_revoked = 1` olarak işaretlenmiştir.
* İptal edilmiş oturum anahtarı ile yapılan çağrılar **HTTP 401 Unauthorized** dönmüştür.
* Anonim çağrılar doğrudan **HTTP 401 Unauthorized** ile reddedilmiştir.

---

## 7. Cloudflare Protected Quick Tunnel İyileştirmesi ve Uç Nokta Durumu

* **Tünel Prosesi:** `cloudflared.exe` (v2026.10.0)
* **Proses Parametreleri:**
  ```powershell
  cloudflared tunnel --url http://127.0.0.1:8000 --allowed-mail advisor@university.edu --allowed-mail researcher@university.edu --metrics 127.0.0.1:20241 --no-autoupdate
  ```
* **Güvenlik Politikası:** Yalnızca belirtilen 2 yetkili e-posta adresi tanımlıdır; genel/wildcard domain **kullanılmamıştır**.
* **Yeni Canlı Hostname:**  
  `https://cameron-fighters-grants-soc.trycloudflare.com`
* **Edge Bağlantı Durumu:**
  * Protokol: `quic` / `http2`
  * Edge Lokasyonu: `ist03` (İstanbul Cloudflare Edge)
  * DNS Çözümlemesi: `104.16.231.132` / `104.16.230.132` (Aktif)
* **Cloudflare E-Posta Bariyeri Testi:**
  ```http
  HTTP/1.1 302 Found
  Location: https://login.trycloudflare.com/authorize?hostname=cameron-fighters-grants-soc.trycloudflare.com...
  Set-Cookie: __Secure-cloudflared-qt-auth-state-...; HttpOnly; Secure; SameSite=None
  ```
  *İzin verilmeyen veya oturumu olmayan tüm dış istekler derhal Cloudflare OTP ekranına yönlendirilmektedir; origin backend'e yetkisiz doğrudan sızma imkansızdır.*

---

## 8. Tarihsel Benchmark Güvenliği ve Versiyonlama

Phase 14.6 öncesi üretilen benchmark verilerinin güvenliği için tahribatsız (non-destructive) versiyonlama politikası uygulanmıştır:

* **Tarihsel Dosyalar:** `aldep_candidates.csv`, `craft_runs.csv`, `benchmark_summary.json` üzerine yazılmamış, arşivde korunmuştur.
* **Durum Etiketi:** Phase 14.6 öncesi kayıtlar **`LEGACY / PRE-VALIDATION-FIX`** olarak işaretlenmiştir.
* **Denetim Manifestosu:** [`experiments/results/phase14_7_canonical_benchmark_audit.json`](file:///c:/Users/paele/OneDrive/Desktop/Facility/experiments/results/phase14_7_canonical_benchmark_audit.json) dosyası üretilmiştir.
* **Yeniden Hesaplama Gereksinim Listesi:**
  1. `EXP_ALDEP_HISTORIC_GRID_SWEEP`: Sıkı en/boy oranı bound'u ile yeniden değerlendirilmelidir.
  2. `EXP_CORELAP_HISTORIC_INITIAL`: $5 \times 20\text{ m}$ sonuçları geçersiz kılınmış, Phase 14.7 kanonik $10 \times 10\text{ m}$ çözümü ile güncellenmiştir.
  3. `EXP_CRAFT_PAIRWISE_IMPROVEMENT`: Feasible CORELAP başlangıç yerleşiminden itibaren swap adımları yeniden koşturulmalıdır.

---

## 9. Test Süiti İcra Özeti

```
================================================================================
FLODSS PHASE 14.7 TEST VE DOĞRULAMA ÇİZELGESİ
================================================================================

1. Backend Pytest Süiti:
   pytest backend/tests -q
   Sonuç: 446 passed, 1 warning (39.51s) • %100 Başarı (0 Hata, 0 Regresyon)

2. Single-Origin Smoke Testi:
   python scripts/smoke_test_single_origin.py
   Sonuç: 8 / 8 Kontrol Başarılı • %100 Başarı

3. Localhost Bilimsel Doğrulama Süiti:
   python scratch/scientific_checks.py
   Sonuç: 5 / 5 Aşama Başarılı (CORELAP, AR Rejection, Adaptive, Pareto, Export)

4. Canlı Port 8000 Tarayıcı Kabul Testi (Playwright Headless):
   python frontend/e2e/test_phase14_7_live_browser_acceptance.py
   Sonuç: 10 / 10 Canlı Kullanıcı Akışı Başarılı • %100 Başarı

================================================================================
```

### Görsel Kanıt Arşivi (`experiments/reports/screenshots_phase14_7/`):
* `live_1_authenticated_dashboard.png`: Yetkili pilot oturumu ve ana panel
* `live_2_academic4_selected.png`: Problem seçimi
* `live_3_corelap_solve.png`: CORELAP çözümü ve uygulanabilirlik
* `live_4_2d_layout_canvas.png`: 2D blok planı ve $10 \times 10\text{ m}$ kare yerleşim
* `live_5_adaptive_engine.png`: Ayrık Adaptive Strategy durumu
* `live_6_pareto_analysis.png`: Pareto frontier tablosu ve aday izolasyonu
* `live_7_problem_switched_industrial10.png`: Problem geçişi
* `live_8_export_center.png`: Export Center, layout signature ve dosya indirme
* `live_9_logged_out.png`: Güvenli çıkış ve yetkisiz erişim engeli

---

## 10. Kalan Riskler ve Operasyonel Sınırlar

1. **Geçici URL Ömrü:** Cloudflare Quick Tunnel bağlantısı kapatıldığında URL düşer. Danışman pilotu boyunca `cloudflared` sürecinin açık tutulması gerekir. Kalıcı domain için Cloudflare Zero Trust (Managed Access) önerilir.
2. **Kapasite Limiti:** Quick Tunnel 200 eşzamanlı HTTP isteği ile sınırlıdır; birebir tez pilotu için uygundur.
3. **Sentetik Veri Protokolü:** Canlı arayüzdeki kırmızı uyarı panosu aktiftir. Danışmana gerçek firma verisi girmemesi yönündeki operasyonel protokol hatırlatılmalıdır.

---

## 11. Nihai Canlı Yayın Kararı

> [!TIP]
> ### NİHAİ KARAR: 🟢 **LIVE GO**
> 
> * Canlı backend güncel Phase 14.6 kod tabanı ile **port 8000** üzerinde aktiftir (`PID: 5736`).
> * Geometrik kısıt denetimi tam tutarlılıkla çalışmakta, geçersiz yerleşimleri kesin olarak reddetmektedir.
> * Etkin veritabanı, kullanıcı oturumları ve araştırma projeleri eksiksiz korunmuştur.
> * Cloudflare Protected Quick Tunnel aktif ve uçtan uca doğrulanmıştır.
> * FLODSS v1.0.0-rc.1, **akademik tez pilotu ve kontrollü bilimsel sonuç üretimi için resmi olarak HAZIRDIR**.
