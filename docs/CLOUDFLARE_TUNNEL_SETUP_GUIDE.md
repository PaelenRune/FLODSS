# FLODSS — Cloudflare Tunnel & Cloudflare Access Kurulum Rehberi

**Sürüm:** `v1.0.0-rc.1`  
**Mimari:** Cloudflare Zero Trust (Access + Tunnel) + FLODSS Single-Origin FastAPI  
**Erişim Modeli:** Davetli ve İki Kademeli Doğrulama (Invite-Only & Dual Perimeter)  
**Güvenlik Sınıfı:** Akademik / Kapalı Kaynak Araştırma Prototipi  

---

## 1. Genel Mimari ve Çalışma Prensibi

FLODSS v1.0.0-rc.1, tez danışmanı ve seçilmiş araştırmacıların uzaktan tarayıcı üzerinden erişebilmesi için **Cloudflare Tunnel (`cloudflared`)** ve **Cloudflare Access (Zero Trust)** koruması arkasında çalıştırılmak üzere optimize edilmiştir.

```
[Kullanıcı Tarayıcısı]
         │  (HTTPS / TLS 1.3)
         ▼
┌────────────────────────────────────────────────────────┐
│ Cloudflare Edge Network                                │
│ 1. TLS 1.3 Sonlandırma                                 │
│ 2. Cloudflare Access OTP / IdP Doğrulama (1. Kapı)     │
│    -> Yalnızca Allowlist'teki e-postalar geçebilir     │
│ 3. Header Enjeksiyonu (CF-Access-Email, CF-IP, vb.)    │
└────────────────────────────────────────────────────────┘
         │  (Giden Şifreli Tünel - Port açmaya gerek yok)
         ▼
┌────────────────────────────────────────────────────────┐
│ Yerel Sunucu / İş İstasyonu                            │
│ 1. cloudflared Daemon                                  │
│ 2. FLODSS Single-Origin FastAPI (:8000)                │
│    - Statik Frontend (dist/index.html & assets/)       │
│    - REST API Router (/api/...)                        │
│    - FLODSS Rol ve Proje Kimlik Doğrulaması (2. Kapı) │
│    - SQLite Veritabanı (:8000 arkasında izole)         │
└────────────────────────────────────────────────────────┘
```

### Neden Bu Mimari Seçildi?
- **Sıfır Port Açma (No Port Forwarding):** Güvenlik duvarında veya ev/ofis/laboratuvar modeminde hiçbir 80/443 portu açılmaz.
- **İki Aşamalı Güvenlik (Defense-in-Depth):**
  - **1. Kapı (Cloudflare Access):** İzin verilmeyen internet kullanıcıları ve botlar sunucuya asla ulaşamaz; doğrudan Cloudflare kenarında engellenir.
  - **2. Kapı (FLODSS Auth):** Kullanıcı içeri girse dahi bağımsız araştırma hesabı, proje izolasyonu ve rol kısıtları devrededir.
- **Tek Origin (Single-Origin):** Frontend ve API aynı origin altındadır; Vite development sunucusu çalıştırılmaz, CORS karmaşası oluşmaz.

---

## 2. Ön Gereksinimler

1. Cloudflare hesabı (Ücretsiz plan yeterlidir).
2. Cloudflare DNS üzerinde yönetilen bir alan adı (Örn: `ornek-arastirma.edu` veya `alanadiniz.com`).
3. Cloudflare Zero Trust paneline erişim (İlk açılışta ücretsiz "Free Plan" seçilmelidir).
4. FLODSS'ın kurulacağı bilgisayar / sunucu (Windows, Linux veya macOS).

---

## 3. Adım Adım Kurulum Kılavuzu

### Adım 1: FLODSS Ortamını Hazırlama
Sunucu üzerindeki `.env` dosyasını üretim moduna alın:

```bash
# FLODSS .env ayarları
DEBUG=false
AUTH_ENFORCED=true
SESSION_COOKIE_SECURE=true
CLOUDFLARE_ACCESS_ENFORCED=true
MAX_CONCURRENT_JOBS_PER_USER=2
MAX_TOTAL_CONCURRENT_JOBS=4
AI_ENABLED=false
```

Frontend'in derlenmiş olduğundan emin olun:
```bash
# frontend klasöründe:
npm run build
# dist/ klasörünün oluştuğunu teyit edin
```

FastAPI sunucusunu single-origin modunda başlatın:
```bash
# backend klasöründe:
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

---

### Adım 2: Cloudflare Zero Trust Paneline Giriş
1. [Cloudflare Dashboard](https://dash.cloudflare.com/) sayfasına gidin.
2. Sol menüden **Zero Trust** seçeneğine tıklayın.
3. İlk defa kullanıyorsanız bir organizasyon/takım adı belirleyin (Örn: `flodss-lab`).

---

### Adım 3: Cloudflare Tunnel Oluşturma
1. Zero Trust panelinde sol menüden **Networks** -> **Tunnels** sekmesine gidin.
2. **Add a tunnel** butonuna tıklayın.
3. Bağlayıcı türü olarak **Cloudflare (cloudflared)** seçeneğini işaretleyin.
4. Tünele bir ad verin: `flodss-research-tunnel` -> **Save tunnel**.
5. Ekranda sunucunuzun işletim sistemine (Windows / Debian / Ubuntu) uygun yükleme komutu görüntülenecektir.
   - Örn. Windows için: `winget install --id Cloudflare.cloudflared` veya verilen `.exe` indirilir.
   - Panelde verilen tek satırlık `cloudflared.exe service install <TOKEN>` komutu **yönetici yetkileriyle** çalıştırılır.
6. Sunucunuz bağlandığında panelde durum **HEALTHY** olarak görünecektir -> **Next** butonuna tıklayın.

---

### Adım 4: Public Hostname ve Yönlendirme (Public Hostname Routing)
1. **Public Hostname** sekmesinde:
   - **Subdomain:** `pilot` (veya `flodss`)
   - **Domain:** Alan adınızı seçin (Örn: `alanadiniz.com`)
   - *Oluşacak tam adres: `https://pilot.alanadiniz.com`*
2. **Service** bölümünde:
   - **Type:** `HTTP`
   - **URL:** `127.0.0.1:8000`
3. **Additional Application Settings** -> **HTTP Settings**:
   - `HTTP2 support`: Etkin
   - `Disable Chunked Encoding`: Kapalı
4. **Save tunnel** butonuna tıklayın.

---

### Adım 5: Cloudflare Access İle E-posta İzin Listesi Oluşturma (1. Kapı)
Bu adım, web pilotunun internet tarayıcılarına tamamen kapalı kalmasını ve **yalnızca davet edilen araştırmacıların** erişmesini sağlar:

1. Zero Trust sol menüsünden **Access** -> **Applications** sekmesine gidin.
2. **Add an application** -> **Self-hosted** seçeneğini seçin.
3. **Application Configuration**:
   - **Application name:** `FLODSS Pilot Access`
   - **Application domain:** `pilot.alanadiniz.com`
   - **Session Duration:** `24 hours`
4. **Next** butonuna tıklayarak **Policy** aşamasına geçin:
   - **Policy name:** `Authorized Researchers Only`
   - **Action:** `Allow`
5. **Configure rules (İzin Kuralları)**:
   - **Selector:** `Emails`
   - **Value:** Yalnızca tez danışmanı ve pilot araştırmacıların e-posta adreslerini girin:
     - `danisman@universite.edu.tr`
     - `arastirmaci1@universite.edu.tr`
     - `admin@flodss.local` (Yönetici)
6. **Next** -> **Add application** diyerek kaydedin.

---

## 4. İki Kademeli Giriş Akışı (Kullanıcı Deneyimi)

Pilot katılımcısı tarayıcısından `https://pilot.alanadiniz.com` adresini açtığında:

1. **Aşama 1 (Cloudflare Access Doğrulaması):**
   - Ekranda Cloudflare Zero Trust kimlik doğrulama sayfası çıkar.
   - Kullanıcı kayıtlı e-posta adresini girer.
   - Cloudflare kullanıcının e-postasına tek kullanımlık bir PIN (One-Time PIN) gönderir.
   - PIN girildikten sonra Cloudflare tünel üzerinden FLODSS'a erişim izni verir.

2. **Aşama 2 (FLODSS Uygulama İçi Giriş):**
   - Kullanıcı FLODSS arayüzü ile karşılaşır (`FLODSS Research Portal`).
   - Kullanıcı ilk defa katılıyorsa: Yönetici tarafından kendisine verilen davet bağlantısı (`/api/auth/invitations/{token}`) üzerinden şifresini belirler.
   - Kullanıcı daha önce kayıt olduysa: Kendi FLODSS şifresiyle oturum açar.
   - `CLOUDFLARE_ACCESS_ENFORCED=true` sayesinde, kullanıcının FLODSS hesabı Cloudflare'da doğrulanan e-posta adresiyle **birebir eşleşmek zorundadır**.

---

## 5. Sorun Giderme ve Güvenlik Kontrolleri

| Sorun Belirtisi | Olası Neden | Çözüm Adımı |
| :--- | :--- | :--- |
| **502 Bad Gateway** | Yerel Uvicorn çalışmıyor | `127.0.0.1:8000` üzerinde Uvicorn'un açık olduğunu `curl http://127.0.0.1:8000/api/health` ile kontrol edin. |
| **403 Forbidden (Cloudflare)** | E-posta allowlist'te yok | Cloudflare Access Policy içerisine kullanıcının e-postasını ekleyin. |
| **403 Forbidden (FLODSS)** | Cloudflare e-postası ile FLODSS kullanıcı e-postası uyuşmuyor | Kullanıcının Cloudflare Access'e girdiği e-posta ile FLODSS'a girdiği e-postanın harfi harfine aynı olduğunu teyit edin. |
| **429 Too Many Requests** | Eşzamanlı iş sınırı aşıldı | Devam eden optimizasyonun bitmesini bekleyin (`MAX_TOTAL_CONCURRENT_JOBS=4`). |
| **Cookie Hatası (Oturum Açılmıyor)** | Tarayıcı HTTPS yerine HTTP görüyor | Cloudflare Tunnel'da HTTPS açık olduğundan ve `X-Forwarded-Proto: https` iletildiğinden emin olun. |
