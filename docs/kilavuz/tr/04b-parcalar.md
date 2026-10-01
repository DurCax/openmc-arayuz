<a id="parcalar"></a>
## 4.2 Parçalar

Parçalar, demetlere ve kora yerleştirilen tekrar kullanılabilir yapı taşlarıdır: **çubuklar**
(yakıt çubuğu, kılavuz boru, kontrol çubuğu; OpenMC'de birer *universe*) ve MTR tipi **plaka
elemanları**. Sayfanın solunda parça listesi, sağında seçili parçanın düzenleyicisi vardır.
Bu sekme küresel düzenekte görünmez (kürede yalnız malzeme kabukları vardır).

Parçalar malzemelerden kurulur: henüz malzeme yoksa ekleme düğmeleri kapalıdır ve sayfa
"Önce malzeme gerekli" der ([4.1](04a-malzemeler.md#malzemeler)).

### Parçalar kartı (liste)

| Düğme | Ne yapar |
|---|---|
| Çubuk ▾ | Şablondan çubuk ekler; malzemeler **rollerine göre** kendiliğinden seçilir. Menü: **PWR yakıt çubuğu** (yakıt, yakıt-zarf aralığı, zarf, soğutucu), **Kılavuz boru** (suyla dolu boru: zarf + soğutucu), **Kontrol çubuğu** (kılavuz borusunda eksenel hareket eden emici; yalnız 3B ve kafesli modelde sunulur). Yalnız çubuk kullanan kor türlerinde görünür. |
| Plaka | MTR plaka elemanı ekler (23 plaka). Yalnız plaka modelinde (kor türü "Plaka elemanı (MTR)") sunulur. |
| Kopyala | Seçili parçanın kopyasını ekler (ör. iki farklı zenginlikte yakıt çubuğu). |
| Sil | Seçili parçayı siler; kullanılıyorsa önce sorar. |

Şablon ölçüleri PWR 17×17 (Westinghouse) değerleridir: pelet 0.4096 cm, zarf iç/dış
0.418/0.475 cm; kılavuz boru 0.561/0.602 cm; emici 0.433 cm. Şablonun istediği rolde
malzeme yoksa (ör. emici malzeme yok) eksik roller adıyla söylenir; bölgenin malzemesi
"— Malzeme seçin —" olarak kırmızı işaretlenir ve listede parçanın yanında ⚠ çıkar.

Listede kontrol çubukları "· kontrol", plaka elemanları "· plaka" ekiyle gösterilir.

### Çubuk kartı

| Alan | Anlamı | Birim | Tipik aralık | Yaygın yanlış kullanım | Spec anahtarı |
|---|---|---|---|---|---|
| **Ad** | Çubuğun adı. Demet haritaları, kor ve güç dağılımı ona bu adla başvurur; ad değişimi bütün başvuruları günceller (kafes anahtarları, kor dolgusu, eksenel katmanlar, güç hedefi). | — | `yakit_cubugu`, `kilavuz_boru`, `kontrol_cubugu` (ASCII) | Bir malzeme ya da başka parça adıyla aynı ad (ad kutusunun altında kırmızı uyarı) | `cubuklar[].ad` |
| **Tür** | **Sabit çubuk** ya da **Kontrol çubuğu (eksenel hareketli)**. Kontrol çubuğu yalnız 3B ve kafesli modelde (demet, kor haritası, tambur dolgusu) seçilebilir; seçenek yoksa alan gizlenir. | — | — | 2B modelde kontrol çubuğu: "kontrol çubuğu 3B model gerektirir (kor yüksekliği tanımsız)" hatası | `cubuklar[].tur` (`silindirik` \| `kontrol`) |
| **Kesit** | Bölgelerin şekli: **Silindir (eş merkezli daireler)**, **Kare** ya da **Altıgen**. Kare ve altıgende tablodaki "yarıçap" yarı ölçüdür: kare kenarı 2r, altıgen düz yüzden düz yüze 2r. En dış sınır hücre adımıdır. | — | silindir (LWR, SFR); kare/altıgen özel tasarımlar | Altıgen pinin yönelimini kafesle uyumsuz bırakmak (aşağıda) | `cubuklar[].kesit` (`silindir` \| `kare` \| `altigen`) |
| **Kesit yönelimi** | Yalnız altıgen kesitte: **y — düz yüzler sağda/solda** ya da **x — düz yüzler üstte/altta** (HexagonalPrism anlamı). Kafes 'y' ise pin 'x', kafes 'x' ise pin 'y' olmalıdır (ölçüldü). | — | — | Kafesle aynı harfi vermek: pin köşeleri komşu hücreye taşar | `cubuklar[].kesit_yonelim` |
| **Emici bölge** | Kontrol çubuğunda eksenel olarak daldırılan (emici) radyal bölge. Bölgeler 1'den numaralanır; dış bölge seçilemez. | — | çoğunlukla 1. bölge | Emici olmayan bir bölgeyi seçmek: "emici bölgenin malzemesi (…) güçlü bir nötron emici içermiyor" uyarısı | `cubuklar[].emici_bolge` (JSON'da 0'dan sayılır) |
| **İzleyici malzeme** | Emici bölgenin çubuk ucunun **altında** kalan kısmını dolduran malzeme (follower). Yakıt ve emici malzemeler listelenmez. | — | soğutucu (su) | Boş bırakmak: "izleyici malzeme seçilmemiş — çubuk çekildiğinde yeri boş (madde yok) kalır" uyarısı | `cubuklar[].izleyici_malzeme` |
| **Daldırma** | Çubuğun ne kadar dalmış olduğu; kutu ve kaydırıcı aynı değeri değiştirir. Çubuk **yukarıdan** daldırılır: %0 tamamen çekilmiş (emici aktif bölgede yok), %100 tamamen dalmış. Daldırma **aktif yakıt aralığında** ölçülür, modelin toplam yüksekliğinde değil. | % | 0–100; `pwr_kontrol` kritik konum %87.85 ± 0.09 (README) | Değeri burada elle aramak: kritik konum için Analiz'de kritik arama kullanın ([4.8](04h-analiz.md#analiz)); bir daldırma grubunun üyesiyse buradaki değer yok sayılır | `cubuklar[].daldirma` |
| **Uç konumu** | Daldırmadan hesaplanan emici uç yüksekliği: z_uç = z_üst − (daldırma/100)·(z_üst − z_alt), aktif aralıkta. Salt okunur. | cm | — | "Model 2B: Kor sekmesinde yükseklik tanımlayın" yazıyorsa model 2B'dir; kontrol çubuğu çalışmaz | (hesaplanır, saklanmaz) |

Kontrol çubuğunda kartın altındaki not kuralı özetler: emici bölgenin uç altında kalan
kısmı izleyici malzemeyle dolar; kritik çubuk konumu için Analiz sekmesinde "Kritik arama"
ve "Kontrol çubuğu daldırma" parametresi kullanılır. Eksenel katmanlı modelde aktif aralık,
fisil malzeme içeren katmanlardır (README "Üç ayrı yükseklik").

### Radyal bölgeler kartı

Bölgeler **içten dışa** sıralanır; her satırın yarıçapı o bölgenin **dış** sınırıdır ve bir
öncekinden büyük olmalıdır (her kutunun alt/üst sınırı komşularından gelir). Son satır
**dış bölgedir**: yarıçapı yoktur, çubuğun çevresini hücrenin kenarına kadar doldurur
(çoğunlukla soğutucu).

| Sütun | Anlamı | Birim | Tipik aralık | Yaygın yanlış kullanım | Spec anahtarı |
|---|---|---|---|---|---|
| **Dış yarıçap** | Bölgenin dış yarıçapı (kare/altıgen kesitte yarı ölçü). 6 ondalıkla saklanır; dış bölgede "dış bölge" yazar. | cm | PWR: 0.4096 / 0.418 / 0.475; SFR (`sfr_altigen`): 0.32 / 0.345 / 0.395 | Artan sırada değil ("yarıçaplar artan sırada olmalı"); dış çap demet adımından büyük ("çubuğun dış çapı … kafes adımından … büyük — çubuk komşu hücreye taşar"; OpenMC bunu hata saymaz, sessizce keser) | `cubuklar[].bolgeler[].r` |
| **Malzeme** | Bölgenin malzemesi. **Boş (madde yok)** bilinçli bir void seçimidir (ör. yakıt-zarf aralığı gazsız). | — | yakıt / gaz / zarf / soğutucu | "— Malzeme seçin —" bırakmak: "… bölgenin malzemesi seçilmemiş" hatası; tanımsız malzeme adı | `cubuklar[].bolgeler[].malzeme` |
| **Bölge** | Bölgenin okunur açıklaması (yakıt, aralık, zarf, dış bölge…). Salt okunur. | — | — | — | — |

| Düğme | Ne yapar |
|---|---|
| Bölge ekle | Dış bölgenin hemen içine yeni bir bölge ekler. |
| Bölge sil | Seçili bölgeyi siler (en az iki bölge kalmalı: iç bölge + dış dolgu). |
| İçe taşı / Dışa taşı | Seçili bölgenin **malzemesini** komşusuyla değiştirir; yarıçaplar yerinde kalır. Dış bölgeye taşınmaz. |

JSON'da bölge listesi `cubuklar[].bolgeler` ve her öğe `{"r": yarıçap, "malzeme": ad}`
biçimindedir; son öğenin `r` değeri `null` olmalıdır ("son bölgenin yarıçapı boş olmalı").

### MTR tipi plaka yakıt elemanı kartı

Plaka elemanının kesiti x yönünde sırayla kurulur: kanal [zarf | yakıt | zarf] kanal
[zarf | yakıt | zarf] … ve sonda bir kanal daha. Yan levhalar y yönünde aktif bölgenin
altında ve üstünde yer alır. Plaka listelerinde role uymayan malzeme sunulmaz.

| Alan | Anlamı | Birim | Tipik aralık | Yaygın yanlış kullanım | Spec anahtarı |
|---|---|---|---|---|---|
| **Ad** | Plaka elemanının adı. | — | `mtr_eleman` | Başka parça ya da malzemeyle aynı ad | `plakalar[].ad` |
| **Plaka sayısı** | Elemandaki yakıt plakası sayısı. | plaka | 1–500; MTR 23 (`mtr_plaka`) | — | `plakalar[].plaka_sayisi` |
| **Yakıt tabakası kalınlığı** | Bir plakanın yakıt (et, meat) tabakasının x kalınlığı. | cm | 0.051 (MTR) | 0 ya da negatif ("… sıfırdan büyük olmalı") | `plakalar[].et_kalinlik` |
| **Zarf kalınlığı (her yüz)** | Yakıt tabakasının **her iki** yüzündeki zarf kalınlığı (toplam değil). | cm | 0.038 (MTR) | Toplam zarfı girmek (iki kat zarf) | `plakalar[].zarf_kalinlik` |
| **Soğutucu kanal aralığı** | İki plaka arasındaki soğutucu kanalının kalınlığı; iki uçta da bir kanal vardır. | cm | 0.200 (MTR) | — | `plakalar[].kanal_kalinlik` |
| **Aktif genişlik (y)** | Plakanın y yönündeki aktif (yakıtlı) genişliği. | cm | 6.30 (MTR) | — | `plakalar[].plaka_genislik` |
| **Yakıt malzemesi** | Yakıt tabakasının malzemesi (yakıt rolündekiler). | — | `u3si2_al` | Seçmemek ("yakıt (et) malzemesi seçilmemiş") | `plakalar[].et_malzeme` |
| **Zarf malzemesi** | Zarfın malzemesi (yapısal; şablonda Al tercihli). | — | `al6061` | — | `plakalar[].zarf_malzeme` |
| **Soğutucu** | Kanallardaki soğutucu. | — | `su` | — | `plakalar[].sogutucu` |
| **Yan levha kalınlığı** | Aktif bölgenin altında ve üstündeki yan levhaların kalınlığı; 0 yan levha kurmaz. | cm | 0.475 (MTR) | 0 girip yan levha malzemesinin etkisiz olduğunu fark etmemek | `plakalar[].yan_levha_kalinlik` |
| **Yan levha malzemesi** | Yan levhaların malzemesi; "Zarf ile aynı" seçilebilir. Kalınlık 0 ise kapalıdır. | — | `al6061` | — | `plakalar[].yan_levha_malzeme` |
| **Eleman dış ölçüsü (x × y)** | Hesaplanan dış ölçü: x = n·(2·zarf + yakıt) + (n + 1)·kanal, y = genişlik + 2·yan levha. Salt okunur. | cm | `mtr_plaka`: 7.7210 × 7.2500 | Kor kafesinde eleman adımının bu ölçüden küçük olması (eleman kesilir) | (hesaplanır, saklanmaz) |

Plaka elemanı sonlu bir kutudur. Kor kafesinde kullanıldığında (ör. `ornekler/mtr_kor.json`)
kafes adımı eleman ölçüsüne eşit ve kare olmalıdır; aksi hâlde eleman dışı tanımsız kalır
(`docs/ORNEKLER.md` "Çekirdekte gereken değişiklikler").

### Tamburlar kartı

Kontrol tamburu (dönen tambur) **tanımlarının** kütüphanesidir (`tamburlar[]`). Kart yalnız
**gelişmiş geometri** modunda ya da modelde zaten bir tambur tanımı varken görünür; şablon
modunda görünmemesi bilinçlidir: **Tamburlu kompakt kor** şablonunun tamburları bu kütüphaneyi
kullanmaz, ölçüleri **Geometri** sayfasındaki tambur alanlarındadır (`kor.tambur`,
[4.4 Geometri](04d-geometri.md#geometri)). Tanımı ağaçta kullanmak için gelişmiş geometriye geçin
([4.5](04e-geometri-gelismis.md#geometri-gelismis)).

| Alan | Ne | Birim | `spec` |
|---|---|---|---|
| **Ad** | tanımın adı (yerleşimler bu adla başvurur) | — | `tamburlar[].ad` |
| **Yarıçap** | tamburun dış yarıçapı | cm | `yaricap` |
| **Gövde malzemesi** | tambur gövdesi (ör. berilyum) | — | `govde_malzeme` |
| **Emici malzemesi** | emici yay (ör. B₄C) | — | `emici_malzeme` |
| **Emici iç yarıçapı** | emici yayın iç yarıçapı (< yarıçap) | cm | `emici_ic_yaricap` |
| **Emici yayı** | emici yayın açısal genişliği | ° | `emici_aci` |

Sayı, merkez yarıçapı ve dönme tanımda değil, gelişmiş geometrideki **yerleşim** ve **dönme
grubundadır** ([5.5](05-dersler.md#ders-tambur)).

### Sık bulgular

| Bulgu (özet) | Seviye | Neden ve çözüm |
|---|---|---|
| en az iki bölge gerekir (iç bölge + dış dolgu) | hata | Çubukta yalnız dış bölge var; Bölge ekle ile en az bir iç bölge ekleyin. |
| yarıçaplar artan sırada olmalı | hata | Bir bölgenin yarıçapı öncekinden küçük ya da eşit; tabloyu içten dışa düzeltin. |
| … bölgenin malzemesi seçilmemiş | hata | Şablon rolü karşılayan malzeme bulamadı; bir malzeme ya da bilinçli olarak Boş (madde yok) seçin. |
| kontrol çubuğu 3B model gerektirir | hata | Geometri sekmesinde yükseklik verin (3B) ya da çubuğu Sabit çubuk yapın. |
| daldırma %0–%100 arasında olmalı | hata | JSON'da aralık dışı değer. |
| izleyici malzeme seçilmemiş | uyarı | Çekilen çubuğun yeri boş kalır; genellikle soğutucu seçilir. |
| çubuğun dış çapı … kafes adımından … büyük | hata | Demetin adımını büyütün ya da yarıçapları küçültün ([4.3](04c-demet.md#demet)). |

Bütün bulgular: [Sorun giderme](09-sorun-giderme.md#bulgu-turleri). Kontrol çubuğu
gruplarıyla birden çok çubuğu birlikte sürmek gelişmiş geometrinin işidir
([4.5](04e-geometri-gelismis.md#geometri-gelismis)).
