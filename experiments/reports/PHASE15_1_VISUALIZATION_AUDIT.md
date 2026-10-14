# FLODSS — PHASE 15.1: INTERACTIVE LAYOUT VISUALIZATION & AUDIT REPORT

**Tarih:** 13 Ekim 2026  
**Denetim Kapsamı:** 2D Layout Viewer (`LayoutCanvas.tsx`), Material Flow Overlay, Department Inspection Drawer, Fit to View, Görsel Bütünlük ve Matematiksel Doğruluk  
**Uygulama Durumu:** CANLI (Single-Origin Port 8000 & Cloudflare Tunnel: `https://finds-code-tattoo-inquiry.trycloudflare.com`)  
**Backend Test Durumu:** 446/446 Test Geçti (`pytest backend/tests -q`)  
**E2E Tarayıcı Doğrulaması:** 7/7 Senaryo Geçti (Playwright Headless Chromium)  

---

## 1. YÜRÜTÜCÜ ÖZETİ (EXECUTIVE SUMMARY)

Phase 15.1 kapsamında FLODSS'ın 2D Block Layout Viewer bileşeni pasif bir çizim ekranından, araştırmacılar ve fabrika yöneticileri için etkileşimli, analitik ve bilimsel bir **Karar Destek Motoru**na dönüştürülmüştür. Bu aşamada optimizasyon algoritmalarının ürettiği koordinatlar, aspect ratio kısıtları ve nesnel fonksiyon değerleri **kesinlikle değiştirilmemiş**, odak tamamen sonuçların matematiksel tutarlılıkla sunulmasına verilmiştir.

### Temel Başarılar:
1. **Dinamik Viewport Oturumu (Auto-Fit & Center):** Tesis sınırları ve en-boy oranları (aspect ratio) ne olursa olsun (kare, dar-uzun, geniş holler) layout hiçbir kırpılma (clipping) olmadan SVG viewport'una tam olarak sığdırılmaktadır.
2. **Akıllı Departman Etiketleme:** Küçük departman bloklarında yalnızca kısa kodlar gösterilmekte, uzun isimler sınır kutusunu (bounding box) aşmayacak biçimde kırpılmakta ve hiçbir blokta metin taşması veya üst üste binme yaşanmamaktadır.
3. **From–To Malzeme Akış Katmanı (Material Flow Overlay):** Yönlü kuadratik yaylar (Bézier quadratic curves) ile departman ağırlık merkezleri (centroids) birbirine bağlanmış; çizgi kalınlıkları akış debisi ($f_{ij}$) ile orantılanmış ve en yüksek taşıma maliyeti yaratan "İlk 5 Maliyet Sürücüsü" (Top 5 Cost Drivers) kehribar/turuncu vurguyla öne çıkarılmıştır.
4. **Matematiksel Doğruluk & Koridor Şeffaflığı:** Akış çizgilerinin fiziksel bir forklift/koridor rotası olmadığı, FLODSS canonical MHC metriğiyle uyumlu **Centroid Rectilinear (Manhattan) Mesafesi** olduğu açıkça etiketlenmiştir.
5. **Ayrıntılı Departman Denetim Çekmecesi (Inspection Drawer):** Tıklanan departmanın 1:1 Kartezyen koordinatları, genişlik/yükseklik, gerçek aspect ratio, malzeme giriş/çıkış trafiği ve Muther REL ilişkileri sağ panelde sunulmaktadır.
6. **Kullanıcı Karar Rehberleri (Decision Guidance):** "Ne görüyorum?", "Neye bakmalıyım?", "MHC neden minimize edilmeli?", "Yüksek REL ne anlama gelir?", "Feasible = Optimal midir?" sorularına yanıt veren akordeon kartları entegre edilmiştir.

---

## 2. GİDERİLEN GÖRÜNTÜLEME VE ETKİLEŞİM SORUNLARI

| No | Önceki Durum (Phase 14.7) | Düzeltilen Durum (Phase 15.1) | Doğrulama Yöntemi |
|---|---|---|---|
| **1** | Dar Pareto önizlemesinde veya dar viewport'larda layout kenarlardan kesiliyordu (clipping). | `fitToView()` algoritması ve `compact?: boolean` prop'u eklendi. SVG viewBox oranları dinamik hesaplanarak sıfır kırpılma garanti edildi. | Responsive Playwright testi (768px ve 1440px) |
| **2** | Küçük bloklarda uzun isimler kutudan taşıyor, komşu blokların üstüne biniyordu. | Akıllı etiketleme getirildi: Dar bloklarda ($W < 14\text{m}$) yalnızca kısa ID (ilk 4 karakter), geniş bloklarda ise kutu genişliğine göre `truncate` uygulandı. | Academic4 ve Industrial10 blok denetimi |
| **3** | Malzeme akış miktarları sadece From-To matris tablosunda sayısal olarak vardı, layout üzerinde görülemiyordu. | Dinamik yönlü ok katmanı eklendi. Tooltip içinde akış hacmi, Manhattan mesafesi, birim maliyet ve toplam maliyet katkısı ($f_{ij} \cdot d_{ij} \cdot c_{ij}$) gösterildi. | Flow Overlay toggle & hover testi |
| **4** | Yoğun akış matrislerinde (ör. Industrial 10) onlarca çizgi karmaşaya yol açıyordu. | Akış Yoğunluk Filtresi (`'all' \| 'top5' \| 'top10'`) eklendi. Varsayılan olarak en kritik ilk 5 maliyet sürücüsü filtrelenebilmektedir. | Select filtre testi (all -> top5) |
| **5** | Departman tıklamalarında yalnızca alt tablodaki satır vurgulanıyordu; geometrik detaylar dağınıktı. | Sağdan açılan "Departman İnceleme Paneli" eklendi. Fiziksel boyutlar, alan sapması, AR kısıt kontrolü, trafik özeti ve REL ilişkileri tek panelde toplandı. | Tıklama ile Drawer açılış testi |
| **6** | Kullanıcılar için analitik yönlendirme ve yorumlama metinleri eksikti. | TR ve EN dilli `DecisionGuidanceBox` bileşeni eklendi. | 2D Layout ve Pareto sekmelerinde doğrulandı |

---

## 3. MALZEME AKIŞI (FLOW OVERLAY) & MHC MATEMATİKSEL TUTARLILIĞI

FLODSS çekirdek değerlendirme motorunda (`app.evaluation.metrics.material_handling_cost.MaterialHandlingCostEvaluator`) toplam malzeme taşıma maliyeti aşağıdaki formülle hesaplanır:

$$\text{MHC} = \sum_{i=1}^{N} \sum_{j=1}^{N} f_{ij} \cdot d_{ij} \cdot c_{ij}$$

Burada:
- $f_{ij}$: Departman $i$'den departman $j$'ye birim zamandaki akış miktarı (palet, ton vb.)
- $c_{ij}$: Birim mesafe ve birim akış başına taşıma maliyeti (\$/m)
- $d_{ij}$: Ağırlık merkezleri (centroids) arasındaki Rectilinear (Manhattan) mesafesi:

$$d_{ij} = |c_{x_i} - c_{x_j}| + |c_{y_i} - c_{y_j}|$$

`LayoutCanvas.tsx` içerisindeki hesaplama motoru:
```typescript
const dist = Math.abs(srcCx - tgtCx) + Math.abs(srcCy - tgtCy);
const unitCost = flow.cost_per_unit_distance ?? 1.0;
const cost = flow.quantity * dist * unitCost;
```

### Bilimsel Uyum Kanıtı:
1. **Sıfır Akış Koruması:** $f_{ij} \le 0$ olan hiçbir çift için akış çizgisi üretilmez (`if (flow.quantity <= 0) return`). Sentetik veya sahte ok çizimi engellenmiştir.
2. **Kanonik Toplam Uyumu:** Layout Canvas üzerinde çizilen tüm yönlü akışların maliyet katkıları toplandığında elde edilen değer ($\sum \text{cost}_{ij}$), backend'in ürettiği kanonik `material_handling_cost` nesnel fonksiyon değeri ile tam olarak kuruşu kuruşuna örtüşmektedir.
3. **Mesafe Modeli Beyanı:** Ekranda ve yönlendirme kartında, gösterilen bağlantıların *"Centroid Rectilinear Distance • Conceptual flow line"* olduğu; fiziksel koridor (aisle network) ve forklift dönüş yarıçapı içermediği açıkça beyan edilmiştir.

---

## 4. DEPARTMAN DETAY DENETİMİ (DEPARTMENT INSPECTION DRAWER)

Bir departmana tıklandığında açılan denetim panelinin içerdiği analitik veriler:

1. **Temel Kimlik:** Tam Departman Adı (`name`), Sistem Kodu (`id`), Kaynak Problem Tanımı.
2. **Fiziksel Geometri:**
   - Genişlik ($W$) ve Yükseklik ($H$) metre cinsinden.
   - Gerçekleşen Alan ($A = W \times H$) ve İstenen Alan ile sapma yüzdesi.
   - En-Boy Oranı: $\text{Aspect Ratio} = \frac{\max(W, H)}{\min(W, H)}$. Problem kısıtında tanımlanan `max_aspect_ratio` (ör. 3.0) aşılmışsa kırmızı uyarı rozeti verilir.
3. **Kartezyen Konum:**
   - Sol-alt köşe orjini: $(x, y)$
   - Ağırlık merkezi: $(c_x, c_y) = (x + W/2, y + H/2)$
4. **Malzeme Trafiği Özeti:**
   - Gelen Malzeme Akışı: $\sum_{k} f_{ki}$ (palet/gün)
   - Giden Malzeme Akışı: $\sum_{k} f_{ik}$ (palet/gün)
   - En Yüksek Maliyetli İlişki: Departmanın dahil olduğu en pahalı $f \cdot d \cdot c$ hattı.
5. **Muther REL Yakınlık Analizi:**
   - Komşu departmanlarla Muther skorları (A, E, I, O, U, X) renkli rozetlerle listelenir.

---

## 5. EKRAN GÖRÜNTÜLERİ VE GRAFİK ÇIKTI DENETİMİ

Tüm test çıktıları ve görsel kanıtlar `experiments/reports/screenshots_phase15_1/` dizininde arşivlenmiştir:

| Dosya Adı | Çözünürlük | Açıklama |
|---|---|---|
| `01_dashboard_home.png` | 1440x900 | Canlı sistem ana ekranı ve navigasyon paneli |
| `02_academic4_guidance_open.png` | 1440x900 | Academic 4 üzerinde açık akordeon Kullanıcı Rehberi kartı |
| `03_academic4_department_inspection.png` | 1440x900 | Tıklanan departman için sağda açılan Departman İnceleme Paneli |
| `04_academic4_flow_overlay.png` | 1440x900 | Centroid-to-centroid akış çizgileri ve Top 5 Cost Drivers katmanı |
| `05_industrial10_layout_fit.png` | 1440x900 | Industrial 10 (10 departman) 1:1 auto-fit ve ızgara görünümü |
| `06_pareto_single_candidate.png` | 1440x900 | Pareto Frontier scatter plot ve sağ panelde dar alanda kırpılmayan layout önizlemesi |
| `07_pareto_comparison_mode.png` | 1440x900 | Aday A vs Aday B yan yana karşılaştırma modu, $\Delta$ metrik tablosu ve ikili mini layout |
| `08_narrow_viewport_layout.png` | 768x1024 | Tablet/Mobil dikey görünümde responsive sıfır taşma denetimi |
| `09_cloudflare_live_pareto.png` | 1440x900 | Canlı Cloudflare Public Tüneli üzerinden uçtan uca doğrulama |

---

## 6. MEVCUT SINIRLAMALAR VE GELECEK AŞAMALAR

1. **Fiziksel Koridor Geometrisi:** Mevcut akış hatları centroid-to-centroid Manhattan varsayımına dayanmaktadır. Gelecek aşamalarda omurga koridor (spine corridor) ve yangın kaçış koridorları eklendiğinde gerçek güzergâh (A* aisle-route pathfinding) görselleştirilebilir.
2. **Çok Katlı Tesisler (Multi-Floor):** 2D Layout Viewer tek katlı sürekli Kartezyen düzlemi desteklemektedir; asansör ve dikey konveyör hatları için 2.5D/3D görünüm ileride değerlendirilebilir.
3. **SVG/PNG Çıktı Çözünürlüğü:** Layout Canvas doğrudan tarayıcı DOM'undan vektörel SVG ve yüksek DPI PNG indirebilmektedir; bu çıktılar akademik makaleler için 300 DPI baskı kalitesindedir.
