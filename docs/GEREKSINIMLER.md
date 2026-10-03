# Yazılım gereksinimleri (Dalga S-4)

Durum: 01.10.2026. Bu belge, kullanıcının onayladığı v2 kapsamını (A1–A4, M1–M10; 28.09.2026),
Dalga G kararlarını (`docs/GEOMETRI_MODELI.md` §15) ve Dalga S kurallarını (`docs/STANDARTLAR.md`
§3) **doğrulanabilir tek cümlelik gereksinimlere** çevirir. Her gereksinimin kimliği testlerde
`@gereksinim("R-…")` işaretiyle kullanılır (`testler/ortak_test.py`); gereksinim → test → son
sonuç matrisi `araclar/izlenebilirlik.py` ile `docs/IZLENEBILIRLIK.md`'ye üretilir.

Kurallar:
- Kimlik biçimi `R-<grup>-<iki hane>`; bir kimlik silinmez, yalnız "geri çekildi" diye işaretlenir.
- **Yöntem** sütunu: **T** = otomatik test, **İ** = inceleme (belge/dosya/elle denetim),
  **A** = analiz (ölçüm raporu). Yalnız T satırları için test beklenir; testsiz T satırı
  matriste "testsiz" görünür ve bu bir **eksikliktir**, gizlenmez.
- Sayısal eşikler buradan değil, kaynak gösterilen test/profil dosyasından gelir; burada yalnız
  ne istendiği yazılır.
- Bu liste bir **güvenlikle ilgili (safety-related) yazılım** gereksinim belgesi değildir;
  bağlam için `docs/YAZILIM_KALITE.md` §1.

## 1. Fizik çıpaları (Ortak kural 4)

| Kimlik | Gereksinim | Kaynak | Yöntem |
|---|---|---|---|
| R-FZ-01 | Referans pin hücresinin k∞ değeri kayıtlı çıpa değerinden (1.3570 ± 0.0020) sapmaz. | Plan, Ortak kural 4 | T |
| R-FZ-02 | Godiva (HEU-MET-FAST-001) modeli deneysel k_eff değeriyle ölçülmüş belirsizlik içinde uyuşur. | Plan, Ortak kural 4 | T |
| R-FZ-03 | Üretilen Python betiği, uygulamanın kendi kurucusuyla aynı modeli ve istatistik içinde aynı k_eff değerini verir. | Plan, Ortak kural 4 | T |
| R-FZ-04 | Üretilen betiğin geometri XML'i uygulama kurucusunun XML'iyle eşdeğerdir. | GEOMETRI_MODELI §16 (eşdeğerlik kapısı D) | T |

## 2. Onaylı kapsam: A1–A4

| Kimlik | Gereksinim | Kaynak | Yöntem |
|---|---|---|---|
| R-A1-01 | `altigen_kafes` kor türü şemada tanımlıdır, doğrulamadan geçer ve OpenMC geometrisi olarak kurulur. | A1 | T |
| R-A1-02 | Yansıtıcı sınırlı, bütün demetleri aynı 7 demetli altıgen kor, tek demetin k∞ değeriyle 2σ içinde aynıdır. | A1, fizik kabulü | T |
| R-A1-03 | Kor kafesi ile demet pin kafesi arasındaki yönelim nokta-hücre testleriyle ölçülerek doğrulanır. | A1 | T |
| R-A2-01 | Tükenme zincirinde bulunmayan izlenen nüklid doğrulamada HATA verir ve en yakın ad önerilir. | A2 | T |
| R-A2-02 | Sonuç dosyasında bulunamayan izlenen nüklid sessizce atlanmaz, notlarda listelenir. | A2 | T |
| R-A2-03 | Eski proje dosyalarındaki `izlenen` listeleri aynen yüklenir ve seçim değişince koşu tekrarlanmadan sonuçtan yeniden okunur. | A2 | T |
| R-A2-04 | Tükenme sonuçları zaman, yanma, k ve seçili nüklidlerle CSV olarak dışa aktarılır. | A2 | T |
| R-A3-01 | Dağıtılan her örnek proje doğrulama kapısından HATA bulgusu olmadan geçer. | A3 | T |
| R-A3-02 | Her örnekte başlık, kategori ve seviye meta alanları bulunur ve geçerlidir. | A3 | T |
| R-A4-01 | Tasarım tokenlarındaki metin/arka plan renk çiftleri WCAG 2.2 AA kontrast oranını sağlar. | A4 | T |
| R-A4-02 | Arayüz kodunda tasarım tokenları dışında sabit renk değeri bulunmaz. | A4, Ortak kural 6 | T |
| R-A4-03 | Arayüzdeki her QLayout bir widget'a bağlıdır (sahipsiz yerleşim yok). | Dalga 2 kuralı | T |

## 3. Onaylı kapsam: M1–M10

| Kimlik | Gereksinim | Kaynak | Yöntem |
|---|---|---|---|
| R-M1-01 | Tam kor güç haritası her demeti kendi kafes konumuyla ayırır (farklı zenginlikli demetlerin farkı haritada görünür). | M1 | T |
| R-M1-02 | F_ΔH ve F_q bütün kor üzerinden hesaplanır ve her demetin kendi tepe değeri de verilir. | M1 | T |
| R-M1-03 | Çok zenginlikli korda her yakıt çubuğu türü güç haritasına girer. | M1 (Dalga 2'ye devreden iş) | T |
| R-M1-04 | Güç dağılımı toplamı referans güç toplamıyla korunur (korunum denetimi). | M1 | T |
| R-M2-01 | Her benchmark için hesap/deney oranı (C/E) ve fark σ cinsinden V&V tablosunda kayıtlı ve kaynak JSON ile tutarlıdır. | M2 | T |
| R-M3-01 | Tam kor örnekleri koşar ve kayıtlı referans k değerleriyle tutarlıdır. | M3 | T |
| R-M4-01 | Yeni ya da değişen kaynak dosyalar 800 satır tavanını aşmaz (aşan dosya gerekçesiyle listelenir). | M4, Ortak kural 8 | İ |
| R-M5-01 | Kaynak kodda hata yutan (`except: pass` türü) blok izin listesi dışında bulunmaz. | M5, Ortak kural 7 | T |
| R-M5-02 | Uygulama hataları dönen günlük dosyasına yazılır ve arayüzde hata diyaloğuyla gösterilir. | M5 | T |
| R-M6-01 | Eski test sözleşmesi (`kontrol()`, HIZLI/YAVAS) pytest altında aynı sonuçla koşar; eksik veri nedeni atlama metninde yazılır. | M6 | T |
| R-M6-02 | Sürekli tümleştirme (GitHub Actions) hızlı süiti her gönderimde koşar. | M6 | İ |
| R-M7-01 | Uygulama sürümü tek kaynaktan (`pyproject.toml`) okunur ve `openmc-arayuz` / `openmc-arayuz-kosu` giriş noktaları tanımlıdır. | M7 | T |
| R-M8-01 | Depoda lisans dosyası ve üçüncü taraf lisans listesi bulunur. | M8 | İ |
| R-M9-01 | Kullanıcıya görünen metinler çeviri katalogundan gelir; İngilizce seçildiğinde çeviri yüklenir. | M9 | T |
| R-M9-02 | Doğrulama bulgusu metinleri iki dilde de üretilebilir (çevrilmemiş msgid kalmaz). | M9 | T |
| R-M10-01 | Rapor bir koşu dizininden HTML ve PDF olarak üretilir; sayılar statepoint ile birebir aynıdır. | M10 | T |
| R-M10-02 | Raporun tekrarlanabilirlik bloğu uygulama sürümü, git commit, OpenMC sürümü, kütüphane, zincir sha256 ve tohumu içerir; bilinmeyen alan "bilinmiyor" yazılır. | M10 | T |
| R-M10-03 | `openmc-arayuz-kosu rapor` komutu raporu terminalden üretir ve hatada sıfırdan farklı çıkış kodu döndürür. | M10 | T |

## 4. Tükenme (genel fizik)

| Kimlik | Gereksinim | Kaynak | Yöntem |
|---|---|---|---|
| R-TK-01 | Tükenme çözücüsü salt bozunum probleminde analitik Bateman çözümüyle uyuşur. | Fizik kabulü | T |
| R-TK-02 | Tükenen malzemelerin analitik hacimleri OpenMC stokastik hacmiyle 1σ içinde uyuşur. | A1, G-2 | T |
| R-TK-03 | Seçilen tükenme zinciri dosyası bütündür ve spektruma göre doğru zincir seçilir. | Fizik kabulü | T |

## 5. Dalga G — esnek geometri (GEOMETRI_MODELI §15–16)

| Kimlik | Gereksinim | Kaynak | Yöntem |
|---|---|---|---|
| R-G-01 | Eski kor türleri ağaç kurucusuyla aynı modeli verir: rastgele noktalarda aynı malzeme/hücre yolu ve aynı örnek hacimleri. | Plan, eşdeğerlik kapısı | T |
| R-G-02 | Proje dosyası şema sürümü taşır; göç zinciri saf işlevdir, bozuk dosya yedeklenir ve açıkça reddedilir. | Ek öneri M2 | T |
| R-G-03 | Gelişmiş geometri moduna geçiş tek yönlüdür ve Geri Al ile tek adımda geri alınır. | §15.1 | T |
| R-G-04 | Kafes konumu bölgeye tam oturmayan (kesik) blok/çubuk doğrulamada UYARI üretir. | §15.2 | T |
| R-G-05 | Yakıt pini kesiti silindir, altıgen ve kare olabilir ve analitik hacmi şekle göre hesaplanır. | §15.3 | T |
| R-G-06 | Dış sınırın her yüzü ayrı sınır koşulu alır; çeyrek kor örneği tam korla 2σ içinde aynı k'yı verir. | §15.4 | T |
| R-G-07 | Her kontrol çubuğu yerleşimi ayrı bir evren, örnek ve hacimdir. | §15.5 | T |
| R-G-08 | Kasıtlı örtüşen ve kasıtlı boşluklu geometriler doğrulamada yakalanır. | G-2 (Ek öneri M1) | T |
| R-G-09 | Ağaç geometrisi fizik kabullerini sağlar: sonsuz ortam eşdeğerliği, tambur dönmesinde monoton k, 60° simetri ve hacim uyumu. | G-4 | T |
| R-G-10 | Üretilen betik kullanıcı adlarını kaçışlı yazar; tırnak, satır sonu ve kod içeren adlar betiği bozmaz. | Ek öneri M3 | T |
| R-G-11 | Hedef düzenekler (kare çekirdek + altıgen halka, altıgen kor + tambur halkası, kafesli kor + tamburlu yansıtıcı) kurulur ve koşar. | G-1 kabulü | T |

## 6. Dalga S — uygunluk denetimi ve yazılım kalite kanıtı (STANDARTLAR §3)

| Kimlik | Gereksinim | Kaynak | Yöntem |
|---|---|---|---|
| R-S-01 | Uygunluk çıktıları "sertifika değildir, kanıt üretir" dürüst çerçeve metnini taşır. | STANDARTLAR §1 | T |
| R-S-02 | K1: Shannon entropisi platoya ulaşmadan aktif çevrime geçen koşu bulgu üretir. | K1 | T |
| R-S-03 | K2: σ_k, aktif çevrim ve çevrim başı parçacık profil eşikleriyle denetlenir. | K2 | T |
| R-S-04 | K3: Koşu çıktısındaki kayıp parçacık ayrıştırılır ve sıfırdan büyükse bulgu üretir. | K3, Ek öneri M5 | T |
| R-S-05 | K4: Raporda kütüphane, sürüm, sıcaklık, S(α,β) ve zincir sha256 bulunmazsa bulgu üretilir. | K4 | T |
| R-S-06 | K5: k ile birlikte 1σ standart belirsizlik etiketi, ≤ 2 anlamlı rakam ve pcm tanımı yazılır. | K5 | T |
| R-S-07 | K6: k + 2σ < USL koşulu denetlenir; doğrulama kümesi yoksa "USL hesaplanamadı" denir. | K6 | T |
| R-S-08 | K8–K11: pozitif yanlılık kredilendirilmez, k_exp normalleştirilir, az deney uyarı verir, ΔSM < 0.02 profili geçersizdir. | K8–K11 | T |
| R-S-09 | K12, K6-AOA, K13, K14: uygulanabilirlik alanı dışı, eğilim/normallik ve deney korelasyonu bulgu üretir. | K12–K14 | T |
| R-S-10 | K7: güç/Doppler katsayısı işareti, kapatma marjı ve F_ΔH/F_q yalnız kullanıcı sınırıyla denetlenir. | K7 | T |
| R-S-11 | Dağıtılan örnekler temiz profilde yanlış alarm üretmez ya da nedeni açıklanır. | S-1 kabulü | T |
| R-S-12 | `openmc-arayuz-kosu uygunluk` hata bulgusunda sıfırdan farklı çıkış kodu döndürür. | S-2 | T |
| R-S-13 | Rapora uygunluk eki (karşılanan / karşılanmayan / uygulanamayan) girer ve denetim hatası raporu durdurmaz. | S-2 | T |
| R-S-14 | Benchmark kümesinden yanlılık, yanlılık belirsizliği ve USL NUREG/CR-6698 yöntemiyle hesaplanır. | S-3, K6 | T |
| R-S-15 | Gereksinim → test → son sonuç matrisi üretilir; testsiz gereksinim ve gereksinimsiz kritik test listelenir. | Y1 | T |
| R-S-16 | Her koşu dizinine spec karması, sürümler, veri karmaları, tohum ve ortam kilidi özetini içeren tekrarlanabilirlik kapsülü yazılır. | Y2, Ek öneri M4 | T |
| R-S-17 | Bir koşu kapsüldeki spec ile yeniden üretilir ve ortam/sonuç farkı raporlanır. | Y2, Ek öneri M4 | T |
| R-S-18 | Belge seti (gereksinimler, tasarım, test planı/sonuçları, V&V, kılavuz, bilinen sınırlamalar, değişiklik günlüğü) listelenir ve eksikleri yazılır. | Y3, Y4 | İ |

## 7. v3 (Dalga T–Q) — hız, başlangıç, veri, pin/demet sonuçları, yeni fizik, paketleme

Kimlikler `R-V3-NN`. Yöntem **T** = otomatik test; **A** = analiz (`docs/VV.md`); **İ** = inceleme (öğrenci QA ve profesör denetimi raporları; CHANGELOG 3.0.0).

| Kimlik | Gereksinim | Kaynak | Yöntem |
|---|---|---|---|
| R-V3-01 | Yeni ("Sıfırdan") model gerçekten boştur: yalnız çekirdek türü içerir; boş modelde eksik aşamalar bilgi olarak sunulur, gerçek hatalar gizlenmez ve Çalıştır kapalıdır. | K1 | T |
| R-V3-02 | Örnek kullanmadan sıfırdan kurulan pin hücresi doğrulamadan geçer ve gerçek bir koşu verir. | K1 | T |
| R-V3-03 | Nükleer veri kütüphanesi yolu tek çözümleyiciden gelir: ortam değişkeni > kullanıcı ayarı > aday klasör; hiçbiri yoksa açık "yok". | K2 | T |
| R-V3-04 | Kütüphane indirme atomiktir, kesintiden sürdürülür ve bayt/sha256 uyuşmazlığında hata verir. | K2 | T |
| R-V3-05 | İndirme yalnız https ve katalogdaki izinli alan adlarına yapılır; yönlendirmeler de denetlenir. | K2 | T |
| R-V3-06 | Pin gücü tablosu güç haritasıyla aynı değerleri taşır ve toplamı toplam güç × hedef payına eşittir. | K3 | T |
| R-V3-07 | Çeyrek katlama yalnız geometri simetrisi doğrulanırsa yapılır; aksi halde nedeniyle reddedilir. | K3 | T |
| R-V3-08 | Tükenmede adım başına pin gücü tablosu üretilir (adım × pin). | K3 | T |
| R-V3-09 | Yerel k haritası: üretim ağırlıklı ortalama ΣP/ΣD sonsuz kafeste k∞'a eşittir; yakıtsız hücrelerin yok olması paydada kalır. | K4 | T |
| R-V3-10 | Demet k∞ sihirbazının kurduğu tek demet modeli elle kurulanla fiziksel olarak özdeştir; budama yalnız kullanılmayan malzemeleri atar. | K4 | T |
| R-V3-11 | Önizleme kapsamında alt model yalnız seçili parçanın malzemelerini içerir. | K5 | T |
| R-V3-12 | Önizleme çizimi eski Model.plot ile aynı malzeme haritasını verir ve Çalıştır kapısı davranışı değişmez. | H2 | T |
| R-V3-13 | Geometri doğrulaması tuş başına tek ağaç gezintisi yapar; büyük örneklerde açılış ve tuş süreleri gerekçeli eşiklerin altındadır. | H1 | T |
| R-V3-14 | Malzeme hesaplayıcıları bağımsız el hesabıyla ve OpenMC ile uyumludur (U izotop vektörü, türetilmiş değerler). | K6 | T |
| R-V3-15 | Kullanıcı malzeme kütüphanesi atomik yazılır; bozuk dosya silinmez, yedeklenir. | K6 | T |
| R-V3-16 | Mesh tally: kurucu ve üretilen betik aynı ağı ve aynı sonucu verir. | Y1 | T |
| R-V3-17 | Dört faktör çarpımı (c_xn ile) tally'lerden k∞'u verir; hızlı sistemde termal çarpanlar tanımsız bildirilir. | Y3 | T |
| R-V3-18 | Nokta kinetiği çözücüsü tek grup analitik çözümle, çok grup Inhour köküyle ve matris üstelle uyuşur. | Y6 | T |
| R-V3-19 | Sabit kaynakta yüzey akımı dengesi (giren − çıkan + kaynak + üretim = soğurma) korunur. | Y7 | T |
| R-V3-20 | Foton açıkken heating skorları üretilir; ara sıcaklık interpolasyonla koşar ve sıralama monotondur. | Y7 | T |
| R-V3-21 | Soğuma adımında bozunma ısısı tek nüklidli analitik çözümle uyuşur. | Y4 | T |
| R-V3-22 | Tükenme kaldığı yerden yalnız uyumlu fizik ve adım planıyla sürdürülür; uyumsuz istek nedeniyle reddedilir. | Y4 | T |
| R-V3-23 | Dal tablosunun koşulları tek değişkenli taramayla aynı koddan uygulanır. | Y5 | T |
| R-V3-24 | Tükenme bölgesi bölme yakıt hacmini korur (Gd pininde halka bölme dahil) ve betik eşdeğeridir. | Y5 | T |
| R-V3-25 | Grup sabitleriyle sonsuz ortam k∞ (yukarı saçılma dahil G×G özdeğer) el formülüyle uyuşur. | Y8 | T |
| R-V3-26 | TRISO paketleme oranı hedefe ±%1 içindedir ve kurucu ile betik aynı parçacıkları kurar. | Y9 | T |
| R-V3-27 | MAGIC ağırlık penceresi sonucu analogla istatistik içinde uyuşur (yanlılıksız) ve FOM'u artırır. | Y9 | T |
| R-V3-28 | Koşu kuyruğu işleri sırayla çalıştırır, iş parçacığı bütçesini aşmaz ve her koşuya ayrı dizin verir. | Y10 | T |
| R-V3-29 | Masaüstü kurulumu (.desktop, MIME, ikon) geri alınabilir: kaldırma kurulumdan önceki dosya ağacını bırakır. | P2 | T |
| R-V3-30 | Dosya yolları tek kaynaktan çözülür ve kurulu paketten (kaynak ağacı olmadan) uygulama açılır. | T2 | T |
| R-V3-31 | V&V kümesi 24 yeni LEU oksit kafes vakasıyla genişletildi; USL NUREG/CR-6698 ile hesaplanır ve bağımsızlık/normallik sınırlamaları belgelenir (sertifika değildir). | Y11 | A |
| R-V3-32 | v3 özellikleri bağımsız öğrenci QA (Q1) ve profesör/standart denetiminden (Q2) geçirildi; bulgular düzeltildi ya da açık nokta olarak yazıldı. | Q1, Q2 | İ |
