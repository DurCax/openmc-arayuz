<a id="demet"></a>
## 4.3 Demet

Demet, çubukların (ve gerekirse plaka elemanlarının, iç demetlerin ya da malzeme
hücrelerinin) düzenli bir ızgaraya dizilmesidir; OpenMC'de bir **kafestir** (*lattice*):
kare demet `RectLattice`, altıgen demet `HexLattice`. Sayfanın solunda boyanabilir
**Izgara**, sağında **Demetler** listesi, seçili demetin özellikleri (**Kare demet** /
**Altıgen demet** kartı), **Parça paleti** ve **Gelişmiş** bölümü vardır.

Bu sekme yalnız demet kullanan modellerde görünür: tek demet (`tek_demet`), kare ve altıgen
tam kor (`kare_kafes`, `altigen_kafes`), tamburlu kor (`tamburlu`; dolgu kafes olabilir) ve
geometrisinde bir kafes bulunan gelişmiş model (`agac`). Demet **Parçalar** sekmesindeki
çubuklardan kurulur; henüz çubuk yoksa ekleme düğmeleri kapalıdır ve sayfa "Önce çubuk
gerekli" der ([4.2](04b-parcalar.md#parcalar)).

![Demet sekmesi: solda 17×17 ızgara, sağda demet özellikleri ve parça paleti](../resimler/tr/ilk-hesap-demet.png)

### Demetler kartı (liste)

Listede her demet adı ve türüyle görünür ("demet_17x17 · kare 17×17", "demet_hex · altıgen,
7 halka").

| Düğme | Ne yapar |
|---|---|
| Kare demet | 5×5 hücrelik, yakıt çubuğuyla dolu yeni bir kare demet ekler. Adım, çubuğun dış çapının 1.33 katından (en az 1.26 cm) başlar. Altıgen kor haritasında (`altigen_kafes`) sunulmaz: kare kor haritasının hücresi kare, altıgen haritanınki altıgendir; öteki tip oturmaz. |
| Altıgen demet | 5 halkalı (61 hücre) yeni bir altıgen demet ekler. Kare kor haritasında (`kare_kafes`) sunulmaz. |
| Kopyala | Seçili demetin kopyasını ekler (ör. iki farklı zenginlikte demet). |
| Sil | Seçili demeti siler; kor haritasında, eksenel katmanda ya da başka bir demetin içinde kullanılıyorsa önce nerede kullanıldığını söyleyip sorar. |

Tek demet modelinde kor henüz bir demete işaret etmiyorsa ilk eklenen demet kendiliğinden
korun demeti olur; boş modelde ilk demet eklenince model hemen kurulur. Demetin tipi (kare
ya da altıgen) eklenirken seçilir ve **sonradan değişmez** (tip değişimi haritayı yok
ederdi); başka tip gerekiyorsa yeni demet ekleyin.

### Demet kartı (özellikler)

| Alan | Anlamı | Birim | Tipik aralık | Yaygın yanlış kullanım | Spec anahtarı |
|---|---|---|---|---|---|
| **Ad** | Demetin adı. Kor haritası, eksenel katmanlar, tambur dolgusu ve iç içe demetler ona bu adla başvurur; ad değişimi bütün başvuruları günceller. | — | `demet_17x17`, `demet_hex`, `tvs` (ASCII) | Bir malzeme ya da başka parça adıyla aynı ad: ad kutusunun altında kırmızı uyarı çıkar ve ad değiştirilmez | `demetler[].ad` |
| **Adım** | Komşu iki hücre merkezi arası uzaklık (*pitch*). Kare demette hücre kenarı, altıgen demette hücrenin **düz yüzden düz yüze** ölçüsü. Kutunun alt sınırı haritadaki en büyük içeriktir (çubuk dış çapı, plaka elemanı ölçüsü ya da iç demet ölçüsü); ipucu bu sınırı ve nedenini yazar. | cm | PWR 17×17: 1.26; BWR 10×10: 1.295; VVER-1000: 1.275; SFR (`sfr_altigen`): 0.9 | Adımı çubuk dış çapından küçük vermek: "çubuğun dış çapı … kafes adımından … büyük — çubuk komşu hücreye taşar" hatası (OpenMC bunu hata saymaz, hücre çubuğu sessizce keser) | `demetler[].adim` |
| **Boyut** | Yalnız kare demette: sütun (x) × satır (y) hücre sayısı. Büyütmede yeni hücreler haritada en sık geçen parçayla dolar; küçültme haritanın sağ/alt kısmını **siler** ve önce onay ister (büyütmek silineni geri getirmez; Ctrl+Z getirir). | hücre | 17×17 (PWR), 10×10 (BWR), 1×1–200×200 | Değeri yazarken ara değer işlenir sanmak: değer Enter, odak kaybı ya da ok tuşlarıyla işlenir (ör. "17" yerine "15" yazmak haritayı önce tek sütuna kırpmaz) | `demetler[].boyut` (`[nx, ny]`) |
| **Halka sayısı** | Yalnız altıgen demette: merkez dahil halka sayısı; k. halkada 6k hücre vardır (2 halka → 7, 7 halka → 127, 11 halka → 331 hücre). Azaltma dıştaki halkaları **siler** ve önce onay ister. | — | SFR 7–10, VVER-1000 11 | Merkezi saymamak (2 halkalı demet 7 hücredir, 13 değil) | `demetler[].halka_sayisi` (altıgende `boyut` = `[halka, halka]` geriye uyum için yazılır) |
| **Demet dışı** | Demet hücrelerinin dışında kalan alanı dolduran malzeme: altıgen demette köşe boşlukları, iç içe kullanımda ya da tam korda hücrenin kalanı, tamburlu korda kor silindirinin kalanı. Yakıt rolündeki malzemeler listelenmez; **Boş (madde yok)** seçilebilir. Kare demet tek demet modelinin kendisiyse model sınırı demet zarfıdır, bu alana hiç ulaşılmaz ve alan gizlenir (değeri dosyadan silinmez). | — | soğutucu: su, sodyum | Boş bırakmak (void): sızan nötron yok olur; yanlışlıkla yakıt seçmek (listede çıkmaz ama elle yazılmış dosyada olabilir) | `demetler[].dolgu_disi` |

Kartın altındaki ölçü özeti demetin dış ölçüsünü ve hücre sayısını yazar (kare:
"21.420 × 21.420 cm · 289 hücre"; altıgen: kapsayan dikdörtgen + "127 hücre, 7 halka").

### Izgara kartı (harita)

Harita **parça adlarıyla** boyanır; harf görmezsiniz:

- **Sol tık / sürükle:** paletteki seçili parçayı (fırça) hücrelere boyar. Bir basma-sürükleme-
  bırakma darbesi **tek değişikliktir**: Ctrl+Z onu tek adımda geri alır.
- **Sağ tık:** o hücredeki parçayı fırça yapar (paletten aramak gerekmez).
- Hücreler parçanın rengiyle ve kısa adıyla çizilir; tanımsız hücre açık gri görünür.
- Altıgen haritada halkalar **merkezden dışa** numaralanır; hücre konumları OpenMC'nin
  `HexLattice` düzeniyle birebir aynıdır (`cekirdek/altigen.py`, testle doğrulanır).

Dosyada harita yine harflerle tutulur: kare demette satır satır (ilk satır en üst),
altıgen demette **dıştan içe** halka listesi; her halka tepeden ('y' yönelim) ya da sağdan
('x' yönelim) başlayıp saat yönünde ilerler. Harfler kayıtta kendiliğinden atanır (adın ilk
harfi: `yakit_cubugu` → `y`, `kilavuz_boru` → `k`) ve var olan harfler korunur; eski dosyalar
birebir geri yazılır. `.` karakteri tanımsız hücredir.

| Kavram | Anlamı | Spec anahtarı |
|---|---|---|
| Harita | Satır (kare) ya da halka (altıgen) başına bir harf dizesi. Yalnız JSON'da görünür; arayüzde boyanır. | `demetler[].harita` |
| Harf anahtarı | Harf → parça adı eşlemesi (çubuk, plaka, iç demet, malzeme ya da `bosluk`). Yalnız JSON'da görünür. | `demetler[].anahtar` |
| Tür | `kare` (RectLattice) ya da `altigen` (HexLattice); ekleme düğmesi belirler. | `demetler[].tur` |

### Parça paleti kartı

Palet bu demete **gerçekten konabilecek** parçaları listeler: çubuklar; aynı tipte (kare
içine kare, altıgen içine altıgen) ve döngü kurmayan iç demetler (kendisi ya da onu içeren
demet çıkmaz); plaka elemanları yalnız plaka modelinde ve kare demette; malzeme hücresi
olarak yalnız soğutucu/moderatör rolündeki malzemeler. Haritada **zaten geçen** her parça
her zaman listelenir (veri gizlenmez). Varsayılan fırça haritada en sık geçen parçadır.
Adıma sığmayan iç demetler paletin altında "Adıma sığmayan iç demetler: …" notuyla
yazılır: bir demeti iç demet olarak koymak için adım en az o demetin ölçüsü kadar olmalıdır.

| Düğme / alan | Ne yapar |
|---|---|
| Tümünü doldur | Bütün hücreleri seçili parçayla doldurur (Ctrl+Z geri alır). |
| Halka seçimi | Yalnız altıgen demette: doldurulacak halka ("Merkez hücre", "1. halka · 6 hücre", …, "(en dış)"). |
| Halkayı doldur | Seçili halkanın bütün hücrelerini seçili parçayla doldurur (ör. dış halkayı farklı zenginlikte çubukla). |

### Gelişmiş bölümü

| Alan | Anlamı | Birim | Tipik aralık | Yaygın yanlış kullanım | Spec anahtarı |
|---|---|---|---|---|---|
| **Yönelim** | Yalnız altıgen demette: **Üst/alt yüzler yatay (tepede hücre)** = `y` ya da **Sağ/sol yüzler düşey (sağda hücre)** = `x`. `HexLattice.orientation` anlamındadır: `y`'de ilk komşu tepededir. Harita yönelim değişince yeniden çizilir. | — | demetlerde çoğunlukla `y` | Altıgen tam korda demet ile kor kafesine aynı harfi vermek: demet pin kafesi `y` ise kor kafesi `x` olmalıdır (birbirine 90°; `vver1000_kor`, `sfr_met1000_kor`) | `demetler[].yonelim` (`x` \| `y`) |
| **Palette bütün malzemeler ve Boş hücre** | Paleti genişletir: yalnız soğutucu/moderatör değil **bütün malzemeler** ve **Boş (madde yok)** hücresi de seçilebilir (ör. gaz kanalı, su deliği, boş konum). Kaydedilmez; yalnız paletin görünümüdür. | — | — | Boş hücreyi soğutucu yerine kullanmak: o hücrede madde yoktur, nötron serbest uçar | (kaydedilmez) |

### Kılıf (duct) — yalnız JSON

Altıgen demetlerin (SFR, VVER-440) çevresindeki altıgen kılıf (*duct*) bugün arayüzden
düzenlenmez; dosyada `demetler[].kilif` alanıyla verilir ve korunur:

| Anahtar | Anlamı | Birim | Tipik değer |
|---|---|---|---|
| `kilif.ic_duz` | Kılıfın **iç** düz yüzden düz yüze ölçüsü | cm | SFR MET-1000 (`sfr_met1000_demet`): 15.0191 |
| `kilif.kalinlik` | Kılıf duvar kalınlığı | cm | SFR MET-1000: 0.3966 |
| `kilif.malzeme` | Kılıf malzemesi | — | HT-9, SS-316 |

Kılıfın dışı ile demet hücresinin sınırı arası **Demet dışı** malzemesiyle dolar (demetler
arası boşluk). Kılıf yalnız altıgen demette kurulur (kare demette "yok sayılır" uyarısı);
pinler kılıfa sığmalıdır: en dış pin merkezleri (halka − 1)·adım·√3/2 uzaklıktadır, iç ölçü
en az bunun iki katı + iki pin yarıçapı olmalıdır ("pinler kılıfa sığmıyor" hatası).
Başlangıç ekranındaki **Tam kor — altıgen** kartının **Boş başla** şablonu, SFR altıgen demetine
SS-316 kılıf (iç ölçü 10.30 cm, 0.30 cm duvar) ekleyerek 7 demetli bir kor kurar.

### Altıgen demette iki tuzak

- **Yönelim harfleri.** OpenMC'de `HexLattice` ve `HexagonalPrism` yönelimleri aynı harfi
  kullanır ama tanımları terstir (biri "y eksenine dik", öteki "y eksenine paralel"). Bir
  altıgen kafesi saran prizmanın yönelimi kafes yönelimiyle **aynı harftir**; bu ölçümle
  doğrulanmıştır. Yanlış eşleme %2.4 Δk hataya yol açıyordu (README "Bilinen tuzaklar";
  ayrıntı [6. Bilinen tuzaklar](06-sonuclar.md#tuzaklar)). Arayüz bu eşlemeyi kendisi yapar;
  elle JSON düzenlerken dikkat edin.
- **Kılıf apotemi.** Altıgen pin zarfının apotemi (merkezden düz yüze) `(halka − 1)·adım·√3/2
  + adım/2`'dir, `(halka − 0.5)·adım` değil. İkincisi köşelerde doğru görünür ama düz
  yüzlerde fazla boşluk bırakır. Kılıfsız tek altıgen demette model sınırı bu zarftır.

### Sık doğrulama bulguları (`demet:<ad>`)

| Bulgu (özet) | Seviye | Çözüm |
|---|---|---|
| harita boş | hata | Haritayı boyayın (Tümünü doldur). |
| harita N satır ama boyut M satır bekliyor / N. satır … karakter ama … bekleniyor | hata | Elle yazılmış dosyada harita ile **Boyut** uyuşmuyor; boyutu düzeltin ya da haritayı yeniden boyayın. |
| N halka bekleniyor, haritada M satır var / N. halka … öğe bekliyor | hata | Altıgen harita dıştan içe halkalardır; k yarıçaplı halkada 6k öğe, merkezde 1 öğe olmalı. |
| haritada tanımsız harf: 'x' | hata | Hücreyi paletteki bir parçayla yeniden boyayın (harf anahtarında karşılığı yok). |
| 'x' harfi tanımsız bir ada işaret ediyor | hata | Silinmiş ya da yeniden adlandırılmış bir parça; hücreleri yeniden boyayın. |
| çubuğun dış çapı … kafes adımından … büyük | hata | **Adım**'ı büyütün ya da çubuk yarıçaplarını küçültün ([4.2](04b-parcalar.md#parcalar)). |
| iç içe demet '…' … demet adımına sığmıyor | hata | Dış demetin adımını en az iç demetin ölçüsü kadar yapın. |
| anahtarda tanımlı ama haritada kullanılmayan harf | bilgi | Zararsız; kayıtta temizlenir. |
| pinler kılıfa sığmıyor | hata | `kilif.ic_duz`'u büyütün ya da adımı küçültün. |

Bütün bulgu türleri: [9. Sorun giderme](09-sorun-giderme.md#bulgu-turleri). Demetlerin kor
haritasına yerleştirilmesi: [4.4 Geometri](04d-geometri.md#geometri); bir demeti başka bir
şeklin içine (ör. altıgen halkanın ortasına) koymak:
[4.5 Gelişmiş geometri editörü](04e-geometri-gelismis.md#geometri-gelismis).
