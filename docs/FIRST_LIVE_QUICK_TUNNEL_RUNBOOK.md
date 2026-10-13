# FLODSS: First Live Protected Quick Tunnel Runbook

**Document Version:** `1.0.0`  
**Classification:** Confidential — Academic Research Prototype  
**Audience:** System Operator / Lead Researcher / Faculty Advisor  
**Status:** **Approved for Controlled Pilot Testing**  

---

## 1. Mimari ve Güvenlik Modeli Özeti

FLODSS (`v1.0.0-rc.1`), tez danışmanları ve pilot araştırmacıların dış ağlardan sisteme erişebilmesi için **Cloudflare Protected Quick Tunnel** mimarisini destekler.

### Çift Katmanlı Savunma Mimarisi (Defense-in-Depth)

```
[Kullanıcı Tarayıcısı]
        │
        ▼ (HTTPS)
┌────────────────────────────────────────────────────────┐
│  Cloudflare Edge Perimeter (1. Savunma Katmanı)        │
│  - Geçici URL: https://<random>.trycloudflare.com      │
│  - Güvenlik Sınırı: --allowed-mail email@university.edu│
│  - Kimlik Sınaması: 6 Haneli E-posta Tek Kullanımlık   │
│                     PIN (OTP)                          │
└────────────────────────────────────────────────────────┘
        │
        ▼ (Şifreli Cloudflare Tüneli)
┌────────────────────────────────────────────────────────┐
│  Yerel Makine (127.0.0.1)                              │
│  cloudflared.exe (v2026.10.0)                          │
│  - Bellek içi allowlist doğrulaması                    │
│  - Trafiği http://127.0.0.1:8000 adresine yönlendirir  │
└────────────────────────────────────────────────────────┘
        │
        ▼ (Yalnızca 127.0.0.1 Soketi)
┌────────────────────────────────────────────────────────┐
│  FLODSS Backend & Production Frontend (2. Savunma Kat.)│
│  - Soket Kontrolü: 127.0.0.1 dışı doğrudan erişim YASAK│
│  - Kimlik Doğrulama: PBKDF2-HMAC-SHA256 Şifre / Token │
│  - Yetkilendirme: RBAC (ADMIN, RESEARCHER, VIEWER)     │
│  - Proje İzolasyonu: Kullanıcı bazlı veri sınırları    │
│  - Sentetik Veri Uyarısı: Gerçek firma verisi YASAK    │
└────────────────────────────────────────────────────────┘
```

> [!IMPORTANT]
> **Kritik Tasarım İlkesi:**
> - Quick Tunnel modunda Cloudflare'ın ilettiği HTTP başlıkları (ör. `CF-Access-Authenticated-User-Email`) kriptografik olarak imzalanmadığı ve Cloudflare belgelerinde garantilenmediği için **kullanıcı kimliği kanıtı olarak kabul edilmez**.
> - Cloudflare Edge OTP yalnızca **1. Savunma Katmanı** (çevre kapısı) olarak işlev görür.
> - Sisteme giriş ve tüm veri erişimleri, FLODSS'ın kendi kullanıcı adı, parolası, tek kullanımlık davetiye anahtarı ve oturum belirteçleri (**2. Savunma Katmanı**) ile zorunlu olarak korunur.

---

## 2. Windows Sisteminde `cloudflared` Kurulumu

### Adım 2.1: Resmi Kaynak ve Kurulum
Cloudflare Tunnel resmi Windows sürümü en az `2026.9.3` olmalıdır. Bu sistemde `2026.10.0` sürümü resmi Windows Paket Yöneticisi (`winget`) ile kurulmuştur:

```powershell
# Windows PowerShell (Yönetici veya Standart Kullanıcı)
winget install --id Cloudflare.cloudflared --accept-package-agreements --accept-source-agreements
```

*Alternatif (Manuel Taşınabilir Kurulum):*
1. [Cloudflare Tunnel İndirme Sayfası](https://developers.cloudflare.com/tunnel/downloads/) adresinden `cloudflared-windows-amd64.exe` dosyasını indirin.
2. `C:\Program Files (x86)\cloudflared\cloudflared.exe` konumuna yerleştirin ve PATH çevre değişkenine ekleyin.

### Adım 2.2: Kurulum ve `--allowed-mail` Desteğinin Doğrulanması

Aşağıdaki komutlarla sürümü ve Protected Quick Tunnel desteğini teyit edin:

```powershell
# 1. Sürüm Kontrolü (>= 2026.9.3 gereklidir)
cloudflared --version
# Beklenen Çıktı Örneği:
# cloudflared version 2026.10.0 (built 2026-10-05T08:39 UTC)

# 2. --allowed-mail Desteğinin Doğrulanması
cloudflared tunnel --help | Select-String -Pattern "allowed-mail"
# Beklenen Çıktı:
# --allowed-mail value   Email addresses or wildcard domains allowed to access a protected Quick Tunnel.
```

---

## 3. Pilot Öncesi Güvenlik Sıkılaştırması (Pre-Flight)

### Adım 3.1: Varsayılan Yönetici Parolasını Değiştirin
Kaynak kodda bilinen varsayılan parolalarla (`FlodssAdmin2026!`, `admin123`) canlı pilot **kesinlikle başlatılmamalıdır**.

Yönetici parolasını güvenli biçimde sıfırlamak için sağlanan betiği çalıştırın:

```powershell
# Rastgele 24 karakterlik yüksek entropili parola üretip atamak için:
backend\.venv\Scripts\python.exe scripts/rotate_admin_credentials.py --email admin@university.edu

# Veya kendi belirlediğiniz güçlü bir parola ile:
backend\.venv\Scripts\python.exe scripts/rotate_admin_credentials.py --email admin@university.edu --password "KarmasikGucluParola2026!"
```

### Adım 3.2: Veritabanı Dosya İzinlerini Doğrulayın
SQLite veritabanı dosyasının (`backend/data/flodss_research.db`) yalnızca yerel Windows kullanıcısı ve Administrators tarafından okunabildiğini doğrulayın:

```powershell
icacls backend/data/flodss_research.db
```
*`Everyone` veya `Users` grubuna genel okuma/yazma izni verilmemelidir.*

### Adım 3.3: Çevre Değişkenleri (`.env`)
`backend/.env` dosyanızı aşağıdaki gibi yapılandırın:

```ini
HOST=127.0.0.1
PORT=8000
ENVIRONMENT=production
CLOUDFLARE_PERIMETER_MODE=PROTECTED_QUICK_TUNNEL
CLOUDFLARE_QUICK_TUNNEL_ALLOWED_EMAILS=advisor@university.edu
```

---

## 4. Tüneli Başlatma ve Canlıya Alma Adımları

> [!CAUTION]
> - Vite development sunucusunu (`npm run dev`) internete **kesinlikle açmayın**.
> - Tek bir origin üzerinden hem API hem de derlenmiş React arayüzü `http://127.0.0.1:8000` adresinden sunulur.

### Adım 4.1: Frontend Üretim Derlemesini Alın
```powershell
cd frontend
cmd.exe /c "npm run build"
cd ..
```

### Adım 4.2: FLODSS Backend Sunucusunu Başlatın (Terminal 1)
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_backend.ps1
```
*Sunucu `http://127.0.0.1:8000` üzerinde dinlemeye başlar.*

### Adım 4.3: Protected Quick Tunnel'ı Başlatın (Terminal 2)

Danışmanın e-posta adresini girerek tüneli başlatın:

```powershell
cloudflared tunnel --url http://127.0.0.1:8000 --allowed-mail advisor@university.edu
```

*Veya birden fazla araştırmacı için:*
```powershell
cloudflared tunnel --url http://127.0.0.1:8000 --allowed-mail advisor@university.edu --allowed-mail researcher@university.edu
```

> [!WARNING]
> **E-posta Listesi Güncelleme Kuralı:**  
> `--allowed-mail` listesi, çalışan `cloudflared` sürecinin belleğinde tutulur. İzin verilen e-postalar değiştiğinde, Terminal 2'de `Ctrl+C` ile tünel durdurulmalı ve yeni parametrelerle yeniden başlatılmalıdır.

Terminalde üretilen geçici bağlantıyı kopyalayın:
`Your quick tunnel has been created! Visit it at: https://xxxx-xxxx-xxxx.trycloudflare.com`

Bu adresi güvenli kanal (e-posta/özel mesaj) üzerinden danışmanınıza iletin.

---

## 5. Tek Kullanıcılı İlk Canlı Test Planı

Aşağıdaki 6 adımlı test planını danışman ile birlikte sırayla yürütün:

| Aşama | Yapılacak İşlem | Beklenen Güvenlik Davranışı | Doğrulama Kriteri |
| :--- | :--- | :--- | :--- |
| **Aşama 1: İzin Verilen E-posta ile Cloudflare OTP** | Danışman tarayıcıda tünel URL'sini (`https://...trycloudflare.com`) açar ve `advisor@university.edu` adresini girer. | Cloudflare Edge, gelen kutusuna 6 haneli tek kullanımlık bir PIN gönderir. PIN girilince FLODSS arayüzü açılır. | Arayüzün ve "Confidential Research Pilot Notice" panosunun yüklenmesi. |
| **Aşama 2: İzin Verilmeyen E-postanın Reddi** | Farklı bir gizli sekmede izin verilmemiş bir e-posta adresi (`intruder@outside.net`) girilir. | Cloudflare Edge istek kodu göndermeyi veya erişim vermeyi derhal reddeder. | Sayfa içeriğine veya FLODSS backend'ine hiçbir erişim sağlanamaması. |
| **Aşama 3: FLODSS Uygulama İçi Giriş** | Danışman, kendisine tahsis edilen FLODSS e-posta ve güçlü parolasını (veya tek kullanımlık davetiye bağlantısını) kullanarak giriş yapar. | FLODSS PBKDF2 hash kontrolü yapar, oturum açar ve `HttpOnly; Secure; SameSite=Lax` oturum çerezi üretir. | Başarılı giriş; sağ üstte kullanıcı profilinin ve rolünün görünmesi. |
| **Aşama 4: Örnek Fabrika Optimizasyonu** | Danışman, hazır sentetik benchmark (ör. 4 departmanlı veya 8 departmanlı test problemi) seçip CORELAP veya Genetic Algorithm çalıştırır. | Optimizasyon sunucu tarafında 120 saniyelik CPU sınırı içinde çalışır; 2D yerleşim planı ve Pareto grafiği çizilir. | MHC skoru, feasibility doğrulaması ve 2D blok planının hatasız render edilmesi. |
| **Aşama 5: Güvenli Çıkış (Logout)** | Danışman sağ üstteki "Logout" düğmesine basar. | Sunucu oturumu `sessions` tablosunda iptal eder (`is_revoked = 1`), tarayıcı çerezi silinir. | Giriş ekranına yönlendirme; korumalı uç noktalara yapılan sonraki isteklerin HTTP 401 dönmesi. |
| **Aşama 6: Tünel Kapatılınca Bağlantının Kesilmesi** | Operatör Terminal 2'de `Ctrl+C` tuşlarına basarak `cloudflared` sürecini sonlandırır. | Tünel soketi derhal düşer; Cloudflare Edge `Error 1033 (Argo Tunnel error)` veya `Connection Refused` döndürür. | Tarayıcı yenilendiğinde uygulamanın tamamen erişilemez hale gelmesi. |

---

## 6. Kalan Riskler ve Operasyonel Sınırlar

1. **Geçici URL Ömrü:** Tünel kapatılıp yeniden açıldığında rastgele yeni bir subdomain atanır. Kalıcı domain gerekirse `MANAGED_ACCESS` (Cloudflare Zero Trust kalıcı tünel) moduna geçilmelidir.
2. **Eşzamanlı İstek Sınırı:** Quick Tunnel eşzamanlı maksimum 200 HTTP isteği kabul eder. Yalnızca birebir danışman pilotu için uygundur.
3. **Sentetik Veri Protokolü:** Arayüzde kırmızı uyarı panosu bulunmaktadır. Danışmana gerçek firma layout verisi girmemesi yönünde sözlü/yazılı protokol hatırlatılmalıdır.
