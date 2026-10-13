# FLODSS — Phase 14.3 Deployment Readiness & Pilot Security Report

**Document Version:** 1.0.0-rc.1  
**Classification:** Confidential Institutional Research Assessment  
**Evaluation Date:** October 12, 2026  
**Final Status:** **GO FOR RESTRICTED CAMPUS VPN / PRIVATE LAB HOSTING ONLY**  
**(STRICT NO-GO FOR PUBLIC CLOUD / DIRECT INTERNET ACCESS)**  

---

## 1. Kullanıcı Arayüzü İncelemesi (Sanitized UI Review)

Phase 14.2 sırasında Playwright tarafından tam ekran ($1440 \times 900$) çözünürlükte kaydedilen gerçek tarayıcı etkileşim ekran görüntüleri incelenmiş, hassas verilerden arındırılarak aşağıdaki işlevsel değerlendirme yapılmıştır:

### 1.1 İncelenen Temel Ekranlar

#### A. Giriş ve Kimlik Doğrulama Bariyeri (`pilot_01_login_barrier.png`)
- **İnceleme**: Oturum açmamış tüm kullanıcılar için koyu temalı, odaklanmış bir `FLODSS Research Portal` modalı görüntülenmektedir. Arka plan bulanıklaştırılarak (backdrop blur) çalışma alanı verileri gizlenmektedir.
- **İşlevsellik**: E-posta, parola ve davet aktivasyonu bağlantısı tek bir kompakt kutudadır. Hatalı parola girişinde kırmızı uyarı kutusu gösterilmektedir.

#### B. Çalışma Alanı ve Proje Yöneticisi (`pilot_03_researcher_a_workspace.png`)
- **İnceleme**: Üst başlıkta FLODSS logosu, sürüm etiketi (`v1.0.0-rc.1`), sistem sağlık durumu (`Online`), kullanıcı profili ve mavi renkli `RESEARCHER` rol rozeti net olarak yer almaktadır.
- **İşlevsellik**: "Active Research Project" kartı; aktif proje açılır menüsü, "+ New Project" butonu ve "💾 Save Current Run" butonunu barındırmaktadır.

#### C. Problem Düzenleyici — Sekme 1 (`pilot_04_tab1_problem_editor.png`)
- **İnceleme**: Tesis boyutları ($150\text{ m} \times 80\text{ m}$), alan kullanımı (%86.67), 10 departman kartı ve "Load Benchmark Example" seçicisi yer almaktadır.
- **İşlevsellik**: Her departmanın gerekli alanı, en-boy oranları (min/max aspect ratio) ve sabit konum bayrakları listelenmektedir.

#### D. 2D İnteraktif Yerleşim Tuvali — Sekme 5 (`pilot_07_tab5_2d_layout.png`)
- **İnceleme**: Koyu gri fabrika zemininde her departman yüksek kontrastlı renklerle bloklar halinde çizilmektedir. Departman etiketleri, boyut ölçüleri ve ağırlık merkezleri (centroid) belirgindir.
- **İşlevsellik**: Zoom In/Out, Fit to screen, Grid ve Centroids butonları interaktif olarak çalışmaktadır. Üst bilgi çubuğunda "✓ Complete & Feasible" rozeti gösterilmektedir.

#### E. Pareto Çok Amaçlı Ödünleşim Grafiği — Sekme 6 (`pilot_08_tab6_pareto.png`)
- **İnceleme**: Malzeme Taşıma Maliyeti (MHC), İlişki Memnuniyeti (REL %) ve Yumuşak Kısıt Cezasını gösteren etkileşimli saçılım grafiği yer almaktadır.
- **İşlevsellik**: Pareto sınırındaki baskın (non-dominated) çözümler yeşil renkli noktalarla vurgulanmaktadır.

#### F. Araştırma Dışa Aktarma Merkezi — Sekme 8 (`pilot_09_tab8_export_center.png`)
- **İnceleme**: Tez için kriptografik SHA-256 yerleşim imzası, değerlendirme konfigürasyon özeti ve dışa aktarma butonları grid halinde sunulmaktadır.
- **İşlevsellik**: Metrics CSV, Comparison CSV, Layout JSON ve Layout SVG butonları tek tıkla tarayıcıya dosya indirmektedir.

### 1.2 Gerçek Tarayıcı Etkileşimleriyle Belirlenen İşlevsel Eksikler
1. **Çoklu Proje Filtreleme**: Araştırmacının 10'dan fazla projesi olduğunda basit bir `<select>` kutusu yerine metin aramalı bir arama kutusu ilerleyen sürümlerde kullanıcı deneyimini artıracaktır.
2. **Yan Yana Yerleşim Karşılaştırması**: Pareto grafiğinde iki alternatif seçildiğinde ekranı ikiye bölerek (split-screen) yan yana 2D çizim gösterme henüz desteklenmemektedir (tek aktif çözüm gösterilmektedir).
3. **Büyük Matrislerde Sayfalama**: 10-15 departman için Flow ve REL matrisleri kusursuz görünmektedir; ancak 30+ departmanlı problemlerde tablo sanallaştırma (virtual scrolling) gerekebilecektir.

---

## 2. Uzaktan Erişim Mimarisi Değerlendirmesi

Üç aday mimari güvenlik, fikrî mülkiyet, maliyet ve yönetim yükü açısından karşılaştırılmıştır:
- **Option A (Üniversite / Bölüm Ağı + VPN Sunucusu)**: En dengeli ve güvenli seçenek. Kod üniversite içinde kalır, danışman mevcut VPN'i ile erişir, ek bulut maliyeti yoktur.
- **Option B (Kimlik Doğrulamalı Özel Bulut VM)**: AWS/GCP üzerinde özel ağda çalışan VM. WireGuard veya IP kısıtı gerektirir; aylık \$20-\$60 maliyeti ve buluta kod yükleme riskleri vardır.
- **Option C (Laboratuvarda Fiziksel İş İstasyonu)**: Fiziksel bir PC'de intranet üzerinden yerel çalıştırma. Sıfır maliyet ve en yüksek kod kontrolü; ancak uzaktan danışman erişimi için laboratuvar port yönlendirmesi veya VPN köprüsü gerektirir.

### **Teknik Öneri:**
**BİRİNCİL TERCİH: Option A (Üniversite Ağı / VPN Üzerinden Özel Sanal Sunucu).**
Kurum içi Linux sunucu üzerinde Nginx + FastAPI kurulumu hem hukuki gizliliği garanti altına alır hem de tez danışmanına ek yazılım kurdurmadan pürüzsüz tarayıcı deneyimi sunar.

---

## 3. Üretime Benzer Paketleme Hazırlığı (Production Packaging)

FLODSS v1.0.0-rc.1 için aşağıdaki üretim dosyaları hazırlanmıştır:
1. **Frontend Production Build**: `frontend/dist/` dizini statik olarak derlenmiştir (Vite + TypeScript, 0 hata, 10.53s).
2. **Backend Kilitli Bağımlılıklar**: `backend/requirements-prod.txt` dosyası exact version pinning ile kilitlenmiştir (FastAPI 0.142.2, NumPy 2.5.3, SciPy 1.18.1 vb.).
3. **Gizli Anahtar Şablonu**: `deploy/.env.production.example` hazırlanmış; üretimde `chmod 600` ile korunması tanımlanmıştır.
4. **Nginx HTTPS Ters Proxy**: `deploy/nginx/flodss.conf` hazırlanmış; TLS 1.3, HSTS, 10MB yük sınırı, `/api/auth/login` hız sınırlaması ve SPA fallback yönlendirmesi içermektedir.
5. **Systemd Servis Birimi**: `deploy/systemd/flodss-backend.service` oluşturulmuş; sandbox güvenliği (`ProtectSystem=strict`, `PrivateTmp=true`, `NoNewPrivileges=true`) tanımlanmıştır.
6. **Yedekleme/Geri Yükleme Aracı**: `scripts/backup_and_restore.py` canlı test edilmiş; `PRAGMA integrity_check; OK` alınmıştır.

---

## 4. Güvenlik Engelleyicileri (Security Blockers Audit)

Aşağıdaki güvenlik denetimi maddeleri teker teker incelenmiş ve durumları listelenmiştir:

| Güvenlik Kriteri | Mevcut Durum | Değerlendirme & Gerekçe |
| :--- | :---: | :--- |
| **HTTPS Zorunluluğu** | Şablon Hazır | **BLOKER (İnternet için)**: Yerel geliştirmede HTTP çalışır; ancak uzaktan erişimde TLS 1.3 (Nginx) zorunludur. |
| **Oturum Çerezleri & Header** | Güvenli | `HttpOnly`, `SameSite=Lax`, Bearer Authorization header stratejisi etkindir. Üretimde `Secure=True` açılmalıdır. |
| **CSRF Koruması** | Güvenli | Tarayıcı oturumu `Authorization: Bearer <token>` başlığına dayanmaktadır; salt çerez tabanlı form zaafiyeti yoktur. |
| **CORS İzin Listesi** | Kısıtlı | Wildcard (`*`) yasaklanmıştır; `settings.CORS_ORIGINS` yalnızca yetkili yerel/iç alan adlarına izin verir. |
| **Veritabanı Dosya İzinleri** | Tanımlandı | `chmod 600 data/flodss_research.db` uygulanmalıdır. |
| **Kimlik Doğrulama Atlatma (Bypass)**| Engellendi | Tüm hesaplama ve proje uç noktaları `Depends(get_current_user)` ile zorunlu kılınmıştır. |
| **Hız Sınırlama (Rate Limiting)** | Single-Worker Güvenli | Bellek içi sliding-window limiter mevcuttur. Çoklu worker için Nginx `limit_req` katmanı eklenmiştir. |
| **Uzun Süren İş Koruması** | Güvenli | `JobConcurrencyManager` kullanıcı başına en fazla 1 eşzamanlı iş sınırlar; FastAPI threadpool kilitlemeyi önler. |
| **URL/Log Token Sızıntısı** | Temiz | Token'lar URL parametrelerinde taşınmaz; veritabanında SHA-256 ile özetlenir; uvicorn loglarında token basılmaz. |
| **AI Veri Aktarım Politikası** | Güvenli | `AI_ENABLED=false` varsayılandır. Çift onaylı (Admin + Kullanıcı) rıza olmadan hiçbir veri dışarıya çıkamaz. |

---

## 5. Fikrî Mülkiyet (IP) ve Gizlilik Protokolü

Pilot aşamasında yer alacak tez danışmanları ve doktora araştırmacıları için aşağıdaki yasal ve operasyonel şartlar yürürlüğe konmalıdır:
1. **Kurumsal Gizlilik Taahhütnamesi (NDA)**: Pilot katılımcılar FLODSS algoritma mimarisi, ekran görüntüleri veya performans sonuçlarını üçüncü taraflarla paylaşamaz.
2. **Tersine Mühendislik Yasağı**: İstemci veya sunucu kodlarını decompile etme, klonlama veya kopyalama kesinlikle yasaktır.
3. **Mülkiyet Beyanı**: Sistem üzerindeki tüm optimizasyon mantığı ve karar destek yapıları lisans sahibi araştırmacıya / üniversiteye aittir.
4. **Alıntı ve Atıf Protokolü**: Sistem çıktılarından üretilen akademik makalelerde ve tez bölümlerinde FLODSS v1.0.0-rc.1'e kanonik atıf yapılması zorunludur.

---

## 6. Yedi Kritik Soruya Yanıtlar

### 1. En uygun private hosting seçeneği hangisi?
**Option A: Üniversite Ağı / VPN Üzerinden Özel Sanal Sunucu.** Kurumsal IP koruması, sıfır ek maliyet ve danışman için mevcut üniversite VPN'i ile pürüzsüz erişim sağlar.

### 2. Hangi maliyet ve sunucu kaynakları bekleniyor?
- **Maliyet**: Üniversite iç sunucusu kullanılırsa **\$0 ek maliyet**. (Bulut seçilirse aylık \$20–\$60).
- **Kaynaklar**: 2–4 vCPU, 4–8 GB RAM, 20–30 GB SSD disk alanı (Ubuntu 24.04 LTS).

### 3. Uzaktan erişim için hangi teknik gereksinimler var?
Üniversite VPN bağlantısı (Eduroam/GlobalProtect), Nginx HTTPS ters proxy, kurum içi TLS sertifikası ve dahili DNS kaydı (`flodss-lab.internal.university.edu`).

### 4. Kaynak kodu kullanıcıya gönderilmeden çalıştırılabiliyor mu?
**EVET.** Kaynak kodu sunucuda kapalı bir dizinde (`/opt/flodss`) kalır. Kullanıcı (danışman/araştırmacı) yalnızca web tarayıcısı üzerinden derlenmiş arayüzü (`dist/`) ve JSON API yanıtlarını görür. Python kaynak kodları, model dosyaları ve çözücü algoritmaları istemciye asla iletilmez.

### 5. Güvenlikte kalan kritik eksikler neler?
- Genel internete açılmak istenirse Nginx düzeyinde TLS sertifikası yapılandırılmalı ve `secure=True` çerez bayrağı açılmalıdır.
- İşletim sistemi düzeyinde fiziksel cgroups/Docker CPU sınırı konulmamıştır (uygulama düzeyinde çözülmüştür).
- Dağıtık çoklu sunucu mimarisine geçilirse Redis tabanlı paylaşımlı rate limiter gerekecektir (mevcut tek sunuculu uvicorn + Nginx için gereksizdir).

### 6. Uygulama uzaktan pilot kullanıma GO mu NO-GO mu?
- **Üniversite VPN / Dahili Ağ Pilotu için**: **GO (ONAYLANDI)**.
- **Doğrudan Açık İnternet Dağıtımı için**: **STRICT NO-GO (KESİNLİKLE YASAK)**.

### 7. Test ve build sonucu nedir?
- **Backend Testleri**: **398 Passed** (0 failed, %100 başarılı, 28.16 saniye).
- **Frontend Build**: `npm run build` hatasız tamamlandı (10.53 saniye, 479 kB bundle).
- **E2E Tarayıcı Testleri**: Playwright Chromium testleri tüm adımlarda %100 başarılı.
- **Veritabanı Yedekleme**: Online yedekleme ve geri yükleme doğrulandı (`PRAGMA integrity_check; OK`).
