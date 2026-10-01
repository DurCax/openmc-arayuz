# Standartlar ve uygunluk matrisi (Dalga S-0)

Durum: S-0 araştırma çıktısı, 30.09.2026. Bu belge planın "Dalga S — Standart haritası"
tablosunu birincil kaynaklardan denetler. Kod içermez. Her iddianın yanında kaynak bağlantısı
verilir; doğrulanamayan her şey **DOĞRULANMADI** diye işaretlidir.

Telif notu: ANS, ASME, ISO ve IEEE standartları ücretlidir. Aşağıdaki özetler bu metinlerin
alıntısı değildir; yayıncı sayfalarındaki kapsam özetlerinden ve açık ikincil kaynaklardan
kendi sözcüklerimizle yazılmıştır. Madde numarası yalnızca açık bir kaynakta görüldüyse verilir.
Açık kaynaklar (NUREG, NRC SRP, IAEA, JCGM, BIPM, NEA) doğrudan okunmuştur.

---

## 1. Dürüst çerçeve

Bu program hiçbir standarda **sertifika vermez** ve bir analizi "standarda uygun" diye
onaylayamaz. Yaptığı iş, bir koşu ya da model için standartların ve iyi uygulamanın
isteyeceği **kanıtı üretmek** (girdi ve veri izlenebilirliği, belirsizlik bildirimi, yakınsama
göstergeleri, kriter karşılaştırmaları, yanlılık/USL hesabı) ve **eksikleri görünür kılmaktır**.
Bir tesisin lisanslanması ya da güvenlik analizinde kullanılması için kullanıcı kuruluşun
kendi kalite güvence programı (ör. ASME NQA-1 Subpart 2.7 türü bir yazılım QA programı),
nitelikli personeli, bağımsız gözden geçirmesi ve kendi doğrulama (validation) raporu ayrıca
gerekir. NUREG/CR-6698 bunu açıkça söyler: doğrulama, yalnızca kod ve kütüphaneye değil,
kodun kurulu olduğu donanıma ve modeli kuran kişinin yetkinliğine de bağlıdır; başka yerde
hazırlanmış girdi dosyalarının sorumluluğu onları kullanan kuruluşa geçer
([NUREG/CR-6698 §1.2, §2.3](https://www.nrc.gov/docs/ML0502/ML050250061.pdf)).
Kaynağı gösterilemeyen hiçbir eşik araca gömülmez; eşikler profil dosyasında durur ve
kullanıcı tarafından değiştirilebilir.

Program hedef kitlesi (üniversiteler, araştırma ve eğitim) açısından en uygun yazılım
çerçevesi **ANSI/ANS-10.4**'tür: bu standart açıkça *güvenlikle ilgili olmayan* (araştırma,
eğitim, kritik olmayan) bilimsel/mühendislik programlarının V&V'si içindir
([ANSI webstore](https://webstore.ansi.org/standards/ansi/ansians102008r2021)).

---

## 2. Doğrulanmış standart tablosu

Sütunlar: tam ad; güncel sürüm; yürürlük; erişim; kapsam; bu araca "ne gerektirir / ne
gerektirmez".

### 2.1 Yazılım kalitesi ve V&V

| Kimlik | Tam ad | Güncel sürüm / yürürlük | Erişim | Kapsam (özet) | Araç için ne gerektirir | Ne gerektirmez | Kaynak |
|---|---|---|---|---|---|---|---|
| ANSI/ANS-10.4 | Verification and Validation of Non-Safety-Related Scientific and Engineering Computer Programs for the Nuclear Industry | **2008 (R2021)** yürürlükte; ANS-10.4-202x revizyonu taslak aşamasında | ücretli | Güvenlikle ilgili olmayan, araştırma/kritik olmayan uygulamalardaki bilimsel yazılımın V&V yönergeleri (yeni ve mevcut yazılım) | S-4: V&V planı ve raporu, gereksinim→test izlenebilirliği, bilinen sınırlamalar listesi, sürüm notunda "neyi doğruladık" | Güvenlikle ilgili (safety-related) yazılım QA'sı; bunun için NQA-1 gerekir | [ANSI](https://webstore.ansi.org/standards/ansi/ansians102008r2021), [ANS What's New](https://www.ans.org/standards/new/) |
| ANSI/ANS-10.3 | Documentation of Computer Software | **1995 — tarihsel (historical), güncel değil**; ANS-10 alt komitesi artık yalnız 10.2, 10.4, 10.5'i sürdürüyor | ücretli (tarihsel kopya) | Bilimsel yazılım belgelendirmesi | Yalnız belge seti için esin kaynağı olarak anılabilir; uygunluk iddiasının dayanağı yapılmamalı | — | [ANSI](https://webstore.ansi.org/standards/ansi/ansians101995); geri çekilme yılı **DOĞRULANMADI** |
| ANSI/ANS-10.5 | Accommodating User Needs in Scientific and Engineering Computer Software Development | **2006**; yeniden onay yılı kaynaklarda çelişkili: ANSI blog **R2026**, ANSI webstore aramaları R2016 gösteriyor → **R-yılı DOĞRULANMADI** | ücretli | Kullanıcı ihtiyaçlarının (kullanılabilirlik, sağlamlık, belgeler, hata iletileri) yazılım geliştirmede gözetilmesi | Kılavuz (13b), hata iletilerinin anlaşılırlığı, girdi doğrulama, örnek problemler | Belirli bir arayüz tasarımı | [ANSI blog](https://blog.ansi.org/ansi/ansi-ans-10-5-2006-r2026-user-needs-software/) |
| ANSI/ANS-10.7 | (Yüksek bütünlüklü, gerçek zamanlı olmayan nükleer yazılım — geliştirici gereksinimleri) | 2013 (R2023) | ücretli | Yüksek bütünlüklü yazılım geliştirme | Bu araç için gerekmez; yalnız bilgi | — | [ANSI blog](https://blog.ansi.org/ansi/ansi-ans-10-7-2013-r2023-nuclear-industry-software/); tam başlık **DOĞRULANMADI** |
| ASME NQA-1 (Subpart 2.7) | Quality Assurance Requirements for Nuclear Facility Applications; Subpart 2.7: nükleer tesis uygulamaları için bilgisayar yazılımı QA gereksinimleri | ASME sayfası **en son baskıyı 2026** olarak gösteriyor (önceki: 2024, 24.07.2024'te yayımlandı). Subpart 2.7 **hâlâ var**; ASME sayfası "Subpart 2.7 ve 3.2-2.7.1'in yeniden yapılandırıldığını" belirtiyor — hangi baskıda olduğu **DOĞRULANMADI** | ücretli (310–415 USD) | Tesis yaşam döngüsü QA; yazılımın geliştirilmesi, edinilmesi, bakımı ve kullanımı | S-4: sürüm/ortam kilidi, değişiklik kaydı, yapılandırma yönetimi, kullanım ortamındaki değişikliklerin değerlendirilmesi. Araç **NQA-1 kapsamında geliştirilmiyor**; bir kuruluş kullanmak isterse kendi edinme/kabul (dedication) sürecini uygular | Aracın NQA-1 sertifikalı olması (olamaz; kuruluş programıdır) | [ASME](https://www.asme.org/codes-standards/find-codes-standards/quality-assurance-requirements-for-nuclear-facility-applications), [ANSI blog 2024](https://blog.ansi.org/ansi/asme-nqa-1-2024-nuclear-facility-applications/), [BSB Edge 2026](https://www.bsbedge.com/standard/quality-assurance-requirements-for-nuclear-facility-applications-asme-nqa-1-2026/ASME-NQA-1-2026) |
| IEEE 1012 | IEEE Standard for System, Software, and Hardware Verification and Validation | **1012-2024** (1012-2016'nın revizyonu; 2025'te yayımlandı) | ücretli | Bütünlük düzeyine göre ölçeklenen V&V süreç gereksinimleri; analiz, gözden geçirme, denetim, test | S-4: aracın bütünlük düzeyini (düşük) açıkça beyan edip V&V görevlerini buna göre seçmek | Yüksek bütünlük düzeyi görevlerinin tamamı | [IEEE Xplore](https://ieeexplore.ieee.org/document/11134780), [ANSI](https://webstore.ansi.org/standards/ieee/ieee10122024) |
| ISO/IEC/IEEE 12207 | Systems and software engineering — Software life cycle processes | **12207:2026** (Nisan 2026; 2017 baskısını iptal edip yerine geçti) | ücretli | Yazılım yaşam döngüsü süreçleri (yapılandırma, risk, doğrulama, bakım…) | S-4 belge setinin süreç adlandırması için çerçeve | Tüm süreçlerin uygulanması; standart uyarlamaya (tailoring) izin verir | [IEEE Xplore 2026](https://ieeexplore.ieee.org/iel8/11481696/11481697/11481698.pdf), [ANSI blog](https://blog.ansi.org/ansi/iso-iec-ieee-12207-2026-software-life-cycle/); iso.org sayfası erişilemedi (403) — yürürlükten kaldırma tarihi **DOĞRULANMADI** |

### 2.2 Kritiklik güvenliği ve hesap yöntemi doğrulaması

| Kimlik | Tam ad | Güncel sürüm / yürürlük | Erişim | Kapsam | Araç için ne gerektirir | Ne gerektirmez | Kaynak |
|---|---|---|---|---|---|---|---|
| ANSI/ANS-8.1 | Nuclear Criticality Safety in Operations with Fissionable Materials Outside Reactors | **2014 (R2023)** yürürlükte; ANS-8.1-202x revizyonu taslakta | ücretli | Reaktör dışı bölünebilir madde işlemlerinde kritiklik güvenliğinin temel ilkeleri; hesap yöntemlerinin deneyle doğrulanması, yanlılık ve uygulanabilirlik alanı kavramı | Profil B: hesap yönteminin kriter deneyleriyle doğrulanmış olduğunu, yanlılığın ve AOA'nın raporlanmasını istemek | Tesis işletme denetimleri, çift olasılık (double contingency) uygulaması — araç kapsamı dışı | [ANS What's New](https://www.ans.org/standards/new/); madde numaraları **DOĞRULANMADI** |
| ANSI/ANS-8.24 | Validation of Neutron Transport Methods for Nuclear Criticality Safety Calculations | **2017 (R2023)** yürürlükte; ANS-8.24-202x revizyonu taslakta | ücretli | Kritiklik güvenliği analizinde kullanılan nötron taşıma yöntemlerinin doğrulanması ve uygulanabilirliğinin kurulması (gereksinim + öneri) | S-3: yanlılık, yanlılık belirsizliği, AOA, alt-kritik pay ve belgeleme | Belirli bir istatistik yöntemi dayatması **DOĞRULANMADI** (metin görülmedi) | [ANSI](https://webstore.ansi.org/standards/ansi/ansians242017r2023), [ANS What's New](https://www.ans.org/standards/new/) |
| **NUREG/CR-6698** | Guide for Validation of Nuclear Criticality Safety Calculational Methodology (J.C. Dean, R.W. Tayloe Jr., SAIC; NRC NMSS) | **Ocak 2001**; revizyonu bilinmiyor; kılavuz (bağlayıcı değil) | **açık** (NRC ADAMS) | Kritiklik hesap yöntemi doğrulamasının adımları: işletme parametreleri → deney seçimi → modelleme → yanlılık/belirsizlik → eğilim → normallik → istatistik yöntemi → alt-kritik pay → USL → AOA → rapor | S-3'ün **istatistik yönteminin birincil kaynağı** (bkz. §4). Aracın sayısal çapraz kontrolü için belgedeki 25 noktalı örnek veri kullanılabilir | Belirli bir kod ya da kütüphane | [ML050250061](https://www.nrc.gov/docs/ML0502/ML050250061.pdf) |
| NUREG-1520 Bölüm 5 Ek B (eski FCSS ISG-10) | Justification for Minimum Margin of Subcriticality for Safety | ISG-10 (2006) NUREG-1520 Bölüm 5 Ek B'ye alındı | açık | Asgari alt-kritiklik payının (MMS) gerekçelendirilmesi; NUREG-1718 §6.4.3.3.4'te 0.05'in ek gerekçe olmadan genellikle kabul edildiği ifadesi (arama özeti) | Profil B'de varsayılan pay önerisi için kaynak | — | [NRC ISG listesi](https://www.nrc.gov/docs/ML0616/ML061650370.pdf); 0.05 ifadesi yalnız arama özetinden → **DOĞRULANMADI** |
| NRC RG 3.71 | Nuclear Criticality Safety Standards for Nuclear Materials Outside Reactor Cores | **Rev. 3 (Ekim 2018)**; ANSI/ANS-8 standartlarını onaylar (endorse) | açık | ANS-8 standartlarının NRC tarafından kabulü | Bilgi; ABD dışı kullanıcı için bağlayıcı değil | — | [RG 3.71 Rev.3](https://www.nrc.gov/docs/ML1816/ML18169A258.pdf), [FR 2018-21534](https://www.govinfo.gov/app/details/FR-2018-10-03/2018-21534) |
| ISO 1709 | Nuclear energy — Fissile materials — Principles of criticality safety in storing, handling and processing | **ISO 1709:2018** (3. baskı) + **Amd 1:2022** (kontrol yöntemleri ve güvenlik ekipmanı); 2023'te gözden geçirilip onaylandı | ücretli | Reaktör dışı bölünebilir madde işlemlerinde kritiklik güvenliğinin temel ilkeleri ve sınırlamaları; değerlendirme temeli, kritiklik güvenlik payı, güvenliğin gösterilmesi; QA gereksinimi içermez | Profil B'nin genel çerçevesi (pay kavramı, gösterim) | Hesap doğrulama istatistiği (bu standartta değil) | [ISO 1709:2018](https://www.iso.org/standard/68617.html), [Amd 1](https://www.iso.org/standard/81439.html), [NCSP özeti](https://ncsp.llnl.gov/sites/ncsp/files/2023-12/iso1709_summary_issue3.pdf) |
| IAEA SSG-27 (Rev. 1) | Criticality Safety in the Handling of Fissile Material | **2022** | **açık** | Alt-kritikliğin sağlanması; güvenlik değerlendirmeleri; **hesap yöntemlerinin doğrulanması, benchmark ve geçerlemesi**; kaza müdahalesi | Profil B için açık uluslararası kaynak (plan tablosunda yok) | — | [IAEA](https://www.iaea.org/publications/14883/criticality-safety-in-the-handling-of-fissile-material) |
| NEA/NSC/WPNCS/DOC(2013)7 | Overview of Approaches Used to Determine Calculational Bias in Criticality Safety Assessment (UACSA durum raporu, 1. bölüm; Ivanova vd.) | 2013 | açık | Ülkelerin yanlılık/USL belirleme uygulamalarının karşılaştırması | S-3 yöntem seçiminin gerekçesi, sınırlamalar (normallik, korelasyon) | — | [NEA PDF](https://oecd-nea.org/science/wpncs/UACSA/publications/EGUACSASOAR1.pdf) |
| NUREG/CR-7109 | An Approach for Validating Actinide and Fission Product Burnup Credit Criticality Safety Analyses — Criticality (keff) Predictions | 2012 (ORNL) | açık | Yanma kredisi doğrulaması; duyarlılık/benzerlik (c_k > 0.8) | Kapsam dışı (araçta duyarlılık hesabı yok); gelecekte AOA için benzerlik ölçüsü fikri | — | [NRC](https://www.nrc.gov/regulations-legislation/nureg-series-publications/publications-prepared-by-nrc-contractors/cr7109) |

### 2.3 Reaktör kor tasarımı ve reaktör fiziği yöntemleri

| Kimlik | Tam ad | Güncel sürüm / yürürlük | Erişim | Kapsam | Araç için ne gerektirir | Ne gerektirmez | Kaynak |
|---|---|---|---|---|---|---|---|
| IAEA SSG-52 | Design of the Reactor Core for Nuclear Power Plants | **2019**; SSR-2/1 (Rev. 1)'i destekler | **açık** | **Nükleer güç santrali** kor tasarımı: nötronik, termohidrolik, termomekanik; kor kontrolü, kapatma, izleme, kor yönetimi | Profil C (güç reaktörü alt profili) | Araştırma reaktörleri (onlar için SSR-3 ailesi) | [IAEA](https://www.iaea.org/publications/13382/design-of-the-reactor-core-for-nuclear-power-plants) |
| IAEA SSR-3 | Safety of Research Reactors (Specific Safety Requirements) | **2016** | **açık** | Araştırma reaktörlerinin bütün yaşam döngüsü; Bölüm 6 tasarım gereksinimleri | Profil C (araştırma reaktörü alt profili) | — | [IAEA](https://www.iaea.org/publications/7024/safety-of-research-reactors), [PDF](https://www-pub.iaea.org/MTCD/Publications/PDF/P1751_web.pdf) |
| IAEA SSG-22 (Rev. 1) | Use of a Graded Approach in the Application of the Safety Requirements for Research Reactors | **2023** (plan tablosunda "Rev. 1" eksik) | **açık** | SSR-3 gereksinimlerinin kademeli uygulanması (gereksinimden muafiyet değil, uyum biçimi) | Kademeli yaklaşımın gerekçesi: profillerin ve eşiklerin reaktör türüne göre ayarlanması | — | [IAEA](https://www.iaea.org/publications/15080/use-of-a-graded-approach-in-the-application-of-the-safety-requirements-for-research-reactors) |
| IAEA SSG-20 (Rev. 1) | Safety Assessment for Research Reactors and Preparation of the Safety Analysis Report | 2022 (**Rev. numarası ve yıl DOĞRULANMADI**) | açık | Araştırma reaktörü güvenlik değerlendirmesi ve SAR içeriği | Rapor bölümlerinin adlandırılması için bilgi | — | [IAEA PDF](https://www-pub.iaea.org/MTCD/Publications/PDF/PUB1981_web.pdf) |
| IAEA SSG-82 | Core Management and Fuel Handling for Research Reactors (NS-G-4.3'ün yerine) | yıl **DOĞRULANMADI** | açık | Araştırma reaktörü kor yönetimi ve yakıt işleme | Profil C araştırma reaktörü | — | [IAEA](https://www.iaea.org/publications/15095/core-management-and-fuel-handling-for-research-reactors) |
| IAEA SSG-2 (Rev. 1) | Deterministic Safety Analysis for Nuclear Power Plants | 2019 | açık | Deterministik güvenlik analizi; muhafazakâr ve en iyi tahmin + belirsizlik yaklaşımları | Bilgi (kod doğrulama beklentileri); araç geçici rejim analizi yapmaz | — | [IAEA](https://www.iaea.org/publications/12335/deterministic-safety-analysis-for-nuclear-power-plants) |
| NUREG-0800 §4.3 | Standard Review Plan, Section 4.3 "Nuclear Design" | **Rev. 3, Mart 2007** (ML070740003); daha yeni revizyon yok (NRC Bölüm 4 sayfası) | **açık** | GDC 10, 11, 12, 13, 20, 25, 26, 27, 28'e göre nükleer tasarım incelemesi: güç dağılımı, reaktivite katsayıları, kontrol gereksinimleri, kapatma marjı, en değerli çubuk sıkışık, analitik yöntemlerin ölçümle doğrulanması | Profil C'nin ABD LWR alt profili (bkz. §3 K7 düzeltmesi) | Katsayılar için sayısal kabul aralığı (SRP açıkça **vermez**); kapatma marjının sayısal değeri (SRP'de boş bırakılmış, tesise özel) | [SRP 4.3 Rev.3](https://www.nrc.gov/docs/ML0707/ML070740003.pdf), [NRC Bölüm 4](https://www.nrc.gov/regulations-legislation/nureg-series-publications/publications-prepared-by-nrc-staff/nureg-0800/chapter-4) |
| NRC RG 1.203 | Transient and Accident Analysis Methods | **Rev. 0, Aralık 2005** (tek revizyon) | açık | Tasarım esaslı **geçici rejim ve kaza** analizinde kullanılan değerlendirme modellerinin geliştirme ve değerlendirme süreci (EMDAP, 4 öğe); kademeli yaklaşım | Yalnız **benzetme** yoluyla: "değerlendirme tabanı", uygulanabilirlik ve kademeli yaklaşım fikirleri S-3/S-4'e esin verir | Kor statik nötronik tasarımı ya da kritiklik güvenliği için doğrudan gereksinim (kapsamı değil) | [RG 1.203](https://www.nrc.gov/docs/ML0535/ML053500170.pdf) |
| ANSI/ANS-19.3 | Steady-State Neutronics Methods for Power Reactor Analysis | **2022** (2011'in revizyonu) | ücretli | Kararlı durum reaksiyon hızı dağılımı, reaktivite ve nüklit bileşimi hesaplarının yapılması ve **doğrulanması**; yöntem seçimi, V&V ölçütleri, uygulanabilirlik aralığı, belgeleme; MOX kapsam dışı | Profil C'nin yöntem-doğrulama kuralları için en doğrudan ANS kaynağı (plan tablosunda yok) | — | [Accuris](https://store.accuristech.com/standards/ans-19-3-2022?product_id=2523230), [ANSI 2011](https://webstore.ansi.org/standards/ansi/ansians192011) |
| ISO 18075 | Steady-state neutronics methods for power-reactor analysis | 2018 | ücretli | ANS-19.3'ün ISO karşılığı | Profil C, uluslararası kaynak | — | [ISO](https://www.iso.org/standard/61293.html) |
| ANSI/ANS-19.11 | Calculation and Measurement of the Moderator Temperature Coefficient of Reactivity for Pressurized Water Reactors | 2017 | ücretli | PWR MTC hesap ve ölçümü | Profil C, K7 MTC notu | — | [ANSI](https://webstore.ansi.org/standards/ansi/ansians19112017) |
| ANSI/ANS-19.6.1 | Reload Startup Physics Tests for Pressurized Water Reactors | 2019 (R2024) | ücretli | Yakıt yenileme sonrası kor nükleer özelliklerinin testle doğrulanması | Bilgi (ölçüm-hesap karşılaştırma kültürü) | — | [Intertek](https://www.intertekinform.com/en-gb/standards/ansi-ans-19-6-1-2019-r2024--94754_saig_ans_ans_3441905/) |
| ANSI/ANS-19.13 | Initial Fuel Loading and Startup Physics Tests for First-of-a-Kind Advanced Reactors | 2024 | ücretli | İleri reaktörlerde ilk yükleme ve başlangıç fizik testleri | Bilgi | — | [ANSI](https://webstore.ansi.org/standards/ansi/ansians19132024) |
| ANS-19.5-202x | Requirements for Reference Reactor Physics Measurements | taslak (tarihsel 19.5-1995, W2005) | — | Referans reaktör fiziği ölçümleri | İzlenmeli; çıkarsa IRPhEP kullanımıyla ilişkili | — | [ANS What's New](https://www.ans.org/standards/new/) |

### 2.4 Kriter (benchmark) el kitapları

| Kimlik | Güncel baskı | Erişim ve kullanım koşulları | Kaynak |
|---|---|---|---|
| ICSBEP Handbook (International Handbook of Evaluated Criticality Safety Benchmark Experiments), NEA/NSC/DOC(95)03 | **2024 baskısı, Aralık 2025'te yayımlandı** (arama özeti; NEA sayfası 403 verdi → **DOĞRULANMADI**) | "İstek üzerine"; **adı belli kullanıcılara ve ayrıntılı kullanım amacıyla** dağıtılır; her yeni baskı için istek **yenilenmelidir**; NEA GitLab'da kod modelleri (şu an yalnız Serpent) — yeniden dağıtım koşulları sayfada yok (**DOĞRULANMADI**). NUREG/CR-6698, el kitabındaki deney tanımlarının hakemli kabul edildiğini, ama el kitabındaki örnek hesapların bir doğrulama yerine geçmediğini vurgular | [NEA ICSBEP](https://www.oecd-nea.org/jcms/pl_20291/international-criticality-safety-benchmark-evaluation-project-icsbep-handbook), [NEA Data Bank GitLab](https://databank.io.oecd-nea.org/benchmarks/icsbep/), [NUREG/CR-6698 §2.2](https://www.nrc.gov/docs/ML0502/ML050250061.pdf) |
| IRPhE Handbook (International Handbook of Evaluated Reactor Physics Benchmark Experiments) | **2022/23 baskısı** (NEA-1765) | DVD ya da çevrimiçi; paket istek formuyla; her baskıda istek yenilenir; **OECD üye ülkelerinin yetkili kullanıcılarına** ve katkı veren kuruluşlara; diğerleri tek tek değerlendirilir. Türkiye OECD/NEA üyesidir; Türk üniversitelerinin uygunluğu **DOĞRULANMADI** | [NEA-1765](https://www.oecd-nea.org/tools/abstract/detail/nea-1765/), [NEA IRPhE](https://www.oecd-nea.org/jcms/pl_20279/international-handbook-of-evaluated-reactor-physics-benchmark-experiments-irphe) |
| mit-crpg/benchmarks (GitHub) | etkin (son itme 17.09.2025) | **MIT lisanslı** OpenMC/MCNP modelleri (~120 ICSBEP değerlendirmesi); `icsbep/icsbep/uncertainties.csv` kriter k ve σ değerleri. Not: modeller açık lisanslı olsa da kriter tanımının kaynağı ICSBEP'tir; raporda ICSBEP kimliği ve baskısı yazılmalıdır | [GitHub](https://github.com/mit-crpg/benchmarks) |
| LANL MCNP kritiklik doğrulama takımı (Mosteller) | LA-UR-02-0878 (2002, 26 vaka); genişletilmiş 119 vaka LA-UR-10-06230 | "Approved for public release; distribution is unlimited" — açık | [LA-UR-02-0878](https://mcnpx.lanl.gov/pdf_files/TechReport_2002_LANL_LA-UR-02-0878_Mosteller.pdf), [OSTI 1092464](https://www.osti.gov/biblio/1092464) |

### 2.5 Belirsizlik, nicelik/birim ve terminoloji

| Kimlik | Güncel sürüm | Erişim | Araç için ne gerektirir | Kaynak |
|---|---|---|---|---|
| JCGM 100:2008 (GUM) | 2008 + **Amd. 1:2026** (doğrusal olmama) | **açık** | K5: standart belirsizliğin açık etiketlenmesi; sonuç biçimi (§7.2.2); belirsizliğin **en çok iki anlamlı rakamla** verilmesi (§7.2.6); "±" biçimi standart belirsizlik için kullanılıyorsa bunun güven aralığı olmadığının yazılması (§7.2.2 notu); genişletilmiş belirsizlikte k'nın belirtilmesi (§7.2.3) | [BIPM JCGM](https://www.bipm.org/en/committees/jc/jcgm/publications), [JCGM 100 PDF](https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf) |
| JCGM 101:2008 | GUM Ek 1 — Monte Carlo ile dağılım yayılımı; hâlâ güncel | **açık** | Girdi belirsizliği yayılımı yapılırsa (ör. yoğunluk/zenginlik örneklemesi) yöntem kaynağı; Monte Carlo taşıma istatistiğinin kendisi için değil | aynı |
| JCGM GUM-1:2023, GUM-6:2020 | yeni GUM bölümleri (giriş; ölçüm modeli geliştirme) | açık | Bilgi | aynı |
| BIPM SI Broşürü | 9. baskı (2019); indirilen sürüm **V3.01 (2024)**; BIPM sayfası "2026'da güncellendi" diyor — güncel alt sürüm numarası **DOĞRULANMADI** | **açık** (CC BY 4.0) | Birim yazımı; %'nin sayıdan boşlukla ayrılması; "ppm" türü tanımsal terimlerin kullanılıyorsa tanımının açıkça yazılması (pcm için de aynı ilke) | [BIPM SI Brochure](https://www.bipm.org/en/publications/si-brochure), [V3.01 PDF](https://www.bipm.org/documents/d/guest/si-brochure-9-3_01) |
| ISO 80000-10 | **2019 + Amd 1:2025** | ücretli | Atom ve nükleer fizik nicelik adları/simgeleri (ör. etkin çoğaltma katsayısı, reaktivite) — madde numaraları **DOĞRULANMADI** | [ISO 80000-10](https://www.iso.org/standard/64980.html), [Amd 1](https://www.iso.org/standard/87106.html) |
| IAEA Nuclear Safety and Security Glossary | **2022 (Interim) Edition** (eski adıyla IAEA Safety Glossary) | **açık** | `docs/SOZLUK.md` ve İngilizce arayüz terimleri | [IAEA](https://www.iaea.org/publications/15236/iaea-nuclear-safety-and-security-glossary) |
| ISO 921:1997 | **Geri çekildi**; yerine **ISO 12749** serisi (ör. 12749-3:2024 nükleer tesisler/süreçler; 12749-5:2018 nükleer reaktörler) | ücretli | Terminoloji için ISO kaynağı gerekiyorsa 12749 anılmalı | [ISO 921](https://www.iso.org/standard/5333.html), [ISO 12749-3:2024](https://www.iso.org/standard/82724.html), [ISO 12749-5:2018](https://www.iso.org/standard/67429.html) |

---

## 3. Uygunluk matrisi iskeleti

Kural kimlikleri planın K1–K7'sini korur; S-0 yeni kurallar önerir (K8–K17). Profiller:
**A** Monte Carlo iyi uygulaması (her koşu), **B** kritiklik güvenliği, **C** reaktör kor tasarımı,
**D** raporlama, **Y** yazılım kalite kanıtı (S-4; yeni harf önerisi). "Durum" sütunu S-1…S-4
sonrasıdır (01.10.2026). "Test" sütunu kırmızı→yeşil fixture fikridir.

**Profil B bağlantısı (01.10.2026, Dalga 4).** S-3 yanlılık/USL özetini hesaplar; uygunluk
paneli, rapor eki ve `openmc-arayuz-kosu uygunluk` komutu onu `cekirdek/vv/kume.uygulama_ozeti`
ile **kendiliğinden** bağlar. USL yalnız uygulamayla aynı bölünebilir tür, fiziksel biçim, tayf
(U-235'te zenginlik sınıfı LEU/IEU/HEU) taşıyan alt kümeden hesaplanır; uygun alt kümede 10'dan
az vaka varsa USL **verilmez** (`testler/test_vv_altkume.py`). Depodaki 26 vakalık kümede en
büyük uygun alt küme 5 vakadır; bu yüzden **bugün hiçbir uygulama için USL çıkmaz** (ör.
pwr_17x17: uygun vaka yalnız LCT-008). Önceki sürüm alt kümeyi yalnız tayfla seçip pwr_17x17'ye
9 çözelti + 1 kafesten USL 0.93877 veriyordu; düzeltildi. Aşağıda K6, K6-AOA ve K8–K14 bu
yüzden "kısmen"dir: kurallar bağlı ve sınanmış, ama kümenin kapsamı USL için yetersiz.

| # | Kaynak / konu | Kural | Profil | Ne denetlenir (özet) | Önerilen test | Durum |
|---|---|---|---|---|---|---|
| 1 | İyi uygulama (standart değil); NUREG/CR-6698 §2.4 dipnotu: Monte Carlo'da yakınsamanın kullanıcı tarafından yargılanması gerekir | K1 | A | Shannon entropisi platosu; inaktif çevrim sayısı plato başlangıcından büyük | Entropisi platoya ulaşmadan aktif çevrime geçen sahte `statepoint` | karşılandı (S-1 kuralı; S-2 panel + rapor eki) |
| 2 | İyi uygulama (standart değil): Brown, LA-UR-09-03136 (2009) §III.C (her hesapta "1000s of neutrons/cycle" → 1000), §V (uzun üretim koşusunda "at least 5000"; "a few hundred active cycles" → sayı yok), §IV.A (çevrimler arası ilinti σ'yı küçümsetir); NUREG/CR-6698 eş. (36) k'nın σ'sını kullanır | K2 | A | σ_k ≤ profil hedefi; aktif çevrim ve çevrim başı parçacık alt sınırı; çevrimler arası korelasyon notu. Parçacık eşikleri **iyi uygulama kaynağından** (standart değil); σ hedefi profil değeridir. Brown'ın "1,7–4,7 kat" bulgusu yerel tally'ler içindir (§IV.B Tablo 2), k-eff'e taşınmaz | σ_k hedefin üstünde koşu | kısmen: parçacık alt sınırı ve çevrim ilintisi denetlenir; σ hedefi ve aktif çevrim alt sınırının kaynaklı sayısı yok → profil girdisi (yoksa "uygulanamadı") |
| 3 | İyi uygulama (OpenMC) | K3 | A | Kayıp parçacık = 0 | Kayıp parçacık uyarısı içeren çıktı | karşılandı (S-1; S-2: arayüz koşusu da `kosu.log` yazar, kayıp parçacık Çalıştır sayfasında görünür — M5) |
| 4 | ANS-10.4 (izlenebilirlik), NUREG/CR-6698 §2.3 (kod, modül, kütüphane, donanım tanımı) | K4 | D | Kütüphane adı+sürümü, sıcaklıklar, S(α,β), veri sha256, OpenMC sürümü, işletim sistemi/donanım özeti raporda | Kütüphane sürümü eksik rapor | karşılandı (S-1 kuralı; rapor tekrarlanabilirlik bloğu) |
| 5 | JCGM 100 §7.2.2, §7.2.3, §7.2.6; BIPM SI Broşürü (tanımsal terimler) | K5 | D | (a) k ile birlikte standart belirsizlik ve "1σ, standart belirsizlik" etiketi; (b) belirsizlik ≤ 2 anlamlı rakam, değer aynı basamağa yuvarlı; (c) "±" kullanılıyorsa güven aralığı olmadığı yazılı ya da parantez biçimi `1.00038(25)`; (d) pcm tanımı yazılı **ve hangi büyüklüğe uygulandığı açık**: Δk × 10⁵ mi (VV.md'deki C−E sütunu böyle) yoksa Δρ × 10⁵ mi (ρ = (k−1)/k; iki durum arası Δρ = (k₂−k₁)/(k₁k₂)) | 3 anlamlı rakamlı σ; tanımsız pcm | karşılandı (S-1 denetçisi; S-2: üretilen rapor K5'ten temiz geçer — `test_uygunluk_arayuz` S2-1) |
| 6 | NUREG/CR-6698 eş. (1), (35), (36) | K6 (**düzeltilmiş**) | B | `k_calc + 2σ_calc < USL`. Plandaki `k + Kσ` genellemesi kalabilir, ama **varsayılan K = 2** olmalı (6698'in koşulu) ve eşitsizlik katıdır (<) | k + 2σ = USL − ε ve USL + ε | kısmen (S-3): 26 deneylik V&V kümesi; uygulamanın alt kümesi (tür + biçim + tayf + U-235 zenginlik sınıfı) en çok 5 vaka → USL **verilmez**; yalnız tayfla seçilen karışık alt kümeler (hızlı 0.9444, termal 0.9388) betimseldir (`docs/VV.md`); K6 geçtiğinde alt küme, n ve yöntem yazılır |
| 7 | NUREG/CR-6698 §2.5, Tablo 2.3 | K6-AOA | B | Uygulanabilirlik alanı: bölünebilir element aynı; zenginlik bandı (ör. %2–5 için ±1,5; %80–100 için ±10 ağırlıkça yüzde puanı); fiziksel biçim (metal/oksit/çözelti/bileşik) aynı; H/X ±%20; yansıtıcı malzemesi aynı; tayf sınıfı aynı (termal 0–1 eV, ara 1 eV–100 keV, hızlı 100 keV–20 MeV; EALF ile) | Kapsam dışı zenginlik ve farklı fiziksel biçim | kısmen (S-3): AOA parametreleri spec'ten ve EALF tally'sinden çıkarılır (`cekirdek/vv/aoa.py`; `docs/VV.md` AOA tablosu); panel/rapor/CLI'ye bağlı (yukarıdaki not) |
| 8 | NUREG/CR-6698 §2.4.1 eş. (8), §1.2 | K8 (yeni) | B | Pozitif yanlılık kredilendirilmez (bias > 0 ise 0) | Ortalama k > 1 olan küme | kısmen (S-3): kural V&V kümesiyle sınandı (VV7); bütün alt kümelerde yanlılık negatif; panel/rapor/CLI'ye bağlı (yukarıdaki not) |
| 9 | NUREG/CR-6698 §2.4.1 eş. (9) | K9 (yeni) | B | Kriter k_exp ≠ 1 ise k_norm = k_calc / k_exp kullanılır; birleşik σ = √(σ_calc² + σ_exp²) | k_exp = 1.0007 olan LCT-008 | kısmen (S-3): k_norm = k_calc / k_exp kümede uygulanır (ör. LCT-008 E = 1.0007); panel/rapor/CLI'ye bağlı (yukarıdaki not) |
| 10 | NUREG/CR-6698 §2.2 (10'dan az deney gerekçe ister), Tablo 2.2 (güven ≤ %40 → ek veri gerekli) | K10 (yeni) | B | n < 10 → UYARI "teknik gerekçe gerekli"; parametrik olmayan güven ≤ %40 → **USL hesaplanamadı** | n = 5 ve n = 9 kümeleri | kısmen (S-3): n < 10 → USL verilmez (aracın ek kuralı, `n_usl_asgari`); β ≤ %40 → "hesaplanamadı"; panel/rapor/CLI'ye bağlı (yukarıdaki not) |
| 11 | NUREG/CR-6698 §2.4.5 (ΔSM ≥ 0.02 mutlak alt sınır); NUREG-1520 Bl.5 Ek B / NUREG-1718 (0.05 genellikle kabul — **DOĞRULANMADI**) | K11 (yeni) | B | Profil ΔSM < 0.02 ise HATA (profil geçersiz); varsayılan 0.05, kaynağı yazılı | ΔSM = 0.01 profili | karşılandı (profil ΔSM eşiği denetlenir; V&V gerekmez) |
| 12 | NUREG/CR-6698 §5 | K12 (yeni) | B | Uygulama parametresi doğrulama aralığının dışındaysa: tolerans *sınırı* yönteminde dış değerleme yasak → HATA/UYARI; aralığın %10'undan fazla dış değerleme → "doğrulama kümesi genişletilmeli"; ΔAOA kullanıcı girdisi ve gerekçe metni | Aralığın %12 dışında bir uygulama | kısmen (S-3): sayısal AOA aralığı kümeden (zenginlik, H/X, EALF); ΔAOA kullanıcı girdisi; panel/rapor/CLI'ye bağlı (yukarıdaki not) |
| 13 | NUREG/CR-6698 §2.4.2–2.4.3 | K13 (yeni) | B | Eğilim testi (ağırlıklı doğrusal uydurma; eğim anlamlılığı) ve normallik testi sonuçları raporda; yöntem seçimi bu sonuçlara bağlı | Belirgin H/X eğilimli küme | kısmen (S-3): Shapiro–Wilk ve ağırlıklı doğrusal eğilim (t-testi SCALE/VADER kökenli, 6698'de yok); hiçbir alt kümede anlamlı eğilim yok; panel/rapor/CLI'ye bağlı (yukarıdaki not) |
| 14 | WPNCS/UACSA 2013; UACSA Faz IV (deneyler arası korelasyon) | K14 (yeni) | B | Aynı deney serisinden çok vaka (ör. LCT-008'in 17 durumu) kümeye girerse BİLGİ: "vakalar bağımsız değil; istatistik güveni abartılı olabilir" | Tek seriden 10 vaka | kısmen (S-3): LEU-SOL-THERM-002 durum 1/2 için "bağımsız değil" notu; korelasyonun kendisi hesaplanmaz; panel/rapor/CLI'ye bağlı (yukarıdaki not) |
| 15 | NUREG/CR-6698 §6 (rapor biçimi), §2 (bağımsız yinelenebilirlik) | K15 (yeni) | D (+B) | Doğrulama raporu bölümleri: giriş, kod sistemi, yöntem, deney tanımları, sonuç analizi (eğilim, istatistik, yanlılık, belirsizlik, AOA, USL), sonuç; imza/bağımsız gözden geçiren alanı boş bırakılır (kuruluş doldurur) | Bölüm eksik rapor | kısmen: `docs/VV.md` (S-3) 6698 §6 bölümlerinin çoğunu içerir (kod sistemi, yöntem, deney tanımları, eğilim/normallik/yanlılık/AOA/USL, sınırlamalar); imza/bağımsız gözden geçiren alanı yok; raporu denetleyen kural yok |
| 16 | NUREG-0800 §4.3 II.2 (GDC 11), SRP §4.3 III | K7 (**düzeltilmiş**) | C | **Güç katsayısı ve Doppler katsayısı** işareti (güç işletme aralığında net anlık geri besleme negatif olmalı) → HATA/UYARI. **Pozitif MTC tek başına HATA değildir** (SRP açıkça pozitif MTC'yi dışlamaz; ör. PWR ömür başı) → BİLGİ + "geçici rejim analizinde değerlendirilmeli". Katsayılar için sayısal kabul aralığı **yok** | Pozitif MTC + negatif Doppler: bilgi; pozitif güç katsayısı: hata | kısmen: kural hazır; katsayılar `uygunluk_girdisi.json` "kor" anahtarından (Analiz sekmesi bağlantısı yok) |
| 17 | NUREG-0800 §4.3 (SDM, en değerli çubuk sıkışık; değer boş), GDC 26/27 | K7-SDM | C | Kapatma marjı en değerli çubuk sıkışık varsayımıyla hesaplanır; sınır **kullanıcı girdisi**, varsayılan yok; çubuk değeri belirsizliği (yöntem hatası dahil) not edilir | Sınır girilmemiş profil → "karşılaştırılamadı" | kısmen: kural hazır; marj ve sınır kullanıcı girdisi (`uygunluk_girdisi.json`) |
| 18 | NUREG-0800 §4.3 (güç dağılımı sınırları tesise özel) | K7-F | C | F_ΔH, F_q yalnız kullanıcı sınırıyla karşılaştırılır | Sınırsız profil | karşılandı (F_ΔH / F_q statepoint'ten; sınır yoksa "karşılaştırılamadı") |
| 19 | ANS-19.3-2022 / ISO 18075 (yöntem V&V, uygulanabilirlik aralığı, belgeleme) | K16 (yeni) | C | Kor hesabının hangi kriterlerle (IRPhEP/hesap-hesap) doğrulandığı ve bu kriterlerin uygulama aralığı raporda | Kriter referansı olmayan kor raporu | kısmen: referans girilmemişse "karşılanmadı" notu; madde ayrıntıları **DOĞRULANMADI** |
| 20 | IAEA SSG-22 (Rev. 1) kademeli yaklaşım | profil yapısı | C | Profil eşiklerinin reaktör türüne göre (güç / araştırma / kritik düzenek) seçilebilmesi | — | kısmen: Profil C `reaktor_turu` eşiği; eşikler `profiller.dosyadan_uyarla` ile |
| 21 | ANS-10.4-2008 (R2021); IEEE 1012-2024 (bütünlük düzeyi) | Y1 (yeni) | Y | Gereksinim (R-…) → test → son sonuç matrisi; testsiz gereksinim ve gereksinimsiz test listesi; aracın bütünlük düzeyinin beyanı | Testsiz gereksinim | karşılandı (S-4): `docs/IZLENEBILIRLIK.md` (`araclar/izlenebilirlik.py`; R-S-15); bütünlük düzeyi beyanı `docs/YAZILIM_KALITE.md` §1. Not: depodaki matris S-3 birleşmeden önceki sonuç dosyalarından üretildi (R-M2-01 ve R-S-14 orada "testsiz"; testleri artık işaretli) — yeniden üretilmeli |
| 22 | NQA-1 Subpart 2.7 (yapılandırma yönetimi, kullanım ortamı değişikliği); NUREG/CR-6698 §1.2 (periyodik doğrulama testi) | Y2 (yeni) | Y | Ortam kilidi (conda karması, OpenMC ve kütüphane sürümü); ortam değiştiğinde kısa kriter paketinin yeniden koşulması ve önceki sonuçlarla karşılaştırılması | Kütüphane karması değişmiş koşu dizini | kısmen (S-4): her koşuda `kapsul.json` (spec, OpenMC, kütüphane ve zincir karmaları, ortam kilidi özeti) ve `openmc-arayuz-kosu yeniden` fark raporu (R-S-16, R-S-17); ortam değişince kriter paketinin yeniden koşulması otomatik değil (elle: `pytest testler/test_benchmark.py -m yavas`); tam kilit dosyası saklanmıyor (`docs/YAZILIM_KALITE.md` §4 md. 7) |
| 23 | ANS-10.5 (kullanıcı ihtiyaçları); ANS-10.3 (tarihsel) | Y3 (yeni) | Y | Belge seti: kullanıcı kılavuzu, bilinen sınırlamalar, örnek problemler, değişiklik günlüğü | — | kısmen (S-4): belge seti ve eksikleri `docs/YAZILIM_KALITE.md` §2'de (R-S-18); örnek problemler `docs/ORNEKLER.md`; bilinen sınırlamalar dağınık; kullanıcı kılavuzu `docs/kilavuz/{tr,en}` (TR + EN); değişiklik günlüğü Dalga 4'te ayrı iş |
| 24 | ISO/IEC/IEEE 12207:2026 | Y4 | Y | S-4 belgelerinde süreç adları 12207 terimleriyle eşlenir (yalnız adlandırma) | — | karşılandı (S-4): `docs/YAZILIM_KALITE.md` §2 son sütun (yalnız adlandırma; süreçlerin 12207'ye göre uygulandığı iddia edilmez) |
| 25 | IAEA Glossary 2022; ISO 12749 | terminoloji | D | SOZLUK.md terimleri IAEA tanımlarına bağlanır | — | kısmen: `docs/SOZLUK.md` (Dalga 3) IAEA Glossary 2022 ve OpenMC adlandırmasını kaynak alır; terim başına IAEA tanımına bağlantı yok |
| 26 | ANS-8.1 / ISO 1709 / SSG-27: işletme denetimleri, çift olasılık ilkesi, kaza alarmı | — | — | Araç tesis işletmesi değerlendirmez | — | kapsam dışı |
| 27 | RG 1.203 EMDAP (geçici rejim ve kaza modelleri) | — | — | Araç geçici rejim/kaza analizi yapmaz; yalnız kademeli yaklaşım fikri alınır | — | kapsam dışı |
| 28 | ANS-8.24 madde düzeyi gereksinimler | — | B | Metin görülmedi | — | doğrulanmadı |

---

## 4. NUREG/CR-6698 yöntem özeti (koda dökülebilir)

Kaynak: NUREG/CR-6698 (Ocak 2001), [ML050250061](https://www.nrc.gov/docs/ML0502/ML050250061.pdf).
Denklem numaraları belgedekilerdir. Belge açık bir NRC yüklenici raporudur; formüller
matematiksel ifadedir, aşağıda kendi gösterimimizle yazılmıştır. **Aşağıdaki bütün formüller,
belgenin §3–4'teki 25 noktalı örneği sayısal olarak yeniden üretilerek doğrulandı** (bkz. §4.9).

### 4.1 Girdiler

Her kriter vakası i = 1…n için: `k_i` (hesap), `σ_calc,i` (Monte Carlo 1σ), `k_exp,i` ve
`σ_exp,i` (kriter değeri ve belirsizliği), bir ya da daha çok eğilim parametresi `x_i`
(H/X, zenginlik, EALF…), ve AOA parametreleri.

1. **Normalleştirme** (eş. 9): `k_norm,i = k_i / k_exp,i`. Yanlılığın mutlak değeri bu adımla
   asla küçültülmemelidir.
2. **Birleşik belirsizlik** (eş. 3): `σ_i = sqrt(σ_calc,i² + σ_exp,i²)`; ağırlık `w_i = 1/σ_i²`.
   (VADER uygulaması σ'ları göreli olarak birleştirir; k ≈ 1'de fark ihmal edilebilir.)

### 4.2 Ağırlıklı istatistikler (eş. 4–7)

```
W      = Σ w_i
k̄      = Σ w_i k_i / W                                  (6)  ağırlıklı ortalama
s²     = [ (1/(n−1)) Σ w_i (k_i − k̄)² ] / [ W / n ]      (4)  ortalama etrafında varyans
σ̄²     = n / W                                          (5)  ortalama toplam belirsizlik
S_p    = sqrt(s² + σ̄²)                                  (7)  birleştirilmiş (pooled) std. sapma
bias   = k̄ − 1  (k̄ < 1 ise), aksi hâlde 0              (8)  pozitif yanlılık kredilendirilmez
```

### 4.3 Eğilim (eş. 10–15)

Ağırlıklı doğrusal uydurma `k_fit(x) = a + b·x`:
```
x̄    = Σ w_i x_i / W
b    = Σ w_i (x_i − x̄)(k_i − k̄) / Σ w_i (x_i − x̄)²
a    = k̄ − b·x̄
r    = Σ w_i (x_i − x̄)(k_i − k̄) / sqrt( Σ w_i (x_i − x̄)² · Σ w_i (k_i − k̄)² )
```
Belge uyum iyiliği için (i) farklı eksen ölçekleriyle çizim, (ii) sayısal ölçüt (r, r² ya da χ²)
önerir ve r'nin tek başına mutlak ölçü olmadığını not eder. Eğim anlamlılığı için belge bir
test **tanımlamaz**; SCALE/VADER şu t-testini kullanır (öneri, 6698'de yok):
`t = |b| / (σ_fit / sqrt(S_xx))`, `t > t_{α/2, n−2}` ise eğilim anlamlı
([SCALE VADER](https://scale-manual.ornl.gov/6.3.3/vader.html)).

### 4.4 Normallik testi (§2.4.3)

- 50'den az örnek için **Shapiro–Wilk W testi** (eş. 16–19; katsayılar Ek A, n = 10–50;
  yüzde noktaları Tablo A.5). Değerler artan sıraya dizilir; `W = (Σ_{j=1}^{v} a_j (y_(n+1−j) − y_(j)))² / Σ (y_i − ȳ)²`,
  `v = n/2` (çift) ya da `(n−1)/2` (tek). W, α = 0.05 kritik değerinden büyükse normal kabul edilir.
- Uygulama notu: kodda `scipy.stats.shapiro` kullanılabilir (p > 0.05 ⇒ normal); belgedeki
  örnek için scipy W = 0.9201, belge W = 0.9182 verir (tablo katsayısı farkı); ikisi de n = 25
  kritik değeri 0.918'in üstünde. Ağırlıklı ortalama kullanıldığında belge W = 0.9177 bulur ve
  örneğin "sınırda" olduğunu yazar → araç sınırda sonuçlarda iki yöntemi de raporlamalı.
- n > 50 için belge yöntem vermez (**DOĞRULANMADI**: 6698'de D'Agostino önerisi görülmedi).
  VADER χ² ve Anderson–Darling sunar.
- Normallik başarısızsa **parametrik olmayan yöntem zorunludur**.

### 4.5 Tek taraflı alt tolerans sınırı — eğilim yoksa, veri normalse (eş. 20–22)

```
K_L = min(k̄, 1) − U · S_p                                (20)–(21)
USL = K_L − ΔSM − ΔAOA                                   (22)
```
`U`: %95 güvenle popülasyonun %95'inin üstünde kaldığı tek taraflı tolerans çarpanı
(Tablo 2.1: n=10 → 2.911; 15 → 2.566; 20 → 2.396; 25 → 2.292; 30 → 2.220; 40 → 2.126;
50 → 2.065). **n > 50 için n = 50 değeri muhafazakâr olarak kullanılabilir.** Kodda tam
değer merkezî olmayan t dağılımıyla hesaplanır ve tabloyla 3 ondalıkta örtüşür (doğrulandı):
```
U(n) = t⁻¹_nct(0.95; ν = n−1, δ = z_0.95 · sqrt(n)) / sqrt(n)
```
Bu yöntem AOA'nın dışına **dış değerleme için kullanılamaz**.

### 4.6 Tek taraflı alt tolerans bandı — eğilim varsa (eş. 23–30)

```
S_xx   = Σ w_i (x_i − x̄)² / (W / n)                                      (26)
s_fit² = (n/(n−2)) · Σ w_i (k_i − k_fit(x_i))² / W                       (30)
S_p    = sqrt(s_fit² + σ̄²)                                               (28)–(29)
k*(x)  = min(k_fit(x), 1)                     # pozitif yanlılık kredilendirilmez (24)
K_L(x) = k*(x) − S_p · [ sqrt( 2·F · (1/n + (x − x̄)²/S_xx) ) + z · sqrt( (n−2) / χ² ) ]   (23)
USL(x) = K_L(x) − ΔSM − ΔAOA
```
Sabitler (P = 0.95 güven, n−2 serbestlik):
`F = F⁻¹(0.95; 2, n−2)` (Excel FINV(0.05,2,n−2)); `z = Φ⁻¹(0.95) = 1.645`;
`χ² = χ²⁻¹(0.025; n−2)` yani **alt** %2,5 noktası (Excel CHIINV(0.975, n−2)).
n = 25 için F = 3.422, χ² = 11.689. Bant, veri aralığı dışına çıkıldıkça kendiliğinden
genişler; belge bu nedenle band yönteminde ek ΔAOA'nın gerekmeyebileceğini söyler (§5).
Belge ayrıca bir "güven bandı" tekniğinden söz eder ama formül vermez (VADER'daki USL-1/USL-2
NUREG/CR-6361 kökenlidir — **6698'de yok**, S-3 isterse ayrı kaynakla kodlanmalı).

### 4.7 Parametrik olmayan yöntem — veri normal değilse (eş. 31–34)

```
β(m) = 1 − Σ_{j=0}^{m−1} C(n, j) (1−q)^j q^(n−j)     q = 0.95 (popülasyon oranı)  (31)
m = 1 (en küçük değer) için:  β = 1 − qⁿ                                       (32)
K_L = k_(1) − σ_(1) − NPM          (en küçük k_norm'un kendi birleşik σ'sı)      (33)
k_(1) > 1 ise:  K_L = 1 − S_p − NPM                                            (34)
```
NPM (Tablo 2.2, "önerilen", gerekçeyle değiştirilebilir):

| β (güven) | NPM |
|---|---|
| > %90 | 0.00 |
| > %80 | 0.01 |
| > %70 | 0.02 |
| > %60 | 0.03 |
| > %50 | 0.04 |
| > %40 | 0.05 |
| ≤ %40 | **ek veri gerekli** (yaklaşık n < 10) → araç "USL hesaplanamadı" demeli |

%95/%95 için en az **59 deney** gerekir (NPM = 0). n = 19 → β = %62,3; n = 25 → %72,26.

### 4.8 Alt-kritik pay, USL ve kabul koşulu (§2.4.5–2.4.6, eş. 1, 35, 36)

```
USL = 1 + bias − σ_bias − ΔSM − ΔAOA        (1)  (biçimsel tanım)
USL = K_L − ΔSM − ΔAOA                      (35) (uygulamadaki biçim)
Kabul:  k_calc + 2·σ_calc < USL              (36)
```
- **ΔSM ≥ 0.02 mutlak alt sınırdır**; seçilen değer denetlenen parametrenin reaktivite
  duyarlılığı ve denetim türüne (fiziksel/idari) göre **gerekçelendirilmelidir**. Belgedeki
  örnek: ±½ inç tolerans 0.01 Δk veriyorsa 0.02 pay gerekçelidir.
- ΔAOA: AOA genişletilmiyorsa 0. Parametrenin %5–10 dış değerlemesi "büyük" sayılır ve ek pay
  ister; %10'u aşan dış değerlemede doğrulama kümesi genişletilmelidir (§1.2, §5).
- Pay, süreç bozulmalarını ya da süreç belirsizliklerini karşılamak için **değildir**; yalnızca
  doğrulama sonucuna göre alt-kritik sayılabilecek en büyük k'yı belirler.

### 4.9 Sayısal çapraz kontrol verisi (S-3 test fixture'ı için)

NUREG/CR-6698 Tablo 3.1'deki 25 vaka (H/X, k, σ_calc; bütün vakalarda σ_exp = 0.0049)
ile aşağıdaki sonuçlar bu çalışmada Python/SciPy ile **birebir yeniden üretildi**:

| Nicelik | Belge | Yeniden hesap |
|---|---|---|
| k̄ (ağırlıklı) | 0.99983 | 0.999834 |
| s² | 8.47993e−5 | 8.47993e−5 |
| σ̄² | 2.67991e−5 | 2.67991e−5 |
| S_p | 1.056e−2 | 1.0564e−2 |
| K_L (U = 2.292) | 0.97562 | 0.97562 |
| USL (ΔSM 0.02, ΔAOA 0.03) | 0.92562 | 0.92562 |
| β (parametrik olmayan, n = 25) | %72,26 | %72,26 |
| K_L parametrik olmayan (0.9848 − 0.0051 − 0.02) | 0.9597 | — (aritmetik) |
| a, b (ağırlıklı doğrusal) | 1.00967, −2.863e−5 | 1.00967, −2.8629e−5 |
| x̄ | 343.58 | 343.576 |
| s_fit², S_p (bant) | 3.782e−5, 0.008039 | 3.782e−5, 0.0080386 |
| K_L(421.8) / USL | 0.9746 / 0.9546 | 0.9746 / 0.9546 |
| K_L(971.7) / USL | 0.9515 / 0.9315 | 0.9515 / 0.9315 |
| K_L(133.4) / USL | 0.9758 / 0.9558 | 0.9758 / 0.9558 |

Not: metin çıkarımında satır 17'nin H/X değeri "−133.4" okunmuştur; doğrusu 133.4'tür
(diğer değerler ve sonuçlar bunu doğrular). Örnekte ΔAOA = 0.03 yalnız gösterim içindir.

### 4.10 Belgenin koda yansıyan sınırlamaları

- Deneyler arası **korelasyon** ele alınmaz (bağımsızlık varsayımı); UACSA çalışmaları bunu
  açık konu olarak gösterir ([PSI/UACSA 2007](https://www.oecd-nea.org/science/wpncs/UACSA/kick-off%20meeting/PSI-1.pdf)).
- Yöntem seçiminin gerekçesi kullanıcı kuruluşa aittir (§2.4.4); araç önerir, zorlamaz.
- Excel istatistik işlevlerinin bazı sürümlerde hatalı olduğu uyarısı vardır; araç SciPy
  kullanmalı ve Tablo 2.1 değerleriyle birim testiyle karşılaştırmalıdır.

---

## 5. Aday benchmark vaka listesi (hedef 20–30)

Seçim ölçütleri: (i) ICSBEP'te değerlendirilmiş; (ii) **açık yayımlanmış bir kaynakta**
kriter k ve σ değeri var (LANL LA-UR-02-0878 "distribution is unlimited" ya da
mit-crpg `uncertainties.csv`); (iii) **MIT lisanslı OpenMC modeli** mit-crpg deposunda var;
(iv) araçla kurulabilecek geometri (küre, silindir, kafes, sonsuz ortam). Yeşil kümeyi
LANL'ın 26 vakalık doğrulama takımı oluşturur; çünkü bu küme tayf ve malzeme çeşitliliği
gözetilerek seçilmiş ve açıkça yayımlanmıştır
([LA-UR-02-0878 Tablo 1–2](https://mcnpx.lanl.gov/pdf_files/TechReport_2002_LANL_LA-UR-02-0878_Mosteller.pdf)).

**Önemli uyarı:** E ± σ değerleri ICSBEP baskıları arasında değişebilir. Aşağıda iki açık
kaynak ayrı ayrı gösterilir; çelişkiler işaretlidir. S-3, her vakanın değerini **güncel
ICSBEP baskısından** doğrulamadan kümeye resmî olarak almamalıdır. Hepsi **DOĞRULANMADI
(el kitabı metni görülmedi)** kabul edilmelidir.

| # | ICSBEP kimliği | Kısa ad | Malzeme / biçim / tayf | E ± σ (LA-UR-02-0878) | E ± σ (mit-crpg csv) | OpenMC modeli | Neden uygun | Araçta durum |
|---|---|---|---|---|---|---|---|---|
| 1 | HEU-MET-FAST-001 | Godiva | HEU metal, çıplak küre, hızlı | 1.0000 ± 0.0010 | 1.0 ± 0.001 | var | En temel hızlı U-235 vakası | **mevcut** (godiva_kriter) |
| 2 | HEU-MET-FAST-028 | Flattop-25 | HEU metal, doğal U yansıtıcılı, hızlı | 1.0000 ± 0.0030 | 1.0 ± 0.0030 | var | Ağır yansıtıcı etkisi | **mevcut** |
| 3 | HEU-MET-FAST-004 | "Godiver" | HEU metal, su yansıtıcılı, hızlı | 0.9985 ± 0.0011 | 0.9985 ± **0.0 (csv'de σ eksik)** | var | Hafif yansıtıcı | aday |
| 4 | HEU-MET-INTER-006, durum 2 | ZEUS | HEU plakalar, grafit moderatör, bakır yansıtıcı, ara | 0.9997 ± 0.0008 | **1.0001** ± 0.0008 (çelişki) | var | Ara tayf (az bulunur) | aday |
| 5 | HEU-SOL-THERM-032 | ORNL-10 | HEU uranil nitrat çözeltisi, büyük küre, termal | 1.0015 ± 0.0026 | 1.0015 ± 0.0026 | var | HEU çözelti, termal | aday |
| 6 | HEU-SOL-THERM-013, durum 1 | — | HEU çözelti, termal | — | 1.0012 ± 0.0026 | var | Çözelti çeşitliliği | aday |
| 7 | HEU-SOL-THERM-001, durum 1 | — | HEU çözelti, termal | — | 1.0004 ± 0.0060 | var | Çözelti çeşitliliği (σ büyük) | aday |
| 8 | IEU-MET-FAST-003 | — | %36 U metal, çıplak küre, hızlı | 1.0000 ± 0.0017 | 1.0 ± 0.0017 | var | Ara zenginlik | aday |
| 9 | IEU-MET-FAST-004 | — | %36 U metal, grafit yansıtıcı, hızlı | 1.0000 ± 0.0030 | 1.0 ± 0.0030 | var | Grafit yansıtıcı | aday |
| 10 | IEU-MET-FAST-007 | Big Ten | %10 U metal silindir, doğal U yansıtıcı, hızlı | 0.9948 ± 0.0013 (basit model) | 1.0045 ± 0.0007 (durum 1; ayrıntılı model) — **model türüne göre değişir** | var | Düşük zenginlikli hızlı sistem; U-238 verisine duyarlı | aday (model türü seçilmeli) |
| 11 | LEU-COMP-THERM-008, durum 1 | B&W XI | LEU UO₂ çubuk kafesi, borlu su, termal | 1.0007 ± 0.0012 | 1.0007 ± 0.0012 | var | LWR'ye en yakın vaka | **mevcut** (kriter_lct008) |
| 12 | LEU-COMP-THERM-008, durum 2 | B&W XI (2) | aynı seri | 1.0007 ± 0.0012 | 1.0007 ± 0.0012 | var | LANL takımındaki durum; aynı seriden olduğu için **K14 korelasyon uyarısı** | aday |
| 13 | LEU-SOL-THERM-001 | SHEBA-II | %5 U uranil florür çözeltisi, halka silindir, termal | 0.9991 ± 0.0029 | 0.9991 ± 0.0029 | var | LEU çözelti | aday |
| 14 | LEU-SOL-THERM-002, durum 1 | — | LEU çözelti, termal | — | 1.0038 ± 0.0040 | var | LEU çözelti çeşitliliği | aday |
| 15 | LEU-SOL-THERM-007, durum 14 | (STACY — **DOĞRULANMADI**) | ~%10 U uranil nitrat, termal | — | 0.9961 ± 0.0009 | var | Küçük σ'lı LEU çözelti | aday |
| 16 | PU-MET-FAST-001 | Jezebel | Pu metal, çıplak küre, hızlı | 1.0000 ± 0.0020 | 1.0 ± 0.0020 | var | Temel Pu vakası | **mevcut** (kriter_jezebel) |
| 17 | PU-MET-FAST-002 | Jezebel-240 | Pu (%20,1 Pu-240), çıplak küre, hızlı | 1.0000 ± 0.0020 | 1.0 ± 0.0020 | var | Pu-240 içeriği | aday |
| 18 | PU-MET-FAST-006 | Flattop-Pu | Pu küre, doğal U yansıtıcı, hızlı | 1.0000 ± 0.0030 | 1.0 ± 0.0030 | var | Ağır yansıtıcı + Pu | aday |
| 19 | PU-MET-FAST-011 | — | Pu küre, su yansıtıcı, hızlı | 1.0000 ± 0.0010 | (csv satırı bu çalışmada görülmedi) | var | Hafif yansıtıcı + Pu | aday |
| 20 | PU-MET-FAST-003, durum 3 | Pu Buttons | 3×3×3 küçük Pu silindir dizisi, hızlı | 1.0000 ± 0.0030 | (depoda yalnız "case-103" modeli görüldü — **eşleşme DOĞRULANMADI**) | kısmen | Dizi geometrisi | aday (koşullu) |
| 21 | PU-COMP-INTER-001 | HISS/HPG | Pu + H + grafit sonsuz homojen karışım, ara | 1.0000 ± 0.0110 | 1.0 ± 0.0110 | var | Sonsuz ortam — kurması en kolay; σ_exp büyük (ağırlığı düşük) | aday |
| 22 | PU-SOL-THERM-021, durum 3 | PNL-2 | Pu nitrat çözeltisi küresi, termal | 1.0000 ± 0.0065 | 1.0 ± 0.0065 | var | Pu çözelti | aday |
| 23 | PU-SOL-THERM-001, durum 1 | — | Pu nitrat çözeltisi, termal | — | 1.0 ± 0.0050 | var | Pu çözelti çeşitliliği | aday |
| 24 | MIX-COMP-THERM-002, PNL-33 | PNL-33 | MOX çubuk kafesi, borlu su, termal | 1.0024 ± 0.0021 | 1.0024 ± 0.0024 (pnl-33) / 0.0021 (pnl-33d) — **σ farkı model türünden** | var | MOX kafes (termal Pu) | aday |
| 25 | U233-MET-FAST-001 | Jezebel-233 | U-233 metal, çıplak küre, hızlı | 1.0000 ± 0.0010 | 1.0 ± 0.0010 | var | U-233 (Th çevrimi ilgisi) | aday |
| 26 | U233-MET-FAST-006 | Flattop-23 | U-233 küre, doğal U yansıtıcı, hızlı | 1.0000 ± 0.0014 | 1.0 ± 0.0014 | var | U-233 + ağır yansıtıcı | aday |
| 27 | U233-MET-FAST-005, durum 2 | — | U-233 küre, Be yansıtıcı, hızlı | 1.0000 ± 0.0030 | 1.0 ± 0.0030 | var | Be yansıtıcı | aday |
| 28 | U233-SOL-INTER-001, durum 1 | Falstaff (1) | U-233 uranil florür çözeltisi küresi, ara | 1.0000 ± 0.0083 | (csv satırı görülmedi) | var | Ara tayf çözelti | aday |
| 29 | U233-SOL-THERM-008 | ORNL-11 | U-233 uranil nitrat büyük küre, termal | 1.0006 ± 0.0029 | (csv satırı görülmedi) | var | U-233 termal | aday |

LANL takımında olup **mit-crpg'de OpenMC modeli bulunmayan** üç vaka: HEU-COMP-INTER-004
(HISS/HUG), HEU-MET-THERM-003 durum 4, IEU-COMP-THERM-002 durum 3 — bunlar ICSBEP metninden
yeniden modellenmedikçe kümeye alınamaz.

Kapsam değerlendirmesi ve boşluklar:
- Tayf: hızlı (≈17), ara (4), termal (≈10) — çeşitli; ancak **tek bir AOA'ya** hepsi girmez.
  NUREG/CR-6698'e göre USL her AOA için ayrı hesaplanır; örneğin "LEU termal kafes" AOA'sı
  için bu listede yalnız LCT-008 serisi vardır ve bu tek seri, bağımsız 10 vaka koşulunu
  sağlamaz. Üniversitelerin en sık kullandığı LWR/LEU uygulamaları için **LEU-COMP-THERM
  serilerinden (ör. LCT-001, -002, -039 vb.) ek vaka gerekir**; bunlar mit-crpg'de yoktur ve
  ICSBEP el kitabı isteğiyle edinilmelidir (erişim: §2.4).
- Bu nedenle ilk sürümde araç, "LEU termal kafes" AOA'sı için **USL'yi hesaplamamalı**
  ("yeterli bağımsız vaka yok") ve yalnız C/E tablosunu göstermelidir.

---

## 6. Plan tablosunda yanlış ya da eksik çıkan maddeler

1. **ANSI/ANS-10.3** güncel standart gibi listelenmiş; 1995 baskısı **tarihsel** (historical)
   durumdadır, ANS-10 alt komitesi artık yalnız 10.2, 10.4, 10.5'i sürdürmektedir.
   Uygunluk dayanağı yapılmamalı ([ANSI](https://webstore.ansi.org/standards/ansi/ansians101995)).
2. **ANSI/ANS-10.4**'ün kapsamı plan tablosunda eksik: standart yalnız **güvenlikle ilgili
   olmayan** (araştırma/kritik olmayan) yazılım içindir — bu araç için doğru çerçeve budur,
   ama "güvenlik analizi yazılımı" iddiası buna dayanamaz. Güncel: 2008 (R2021); revizyon taslakta.
3. **ANSI/ANS-10.5**: 2006 baskısı; yeniden onay yılı kaynaklarda çelişkili (R2016 / R2026) —
   DOĞRULANMADI.
4. **ASME NQA-1**: ASME sayfası en son baskıyı **2026** olarak gösteriyor (2024 de vardı).
   Subpart 2.7 yürürlükte, fakat "yeniden yapılandırıldı" notunun hangi baskıya ait olduğu
   DOĞRULANMADI. NQA-1 bir kuruluş QA programıdır; araç "NQA-1 uyumlu" olamaz.
5. **IEEE 1012** artık **1012-2024** (2016 değil); **ISO/IEC/IEEE 12207** artık **12207:2026**
   (2017 baskısı iptal edildi).
6. **ANS-8.1 / 8.24** sürümleri tabloda yoktu: 8.1-2014 (R2023), 8.24-2017 (R2023); ikisinin de
   revizyonu taslakta.
7. **Plan K6 "k_eff + Kσ ≤ USL"**: NUREG/CR-6698 koşulu **k + 2σ < USL**'dir (katı eşitsizlik,
   K = 2). Ayrıca plan ΔSM'nin **0.02 alt sınırından**, **n < 10** için gerekçe gereğinden,
   parametrik olmayan yöntemde **%95/%95 için 59 deney** gereğinden, pozitif yanlılığın
   kredilendirilmemesinden ve k_calc/k_exp normalleştirmesinden söz etmiyordu (yeni K8–K12).
8. **Plan K7 "reaktivite katsayılarının işareti"**: NUREG-0800 §4.3 Rev.3, katsayılar için
   sayısal kabul aralığı vermediğini ve **pozitif MTC'yi dışlamadığını** açıkça yazar;
   doğrudan gereksinim GDC 11'dir (güç işletme aralığında net anlık geri beslemenin reaktivite
   artışını karşılaması; LWR'de Doppler ve negatif güç katsayısıyla sağlanır). Pozitif MTC'yi
   HATA saymak yanlış alarm üretir. Kapatma marjının sayısal değeri de SRP'de boştur (tesise özel).
9. **IAEA SSG-52** yalnız **nükleer güç santrali** kor tasarımı içindir (2019, SSR-2/1 Rev.1
   altında). Araştırma reaktörleri için dayanak **SSR-3 (2016)** ve **SSG-22 (Rev. 1) (2023)**'tür;
   planda SSG-22'nin "(Rev. 1)" eki eksik. Tabloda olmayan ilgili IAEA belgeleri: **SSG-27 (Rev. 1)
   2022** (kritiklik güvenliği — hesap yöntemi doğrulaması dahil; Profil B için açık uluslararası
   kaynak), SSG-20 (Rev. 1), SSG-82.
10. **RG 1.203** geçici rejim ve kaza analizi değerlendirme modelleri (EMDAP) içindir; kor
    statik nötronik tasarımı ya da kritiklik güvenliği için doğrudan kabul ölçütü vermez.
    Profil C'ye "kaynak" diye bağlanmamalı; yalnız benzetme (kademeli yaklaşım, değerlendirme
    tabanı) olarak anılmalı. Kor yöntem doğrulaması için doğru ANS kaynağı **ANS-19.3-2022**
    (ve ISO karşılığı **ISO 18075:2018**) — tabloda yoktu.
11. **ISO 921** geri çekildi; yerine **ISO 12749** serisi (12749-3:2024, 12749-5:2018) geçti.
12. **"IAEA Safety Glossary"** adı eski: güncel yayın **IAEA Nuclear Safety and Security
    Glossary, 2022 (Interim) Edition**.
13. **ICSBEP/IRPhEP "açık (kayıtlı)"** ifadesi eksik: ICSBEP adı belli kullanıcılara, ayrıntılı
    kullanım amacı beyanıyla ve **her baskı için yenilenen istekle** verilir; IRPhE OECD üye
    ülkelerinin yetkili kullanıcılarına verilir. El kitabı içeriğinin yeniden dağıtımı serbest
    değildir (koşullar DOĞRULANMADI) → araç kriter tanımlarını paketlerken yalnız açık kaynaklı
    modelleri (mit-crpg, MIT) ve açık yayımlanmış E ± σ değerlerini kullanmalı, kaynağı yazmalı.
14. **JCGM 100** artık **Amd. 1:2026** ile birlikte anılmalı; JCGM 101:2008 güncel.
    **ISO 80000-10:2019**'un **Amd 1:2025**'i var. **SI Broşürü** 9. baskı, V3.01 (2024) ve
    sonrası (alt sürüm DOĞRULANMADI).
15. **K5** için GUM ayrıntısı: "±" biçimi standart belirsizlik için GUM tarafından önerilmez
    (kullanılırsa güven aralığı olmadığı yazılmalı); belirsizlik en çok iki anlamlı rakamla
    verilir (planın "1–2 anlamlı rakam" ifadesi uyumlu). pcm tanımı yazılırken **Δk mı Δρ mı**
    olduğu ayrılmalı — VV.md'deki "C − E [pcm]" Δk × 10⁵'tir, reaktivite farkı değildir.
16. **K1–K3** (entropi platosu, σ hedefi, kayıp parçacık) hiçbir standardın maddesi değildir;
    "iyi uygulama" olarak etiketlenmeli, standart kaynağı varmış gibi gösterilmemeli.
17. VV.md'deki kabul ölçütü |C − E| ≤ 3·√(σc² + σe²) projenin kendi ölçütüdür; bir standarttan
    gelmez — raporda böyle belirtilmeli.

---

## Kaynakça (erişim: 30.09.2026)

- NRC, NUREG/CR-6698 (2001): https://www.nrc.gov/docs/ML0502/ML050250061.pdf
- NRC, NUREG-0800 §4.3 Rev.3 (2007): https://www.nrc.gov/docs/ML0707/ML070740003.pdf
- NRC, RG 1.203 (2005): https://www.nrc.gov/docs/ML0535/ML053500170.pdf
- NRC, RG 3.71 Rev.3 (2018): https://www.nrc.gov/docs/ML1816/ML18169A258.pdf
- NRC, NUREG/CR-7109: https://www.nrc.gov/regulations-legislation/nureg-series-publications/publications-prepared-by-nrc-contractors/cr7109
- ANS, What's New: https://www.ans.org/standards/new/
- ASME NQA-1: https://www.asme.org/codes-standards/find-codes-standards/quality-assurance-requirements-for-nuclear-facility-applications
- IEEE 1012-2024: https://ieeexplore.ieee.org/document/11134780
- ISO/IEC/IEEE 12207:2026: https://ieeexplore.ieee.org/iel8/11481696/11481697/11481698.pdf
- ISO 1709:2018: https://www.iso.org/standard/68617.html ; NCSP özeti: https://ncsp.llnl.gov/sites/ncsp/files/2023-12/iso1709_summary_issue3.pdf
- IAEA SSG-52: https://www.iaea.org/publications/13382/design-of-the-reactor-core-for-nuclear-power-plants
- IAEA SSR-3: https://www.iaea.org/publications/7024/safety-of-research-reactors
- IAEA SSG-22 (Rev. 1): https://www.iaea.org/publications/15080/use-of-a-graded-approach-in-the-application-of-the-safety-requirements-for-research-reactors
- IAEA SSG-27 (Rev. 1): https://www.iaea.org/publications/14883/criticality-safety-in-the-handling-of-fissile-material
- IAEA Glossary 2022: https://www.iaea.org/publications/15236/iaea-nuclear-safety-and-security-glossary
- NEA ICSBEP: https://www.oecd-nea.org/jcms/pl_20291/international-criticality-safety-benchmark-evaluation-project-icsbep-handbook
- NEA IRPhE: https://www.oecd-nea.org/tools/abstract/detail/nea-1765/
- NEA/NSC/WPNCS/DOC(2013)7: https://oecd-nea.org/science/wpncs/UACSA/publications/EGUACSASOAR1.pdf
- BIPM JCGM yayınları: https://www.bipm.org/en/committees/jc/jcgm/publications
- BIPM SI Broşürü: https://www.bipm.org/en/publications/si-brochure
- SCALE 6.3.3 VADER (ikincil, formül karşılaştırması): https://scale-manual.ornl.gov/6.3.3/vader.html
- LANL LA-UR-09-03136 (F.B. Brown, "A Review of Best Practices for Monte Carlo Criticality Calculations", ANS NCSD 2009): https://mcnpx.lanl.gov/pdf_files/TechReport_2009_LANL_LA-UR-09-03136_Brown.pdf — birincil kaynaktan doğrulandı (01.10.2026): §II.C kaynak yakınsaması (k ve H_src çizimleri); §III.C "1000s of neutrons/cycle … for all calculations"; §IV.A çevrimler arası ilinti σ'yı küçümsetir; §IV.B Tablo 2 yerel fisyon hızlarında 1,7–4,7 kat (ort. 3,1), k-eff için belirgin yanlılık gözlenmedi (§IV.C); §V "at least 5000 or more neutrons per cycle … for long production runs … a few hundred active cycles"
- LANL LA-UR-02-0878 (Mosteller): https://mcnpx.lanl.gov/pdf_files/TechReport_2002_LANL_LA-UR-02-0878_Mosteller.pdf
- mit-crpg/benchmarks: https://github.com/mit-crpg/benchmarks
