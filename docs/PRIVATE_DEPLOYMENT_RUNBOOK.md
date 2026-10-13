# FLODSS — Private Research Deployment Runbook (Phase 14.3)

## 1. Hazırlık ve Önkoşullar

Bu doküman, FLODSS v1.0.0-rc.1 platformunun üniversite iç ağı veya özel araştırma sunucusu üzerine **kapalı kaynaklı ve güvenli** biçimde kurulması için adım adım operasyonel talimatları içerir.

> **ÖNEMLİ**: Sunucu internete açık olmamalıdır. Yalnızca yerel ağ (LAN) veya VPN üzerinden erişilebilir olmalıdır.

---

## 2. Adım Adım Kurulum Kılavuzu

### 2.1 Sistem Kullanıcısı ve Dizin Yapısı
Sunucuda root yerine izole bir `flodss` servis kullanıcısı oluşturun:
```bash
sudo useradd -m -s /bin/bash flodss
sudo mkdir -p /opt/flodss/{backend,frontend/dist,data/backups,deploy,logs}
sudo chown -R flodss:flodss /opt/flodss
```

### 2.2 Kod Paketinin Sunucuya Aktarımı (Kapalı Kaynak Protokolü)
Genel git depoları kullanılmaz. Geliştirme makinesinden güvenli bir tarball oluşturup SCP ile aktarın:
```powershell
# Geliştirme makinesinde (Windows PowerShell):
tar --exclude=".venv" --exclude="node_modules" --exclude="tests/__pycache__" -czvf flodss_v1.0.0_rc1.tar.gz backend/ frontend/dist/ deploy/ scripts/ data/examples/
scp flodss_v1.0.0_rc1.tar.gz admin@10.0.0.50:/tmp/
```
Sunucuda açın:
```bash
# Sunucu terminalinde:
sudo -u flodss tar -xzvf /tmp/flodss_v1.0.0_rc1.tar.gz -C /opt/flodss/
```

### 2.3 Python Sanal Ortamı ve Kilitli Bağımlılıkların Kurulumu
```bash
cd /opt/flodss/backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install --no-cache-dir -r requirements-prod.txt
```

### 2.4 Üretim Ortam Değişkenleri Yapılandırması
```bash
sudo -u flodss cp /opt/flodss/deploy/.env.production.example /opt/flodss/.env.production
chmod 600 /opt/flodss/.env.production
```
Gizli anahtarları oluşturun ve `.env.production` içine yazın:
```bash
# Yüksek entropili gizli anahtar üretimi:
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(48))"
python3 -c "import secrets; print('DEFAULT_ADMIN_PASSWORD=' + secrets.token_urlsafe(18))"
```
Ayrıca `CORS_ORIGINS` satırını sunucunun dahili IP/alan adı ile güncelleyin:
```ini
CORS_ORIGINS='["https://flodss-lab.internal.university.edu", "http://10.0.0.50"]'
```

### 2.5 Veritabanı ve İzinlerin Güvenliği
```bash
chmod 700 /opt/flodss/data
touch /opt/flodss/data/flodss_research.db
chmod 600 /opt/flodss/data/flodss_research.db
```

### 2.6 Systemd Servisi Kurulumu ve Başlatma
```bash
sudo cp /opt/flodss/deploy/systemd/flodss-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable flodss-backend
sudo systemctl start flodss-backend
sudo systemctl status flodss-backend
```
Servisin yerel sokette çalıştığını teyit edin:
```bash
curl -s http://127.0.0.1:8000/api/health | jq .
```

### 2.7 Nginx HTTPS Ters Proxy Yapılandırması
Kurum içi TLS sertifikalarını yerleştirin:
- `/etc/ssl/certs/flodss_internal.crt`
- `/etc/ssl/private/flodss_internal.key`

Nginx konfigürasyonunu aktif edin:
```bash
sudo cp /opt/flodss/deploy/nginx/flodss.conf /etc/nginx/sites-available/flodss
sudo ln -s /etc/nginx/sites-available/flodss /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 2.8 Otomatik Yedekleme Görevi (Cron Job)
Her gece 03:00'te otomatik ve tutarlı veritabanı yedeği almak için:
```bash
sudo -u flodss crontab -e
```
Satırını ekleyin:
```cron
0 3 * * * /opt/flodss/backend/.venv/bin/python /opt/flodss/scripts/backup_and_restore.py backup >> /opt/flodss/logs/backup.log 2>&1
```

---

## 3. Dağıtım Sonrası Doğrulama & Duman Testleri (Smoke Tests)

1. **HTTPS ve Güvenlik Başlıkları**:
   ```bash
   curl -I -k https://127.0.0.1/
   # Beklenen başlıklar:
   # Strict-Transport-Security, X-Content-Type-Options: nosniff, X-Frame-Options: DENY
   ```
2. **API Sağlık Kontrolü**:
   ```bash
   curl -k https://127.0.0.1/api/health
   # Yanıt: {"status":"healthy", "database":"connected", "version":"1.0.0-rc.1"}
   ```
3. **Statik Varlık Teslimi**:
   ```bash
   curl -k -s https://127.0.0.1/ | grep "<title>"
   # Yanıt: <title>FLODSS - Facility Layout Decision Support System</title>
   ```
4. **Kimlik Doğrulama Bariyeri**:
   Tarayıcıdan `https://flodss-lab.internal.university.edu` adresine girildiğinde doğrudan giriş modalı açılmalıdır.

---

## 4. Olağanüstü Durum Kurtarma & Geri Alma (Rollback)

Eğer veritabanında bir tutarsızlık veya bozulma yaşanırsa:
```bash
sudo systemctl stop flodss-backend
sudo -u flodss python /opt/flodss/scripts/backup_and_restore.py restore /opt/flodss/data/backups/flodss_backup_<en_son_tarih>.db
sudo systemctl start flodss-backend
```
Sistem saniyeler içinde son doğrulanmış haline geri döner.
