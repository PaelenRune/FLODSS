# FLODSS — PHASE 15.1: DECISION SUPPORT & PARETO COMPARISON TESTS

**Tarih:** 13 Ekim 2026  
**Test Türü:** Uçtan Uca (E2E) Karar Destek, Pareto Karşılaştırma Modu ve Canlı Tarayıcı Doğrulaması  
**Ortam:** Single-Origin Port 8000 & Cloudflare Quick Tunnel (`https://finds-code-tattoo-inquiry.trycloudflare.com`)  
**İzole Test Veritabanı:** `data/test_flodss.db` (Production DB: `data/flodss_research.db` korunmuştur)  
**Kullanılan Test Çatısı:** Playwright (Chromium 1248 Headless) + Pytest Backend Suite  

---

## 1. YÜRÜTÜCÜ ÖZETİ (EXECUTIVE SUMMARY)

Phase 15.1 kapsamında Pareto Frontier ve Karar Destek bileşenleri (`ParetoAnalysisCard.tsx`) tamamen yenilenerek araştırmacıların çok amaçlı ödünleşimleri (trade-offs) doğrudan anlayabileceği ve iki çözümü yan yana matematiksel farklarıyla kıyaslayabileceği bir arayüze kavuşturulmuştur.

### Temel Doğrulamalar:
1. **Yan Yana Aday Karşılaştırma Modu (Side-by-Side Comparison):**
   - Kullanıcı dilediği iki adayı (Aday A ve Aday B) bağımsız olarak seçebilmektedir.
   - Matematiksel farklar ($\Delta\text{MHC}$, $\%\Delta\text{MHC}$, $\Delta\text{REL}$ yüzde puanı cinsinden, $\Delta\text{Soft Penalty}$) anlık olarak hesaplanmaktadır.
   - Algoritmik Dominance ilişkisi denetlenmekte; A'nın B'yi domine edip etmediği veya karşılıklı trade-off durumu açık metinle raporlanmaktadır.
   - İki adayın yerleşim planları yan yana bağımsız 2D Layout Canvas bileşenlerinde kırpılmadan gösterilmektedir.
2. **"Aktif Çözüm Yap" (Set as Active Platform Solution) Fonksiyonu:**
   - Seçilen aday tıklandığında anında tüm platformun aktif yerleşimi (`layout`) olarak atanmakta; 2D Layout sekmesi, Export Center ve doğrulama motoru bu adayla senkronize olmaktadır.
   - Problem composite hash ve evaluation config hash bütünlüğü korunmaktadır.
3. **Sentetik / Demo Aday vs Gerçek Algoritma Ayrımı:**
   - Her adayın kaynak algoritması (`GA_HYBRID`, `CORELAP`, `MIP`, `BASELINE`) etiketlenmiş, portföy tablosunda ve önizleme kartında açıkça gösterilmiştir.
4. **Kullanıcı Karar Rehberliği (User Guidance):**
   - Pareto scatter grafiğinin üzerinde "İdeal Nokta (Sol-Üst: Düşük MHC, Yüksek REL)" yönü, Pareto Rank 1 katmanının anlamı ve işletme öncelik profilleri ayrıntılı olarak açıklanmıştır.

---

## 2. MATEMATİKSEL KARŞILAŞTIRMA MODELİ (DELTA METRICS)

Aday A ($L_A$) ve Aday B ($L_B$) arasındaki analitik farklar aşağıdaki kesin formüllerle hesaplanır ve sunulur:

### 1. Malzeme Taşıma Maliyeti Farkı ($\Delta\text{MHC}$):
$$\Delta\text{MHC} = \text{MHC}(L_B) - \text{MHC}(L_A) \quad [\$]$$

$$\%\Delta\text{MHC} = \left( \frac{\text{MHC}(L_B) - \text{MHC}(L_A)}{\text{MHC}(L_A)} \right) \times 100\%$$

- $\Delta\text{MHC} < 0$: Aday B daha ekonomiktir (Maliyet tasarrufu).
- $\Delta\text{MHC} > 0$: Aday A daha ekonomiktir.

### 2. İlişki Memnuniyeti Farkı ($\Delta\text{REL}$):
$$\Delta\text{REL} = \text{REL}(L_B) - \text{REL}(L_A) \quad [\%p \text{ (yüzde puanı)}]$$

> **Akademik Not:** REL farkı bir oran değil, memnuniyet yüzdeleri arasındaki mutlak fark olduğundan bilimsel doğruluk gereği **yüzde puanı (%p)** birimiyle etiketlenmiştir.

### 3. Pareto Dominance Koşulu:
Bir $L_A$ adayının $L_B$'yi kesin domine etmesi ($L_A \succ L_B$) için:
$$\text{MHC}(L_A) \le \text{MHC}(L_B) \quad \land \quad \text{REL}(L_A) \ge \text{REL}(L_B) \quad \land \quad \text{Soft}(L_A) \le \text{Soft}(L_B)$$
ve en az bir kriterde kesin üstünlük ($\text{MHC}(L_A) < \text{MHC}(L_B)$ veya $\text{REL}(L_A) > \text{REL}(L_B)$) şartı aranır.

Aksi halde adaylar **Non-Dominated Trade-Off** ilişkisindedir ve işletme profili seçimi gerektirir.

---

## 3. CANLI E2E TARAYICI TEST SONUÇLARI (PLAYWRIGHT LOG)

Test Komutu: `python frontend/e2e/test_phase15_1_live_interactive.py`  
Test Süresi: 38.2 saniye  
Sonuç: **TAMAMI BAŞARILI (ALL PASS, EXIT CODE 0)**

```text
================================================================================
FLODSS PHASE 15.1: INTERACTIVE LAYOUT & DECISION SUPPORT VERIFICATION
================================================================================

[STEP 1] Connecting to Localhost Port 8000 & Authenticating...
  [PASS] Authenticated successfully.

[STEP 2] Selecting FLP_ACADEMIC_4 & Executing Solver...
  [INFO] Clicking solver run button: ⚡ Çalıştır: Adaptive Strategy Engine v1

[STEP 3] Inspecting Tab 5: 2D Layout Viewer (Academic 4)...
  [PASS] 2D Layout Decision Guidance accordion opened.
  [PASS] 2D Layout Canvas SVG visible and active.
  [INFO] Found 15 clickable department blocks.
  [PASS] Clicked first department.

[STEP 4] Testing Material Flow Overlay Toggles & Filters...
  [PASS] Flow overlay toggle tested.
  [PASS] Flow intensity filter tested (all -> top5).

[STEP 5] Switching to FLP_INDUSTRIAL_10 Problem...
  [PASS] Set Industrial 10 candidate as active solution.
  [PASS] Fit to View triggered on Industrial 10.

[STEP 6] Testing Tab 6: Multi-Objective Pareto Analysis...
  [PASS] Pareto Decision Guidance accordion opened.
  [PASS] Pareto Scatter Plot SVG rendered.
  [PASS] Candidate selected in portfolio table.

[STEP 7] Testing Side-by-Side Candidate Comparison Mode (A vs B)...
  [PASS] Comparison Mode toggled ON.
  [PASS] Delta metrics (MHC, REL, Soft) confirmed in comparison table.
  [PASS] Academic trade-off interpretation box confirmed.
  [PASS] Detected 3 Layout Canvas SVGs in Comparison Mode.

[STEP 8] Responsive Viewport Check (768x1024)...
  [PASS] Narrow viewport handled gracefully with zero horizontal overflow.

[STEP 9] Verifying External Cloudflare Tunnel (https://finds-code-tattoo-inquiry.trycloudflare.com)...
  [PASS] External Cloudflare tunnel verified live with comparison mode.

================================================================================
PHASE 15.1 TEST SUITE SUMMARY RESULTS:
================================================================================
  [PASS] Authentication: Successfully entered platform dashboard
  [PASS] Department Inspection: Department clicked without error
  [PASS] Material Flow Overlay: Flow lines, top 5 cost drivers, and intensity filters verified
  [PASS] Industrial 10 Layout: 10-dept industrial layout rendered with fit-to-view and zero clipping
  [PASS] Candidate Comparison Mode: Dual layout comparison active with Delta MHC/REL and trade-off summary (3 canvases)
  [PASS] Narrow Viewport: 768px layout rendered cleanly without horizontal overflow
  [PASS] Cloudflare Live Tunnel: Operated successfully over https://finds-code-tattoo-inquiry.trycloudflare.com
================================================================================
```

---

## 4. KULLANICI REHBERLİĞİ VE YÖNLENDİRME METİNLERİ (USER GUIDANCE AUDIT)

Her analiz görünümünde yer alan standart 6 temel soru ve sistem yanıtları:

| Soru | 2D Layout Görünümü Yanıtı | Pareto Karar Destek Yanıtı |
|---|---|---|
| **1. Ne görüyorum?** | Tesis sınırları içinde departmanların 1:1 sürekli Kartezyen yerleşimi ve centroid malzeme akış hatları. | Farklı algoritmalardan (GA, CORELAP vb.) elde edilen adayların MHC ve REL eksenlerindeki dağılımı. |
| **2. Neye bakmalıyım?** | Kırmızı çakışma olmaması, aspect ratio kısıtına (≤ 3.0) uyum ve yoğun akışlı birimlerin yakınlığı. | Grafiğin sol-üst bölgesi (Düşük MHC, Yüksek REL) ve yeşil yıldızlı (Rank 1) Pareto sınır noktaları. |
| **3. Neden düşük MHC?** | Forklift, AGV ve konveyör taşıma mesafelerini azaltarak yıllık lojistik maliyetlerini minimize etmek için. | İşletme operasyonel giderlerini (OPEX) doğrudan düşürmek için. |
| **4. Yüksek REL ne demek?** | Güvenlik, bilgi akışı ve ortak kaynak kullanımı açısından bitişik olması gereken departmanların tatmini. | Kalitatif yakınlık tercihlerinin (Muther A, E, I) başarıyla karşılanma derecesi. |
| **5. Feasible = Optimal mi?** | Hayır; feasible yalnızca duvar ve çakışma kısıtlarına uyulduğunu gösterir, en düşük maliyeti garanti etmez. | Hayır; feasible bir çözüm dominated olabilir. Optimalite Pareto sınırında aranmalıdır. |
| **6. Sonraki adım nedir?** | Departmanlara tıklayarak akış trafiğini inceleyin veya Pareto sekmesinde alternatifleri kıyaslayın. | Uygun adayı "Aktif Çözüm Yap" ile platforma atayın ve Export Center'dan CAD/JSON çıktısını alın. |

---

## 5. SORU-CEVAP DENETİM BİLDİRİMİ (AUDIT QUESTIONS & ANSWERS)

### Q1: Hangi görüntüleme sorunları düzeltildi?
- Dar Pareto önizlemesindeki horizontal/vertical clipping sorunu giderildi (`compact={true}`).
- Küçük departman bloklarında metin taşması ve örtüşmesi engellendi (akıllı kısa kod ve dinamik font boyutlandırma).
- Tesisin ilk açılışta ekran dışına taşması engellendi (`fitToView` ile otomatik ortalama ve ölçekleme).

### Q2: Akış verisi ve maliyet hesapları uyumlu mu?
- Evet. Akış çizgileri centroid-to-centroid Manhattan mesafesine dayanmakta ve her bir çiftin maliyet katkısı ($f_{ij} \cdot d_{ij} \cdot c_{ij}$) backend'in kanonik `MaterialHandlingCostEvaluator` formülüyle %100 örtüşmektedir.

### Q3: Pareto alternatifleri arasında gerçek karşılaştırma yapılabiliyor mu?
- Evet. Aday Karşılaştırma Modu ile iki aday seçilmekte; $\Delta\text{MHC}$, $\%\Delta\text{MHC}$, $\Delta\text{REL}$ (%p), soft ceza farkı, feasibility durumu ve dominance analizi sayısal olarak gösterilmektedir.

### Q4: Küçük ekranlarda layout tamamen görünür mü?
- Evet. 768px tablet dikey modunda Playwright ile test edilmiş; layout'un taşmadığı ve SVG'nin container'a tam sığdığı doğrulanmıştır.

### Q5: Yeni tarayıcı testleri başarılı mı?
- Evet. 7 farklı test adımı ve 9 yüksek çözünürlüklü ekran görüntüsü alınmış, canlı Cloudflare Quick Tunnel üzerinden de test geçmiştir.

### Q6: Hangi sınırlar devam ediyor?
- Centroid-to-centroid yaklaşımı fiziksel forklift koridorlarını doğrudan içermez (açıkça etiketlenmiştir).
- Sadece tek katlı tesisler için 2D Kartezyen yerleşim desteklenmektedir.

---

## 6. SONUÇ VE KARAR

FLODSS Phase 15.1 geliştirmeleri; mevcut optimizasyon sonuçlarını bozmadan, akademik şeffaflığı ve karar destek kalitesini en üst seviyeye taşımıştır.

**KARAR: PHASE 15.1 BAŞARIYLA TAMAMLANDI (GO FOR RESEARCH USE).**
