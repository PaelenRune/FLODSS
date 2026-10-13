# FLODSS — Private Research Hosting Architecture Options (Phase 14.3)

## 1. Executive Evaluation Overview

To transition FLODSS (Facility Layout Optimization Decision Support System) v1.0.0-rc.1 from a local pair-programming environment to an accessible research platform for thesis advisors and selected doctoral researchers, three distinct private hosting architectures have been evaluated.

### Mandatory Operational Boundaries:
- **Strictly Closed-Source**: No public GitHub, GitLab, or package repositories.
- **No Open Internet Exposure**: The platform must never be directly indexed or accessible from the public internet.
- **Local-First & Multi-Tenant**: Full database isolation (`owner_user_id` boundaries) and reproducibility controls must be preserved.

---

## 2. Evaluation of Candidate Hosting Architectures

### Option A: Özel Üniversite / Bölüm Sunucusu (Campus Intranet / VPN Server)
- **Concept**: A dedicated Linux virtual machine or bare-metal physical machine hosted within the university data center or industrial engineering departmental network.
- **Access Method**: Accessible solely through the university campus network or an institutional VPN (e.g., Eduroam, OpenVPN, WireGuard).
- **Network Perimeter**: Internal IP address (e.g., `10.x.x.x` or `172.16.x.x`) with TLS certificates issued by an internal university Certificate Authority or split-horizon DNS.

### Option B: Kimlik Doğrulamalı Özel Bulut Sunucusu (Private Cloud VM with IP Whitelisting / VPN)
- **Concept**: A hardened, private cloud compute instance (e.g., AWS EC2, GCP Compute Engine, or Hetzner Cloud) running without public DNS.
- **Access Method**: Egress/ingress completely blocked by Cloud Security Group / Firewall except for explicit static IP whitelisting or a peer-to-peer WireGuard VPN tunnel connecting thesis advisors directly to the instance.
- **Network Perimeter**: Zero open web ports; HTTP/HTTPS restricted to tunnel or whitelisted IP ranges.

### Option C: Özel Laboratuvar İş İstasyonu (Dedicated Laboratory Workstation on Intranet LAN)
- **Concept**: A high-performance physical PC situated in the industrial engineering laboratory running Windows 11 or Linux, connected to the local lab Ethernet/Wi-Fi subnet.
- **Access Method**: Researchers and thesis advisors connect via local lab Wi-Fi/LAN or secure remote desktop / SSH port forwarding authorized by departmental IT.
- **Network Perimeter**: Local LAN IP (e.g., `192.168.1.x`), isolated by the laboratory physical router.

---

## 3. Dimensional Comparison Matrix

| Evaluation Dimension | Option A: Üniversite / VPN Sunucusu | Option B: Özel Bulut Sunucusu (VPN'li) | Option C: Laboratuvar İş İstasyonu |
| :--- | :--- | :--- | :--- |
| **Güvenlik (Security)** | **Çok Yüksek**<br>Üniversite kurumsal güvenlik duvarı + VPN çift katmanlı bariyer. | **Yüksek**<br>Doğru firewall/VPN ile güvenli, ancak bulut hesap sızıntısı riski taşır. | **Orta-Yüksek**<br>Fiziksel erişim kontrolü gerektirir; laboratuvar yerel ağı ile sınırlı. |
| **Kaynak Kodu Gizliliği (IP Protection)** | **Mükemmel**<br>Kod ve veriler tamamen kurum bünyesindeki sunucuda kalır. | **İyi**<br>Bulut hizmet sağlayıcısı sözleşmesine bağlıdır; yurt dışı veri aktarım protokolleri doğurabilir. | **Mükemmel**<br>Fiziksel makine tamamen araştırmacının ve danışmanın gözetimindedir. |
| **Kullanım Kolaylığı (UX)** | **Yüksek**<br>Danışman zaten üniversite VPN'ine sahipse doğrudan tarayıcıdan açar. | **Orta**<br>Her pilot kullanıcıya VPN/WireGuard profili veya statik IP tanımlanmalıdır. | **Çok Yüksek (Laboratuvarda)**<br>Yerel ağda veya aynı odada anında erişim. |
| **Maliyet Kalemleri (Costs)** | **Sıfır Ek Maliyet**<br>Üniversitenin mevcut IT ve sunucu altyapısı kullanılır. | **Aylık \$20 – \$60**<br>Bulut VM kirası, egress trafik ve depolama snapshot maliyetleri. | **Sıfır Ek Maliyet**<br>Mevcut laboratuvar bilgisayarı kullanılır. |
| **Yönetim Yükü (Ops Overhead)** | **Düşük-Orta**<br>IT departmanı VM tahsis eder, işletim sistemi araştırmacı tarafından yönetilir. | **Yüksek**<br>Bulut IAM, VPC, güvenlik duvarı kuralları ve faturalandırma takibi. | **En Düşük**<br>Doğrudan geliştirme makinesinde tek tıkla arka plan servisi başlatma. |
| **Yedekleme (Backup)** | **Kurumsal Otomasyon**<br>Kurumsal SAN/NAS snapshot ve gece yedeklemeleri mevcuttur. | **Bulut Snapshot**<br>Otomatik EBS/Disk snapshot ve S3/GCS yedekleme. | **Manuel / Yerel Script**<br>Harici USB disk veya yerel script (`backup_and_restore.py`). |
| **Donanım / Kaynak İhtiyacı** | 2 vCPU, 4–8 GB RAM, 20 GB SSD disk yeterlidir. | 2 vCPU (t3.medium / e2-medium), 4 GB RAM, 25 GB SSD. | Mevcut 4-8 çekirdekli PC, 16 GB RAM fazlasıyla yeterlidir. |

---

## 4. Tercih Edilen İlk Pilot Mimarisi Önerisi

### **ÖNERİ: Option A (Üniversite Ağı / VPN Özel Sunucusu) — Birincil Tercih**
*Yedek / Hızlı Alternatif: Option C (Özel Laboratuvar İş İstasyonu)*

### Teknik Gerekçe:
1. **Kurumsal Fikrî Mülkiyet (IP) Korunumu**:
   FLODSS patent potansiyeli taşıyan bir tez projesidir. Kaynak kodun ve sentetik/endüstriyel fabrika verilerinin hiçbir üçüncü taraf bulut sağlayıcısına (AWS, GCP, Azure vb.) yüklenmemesi, yasal KVKK ve üniversite patent başvuru süreçlerinde "önceki teknik / aleniyet" (prior art) veya gizlilik ihlali iddialarını tamamen bertaraf eder.
2. **Kusursuz Kullanıcı Deneyimi**:
   Tez danışmanları ve üniversite araştırmacıları zaten halihazırda kurumsal VPN profiline (Eduroam/GlobalProtect) sahiptir. Yeni bir bulut hesabı veya özel VPN istemcisi kurmalarına gerek kalmadan, tarayıcılarından dahili adresi (`https://flodss-lab.internal.university.edu`) açarak erişebilirler.
3. **Sıfır Bütçe & Yüksek Kararlılık**:
   Üniversite bilgi işlem biriminden talep edilecek 2 çekirdekli, 4 GB RAM'li bir Ubuntu/Debian Linux sanal makinesi hiçbir ek bütçe gerektirmeden FLODSS'ı 7/24 çalıştırabilir.

---

## 5. Sunucu Donanım & Kaynak Şartnamesi

| Kaynak | Minimum Gereksinim | Önerilen Pilot Konfigürasyonu |
| :--- | :--- | :--- |
| **İşlemci (CPU)** | 2 Çekirdek (x86_64, 2.0 GHz+) | 4 Çekirdek (Intel Xeon / AMD EPYC veya Core i7) |
| **Bellek (RAM)** | 4 GB | 8 GB DDR4/DDR5 |
| **Disk Alanı** | 15 GB SSD | 30 GB NVMe SSD |
| **İşletim Sistemi** | Ubuntu 22.04 LTS / 24.04 LTS veya Debian 12 | Ubuntu 24.04 LTS (HWE Kernel) |
| **Yazılım Bağımlılıkları** | Python 3.12+, Nginx 1.22+, SQLite 3.39+ | Python 3.12+, Nginx 1.24+, SQLite 3.42+ |
| **Ağ Arayüzü** | 100 Mbps dahili intranet bağlantısı | 1 Gbps kurumsal yerel ağ |
