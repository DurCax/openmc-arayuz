<a id="sekmeler"></a>
# 4. Sekme sekme başvuru

Bu bölüm bir başvuru bölümüdür: baştan sona okunmaz, bir alanın ne anlama geldiğini
merak ettiğinizde ilgili sekmeye gidilir. Arayüzdeki her form alanı ve her onay kutusu
burada kendi sekmesinin tablosunda geçer; kılavuzda karşılığı olmayan bir alan otomatik
testi bozar (`testler/test_kilavuz.py`). Alan listesi koddan çıkarılır, elle tutulmaz.

Sekmeler, kenar çubuğundaki sırayla:

| Bölüm | Sekme | Ne yapılır |
|---|---|---|
| [4.0](#pencere-duzeni) | (ortak) | pencere düzeni, menüler, kısayollar, doğrulama şeridi |
| [4.1](04a-malzemeler.md#malzemeler) | Malzemeler | yakıt, zarf, soğutucu, emici ve gaz malzemeleri |
| [4.2](04b-parcalar.md#parcalar) | Parçalar | çubuklar (pin) ve plaka elemanları |
| [4.3](04c-demet.md#demet) | Demet | parçaların kare ya da altıgen ızgaraya yerleştirilmesi |
| [4.4](04d-geometri.md#geometri) | Geometri | kor türü (şablon), yükseklik, sınır koşulları |
| [4.5](04e-geometri-gelismis.md#geometri-gelismis) | Geometri (gelişmiş) | geometri ağacı editörü |
| [4.6](04f-hesap-ayarlari.md#hesap-ayarlari) | Hesap ayarları | hesap türü, hassasiyet, kaynak, güç dağılımı, tally'ler |
| [4.7](04g-calistir.md#calistir) | Çalıştır | koşu, canlı k-eff, sonuç kartı, uygunluk paneli |
| [4.8](04h-analiz.md#analiz) | Analiz | parametre taraması, reaktivite katsayıları, kritik arama |
| [4.9](04i-tukenme.md#tukenme) | Tükenme | yanma hesabı ve izlenen nüklidler |

## Bu bölüm nasıl okunur

Her sekmenin bölümü sayfadaki kartların sırasını izler (her kart bir `###` alt başlığıdır)
ve her kartın alanları bir tabloyla verilir. Sütunlar:

| Sütun | Ne yazar |
|---|---|
| **Alan** | Arayüzdeki etiketin aynısı (sondaki ":" olmadan). Arama yaparken bu metni kullanın. |
| **Anlamı** | Alanın fiziksel ya da modelleme anlamı; OpenMC'de neye karşılık geldiği. |
| **Birim** | Arayüzün beklediği birim. "—" birimsiz demektir. Açılar derece, uzunluklar cm. |
| **Tipik aralık** | Örnek dosyalardan, kod varsayılanlarından ve `docs/` belgelerinden gelen değerler. Bir tasarım değeri değildir. |
| **Yaygın yanlış kullanım** | Doğrulamanın yakaladığı ya da yakalayamadığı tipik hata; ilgili bulgu metni. |
| **Spec anahtarı** | Değerin model dosyasındaki (JSON "spec") yolu. `[]` bir liste öğesi demektir: `cubuklar[].daldirma` her çubuğun kendi `daldirma` alanıdır. |

Model dosyası arayüzün tek gerçek kaynağıdır: arayüz OpenMC nesnelerini değil bu JSON'u
düzenler; `openmc.Model` ve dışa aktarılan Python betiği ondan üretilir
([Kavramlar](03-kavramlar.md#kavramlar)). Bu yüzden her tablonun son sütunu, bir değeri
JSON'da elle değiştirmek ya da betikte aramak istediğinizde nereye bakacağınızı söyler.
"yalnız JSON" notu, alanın arayüzde bir düzenleyicisi olmadığını belirtir.

<a id="pencere-duzeni"></a>
## 4.0 Pencerenin düzeni ve ortak öğeler

Ana pencere beş bölgeden oluşur: üst çubuk, solda kenar çubuğu, ortada etkin sayfa,
sağda önizleme paneli (yalnız tasarım sekmelerinde) ve altta doğrulama şeridi.

### Üst çubuk

| Öğe | Ne yapar |
|---|---|
| Yeni / Aç / Kaydet düğmeleri | Dosya menüsündeki aynı eylemler (Ctrl+N, Ctrl+O, Ctrl+S). |
| Geri al / Yinele düğmeleri | Her düzenleme bir adımdır; kor türü değişimi ve gelişmiş geometriye geçiş de geri alınır. |
| Model adı ve tür rozeti | Modelin adı ve kor türünün sade adı ("17×17 yakıt demeti", "163 demetli altıgen tam kor"). |
| Model özeti | Ölçü, boyut (2B / 3B / 3B katmanlı) ve hesap türü (Özdeğer (k-eff) / Sabit kaynak); bağlantılar ilgili sekmeye götürür. |
| **Türü değiştir…** | Kor türünü değiştirir. Yalnız bu modelde kullanılabilen türler listelenir; Ctrl+Z ile geri alınır. Tür değişince o türde anlamsız kalan kor alanları dosyadan silinmez, yalnız gizlenir. |
| **Komut ara…** | Komut paletini açar (Ctrl+K); aşağıya bakın. |
| **Çalıştır** / **Durdur** | Birincil düğme. Geometri önizlemesi çizilmeden ve doğrulama hataları giderilmeden etkinleşmez ([Önce çiz, sonra çalıştır](06-sonuclar.md#once-ciz)); koşu sürerken Durdur'a döner. Kısayolu F9. |

### Kenar çubuğu ve sekme işaretleri

Kenar çubuğu sekmeleri üç grupta gösterir: **Model** (Malzemeler, Parçalar, Demet,
Geometri), **Hesap** (Hesap ayarları, Çalıştır) ve **Sonuç** (Analiz, Tükenme).
Sekmeler numarasızdır ve **yalnızca modelde anlamlı olanlar görünür**. Kurallar tek bir
yerden gelir (`cekirdek/uygunluk.py`, `gecerli_sekmeler`):

| Sekme | Ne zaman görünür |
|---|---|
| Parçalar | küresel düzenek dışında her zaman (kürede yalnız malzeme kabukları vardır) |
| Demet | tek demet, kare/altıgen tam kor, tamburlu kor, gelişmiş geometri ya da geometride bir kafes varsa |
| Analiz | özdeğer (k-eff) hesabında ve geometride fisil malzeme varken en az bir geçerli tarama varsa |
| Tükenme | özdeğer hesabında ve geometride fisil malzeme varken |
| Malzemeler, Geometri, Hesap ayarları, Çalıştır | her zaman |

Aynı ilke alanlar için de geçerlidir: o modelde anlamsız bir alan (ör. pin hücrede güç
dağılımı, kürede yükseklik) gösterilmez. **Gizlenen bir alanın değeri dosyadan silinmez**;
türü geri değiştirdiğinizde eski değer geri gelir. Doğrulama aynı kuralları kullanır:
arayüzün sunmadığı bir seçenek elle yazılmış bir dosyada doğrulama hatasıdır.

Sekme adının yanındaki işaret durumu söyler; işaretin üzerine gelince tek cümlelik bir
açıklama çıkar:

| İşaret | Anlamı |
|---|---|
| **!** | Bu sekmede yeri olan bir doğrulama hatası var (öncelikli). |
| **•** | Gerekli bir adım eksik: malzeme yok, kor türü çubuk istiyor ama yok, demet ya da kor haritası boş, kor dolgusu seçilmemiş, model henüz çalıştırılmamış. |
| **✓** | Bu adımda eksik ya da hata yok. |
| (işaretsiz) | İsteğe bağlı adım (Analiz, Tükenme) henüz kullanılmadı. |

### Önizleme paneli

Tasarım sekmelerinde (Malzemeler, Parçalar, Demet, Geometri) sağdaki panel her
değişiklikten sonra geometri kesitini yeniden çizer. Çizim `openmc.Model.plot()` ile
yapılır, yani gördüğünüz kesit OpenMC'nin gerçekten kuracağı geometridir. Önizleme
tally'siz bir modeli çizer (tally'ler çizimi etkilemez).

| Denetim | Anlamı |
|---|---|
| **Kesit** | xy (üstten, z = 0), xz (yandan, y = 0), yz (yandan, x = 0). 3B modelde varsayılan "xy + xz": iki kesit yan yana. 2B modelde yalnız xy çizilir. |
| **Renk** | Malzeme ya da Hücre renklendirmesi. Gelişmiş geometride seçili düğüm vurgulanır, diğerleri soluk görünür. |
| **Gösterge** | Malzeme renklerinin açıklaması. |
| **Yenile** | Önizlemeyi yeniden çizer (F6). |
| **Çözünürlük** (Gelişmiş) | Düşük (400) / Normal (800) / Yüksek (1400) piksel. |
| **Çakışmaları göster** (Gelişmiş) | Birden fazla hücrenin kapladığı noktaları ayrı renkle gösterir ve sayısını bildirir. Büyük korlarda çizimi birkaç kat yavaşlatır. |

Önizleme arka planda, ayrı bir süreçte çizilir; arayüz beklemez ("Çiziliyor…" yazısı). Model değişmedikçe OpenMC açık kalır: kesit, renk ya da çözünürlük değişimi hızlıdır. Panel daraltılmışken çizim yapılmaz, yalnız model denetlenir (ÇALIŞTIR kapısı yine çalışır); panel açılınca çizilir. Çizim süreci beklenmedik biçimde kapanırsa önizlemede açık bir hata görünür ve süreç yeniden başlatılır.

Panelin altındaki satır modelin dış ölçüsünü yazar. Panel sağ üstteki düğmeyle daraltılır.

### Doğrulama şeridi ve bulgu listesi

Alt şerit her düzenlemeden sonra çalışan model kontrolünün özetidir: durum simgesi,
"hata / uyarı / bilgi" sayıları, ilk bulgunun metni, **Bulguya git** bağlantısı ve sıradaki
adımın ipucu ("Sonraki adım: …"). Sayı rozetine tıklayınca **Doğrulama bulguları**
listesi açılır; bir satıra tıklamak ilgili sayfaya ve (varsa) ilgili satıra götürür.
**Veri kütüphanesini denetle** (F5) modelin istediği her nüklidin `cross_sections.xml`
içinde bulunup bulunmadığını da denetler; yavaştır, bu yüzden her düzenlemede koşmaz.

Seviyeler: **hata** çalıştırmayı engeller, **uyarı** karar kullanıcıya bırakılır,
**bilgi** yalnız dikkat çeker. Bulgu metinlerinin nedenleri ve çözümleri
[Sorun giderme](09-sorun-giderme.md#bulgu-turleri) bölümündedir.

### Yardım, "?" düğmeleri ve kılavuz

Yardım menüsü bu kılavuzu uygulamanın içinde, çevrimdışı açar. Alanların yanındaki
**?** düğmesi ve doğrulama bulguları kılavuzun ilgili bölümüne götürür; F1 o anki
sayfanın bölümünü açar. Kılavuz penceresinde arama kutusu bütün metinde arar.

### Komut paleti (Ctrl+K)

Üst çubuktaki **Komut ara…** alanı ya da Ctrl+K bir arama kutusu açar. Menü eylemleri ve
etkin sayfanın düğmeleri (ör. "Malzeme: Kütüphaneden ekle…") bulanık aramayla listelenir.
Arama Türkçe harfleri katlar: "calistir" yazmak "Çalıştır"ı bulur. Ok tuşları listeyi
gezer, Enter çalıştırır, Esc kapatır. Yalnız o an etkin olan eylemler listelenir.

### Menüler

| Menü | Eylem | Kısayol | Not |
|---|---|---|---|
| Dosya | Yeni… | Ctrl+N | Başlangıç ekranı ([Başlangıç](01-kurulum.md#baslangic)); Esc açık modele döner. |
| Dosya | Aç… | Ctrl+O | Bir model dosyası (`.json`). `ornekler/` altındaki örnekler **kopya** açılır; üzerine yazılmaz. |
| Dosya | Son kullanılanlar | — | Son açılan dosyalar. |
| Dosya | Kaydet / Farklı kaydet… | Ctrl+S / Ctrl+Shift+S | Örneği kendi dosyanıza kaydetmek için Farklı kaydet. |
| Dosya | Malzemeleri içe aktar (OpenMC XML)… | — | Yalnız malzemeler aktarılır ([4.1](04a-malzemeler.md#malzemeler)); geometri aktarılmaz. |
| Dosya | Python betiği olarak dışa aktar… | Ctrl+E | `openmc_arayuz`'a bağımlı olmayan, tek başına çalışan bir OpenMC betiği. Tek yönlüdür: betik geri içe aktarılamaz. |
| Dosya | OpenMC XML olarak dışa aktar… | — | `model.xml` türü girdi. |
| Dosya | Önizlemeyi PNG olarak kaydet… | — | Görünen kesit. |
| Dosya | Rapor oluştur… | Ctrl+R | Model ve son koşu için HTML ya da PDF rapor ([Rapor dersi](05-dersler.md#ders-rapor)). |
| Düzen | Geri al / Yinele | Ctrl+Z / Ctrl+Y (ya da Ctrl+Shift+Z) | |
| Görünüm | Açık tema / Koyu tema | — | Grafikler de aynı paleti kullanır; seçim hatırlanır. |
| Görünüm | Dil (Türkçe / İngilizce) | — | Uygulama yeniden başlatılınca geçerli olur. |
| Görünüm | Tam ekran | F11 | |
| Yardım | Yardım ve terimler (kılavuz), Hakkında | F1 | F1 kılavuzun o anki sayfaya ait bölümünü açar. |

Kayıtlı bir projede koşu sonuçları projenin yanındaki `kosu` dizinine, kaydedilmemiş (yeni
ya da örnek) bir projede `~/openmc_kosular` altına yazılır; Çalıştır sekmesi tam yolu
gösterir ([4.7](04g-calistir.md#calistir)).

### Klavye kısayolları

| Kısayol | Eylem |
|---|---|
| F1 | Kılavuz (o anki sayfanın bölümü) |
| F5 | Doğrulamayı yenile (veri kütüphanesi dahil) |
| F6 | Önizlemeyi yenile |
| F9 | Çalıştır |
| F11 | Tam ekran |
| Ctrl+K | Komut paleti |
| Ctrl+N / Ctrl+O / Ctrl+S / Ctrl+Shift+S | Yeni / Aç / Kaydet / Farklı kaydet |
| Ctrl+Z / Ctrl+Y | Geri al / Yinele |
| Ctrl+E | Python betiği olarak dışa aktar |
| Ctrl+R | Rapor oluştur |
| Esc | Başlangıç ekranında açık modele dön |

Demet ve kor haritalarında sol tık boyar, basılı tutup sürüklemek bir dizi hücreyi boyar,
sağ tık o hücrenin parçasını fırça yapar; altıgen haritada fare tekerleği yakınlaştırır
([4.3](04c-demet.md#demet)).

### "Gelişmiş" bölümleri

Nadiren gereken alanlar sayfaların altındaki katlanır **Gelişmiş** bölümlerindedir
(yoğunluk birimi, serbest S(α,β) adı, demet yönelimi, önizleme çözünürlüğü…). Varsayılan
olarak kapalıdır; açık/kapalı durumu hatırlanır. Bu kılavuzda Gelişmiş altındaki alanlar
tabloda "(Gelişmiş)" notuyla işaretlenir.

### Fare tekerleği koruması

Sayfayı tekerlekle kaydırırken imlecin altından geçen bir sayı ya da seçim kutusu değerini
**değiştirmez**: odaklanmamış kutular tekerleği yok sayar ve olay sayfa kaydırmasına geçer.
Bir kutunun değerini tekerlekle değiştirmek için önce kutuya tıklayın. (Bu koruma, kor
türünün ve sınır koşulunun kaydırma sırasında sessizce değiştiği gerçek bir hatadan sonra
eklendi.)
