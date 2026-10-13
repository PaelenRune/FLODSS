# Generated Layout Verification & Improvement Baseline: FLP_INDUSTRIAL_10

**Document Reference:** `experiments/reports/GENERATED_LAYOUT_BASELINE.md`  
**Phase:** 8.1 — Generated Layout Verification & Improvement Baseline  
**Evaluation Target:** `FLP_INDUSTRIAL_10` (Precision Machinery Manufacturing Plant, 10 Departments, Facility: $150.0 \times 80.0\,\text{m}$, Total Area: $12{,}000\,\text{m}^2$, Required Area: $11{,}000\,\text{m}^2$, Area Utilization: $91.67\%$)  
**Artifacts Generated:** `data/examples/generated_industrial_10.json`  
**Execution Timestamp:** 2026-10-10  
**Test Suite:** `backend/tests/test_phase8_1_verification.py` (12 passing tests, 240 total backend tests)  

---

## 1. Executive Summary

In Phase 8, the **Feasible Rectangular Layout Generator** successfully resolved the long-standing geometric failure mode on `FLP_INDUSTRIAL_10` by constructing a 100% legal, non-overlapping, complete rectangular layout from scratch using **Guillotine Row / Bay Packing** in 11 milliseconds.

The purpose of **Phase 8.1** is to empirically verify:
1. That this generated layout is **100% baseline-independent** and **strictly deterministic across repeated runs**.
2. That the produced layout can be serialized, cataloged, and cleanly re-loaded as an academic benchmark (`data/examples/generated_industrial_10.json`).
3. How the existing **CRAFT pairwise improvement heuristic** (`craft_pairwise_rectangular_v1`) interacts with this automatically synthesized layout.
4. The exact nature, cause, and penalty magnitude of the **1 soft constraint violation** observed in the generated layout.
5. The structural implications and algorithmic prerequisites for subsequent metaheuristic optimization (Genetic Algorithms).

---

## 2. Direct Answers to Core Research Questions

### Q1: Guillotine Generator gerçekten baseline'dan bağımsız mı?
**Cevap: EVET, kesinlikle bağımsızdır.**
- **Kod Analizi:** `backend/app/algorithms/generator/` ve `backend/app/feasibility/` modüllerinin tamamında `sample_layout`, manuel koordinat veya kayıtlı çözüm referansı sıfırdır (`findstr` taramasında 0 eşleşme).
- **İzolasyon Testi:** `test_02_generator_baseline_independence` testinde `sample_layout.json` dosyasının dosya sisteminde bulunmadığı simüle edilmiş (mocked); generator hiçbir dış koordinat dosyasına erişmeden problemi sıfırdan çözmüş ve bit düzeyinde özdeş yerleşim imzası (`61c4bf88996517780fd1f43839d1e1654c6be9276072a9799c4a7e1c8fc12174`) üretmiştir.
- **Tasarım İlkesi:** Departman koordinatları ve boyutları, problemdeki alan gereksinimleri ($A_{\text{req}}$), fabrika sınırları ($150 \times 80\,\text{m}$) ve `LegalDimensionGenerator` tarafından türetilen dikdörtgensel alternatiflerin giyotin bay bölme kombinasyonlarıyla analitik olarak hesaplanmıştır.

### Q2: 10 çalıştırmada sonuç deterministik mi?
**Cevap: EVET, %100 deterministiktir.**
- `test_01_generator_deterministic_repeatability_10_runs` kapsamında generator aynı konfigürasyonla art arda 10 kez çalıştırılmıştır.
- Tüm 10 çalıştırmada:
  - 10 / 10 departman eksiksiz yerleştirilmiştir (`placed_department_count == 10`).
  - Toplam çakışma alanı istisnasız **$0.00\,\text{m}^2$** olmuştur.
  - Hard kısıt ihlali **0** olmuştur.
  - Üretilen SHA-256 geometric signature istisnasız **`61c4bf88996517780fd1f43839d1e1654c6be9276072a9799c4a7e1c8fc12174`** çıkmıştır (`len(set(signatures)) == 1`).

### Q3: CRAFT otomatik layout'u iyileştirdi mi?
**Cevap: HAYIR, CRAFT herhangi bir iyileştirme bulamamıştır.**
- CRAFT algoritması (`craft_pairwise_rectangular_v1`) üretilen layout'u başarıyla kabul etmiş, doğrulamış ve 1. iterasyonda sonlanmıştır.
- Toplam **2 uygun departman çifti** tespit edilmiş, her iki değişim de MHC değerini artırdığı için (negatif iyileşme) CRAFT hiçbir değişimi kabul etmemiş ve `NO_IMPROVING_SWAP` gerekçesiyle durmuştur.

### Q4: MHC ne kadar değişti?
**Cevap: %0.00 (MHC hiç değişmemiştir).**
- **Başlangıç MHC:** $\$180{,}263.94$
- **Bitiş MHC:** $\$180{,}263.94$
- **Kabul Edilen Swap Sayısı:** 0
- **Değerlendirilen Değişimler ve Maliyet Etkisi:**
  1. `('DEP_CUTTING', 'DEP_SHIPPING')`: MHC $\$180{,}263.94 \to \$182{,}148.94$ ($\Delta = +\$1{,}885.0$, iyileşme: $-\$1{,}885.0$).
  2. `('DEP_FINISHED_GOODS', 'DEP_RAW_MATERIAL')`: MHC $\$180{,}263.94 \to \$200{,}153.94$ ($\Delta = +\$19{,}890.0$, iyileşme: $-\$19{,}890.0$).

### Q5: Soft constraint ihlali tam olarak nedir?
**Cevap:**
- **Kısıt ID:** `CST_SOFT_VIBRATION_SEP`
- **Kapsanan Departmanlar:** `DEP_MACHINING` (Talaşlı İmalat CNC) ve `DEP_QUALITY` (CMM Kalite Metroloji)
- **Kısıt Türü & Sınıfı:** `min_distance`, `ConstraintClassification.SOFT`
- **Gereken Minimum Mesafe:** $25.00\,\text{m}$
- **Gerçekleşen Mesafe:** **$0.00\,\text{m}$** (İki departman $x = 130.0\,\text{m}$ dikey hattında birbirine bitişiktir).
- **İhlal Miktarı (Deficit):** $25.00\,\text{m}$
- **Hesaplanan Ceza Puanı (Penalty):** $25.00 \times 2{,}500.0 = \mathbf{62{,}500.0}$
- **Mühendislik Anlamı:** CNC tezgahlarının dinamik titreşimlerinin hassas CMM ölçüm cihazlarına geçmemesi için konulmuş bir koruma mesafesidir. Bu kısıt bir **hard constraint** değildir (fabrika inşasını imkansız kılmaz); ancak üretimde CMM cihazı için özel pnömatik sönümleme temeli veya titreşim izolasyon bariyeri gerektirir. Gerçek mühendislik projelerinde, eğer yapısal izolasyon sağlanamıyorsa bu kısıt hard constraint'e dönüştürülmelidir.

### Q6: Bir sonraki GA aşaması için hangi sınırlamalar var?
**Cevap:**
1. **Sert Boyut Kilidi (Rigid Dimension Lock):** Klasik CRAFT gibi sadece eşit boyutlu departmanları takas eden sezgiseller, farklı alan ve boyutlardaki departmanları bay'ler arasında taşıyamaz.
2. **Kombinatorik Slicing Temsili İhtiyacı:** GA'da serbest koordinat mutasyonu yerine, **Slicing Tree (Kesme Ağacı) veya Sequence-Pair** kromozom temsili kullanılmalıdır. Aksi halde rastgele koordinat mutasyonları %91.67 yoğunlukta kaçınılmaz olarak geometrik çakışmalara (overlap) yol açar.
3. **Multi-Bay Boyut Adaptasyonu:** Bir departman başka bir bay'e taşındığında, o bay'in yüksekliğine göre enini $W = A_{\text{req}} / H_{\text{bay}}$ formülüyle yeniden ayarlayan dinamik bir decoder mekanizması GA için zorunludur.

---

## 3. Üçlü Karşılaştırma Matrisi (Three-Way Baseline Comparison)

Aynı `EvaluationConfig` ile değerlendirilen üç yerleşimin resmi karşılaştırması:

| Metrik | A. Manuel Baseline (`sample_layout.json`) | B. Guillotine Generated (`generated_industrial_10.json`) | C. Guillotine + CRAFT (`craft_pairwise_v1`) |
| :--- | :---: | :---: | :---: |
| **Problem ID** | `FLP_INDUSTRIAL_10` | `FLP_INDUSTRIAL_10` | `FLP_INDUSTRIAL_10` |
| **Üretim Yöntemi** | İnsan Mühendis Tasarımı | Otomatik Guillotine Row Packing | Guillotine + CRAFT 1 İterasyon |
| **Yerleşim Tamlığı (Completeness)** | **10 / 10 (%100)** | **10 / 10 (%100)** | **10 / 10 (%100)** |
| **Geometrik Uygunluk (Feasibility)** | **%100 Feasible** | **%100 Feasible** | **%100 Feasible** |
| **Toplam Çakışma (Overlap)** | **0.00 m²** | **0.00 m²** | **0.00 m²** |
| **Fabrika Dışına Taşma** | 0 | 0 | 0 |
| **Hard Kısıt İhlali** | **0** | **0** | **0** |
| **Soft Kısıt İhlali** | **0** | **1** (`CST_SOFT_VIBRATION_SEP`) | **1** (`CST_SOFT_VIBRATION_SEP`) |
| **Soft Ceza Skoru (Penalty)** | **0.0** | **62,500.0** | **62,500.0** |
| **Net Alan Kullanımı (Utilization)** | **%91.67** | **%91.67** | **%91.67** |
| **Material Handling Cost (MHC)** | **\$139,498.75** | **\$180,263.94** | **\$180,263.94** |
| **Flow-Distance Skoru** | **117,893.75** | **153,551.14** | **153,551.14** |
| **İlişki Memnuniyeti (Rel Satisfaction)** | **%55.47** | **%44.17** | **%44.17** |
| **Ham Muther İlişki Puanı** | 66.56 | 53.00 | 53.00 |
| **Layout İmzası (SHA-256)** | `b6459286bc1fb50b...` | `61c4bf8899651778...` | `61c4bf8899651778...` |
| **Hesaplama Süresi** | N/A (Manuel) | **0.011 saniye** | **0.003 saniye** |

---

## 4. Guillotine Üretilen Yerleşim Detay Tablosu

Aşağıdaki tablo, `data/examples/generated_industrial_10.json` dosyasında saklanan kesin yerleşim koordinatlarını ve boyutlarını göstermektedir:

| Departman ID | İsim | Alan ($A_{\text{req}}$) | $X$ (m) | $Y$ (m) | Genişlik ($W$) | Yükseklik ($H$) | Aspect Ratio | Bay / Satır |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `DEP_ASSEMBLY` | Montaj | $1{,}700\,\text{m}^2$ | 0.00 | 0.00 | 70.00 | 24.29 | 2.88 | Bay 1 (Alt) |
| `DEP_MACHINING` | Talaşlı İmalat | $1{,}500\,\text{m}^2$ | 70.00 | 0.00 | 60.00 | 25.00 | 2.40 | Bay 1 (Alt) |
| `DEP_QUALITY` | Kalite Kontrol | $500\,\text{m}^2$ | 130.00 | 0.00 | 20.00 | 25.00 | 1.25 | Bay 1 (Alt) |
| `DEP_RAW_MATERIAL` | Hammadde Depo | $1{,}300\,\text{m}^2$ | 0.00 | 26.67 | 51.25 | 25.37 | 2.02 | Bay 2 (Orta) |
| `DEP_FINISHED_GOODS` | Mamul Ambarı | $1{,}300\,\text{m}^2$ | 51.25 | 26.67 | 51.25 | 25.37 | 2.02 | Bay 2 (Orta) |
| `DEP_WELDING` | Kaynak & Birleştirme | $1{,}100\,\text{m}^2$ | 102.50 | 26.67 | 42.50 | 25.88 | 1.64 | Bay 2 (Orta) |
| `DEP_SURFACE_TREAT` | Yüzey İşlem | $1{,}100\,\text{m}^2$ | 0.00 | 53.34 | 43.75 | 25.14 | 1.74 | Bay 3 (Üst) |
| `DEP_CUTTING` | Kesim & Dilme | $900\,\text{m}^2$ | 43.75 | 53.34 | 35.00 | 25.71 | 1.36 | Bay 3 (Üst) |
| `DEP_SHIPPING` | Sevkiyat | $900\,\text{m}^2$ | 78.75 | 53.34 | 35.00 | 25.71 | 1.36 | Bay 3 (Üst) |
| `DEP_MAINTENANCE` | Bakım Atölyesi | $700\,\text{m}^2$ | 113.75 | 53.34 | 26.46 | 26.46 | 1.00 | Bay 3 (Üst) |

**Toplam Departman Alanı:** $11{,}000.0\,\text{m}^2$  
**Fabrika Alanı:** $150.0 \times 80.0 = 12{,}000.0\,\text{m}^2$  
**Boş Kalan Koridor / Rezerv Alan:** $1{,}000.0\,\text{m}^2$  
**Geometrik Çakışma:** **0.00 m²**

---

## 5. CRAFT Neden İyileştirme Bulamadı? Derin Analiz

CRAFT algoritmasının bu yerleşimde takılmasının ardındaki operasyonel nedenler şunlardır:

1. **Katı Eşit-Boyut Gereksinimi (Dimension Equivalence Constraint):**  
   Sürekli dikdörtgensel koordinat uzayında bir departman takası yapıldığında, iki departmanın boyutları ($W, H$) birebir aynı değilse veya 90 derece döndürüldüğünde birbirinin yerine oturmuyorsa, komşu departmanların sınırları bozulur veya çakışma (overlap) meydana gelir.
2. **Kısıtlı Eşit Çift Sayısı:**  
   10 departman arasında $\binom{10}{2} = 45$ olası çift vardır. Ancak bu yerleşimde birebir aynı $(W, H)$ boyutuna sahip yalnızca **2 çift** bulunmaktadır:
   - `DEP_CUTTING` ($35.0 \times 25.71$) $\leftrightarrow$ `DEP_SHIPPING` ($35.0 \times 25.71$)
   - `DEP_FINISHED_GOODS` ($51.25 \times 25.37$) $\leftrightarrow$ `DEP_RAW_MATERIAL` ($51.25 \times 25.37$)
3. **MHC Artış Yönü:**  
   - Kesim ile Sevkiyat yer değiştirildiğinde, Hammadde $\to$ Kesim malzeme akış mesafesi uzamakta ve toplam maliyet $\$1{,}885.0$ artmaktadır.
   - Mamul Ambarı ile Hammadde Deposu yer değiştirildiğinde lojistik akış tamamen tersine dönmekte ve maliyet devasa bir şekilde $\$19{,}890.0$ fırlamaktadır.
4. **Sonuç:**  
   CRAFT yerel arama mantığı gereği maliyeti artıran hiçbir adımı kabul etmez. İyileştirme sağlayan geçerli bir swap kalmadığı için ilk iterasyonda durmuştur. Bu durum CRAFT'ın bir hatası değil, **klasik pairwise swap mantığının sürekli dikdörtgen bloklar üzerindeki teorik sınırıdır**.

---

## 6. Sonraki Aşama (GA / Metaheuristic) İçin Çıkarımlar

Bu çalışma, sonraki optimizasyon aşamasında (Genetic Algorithm) izlenmesi gereken doğru yolu kesinleştirmiştir:

1. **Rastgele Koordinat Arama Yapılmamalıdır:** Koordinatları serbest parametre ($x, y$) olarak mutasyona uğratan genetik algoritmalar %91.67 doluluk oranında %99.9 çakışmalı (infeasible) çözümler üretir.
2. **Kromozom Temsili Slicing Tree Olmalıdır:**
   - Genotip: Normalized Polish Expression (ör. `1 2 V 3 4 H V ...`)
   - Fenotip: `AreaPreservingSlicingDecoder` ile her departmanın alanına göre analitik boyutlandırma
   - Bu sayede crossover ve mutasyon operasyonları %100 garantili biçimde çakışmasız dikdörtgenler üretir.
3. **MHC İyileştirme Potansiyeli:**
   - Guillotine çıktısı (\$180k) ile Manuel Baseline (\$139k) arasında yaklaşık **\$40,765 (%22.6)** optimizasyon marjı bulunmaktadır.
   - GA'nın görevi, Giotin'in bulduğu bu feasible çözüm uzayında departmanların bay sıralamasını akış hacmine göre evrimleştirerek MHC'yi \$139k ve altına çekmektir.
