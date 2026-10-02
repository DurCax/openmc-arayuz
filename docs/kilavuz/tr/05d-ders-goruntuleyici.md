<a id="ders-goruntuleyici"></a>
## 5.18 Görüntüleyici: kesit, çakışma, tally bindirmesi ve 3B

**Örnek:** `ornekler/pwr_mesh_aki.json`, `ornekler/vver1000_kor.json`, `ornekler/pwr_3b.json` ·
**Seviye:** orta · **Ön koşul:** [5.13](05c-ders-mesh.md#ders-mesh) ·
**Başvuru:** [4.12 Görüntüleyici](04l-goruntuleyici.md#goruntuleyici)

Amaç: bir modelin içini koşmadan incelemek (hücre, malzeme, çakışma), ağ tally sonucunun hangi
çubuğa düştüğünü geometri üstünde görmek, kaynağın nereden başladığını göstermek ve modeli 3B
gölgeli görünümde denetlemek.

<a id="ders-goruntuleyici-1"></a>
### Adım 1: kesit ve fare bilgisi

1. **PWR 17×17 demeti: mesh akı ve güç haritası** örneğini açın, **Araçlar › Görüntüleyici…**
   seçin. Pencere `xy` kesitini (z = 0) bütün demetle açar: **Görünür genişlik** 21.420 cm.
2. Fareyi bir yakıt çubuğunun üstüne getirin: alt satırda koordinat, hücre kimliği, örnek
   (instance) numarası ve malzeme adı (ör. "UO2 …") yazar. Su bölgesinde malzeme
   "H2O 0.700 g/cm³ + 1300 ppm B" olur.
3. Tekerlekle bir köşeye yakınlaştırın: her adımda yeni pencere tam çözünürlükte dilimlenir;
   çubuk–zarf–boşluk halkaları ayrışır. **Renklendirme** › **Hücre** her hücreyi ayrı renkle
   gösterir. **Tüm modeli göster** başa döner.

<a id="ders-goruntuleyici-2"></a>
### Adım 2: çakışma ve tanımsız bölge

1. **Renklendirme** › **Çakışma ve tanımsız bölge** seçin (çakışma denetimi kendiliğinden
   açılır). Beklenen: demette **çakışma yok** — durum satırında "ÇAKIŞMA" yazmaz; model soluk gri.
2. **VVER-1000 tam koru** örneğini açın ve **Modeli yenile**'ye basın. Altıgen korun sınır kutusu
   köşeleri turuncudur: hücre bulunmayan bölge (−2). Bu olağandır — köşeler geometrinin
   dışındadır. Modelin **içinde** turuncu bir leke tanımsız bölge olurdu; çakışma (−3) ise hata
   renginde görünür ve fare "ÇAKIŞMA: nokta birden çok hücrede" yazar.

Beklenen sonuç kaynağı: örnek modeller çakışmasız kurulur (`testler/test_h2_isci.py` temiz
modelde çakışma yok); çakışma kodunun konumu bilinen bir çakışmalı modelde
`testler/test_y2_isci.py` ile doğrulanır.

<a id="ders-goruntuleyici-3"></a>
### Adım 3: ağ tally bindirmesi ve kaynak noktaları

1. PWR 17×17 mesh örneğine dönün ve koşun ([5.13](05c-ders-mesh.md#ders-mesh) Adım 2).
   Koşu bitince görüntüleyicide **Modeli yenile**: son koşunun statepoint'i yüklenir.
2. **Ağ (mesh) tally bindirmesi**'ni açın, **Skor** kappa-fission. 17 × 17 ağın her hücresi
   bir çubuk hücresinin tam üstüne düşer (ağ adımı = çubuk adımı = 1.26 cm); kılavuz borularda
   değer düşüktür. **Opaklık** ile geometriyi görünür kılın; fare altındaki tally değeri bilgi
   satırına eklenir.
3. **Güvenilmez hücreleri gizle (σ maskesi)** açıkken bağıl hatası %10'u aşan hücreler çizilmez.
   Kısa koşuda (örn. 4000 parçacık × 40 çevrim) bazı hücreler kaybolursa istatistik yetersizdir.
4. **Kaynak noktaları** › **Model kaynağı (settings.source)**: noktalar yalnız yakıt çubuklarındadır
   (kurucunun kutu kaynağında `fissionable` kısıtı); kılavuz borularda ve suda nokta yoktur.
   **Statepoint kaynak bankası** koşunun son çevrimindeki fisyon noktalarını gösterir.

<a id="ders-goruntuleyici-4"></a>
### Adım 4: 3B görünüm ve PNG

1. **PWR 3B demeti** örneğini açın, **Modeli yenile**, **3B görünüm** sekmesinde **Çiz**.
   Varsayılan kamera (azimut 45°, yükselti 30°) demetin dış su yüzeyini gösterir.
2. **Gizlenen malzemeler** listesinde suyu işaretleyip **Çiz**: çubuk demeti görünür.
   Yükseltiyi 45°'nin üstüne çıkarmak bu modelde OpenMC 0.16 ışın izleyicisinde hata verebilir
   (4.12 Sınırlamalar); görüntüleyici süreci yeniden başlatır.
3. **PNG olarak kaydet…** etkin sekmenin resmini yazar.

Görüntüleyici bir inceleme aracıdır; kesitlerde çakışma görülmemesi modelin bütününde çakışma
olmadığını kanıtlamaz — sertifika değildir.
