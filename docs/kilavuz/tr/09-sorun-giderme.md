<a id="sorun-giderme"></a>
# 9. Sorun giderme

Bu bölüm bir hata ya da uyarı metninden yola çıkar: **belirti → neden → çözüm**. Programın
kendisinin ürettiği iki tür ileti vardır ve ikisi ayrı okunur:

- **Doğrulama bulguları** koşudan *önce*, model her değiştiğinde üretilir (tasarım sayfalarının
  altındaki doğrulama paneli ve durum çubuğundaki rozet). Kaynak: `cekirdek/dogrula/` ve gelişmiş
  geometride `cekirdek/geometri/denetim.py`.
- **Uygunluk denetimi bulguları** koşudan *sonra*, koşu dizinindeki sonuçlar üzerinde üretilir
  (Çalıştır sayfasındaki Uygunluk paneli, rapor eki ve `openmc-arayuz-kosu uygunluk`). Kaynak:
  `cekirdek/uygunluk_denetimi/`. Kurallar K1–K16 kimlikleriyle anılır.

Hızlı yön bulma:

| Belirti | Bakılacak yer |
|---|---|
| ÇALIŞTIR düğmesi etkin değil | [9.5 Koşu sorunları](#kosu-sorunlari) ve [Önce çiz, sonra çalıştır](06-sonuclar.md#once-ciz) |
| Doğrulama panelinde kırmızı satır | [9.2 Bulgu türleri](#bulgu-turleri), satırın yer kodunun tablosu |
| Uygunluk panelinde "kontrolü geçmedi" ya da "uygulanamadı" | [9.3 Uygunluk kuralları](#uygunluk-kurallari) |
| "Kaynak dağılımı … hâlâ kayıyor" | [K1: kaynak yakınsamadı](#yakinsamadi) |
| "USL hesaplanamadı" | [USL hesaplanamadı](#usl-hesaplanamadi) |
| Uygulama açılmıyor, veri bulunamıyor | [9.4 Kurulum ve ortam sorunları](#kurulum-sorunlari) |

Her durumda önce uygulama günlüğüne bakın: `~/.local/state/openmc_arayuz/openmc_arayuz.log`
(`XDG_STATE_HOME` ayarlıysa onun altında). Hata bildirirken bu dosyayı ekleyin.

<a id="bulgu-okuma"></a>
## 9.1 Doğrulama bulgularını okumak

Her bulgunun üç parçası vardır: **seviye**, **yer** ve **ileti** (çoğunda bir de *öneri*).

| Seviye | Anlamı | Ne yapılır |
|---|---|---|
| **hata** | Model kurulamaz ya da koşu kesinlikle yanlış olur. ÇALIŞTIR düğmesi etkinleşmez. | Düzeltmeden koşu başlamaz. |
| **uyarı** | Koşu yapılabilir ama sonuç yanlı ya da beklenenden farklı olabilir. | Okuyun; bilerek kabul ediyorsanız koşun. |
| **bilgi** | Yalnızca dikkat çeker (yok sayılan alan, varsayılan davranış). | Gerekmiyorsa bir şey yapmayın. |

Bulgular önce hatalar, sonra uyarılar, sonra bilgiler olarak sıralanır. Hesap sayfalarında
(Hesap ayarları, Çalıştır, Analiz, Tükenme) aynı bulgular durum çubuğundaki rozettedir; rozete
tıklayınca liste açılır.

**Bulguya git:** Bir satıra tıklayınca program, bulgunun **yer** kodundan ilgili sayfayı bulur ve
oraya geçer. Eşleme şöyledir (`arayuz/pencere/model_islemleri.py`):

| Yer kodu öneki | Açılan sayfa |
|---|---|
| `malzemeler`, `malzeme:` | Malzemeler |
| `cubuk:`, `plaka:` | Parçalar |
| `demet:` | Demet |
| `kor`, `kor/katman ` | Geometri |
| `ayarlar`, `veri kutuphanesi`, `kaynak`, `tally:`, `guc dagilimi`, `guc_dagilimi` | Hesap ayarları |
| `tukenme`, `tukenme/` | Tükenme |
| `geometri:`, `dogrulama`, `uygunluk:` | otomatik geçiş yok (aşağıdaki tablolara bakın) |

Yer kodu bir tanımlayıcıdır, çevrilmez; listede okunur bir adla gösterilir (`malzeme:uo2` →
"Malzeme uo2", `kor/katman 2 (su)` → "Kor, katman 2 (su)").

<a id="bulgu-turleri"></a>
## 9.2 Bulgu türleri (yer koduna göre)

Aşağıdaki iletiler koddan alınmıştır (`cekirdek/dogrula/*.py`, `cekirdek/geometri/denetim.py`,
`cekirdek/dogrula/agac.py`). "…" değişken kısımdır (ad, sayı). Listede bulamadığınız bir ileti
için önerisini okuyun; öneriler iletinin kendisiyle birlikte gelir.

### `veri kutuphanesi` — nükleer veri kütüphanesi

Bu bulgular yalnızca veri kütüphanesiyle doğrulamada (F5) ve koşu öncesi kapıda üretilir.

| Bulgu (özet metin) | Seviye | Neden | Çözüm |
|---|---|---|---|
| OPENMC_CROSS_SECTIONS ortam değişkeni ayarlı değil | hata | Kurulumun 3. adımı yapılmamış ya da terminal yeniden açılmamış. | `./veri_indir.sh --bashrc`, sonra yeni terminal; bkz. [Nükleer veri](01-kurulum.md#nukleer-veri). |
| cross_sections.xml bulunamadı: … | hata | Değişken yanlış yolu gösteriyor (disk değişti, veri taşındı). | Yolu düzeltin ya da veriyi yeniden indirin. |
| cross_sections.xml okunamadı; nüklid denetimi atlandı | uyarı | Dosya bozuk ya da okunamıyor. | Dosyayı denetleyin; gerekirse veriyi yeniden indirin. |

### `malzemeler` — malzeme listesinin bütünü

| Bulgu (özet metin) | Seviye | Neden | Çözüm |
|---|---|---|---|
| 'bosluk' ayrılmış bir addır (Boş, madde yok); malzeme adı olarak kullanılamaz | hata | `bosluk` boşluk (void) dolgusunun ayrılmış adıdır. | Malzemeyi yeniden adlandırın. |
| kullanılan ama tanımsız malzeme: … | hata | Bir parça ya da kor, silinmiş ya da yanlış yazılmış bir malzemeye başvuruyor. | Malzemeyi tanımlayın ya da başvuruyu düzeltin ([Malzemeler](04a-malzemeler.md#malzemeler)). |
| tanımlı ama modelde kullanılmayan malzeme: … | bilgi | Malzeme geometride hiçbir yerde yok; sonuca etkisi yoktur. | Gerekmiyorsa silin. |
| malzemeler kurulamadı: … | hata | Bileşim OpenMC'ye çevrilemedi (geçersiz element/nüklid adı). | İletideki OpenMC metnine bakıp bileşim satırını düzeltin. |

### `malzeme:` — tek bir malzeme (`malzeme:uo2`)

| Bulgu (özet metin) | Seviye | Neden | Çözüm |
|---|---|---|---|
| aynı ad … kez tanımlanmış | hata | İki malzeme aynı adı taşıyor. | Birini yeniden adlandırın. |
| bileşim boş | hata | Bileşim tablosunda satır yok. | En az bir element/nüklid satırı ekleyin. |
| yoğunluk verilmemiş / yoğunluk sıfırdan büyük olmalı: … | hata | Yoğunluk boş ya da ≤ 0. | g/cm³ ya da atom/b-cm cinsinden pozitif bir değer girin. |
| '…' satırının türü geçersiz / birimi geçersiz | hata | Elle yazılmış JSON'da tür `element`/`nuklid`, birim `ao`/`wo` dışında. | Türü ve birimi düzeltin. |
| '…' miktarı sıfırdan büyük olmalı | hata | Bileşim satırının miktarı ≤ 0. | Pozitif miktar girin ya da satırı silin. |
| '…' elementinde zenginlik tanımlı — zenginlik yalnızca U elementinde kullanılabilir | hata | OpenMC zenginliği yalnız U elementine uygular; koşu sırasında reddeder. | Zenginliği U satırına taşıyın. |
| '…' nüklid satırında zenginlik tanımlı — nüklidde zenginlik yok sayılır | hata | Nüklid satırında zenginlik anlamsızdır. | İzotop miktarlarını doğrudan verin. |
| '…' zenginliği %0–100 aralığında olmalı | hata | Zenginlik aralık dışında. | 0 ile 100 arasında ağırlıkça yüzde girin. |
| U zenginliği %… — OpenMC'nin zenginlik kısayolu U234/U235 kütle oranını sabit 0.008 varsayar | uyarı | Zenginlik %5'in üstünde; kısayol yalnız düşük zenginlikte doğrudur. | Bileşimi nüklid bazında (U234/U235/U238) verin ya da U-234 duyarlılığını kabul edin. |
| … görünümünde ama termal saçılma verisi (S(α,β)) eklenmemiş | uyarı | Su, grafit, berilyum, ZrH gibi yoğun bir moderatörde S(α,β) yok; termal spektrumda k yüzde mertebesinde kayar. | Malzemeler sayfasında iletinin önerdiği S(α,β)'yı ekleyin (ör. `c_H_in_H2O`). |
| yoğun fazda hidrojen var ama termal saçılma verisi (S(α,β)) eklenmemiş | uyarı | Hidrojenli yoğun malzeme hiçbir hazır kurala uymuyor. | Hidrojenin bağlı olduğu faza uygun S(α,β) seçin. |
| veri kütüphanesinde olmayan nüklid: … | hata | Kütüphanede bu nüklidin verisi yok. | Bileşimi değiştirin ya da bu nüklidi içeren bir kütüphane kullanın. |
| termal saçılma verisi (S(α,β)) kütüphanede yok: … | hata | Seçilen S(α,β) adı kütüphanede yok (yazım hatası). | Listeden var olan bir kayıt seçin. |

### `cubuk:` — yakıt çubuğu ve kontrol çubuğu (`cubuk:yakit_cubugu`)

| Bulgu (özet metin) | Seviye | Neden | Çözüm |
|---|---|---|---|
| en az iki bölge gerekir (iç bölge + dış dolgu) | hata | Çubuğun yalnız bir bölgesi var. | Bir iç bölge ve dış dolgu (soğutucu) tanımlayın ([Parçalar](04b-parcalar.md#parcalar)). |
| son bölgenin yarıçapı boş olmalı | hata | Son bölge hücrenin geri kalanını doldurur; yarıçapı yoktur. | Son bölgenin yarıçapını silin. |
| …. bölgenin yarıçapı sıfırdan büyük olmalı | hata | Bir iç bölgenin yarıçapı boş ya da ≤ 0. | Pozitif yarıçap girin. |
| yarıçaplar artan sırada olmalı: r1 = … ≥ r2 = … | hata | Bölgeler içten dışa sıralanmamış ya da iki yarıçap eşit. | Yarıçapları artan sıraya koyun. |
| …. bölgenin malzemesi seçilmemiş | hata | Bölge boş bırakılmış. | Malzeme seçin; bilerek boşsa "Boş (madde yok)". |
| tanımsız malzeme: … | hata | Bölge silinmiş bir malzemeye başvuruyor. | Malzemeyi seçin ya da tanımlayın. |
| kontrol çubuğu 3B model gerektirir (kor yüksekliği tanımsız) | hata | Daldırma bir eksenel uç konumu gerektirir. | Geometri sayfasında yüksekliği "3B" yapın. |
| daldırma %0–%100 arasında olmalı | hata | Daldırma aralık dışında. | 0–100 arasında bir değer girin (%0 çekilmiş, %100 tam dalmış). |
| geçersiz emici bölge: … | hata | Emici bölge numarası çubuğun bölgelerinden biri değil. | Emici bölgeyi listeden seçin. |
| emici bölgenin malzemesi ('…') güçlü bir nötron emici içermiyor | uyarı | Emici bölgede B, Gd, Ag, In, Cd, Hf… yok. | B4C, Ag-In-Cd, Gd2O3 ya da Hf seçin. |
| izleyici malzeme seçilmemiş — çubuk çekildiğinde yeri boş (madde yok) kalır | uyarı | Çekilen çubuğun yerini dolduran malzeme yok. | Genellikle soğutucuyu seçin. |

### `plaka:` — plaka elemanı (`plaka:mtr_eleman`)

| Bulgu (özet metin) | Seviye | Neden | Çözüm |
|---|---|---|---|
| … sıfırdan büyük olmalı: … | hata | Plaka sayısı, kalınlık ya da genişlik ≤ 0. | Pozitif ölçü girin ([Parçalar](04b-parcalar.md#parcalar)). |
| yakıt (et) malzemesi / zarf malzemesi / soğutucu seçilmemiş | hata | Seçilmeyen malzeme boş (madde yok) kurulurdu. | Üç malzemeyi de seçin. |
| … için tanımsız malzeme: … | hata | Silinmiş bir malzemeye başvuru. | Malzemeyi seçin ya da tanımlayın. |

### `demet:` — demet (`demet:demet_17x17`)

| Bulgu (özet metin) | Seviye | Neden | Çözüm |
|---|---|---|---|
| harita boş | hata | Demet haritasında hiç hücre yok. | Haritayı paletle boyayın ([Demet](04c-demet.md#demet)). |
| harita … satır ama boyut … satır bekliyor / …. satır … karakter ama … bekleniyor | hata | Elle yazılmış kare haritanın boyutu `boyut` ile uyuşmuyor. | Satır/sütun sayısını eşitleyin. |
| … halka bekleniyor, haritada … satır var / …. halka (yarıçap …) … öğe bekliyor | hata | Altıgen harita halka düzenine uymuyor: halkalar dıştan içe, yarıçapı k olan halkada 6k öğe, merkezde 1. | Haritayı arayüzde yeniden boyayın ya da halka uzunluklarını düzeltin. |
| haritada tanımsız harf: '…' | hata | Haritadaki bir harfin anahtarda karşılığı yok. | Harfi anahtara ekleyin. |
| anahtarda tanımlı ama haritada kullanılmayan harf: '…' | bilgi | Fazla anahtar girdisi. | Gerekmiyorsa silin. |
| '…' çubuğunun dış çapı (…) kafes adımından (…) büyük — çubuk komşu hücreye taşar | hata | OpenMC bunu hata saymaz, kafes hücresi çubuğu sessizce keser. | Adımı büyütün ya da çubuk yarıçaplarını küçültün. |
| pinler kılıfa sığmıyor: kılıf iç ölçüsü …, en az … gerekli | hata | Altıgen demet kılıfı dış halkadaki pinleri kesiyor. | Kılıf iç ölçüsünü büyütün ya da adımı küçültün. |
| kılıf yalnızca altıgen demette kurulur — yok sayılır | uyarı | Kare demete kılıf verilmiş. | Kılıfı kaldırın. |

### `kor` — Geometri sayfası (şablonlar)

| Bulgu (özet metin) | Seviye | Neden | Çözüm |
|---|---|---|---|
| çubuk seçilmemiş / demet seçilmemiş / plaka elemanı seçilmemiş | hata | Kor türünün ana dolgusu boş. | Geometri sayfasında dolguyu seçin ([Geometri](04d-geometri.md#geometri)). |
| çubuğun dış çapı (…) hücre adımından (…) büyük | hata | Pin hücrede çubuk hücreye sığmıyor. | Hücre adımını büyütün. |
| kor haritası boş / haritada tanımsız harf: '…' | hata | Tam kor haritası boyanmamış ya da harfin demeti yok. | Haritayı boyayın, harfi tanımlayın. |
| '…' demetinin yönelimi ('…') kor yönelimiyle aynı — demet köşeleri komşu hücreye taşar | hata | Altıgen korda kor kafesi pin kafesine göre 90° dönük olmalıdır. | Demet `y` ise kor yönelimi `x` (ya da tersi). |
| demet adımı (…) '…' demetinin dış ölçüsünden (…) küçük | hata | Kor hücresi demeti kesiyor. | Demet adımını en az demetin dış ölçüsü kadar yapın. |
| '…' kare bir demet; altıgen kor haritasına yalnızca altıgen demet konabilir | hata | Kafes tipleri karışmış. | Altıgen demet kullanın ya da kare kor türüne geçin. |
| tamburlar kora giriyor / tamburlar yansıtıcı kuşaktan taşıyor / komşu tamburlar çakışıyor | hata | Tambur yerleşimi geometrik olarak geçersiz; model kurulumu durur. | Merkez yarıçapını, tambur yarıçapını ya da sayısını iletideki sayılara göre değiştirin. |
| tambur emicisi ('…') güçlü bir nötron emici içermiyor | uyarı | Emici malzemede B, Gd, Hf… yok. | B4C gibi bir emici seçin. |
| tamburlu kor 2B — eksenel sızıntı yok, k-eff olduğundan yüksek çıkar | bilgi | Yükseklik verilmemiş. | Gerçekçi tambur değeri için aktif yükseklik tanımlayın. |
| tambur sayısı 0 — kontrol tamburu olmadan düz yansıtıcı kuşak | bilgi | Tambur yok. | Bilerek değilse tambur sayısını girin. |
| küresel düzenekte en az bir kabuk gerekir / kabuk yarıçapları artan sırada olmalı | hata | Kabuklar eksik ya da sırasız (yalnız JSON'dan girilir). | `kor.kabuklar` listesini içten dışa sıralayın. |
| küresel düzenekte dış sınır Yansıtıcı (reflective) — çıplak (bare) bir kritiklik düzeneği modelliyorsanız Vakum (vacuum) olmalı | uyarı | Yansıtıcı sınır sonsuz ortam demektir. | Kritik küreler için Vakum seçin. |
| tek hücre/demet modelinde yan sınır Vakum (vacuum) — sızıntı sonsuz kafes varsayımını bozar | uyarı | k∞ istenen bir modelde vakum sınır. | k∞ için Yansıtıcı seçin. |
| yan sınır Yansıtıcı ve haritada birden fazla demet türü var — sonsuz kafes eşdeğerliği yalnız aynı ve simetrik demetlerde geçerli | uyarı | Altıgen tam korda kırık çizgi sınır karışık haritada simetri düzlemi değildir. | Yansıtıcı kuşak ve Vakum sınır kullanın. |
| kılıflı tek demette sınır kılıfın dış yüzündedir — demetler arası boşluk (soğutucu) modelde yok | uyarı | Tek demet, kılıfın dış yüzünde biter. | Bir halkalı altıgen tam kor (`halka_sayisi` = 1) kullanın. |
| Periyodik (periodic) sınır yalnızca düzlemsel sınırlarda (x/y düzlem çiftleri) kullanılabilir | hata | Yan yüzey silindir ya da kırık çizgi. | Yansıtıcı ya da Vakum seçin. |
| … sınır Periyodik (periodic) ama … sınır değil — periyodik yüzeyin eşi yok | hata | Alt/üst periyodiklik tek yüzde; OpenMC başlamadan durur. | Alt/üst için Yansıtıcı ya da Vakum seçin. |
| model 2B — … sınır koşulu (…) yok sayılır / yükseklik verilmemiş — model eksenel yönde sonsuz (2B) kabul ediliyor | bilgi | 2B modelde eksenel sınır yoktur. | Eksenel sızıntı için yükseklik tanımlayın. |
| '…' kor türünde yansıtıcı kuşak kurulmaz — dosyada açık ama yok sayılır / kullanılmayan alanlar dolu | uyarı / bilgi | Başka bir kor türünden kalmış alanlar. | Zararsız; temizlemek için alanı JSON'dan silin. |
| bilinmeyen kor türü: … | hata | Elle yazılmış `kor.tur` geçersiz. | Geçerli türlerden birini yazın. |

### `kor/katman ` — eksenel katmanlar (`kor/katman 2 (su)`)

| Bulgu (özet metin) | Seviye | Neden | Çözüm |
|---|---|---|---|
| katman yüksekliği sıfırdan büyük olmalı | hata | Katman yüksekliği ≤ 0. | Pozitif yükseklik girin. |
| tanımsız dolgu adı: '…' | hata | Dolgu bir çubuk, plaka elemanı, demet ya da malzeme adı değil. | Dolguyu listeden seçin. |
| aynı ad birden fazla katmanda kullanılmış: '…' | uyarı | Katman adları hücre adı olur; karışıklık yaratır. | Katmanlara ayrı ad verin. |
| '…' harfi kor haritasında hiç geçmiyor / tanımsız demet/malzeme adı: '…' | uyarı / hata | Katmana özel `anahtar` eşlemesi haritayla uyuşmuyor. | Eşlemeyi düzeltin (yalnız JSON). |

Katmanlarla ilgili kor düzeyindeki iletiler `kor` yerinde görünür: "eksenel katmanlar açık ama hiç
katman tanımlı değil" (hata), "hiçbir eksenel katmanda fisil malzeme yok" (hata), "eksenel
katmanlar açıkken yükseklik alanı yok sayılır" (bilgi), "kontrol çubuğu daldırması aktif yakıt
aralığında ölçülür" (bilgi).

### `ayarlar` — Hesap ayarları

| Bulgu (özet metin) | Seviye | Neden | Çözüm |
|---|---|---|---|
| parçacık sayısı / çevrim sayısı sıfırdan büyük olmalı | hata | Değer ≤ 0. | Pozitif değer girin ([Hesap ayarları](04f-hesap-ayarlari.md#hesap-ayarlari)). |
| pasif çevrim (…) toplam çevrimden (…) az olmalı | hata | Aktif çevrim kalmıyor. | Toplam çevrimi artırın ya da pasifi azaltın. |
| pasif çevrim çok az (…) — kaynak dağılımı yakınsamamış olabilir | uyarı | 5'ten az pasif çevrim. | 20–50 pasif çevrim kullanın; tam korda daha fazla. |
| aktif çevrim sayısı az (…) — istatistik zayıf kalır | uyarı | 20'den az aktif çevrim. | Toplam çevrimi artırın. |
| Shannon entropisi kapalı — kaynak dağılımının yakınsayıp yakınsamadığı ölçülemez | uyarı | Entropi ağı kapalı. | Özdeğer hesabında açık tutun. |
| entropi ağı boyutları sıfırdan büyük olmalı | hata | Ağ bölmesi 0. | Her eksende en az 1 bölme. |
| çevrim başına parçacık az (…) — kaynak yakınsaması bozulabilir | uyarı | 1000'den az parçacık. | En az birkaç bin parçacık kullanın. |
| Özdeğer (k-eff) hesabı fisil malzeme gerektirir — geometride fisil malzeme yok | hata | OpenMC ilk çevrimde durur ("No fission sites banked"). | Zırhlama için hesap türünü Sabit kaynak yapın. |
| sabit kaynak hesabında hiçbir tally tanımlı değil — koşu hiçbir sonuç üretmez | hata | Sabit kaynakta k-eff yoktur; ölçülecek şey tally olarak tanımlanmalı. | Bir tally ekleyin. |
| sabit kaynak hesabında pasif çevrim (…) yok sayılır / Shannon entropisi sabit kaynak hesabında kullanılmaz / kinetik parametreler … yok sayılır | bilgi | Bu alanlar yalnız özdeğer hesabında anlamlıdır. | Bir şey yapmanız gerekmez. |

### `kaynak` — kaynak tanımı

| Bulgu (özet metin) | Seviye | Neden | Çözüm |
|---|---|---|---|
| kaynak şiddeti sıfırdan büyük olmalı | hata | Şiddet ≤ 0. | Pozitif şiddet [1/s] girin. |
| bilinmeyen parçacık türü: … | hata | Elle yazılmış parçacık türü geçersiz. | `neutron` ya da `photon`. |
| foton kaynağı Özdeğer (k-eff) hesabında anlamsız | hata | Fotonlar fisyon zincirini taşımaz. | Hesap türünü Sabit kaynak yapın. |
| foton kaynağı seçildi ama kütüphanede foton verisi yok | hata | `cross_sections.xml` içinde foton kaydı yok. | Foton verisi içeren bir kütüphane kurun. |
| kaynak enerjisi …, veri tavanı … | hata | Kaynak enerjisi modeldeki bir nüklidin veri üst sınırını aşıyor; OpenMC koşuda durur. | Kaynak enerjisini düşürün. |
| nokta kaynak z = … modelin dışında | hata | Geometri dışında başlayan parçacıklar anında kaybolur. | Konumu modelin içine alın. |
| kutu kaynağı fisil malzeme gerektirir — geometride fisil malzeme yok | hata | Kutu kaynağı yalnız fisil bölgelerde örneklenir. | Nokta kaynak kullanın. |
| sabit kaynak hesabında kutu kaynağı 'yalnızca fisil bölgeler' kısıtıyla örneklenir | uyarı | Kutunun fisil olmayan kısmı boş kalır. | Dış kaynak için nokta kaynak seçin. |
| özdeğer hesabında kaynak şiddeti (…) yok sayılır / enerji tayfı … yalnızca başlangıç tahminidir / açısal dağılım da yalnızca başlangıç tahminidir | bilgi | Özdeğerde sonuç fisyon kaynağına normalize edilir; tayf pasif çevrimlerde değişir. | Bir şey yapmanız gerekmez. |

### `tally:` — kullanıcı tally'leri (`tally:aki`)

| Bulgu (özet metin) | Seviye | Neden | Çözüm |
|---|---|---|---|
| en az bir skor seçilmeli | hata | Tally'nin skoru yok. | Bir skor ya da hazır set seçin. |
| '…' bilinen skorlar arasında değil | uyarı | OpenMC skor adlarını koşuya kadar denetlemez; liste elle tutulur. | Yazımı denetleyin; yeni bir OpenMC skoru ise uyarı yanlış alarm olabilir. |

### `guc dagilimi` ve `guc_dagilimi` — güç dağılımı

İki yazım da Hesap ayarlarına götürür (`guc_dagilimi` eksenel katman denetiminden gelir).

| Bulgu (özet metin) | Seviye | Neden | Çözüm |
|---|---|---|---|
| hedef çubuk seçilmemiş / hedef çubuk tanımsız: … | hata | Güç dağılımı açık ama hedef yok. | Hedef çubuğu seçin. |
| '…' bir demette tekrarlanmıyor (kor türü: 'Yakıt çubuğu (pin hücre)') | hata | Dağılım tekrarlanan hücre örnekleri üzerinden hesaplanır. | Bir demet kurun. |
| '…' çubuğu modelde kullanılmıyor — güç dağılımı yalnızca geometride yer alan bir çubuk için hesaplanabilir | hata | Hedef çubuk hiçbir haritada yok. | Geometride geçen bir yakıt çubuğu seçin. |
| seçilen bölgenin malzemesi ('…') fisil görünmüyor | uyarı | Zarf ya da soğutucu seçilmiş. | Yakıt bölgesini (genellikle 1. bölge) seçin. |
| '…' bir enerji skoru değil | uyarı | `fission` fisyon sayısını verir, gücü değil. | `kappa-fission` kullanın. |
| model 2B — F_q hesaplanamaz, yalnızca F_ΔH verilir | bilgi | F_q eksenel şekle bağlıdır. | Aktif yükseklik tanımlayın. |
| yalnızca … eksenel dilim — F_q olduğundan küçük çıkar | uyarı | Kaba dilimler tepeyi ortalar. | 10–20 dilim kullanın. |
| eksenel dilim sınırları katman sınırlarıyla hizalı değil — F_q birkaç % şişebilir | uyarı | Bir dilim hem çubuklu hem çubuksuz katmana düşüyor. | Dilim sayısını katmanlara göre seçin. |
| toplam güç sıfırdan büyük olmalı / toplam güç verilmiş ama model 2B — çizgisel güç [W/cm] hesaplanamaz | hata / uyarı | Mutlak güç girdisi tutarsız. | Pozitif güç girin; W/cm için 3B model. |
| F_ΔH yalnız '…' çubuğunu kapsar — modelde yakıt içeren başka çubuk türleri de var | uyarı | En sıcak çubuk hedef listesinde olmayan bir türden olabilir. | Bütün yakıt çubuk türlerini hedef listesine ekleyin. |
| fisil aralık … cm ama '…' çubuğu yalnızca … cm boyunca var | uyarı | Örtü gibi fisil katmanların gücü hedef çubuklara paylaştırılır. | W/cm sonucunu buna göre okuyun. |

### `tukenme` ve `tukenme/` — tükenme (`tukenme/uo2`)

| Bulgu (özet metin) | Seviye | Neden | Çözüm |
|---|---|---|---|
| tükenme Özdeğer (k-eff) hesabı gerektirir | hata | Sabit kaynaklı tükenme (aktivasyon) yok. | Hesap türünü Özdeğer yapın. |
| zincir dosyası yok / boş / yarım: kapanış etiketi yok | hata | Tükenme zinciri indirilmemiş ya da indirme kesilmiş. | `./veri_indir.sh --yalniz-zincir`. |
| izlenen nüklid zincirde yok: '…' | hata | Yazım hatası ya da zincirde olmayan nüklid. | Nüklid seçicisinden seçin ([Tükenme](04i-tukenme.md#tukenme)). |
| … zincir seçildi ama model … spektrumlu görünüyor | uyarı | Termal/hızlı zincir model spektrumuyla uyuşmuyor. | Zinciri "otomatik" bırakın. |
| basitleştirilmiş CASL zinciri: 228 nüklid (tam zincir 3820) | bilgi | Ön inceleme zinciri. | Sonucu tam zincirle doğrulayın. |
| güç yoğunluğu sıfırdan büyük olmalı [W/gHM] / güç yoğunluğu … W/gHM olağan dışı | hata / uyarı | Birim W/gHM'dir, mutlak güç değil (tipik PWR 38–40). | Değeri W/gHM cinsinden girin. |
| en az bir zaman adımı gerekli / zaman adımları sıfırdan büyük olmalı | hata | Adım listesi boş ya da ≤ 0. | Adımları girin. |
| ilk adım … gün — Xe-135 dengesi (~2 gün) tek adıma eziliyor | uyarı | Uzun ilk adım ksenon düşüşünü görünmez kılar. | İlk adımları kısa tutun (0.5 ve 1.5 gün). |
| aktif istatistik az (… parçacık × … çevrim) | uyarı | Gürültü adımdan adıma birikir. | Parçacık × aktif çevrim ≥ 100 000. |
| modelde yanabilir (fisil) malzeme yok / hacimler hesaplanamadı | hata | Yanacak yakıt geometride yok ya da hacim hesabı başarısız. | Yakıtı geometriye koyun; iletideki nedene bakın. |
| hacim hesaplanamıyor: … | hata | Yanlış hacim yanma hızını aynı oranda bozar, k-eff'te iz bırakmaz. | İletideki ayrıntıya göre geometriyi düzeltin. |
| '…' hacmi stokastik hesaplanacak | uyarı | Kesik konum ya da kesik çubuk; analitik hacim kesin değil. | Belirsizliği rapordan okuyun. |
| çubuk çubuk yanmada örnek hacmi kesin değil | hata | Kesik konumlarda örnek hacmi bilinmez. | Çubuk çubuk yanmayı kapatın ya da kesik konumları kaldırın. |
| yanabilir zehir '…' tükenmeye katılmıyor | uyarı | Hacmi analitik hesaplanamıyor; malzeme taze kalır. | Zehri kesin hacimli bir çubuk bölgesine koyun. |
| tanımsız ek malzeme: '…' | hata | `tukenme.ek_malzemeler` içinde silinmiş ad. | Listeyi düzeltin. |
| çubuk çubuk yanma açık | bilgi | Her hücre ayrı malzeme olur; bellek ve süre artar. | Bilerek açtıysanız sorun yok. |

Tükenme sayfasındaki önceki sonuç da bir tür bulgudur: "**Eski sonuç** (…): model o koşudan beri
değişti" kırmızı yazılır; gösterilen sayılar bu modele ait değildir, yeniden koşun.

### `geometri:` — gelişmiş geometri ağacı (`geometri:kok/halkalar/0/yerlesimler/1`)

Yer, ağaçtaki düğümün yoludur; listede "geometri: kök › 1. halka › …" biçiminde okunur. Bu
yer kodunda **otomatik sayfa geçişi yoktur**: Geometri sayfasında (gelişmiş görünüm) ağaçta
bu yolu izleyin ([Gelişmiş geometri](04e-geometri-gelismis.md#geometri-gelismis)).

| Bulgu (özet metin) | Seviye | Neden | Çözüm |
|---|---|---|---|
| Tanımsız ad / Tanımsız malzeme / Tanımsız bileşen: '…' | hata | Yuva silinmiş ya da yanlış yazılmış bir ada başvuruyor. | Adı düzeltin ya da tanımı ekleyin. |
| Belirsiz ad '…': … bölümlerinin ikisinde de var | hata | Aynı ad iki kütüphane bölümünde. | Birini yeniden adlandırın. |
| Döngü: '…' parçası kendini içeriyor | hata | Parça kendi içinde kullanılmış. | Döngüyü kırın. |
| Haritada tanımsız harf / Harita … satır; boyut … bekliyor / Altıgen harita … halka bekliyor | hata | Kafes haritası boyutla uyuşmuyor. | Haritayı yeniden boyayın. |
| Kafesin 'dis' yuvası zorunlu | hata | Kafesin dışı ve "." konumları için dolgu yok. | `dis` için bir malzeme seçin. |
| Kök olmayan kapta 'dis' yuvası zorunlu / Kök kapta 'dis' olamaz | hata | Kap yuvaları kurala uymuyor. | Kök dışındaki kaba dış dolgu verin; kökten kaldırın. |
| Halkanın dış kesiti bir önceki sınırı kapsamıyor / Halka kalınlığı sıfırdan büyük olmalı | hata | Halkalar iç içe değil. | Kalınlığı ya da dış kesiti büyütün. |
| '…' deliği bölgesinden taşıyor / bölgenin iç sınırına taşıyor / kafes konumu hücresinden taşıyor | hata | Yerleşim deliği sahip bölgeye sığmıyor. | Merkez yarıçapını ya da delik ölçüsünü değiştirin. |
| '…' ve '…' delikleri örtüşüyor | hata | Örtüşen hücreler kayıp parçacık üretir. | Yerleşimleri ayırın. |
| Altıgen '…' demeti altıgen kafes elemanında aynı yönelimle | hata | Demet elemana oturmaz. | Demet yönelimi kafes yönelimine dik olmalı. |
| '…' plaka elemanı bulunduğu bölgeyi doldurmuyor | hata | Aradaki nokta tanımsız kalır (kayıp parçacık). | Plaka elemanını ölçüsüne eşit bir konuma koyun. |
| 2B modelde eksenel yığın kurulamaz / Kök dışındaki eksenel yığının toplamı model yüksekliğine eşit değil | hata | Eksenel yığın yükseklikle tutarsız. | Kök yüksekliğini verin ya da katmanları eşitleyin. |
| '…' yüzünde … sınır bu dış sınırda kullanılamaz / … sınır periyodik olamaz | hata | Periyodik sınır yalnız dikdörtgen/altıgen dış sınırda ve karşılıklı yüz çiftinde geçerli. | Yansıtıcı ya da Vakum seçin. |
| Nokta yoklaması: … | hata | Örnek noktalarda örtüşen ya da tanımsız bölge bulundu. | Bölgeyi bir malzemeyle doldurun; örtüşmeyi giderin. |
| … kesik konum/bileşen üst bölgeyle kırpılıyor / … kesik çubuk | uyarı | Kafes elemanı ya da çubuk üst sınırla kesiliyor. | Tasarım gereğiyse kabul edin: hacim stokastiğe düşer, güç haritasında "kesik" işaretlenir. |
| Kök içinde boş (void) bölge / 2B modelde kontrol tamburu | uyarı | Boşlukta nötron etkileşmez; 2B'de eksenel sızıntı yok. | Bilerek değilse düzeltin. |
| aynı içerikli iki satır içi alt ağaç | uyarı | Distribcell ve tükenme örnek sayımı bölünür. | Alt ağacı bir parçaya çevirip iki yerde kullanın. |
| … kafes konumu tamamen gizli (delik altında) / 0 cm katman atlandı | bilgi | Zararsız. | Haritada "." yazabilirsiniz. |
| İç içe derinlik … düzeyden fazla / Bir bölgede …'den fazla delik | uyarı | İzleme ve hücre arama yavaşlar. | Ağacı sadeleştirin. |

### `dogrulama` — doğrulamanın kendisi

| Bulgu (özet metin) | Seviye | Neden | Çözüm |
|---|---|---|---|
| doğrulama sırasında hata: … | hata | Bir denetim beklenmedik bir istisnayla durdu (genellikle bozuk bir JSON alanı). | Günlük dosyasındaki ayrıntıya bakın; dosyayı arayüzde açıp kaydetmek alanları tamamlar. Sürerse hatayı günlükle bildirin. |

### `uygunluk:` — uygunluk denetimi bulguları

Uygunluk bulgularının yeri `uygunluk:<kural>` biçimindedir (`uygunluk:K1`, `uygunluk:K2-parcacik`).
Bunlar doğrulama listesinde değil, Çalıştır sayfasındaki Uygunluk panelinde görünür; kural
kimliğiyle [9.3 Uygunluk kuralları](#uygunluk-kurallari) bölümüne bakın. Panelde çift tıklama,
K1/K2 için Hesap ayarlarına, K3 için Geometri'ye, `K4-sicaklik` için Malzemeler'e götürür.

<a id="uygunluk-kurallari"></a>
## 9.3 Uygunluk kuralları (K1–K16)

Uygunluk denetimi bir **sertifika değildir**: standartların ve iyi uygulamanın isteyeceği kanıtı
üretir ve eksikleri görünür kılar (bkz. [Uygunluk denetimi](07-uygunluk.md#uygunluk-denetimi) ve
[Ne kanıtlar, ne kanıtlamaz](07-uygunluk.md#ne-kanitlar)). Kuralların kaynakları
[docs/STANDARTLAR.md](../../STANDARTLAR.md) §3'tedir.

**Durumlar.** Her kural geçtiğinde de bir satır üretir:

| Durum | Anlamı |
|---|---|
| kontrolü geçti | Kural denetlendi ve karşılandı. |
| kontrolü geçmedi | Kural denetlendi ve karşılanmadı; seviye hata, uyarı ya da bilgi olabilir. |
| uygulanamadı | Denetim için gereken veri ya da eşik yok (ör. statepoint yok, eşik girilmemiş). Başarısızlık sayılmaz; `--siki` verilirse sayılır. |
| not | Bilgi notu; karşılandı/karşılanmadı yargısı yok. |

**Etiketler** (kaynağın türü): **iyi uygulama** (standart maddesi değil), **standart**
(açık bir standart/kılavuz maddesine dayanır), **proje ölçütü** (projenin kendi ölçütü),
**kullanıcı sınırı** (eşik kullanıcıdan/tesisten gelir; varsayılan yok).

**Profiller:** A Monte Carlo iyi uygulaması (K1, K2, K3), B kritiklik güvenliği (K6, K6-AOA,
K8–K14), C reaktör kor tasarımı (K7, K7-SDM, K7-F, K16), D raporlama (K4, K5). Profil seçimi
Çalıştır sayfasındaki Uygunluk panelindedir ve `calistirma.uygunluk_profilleri` alanına yazılır
(ayrıntı: [Profiller](07-uygunluk.md#profiller)).

**Eşikler.** Kaynağı gösterilemeyen eşik araca gömülmez. `sigma_hedef`, `aktif_asgari`,
`F_dH_siniri`, `F_q_siniri`, `sdm_siniri_pcm` gibi eşiklerin varsayılanı **yoktur**; bunlara
bağlı alt kurallar "uygulanamadı" der. Bu bir hata değildir. Eşik bugün yalnız Python'dan
verilir (`cekirdek/uygunluk_denetimi/profiller.py`: `uyarla`, `dosyadan_uyarla`); arayüzde
alanı yoktur. Profil C ve B'nin bazı girdileri koşu dizinine elle konan
`uygunluk_girdisi.json` dosyasından okunur (`kor` ve `uygulama` anahtarları).

### Profil A — Monte Carlo iyi uygulaması

<a id="kural-k1"></a>
#### K1 — Kaynak yakınsaması (Shannon entropisi platosu)

- **Etiket:** iyi uygulama. **Kaynak:** F.B. Brown, LA-UR-09-03136 (2009) §II; NUREG/CR-6698
  §2.4 dipnotu (yakınsama kullanıcı yargısıdır).
- **Ne denetler:** Pasif dönemin son yarısı ikiye bölünür; iki yarının entropi ortalamaları
  arasındaki kayma, aktif çevrimlerdeki entropi saçılmasının (σ) iki katını aşıyor mu.
- **Tipik bulgular:**
  - "Kaynak dağılımı pasif dönemin sonunda hâlâ kayıyor (kayma …, aktif saçılma σ = …). Pasif
    çevrim sayısını artırın — k-eff yanlı olabilir." → **uyarı**, kontrolü geçmedi.
  - "Shannon entropisi kapalı — kaynak yakınsaması gösterilemiyor." → uyarı.
  - "pasif çevrim sayısı (…) kaynak yakınsamasını değerlendirmek için çok az" ya da "entropi
    sabit; değerlendirilemedi" → uygulanamadı.
  - "Sabit kaynak koşusu: k-eff ve kaynak yakınsaması tanımsız." / "Koşu dizininde statepoint
    yok." → uygulanamadı.
- **Çözüm:** adım adım tarif aşağıda: [K1: kaynak yakınsamadı](#yakinsamadi).

<a id="kural-k2"></a>
#### K2 — İstatistik yeterliliği

- **Etiket:** iyi uygulama; eşikler standarttan gelmez (profil değeri). Alt kimlikler:
- `K2-sigma`: σ_k ≤ `sigma_hedef`. Varsayılan hedef yok → "σ hedefi tanımlı değil; k = …, σ = …
  (1σ) karşılaştırılmadı." (uygulanamadı). Hedef verilmişse ve aşıldıysa "σ_k = … hedefin (…)
  üstünde." (uyarı) → aktif çevrim ya da çevrim başı parçacığı artırın.
- `K2-parcacik`: çevrim başına parçacık. 1000'in altı **uyarı** ("k-eff ve yerel tally'lerde
  yanlılık beklenir", Brown 2009 §III.C); 1000–5000 arası **not** ("uzun üretim koşusunda en
  az 5000 önerilir", Brown 2009 §V).
- `K2-aktif`: aktif çevrim alt sınırı. Kaynak sayı vermediği için varsayılan yok → uygulanamadı.
- `K2-ilinti`: aktif çevrim k değerlerinin gecikme-1 öz ilintisi 2/√N'yi aşarsa **not**:
  bildirilen σ çevrimler arası ilintiyi yok sayar ve gerçek belirsizliği küçümser. Çözüm:
  bağımsız tohumlarla birkaç koşu yapıp saçılımı karşılaştırın
  ([İstatistik](06-sonuclar.md#istatistik)).

<a id="kural-k3"></a>
#### K3 — Kayıp parçacık = 0

- **Etiket:** iyi uygulama (OpenMC). **Ne denetler:** `kosu.log` ve `particle_*.h5` dosyaları;
  izin verilen kayıp `kayip_azami` = 0.
- **Tipik bulgu:** "… kayıp parçacık (izin verilen 0). …" → **hata**. Neden: geometride boşluk
  (hiçbir hücrenin kapsamadığı nokta) ya da çakışan hücre. Çözüm: Geometri sayfasında kesit
  çizimlerini ve sınır koşullarını denetleyin; gelişmiş geometride "Yokla" ile nokta yoklaması
  yapın.
- `K3-hata`: OpenMC'nin çıktıya yazdığı hata iletileri (hata). `K3-uyari`: kayıp parçacık
  dışındaki OpenMC uyarıları (not; sonucu etkileyip etkilemediğini logda inceleyin).
- "Koşu logu (kosu.log) yok" → uygulanamadı: koşu bu uygulamayla yapılmamış; yeniden çalıştırın.

### Profil B — Kritiklik güvenliği

Yöntem kaynağı NUREG/CR-6698 (2001) ve bu araçta [docs/VV.md](../../VV.md). B'nin K6 dışındaki
kuralları bir **doğrulama (V&V) kümesi özeti** ister. Arayüzdeki Uygunluk paneli ve
`openmc-arayuz-kosu uygunluk` komutu bugün bu özeti denetime **vermez**; bu yüzden K6-AOA ve
K8–K14 "Doğrulama (V&V) kümesi yok: bu kural değerlendirilemedi." der ve K6 "USL hesaplanamadı"
der. V&V kümesiyle denetim Python'dan yapılır (bkz. [USL hesaplanamadı](#usl-hesaplanamadi)).

<a id="kural-k6"></a>
#### K6 — Kabul koşulu k + 2σ < USL

- **Etiket:** standart. **Kaynak:** NUREG/CR-6698 eş. (1), (35), (36). Eşitsizlik katıdır;
  çarpan `kabul_carpani` = 2.
- **Tipik bulgular:** "k + 2σ = …, USL = …: kabul koşulu sağlanmıyor." → **hata** (sistem
  alt-kritiklik ölçütünü karşılamıyor; tasarımı ya da denetim parametrelerini değiştirin).
  "USL hesaplanamadı (…). k = … bir alt-kritiklik sınırıyla karşılaştırılmadı; bu sonuç
  kritiklik güvenliği kanıtı değildir." → uygulanamadı. "Özdeğer koşusu sonucu yok" →
  uygulanamadı.

<a id="kural-k6-aoa"></a>
#### K6-AOA — Uygulanabilirlik alanı (kategorik)

- **Etiket:** standart (NUREG/CR-6698 §2.5, Tablo 2.3). **Ne denetler:** uygulamanın bölünebilir
  elementi, fiziksel biçimi, yansıtıcısı ve tayf sınıfı doğrulama kümesinde var mı.
- **Tipik bulgu:** "…: uygulama '…', doğrulama kümesi yalnız … içeriyor — uygulanabilirlik
  alanının dışında." → uyarı. Çözüm: bu özelliği taşıyan kriter deneylerini kümeye ekleyin.
  Uygulamanın özellikleri verilmediyse uygulanamadı.

<a id="kural-k8"></a>
#### K8 — Pozitif yanlılık kredilendirilmez

- **Etiket:** standart (eş. 8). "USL'de pozitif yanlılık (…) kredilendirilmiş." → hata;
  yanlılık > 0 ise USL hesabında 0 alınmalıdır. Araç bunu kendisi uygular; bu bulgu yalnız dış
  bir özet verildiğinde çıkar.

<a id="kural-k9"></a>
#### K9 — k_calc / k_exp normalleştirmesi

- **Etiket:** standart (eş. 9). "Kriter k_exp ≠ 1 olan vakalar k_calc / k_exp ile
  normalleştirilmemiş." → uyarı. Çözüm: k_norm = k_calc / k_exp ve σ = √(σ_calc² + σ_exp²).

<a id="kural-k10"></a>
#### K10 — Vaka sayısı ve güven düzeyi

- **Etiket:** standart (§2.2, Tablo 2.2). "Kümede … vaka (< 10): teknik gerekçe gerekli." →
  uyarı; kümeye bağımsız kriter deneyleri ekleyin.
- `K10-guven`: parametrik olmayan yöntemde güven β bildirilmemişse uyarı; β ≤ %40 iken USL
  verilmişse **hata** ("ek veri gerekir, USL hesaplanamaz").

<a id="kural-k11"></a>
#### K11 — Alt-kritik pay ΔSM ≥ 0.02

- **Etiket:** standart (§2.4.5). Varsayılan ΔSM = 0.05 (NUREG-1520 / NUREG-1718 kaynaklı;
  değer **doğrulanmadı**). "ΔSM = … mutlak alt sınırın (0.02) altında: profil geçersiz." →
  hata; ΔSM'yi en az 0.02 yapın ve gerekçesini yazın. Seçilen değerin gerekçesi kullanıcı
  kuruluşa aittir.

<a id="kural-k12"></a>
#### K12 — Doğrulama aralığı dışına dış değerleme

- **Etiket:** standart (§5). Uygulamanın sayısal AOA parametreleri (zenginlik, H/X, EALF)
  kümenin aralığında mı. Tolerans sınırı yönteminde aralık dışı **hata** (dış değerleme için
  kullanılamaz); %10'dan büyük taşma **uyarı** ("Doğrulama kümesi genişletilmeli"); ΔAOA = 0
  iken küçük taşma uyarı ("ΔAOA payı ve gerekçesi girilmeli").

<a id="kural-k13"></a>
#### K13 — Eğilim ve normallik

- **Etiket:** standart (§2.4.2–2.4.3).
- `K13-normallik`: "Veri normal değil (…) ama '…' yöntemi kullanılmış." → hata; parametrik
  olmayan yöntem zorunludur. Sonuç raporlanmamışsa uyarı.
- `K13-egilim`: "Anlamlı eğilim var (…) ama tolerans sınırı yöntemi kullanılmış." → uyarı;
  tolerans bandı yöntemini kullanın. Eğilim analizi yoksa uyarı.

<a id="kural-k14"></a>
#### K14 — Deneyler arası bağımsızlık

- **Etiket:** iyi uygulama (NEA/NSC/WPNCS/DOC(2013)7, UACSA). "Aynı deney serisinden birden çok
  vaka: … Vakalar bağımsız değil; istatistik güveni abartılı olabilir." → not. Örnek: V&V
  kümesindeki LEU-SOL-THERM-002 durum 1 ve 2.

### Profil C — Reaktör kor tasarımı

Girdiler koşu dizinindeki `uygunluk_girdisi.json` dosyasının `kor` anahtarından okunur
(`katsayilar`, `kapatma_marji`, `faktorler`, `dogrulama`); güç tepe faktörleri verilmezse
statepoint'ten okunur. Analiz sekmesinin katsayıları bu dosyaya bugün **kendiliğinden yazılmaz**.

<a id="kural-k7"></a>
#### K7 — Reaktivite katsayılarının işareti (GDC 11)

- **Etiket:** standart (NUREG-0800 §4.3 Rev. 3 II.2, GDC 11). Kural yalnız işaret beklentisini
  sınar; "GDC 11'i karşıladı" **demez** (net geri besleme yargısı tasarım analizidir). Anlamlılık
  `anlamlilik_carpani` = 2 (proje ölçütü: |eğim| > 2σ).
- Alt kimlikler `K7-guc`, `K7-yakit_sicaklik`, `K7-sogutucu_sicaklik`, `K7-void_orani`:
  - negatif → kontrolü geçti;
  - `K7-guc` pozitif → **hata** (işaret beklentisiyle çelişiyor);
  - Doppler (`K7-yakit_sicaklik`) pozitif → uyarı (olağan dışı);
  - pozitif MTC ya da boşluk katsayısı → **not**: tek başına hata değildir (SRP 4.3 pozitif
    MTC'yi dışlamaz), geçici rejim analizinde değerlendirilmelidir;
  - |eğim| ≤ 2σ → işaret belirlenemedi (güç katsayısında uyarı, diğerlerinde bilgi): tarama
    aralığını genişletin ya da istatistiği artırın;
  - σ verilmemiş → uygulanamadı.
- `K7-guc` ayrıca "Net güç katsayısı verilmedi" notu olarak da çıkar: GDC 11 yalnız bileşen
  katsayılarından yargılanamaz.
- Katsayı hiç verilmediyse "Reaktivite katsayısı sonucu verilmedi." (uygulanamadı) → Analiz
  sekmesinde tarama yapıp sonucu `uygunluk_girdisi.json`'a girin.

<a id="kural-k7-sdm"></a>
#### K7-SDM — Kapatma marjı (en değerli çubuk sıkışık)

- **Etiket:** kullanıcı sınırı (NUREG-0800 §4.3; GDC 26/27). Sınır `sdm_siniri_pcm` tesise
  özeldir; **varsayılan yok** → "sınır girilmedi, karşılaştırılamadı" (uygulanamadı). Burada
  pcm = Δρ × 10⁵.
- `K7-SDM-N1`: marj en değerli çubuk sıkışık (N−1) varsayımıyla hesaplanmamış → uyarı.
  `K7-SDM-sigma`: marjın belirsizliği verilmemiş → uyarı. Sınırın altı hata, 2σ içinde uyarı.

<a id="kural-k7-f"></a>
#### K7-F — Güç tepe faktörleri F_ΔH / F_q

- **Etiket:** kullanıcı sınırı. `K7-FdH` ve `K7-Fq` değeri `F_dH_siniri` / `F_q_siniri` ile
  karşılaştırır; sınır yoksa "sınır girilmedi, karşılaştırılamadı (tesise özel; varsayılan
  yok)" (uygulanamadı). Sınırı aşarsa hata, sınırdan 2σ içinde uyarı. "Güç dağılımı sonucu yok"
  → güç dağılımını açıp koşuyu yineleyin.

<a id="kural-k16"></a>
#### K16 — Kor yöntem doğrulaması referansı

- **Etiket:** standart (ANSI/ANS-19.3-2022; ISO 18075:2018, madde ayrıntısı doğrulanmadı).
  "Kor hesap yönteminin hangi kriterlerle doğrulandığı ve uygulama aralığı belirtilmedi." →
  bilgi. Çözüm: `uygunluk_girdisi.json` içinde `kor.dogrulama` listesine referansları
  (IRPhEP vakası, hesap-hesap karşılaştırması) yazın.

### Profil D — Raporlama

<a id="kural-k4"></a>
#### K4 — Veri izlenebilirliği

- **Etiket:** standart (ANSI/ANS-10.4-2008 (R2021); NUREG/CR-6698 §2.3). Raporun
  tekrarlanabilirlik alanları (OpenMC sürümü, kütüphane, zincir sha256, tohum…) bilinmiyorsa
  uyarı: koşuyu bu uygulamayla yeniden çalıştırın; sürüm ve kütüphane `kosu.log`'dan okunur.
- `K4-sicaklik`: "Sıcaklığı tanımsız malzeme: …" → uyarı; Malzemeler sayfasında sıcaklığı girin.

<a id="kural-k5"></a>
#### K5 — Belirsizlik ve birim bildirimi

- **Etiket:** standart (JCGM 100:2008 §7.2.2, §7.2.3, §7.2.6; BIPM SI Broşürü). Koşu dizinindeki
  `rapor.html` denetlenir; rapor yoksa uygulanamadı ("Raporu oluşturup denetimi yineleyin").
  Birden çok `.html` varsa hangisinin rapor olduğu belirsizdir: raporu `rapor.html` adıyla
  kaydedin.
- `K5-etiket`: "±" ile verilen değerlerin 1σ standart belirsizlik olduğu yazılmamış (uyarı).
- `K5-rakam`: belirsizlik 2 anlamlı rakamdan fazla (uyarı). Örnek doğru biçim:
  1.1822 ± 0.0029 (1σ).
- `K5-yuvarlama`: değer belirsizlikle aynı ondalık basamağa yuvarlanmamış (uyarı).
- `K5-pcm`: "pcm" kullanılmış ama tanımı (Δk × 10⁵ mi Δρ × 10⁵ mi) o bölümde ya da belge
  başında yazılmamış (uyarı).
- `K5-SI`: SI dışı birim (inch, ft, psi, BTU, lbm, °F) → uyarı.

<a id="yakinsamadi"></a>
### K1: "kaynak yakınsamadı" — adım adım

Uygunluk panelinde K1 satırı "Kaynak dağılımı pasif dönemin sonunda hâlâ kayıyor …" diyorsa:

1. **Ne demek:** Pasif çevrimler bittiğinde fisyon kaynağının uzaysal dağılımı henüz
   oturmamış; aktif çevrimlerde toplanan k-eff ve tally'ler bu oturmamış kaynaktan etkilenir.
   k-eff'in kendisine bakarak bunu fark etmek çoğu zaman mümkün değildir.
2. **Entropi grafiğine bakın:** Çalıştır sayfasındaki yakınsama grafiğinde entropi pasif dönemin
   sonunda hâlâ eğim taşıyorsa (yükseliyor ya da düşüyorsa) kural doğrudur.
3. **Pasif çevrimi artırın:** Hesap ayarlarında **Pasif çevrim** değerini, entropinin
   düzleştiği çevrimden büyük olacak şekilde artırın (tipik: tek demette 20–50, tam korda
   100 ve üstü). **Toplam çevrim**i de aynı miktar artırın; yoksa aktif çevrim azalır.
4. **Entropi ağını denetleyin:** **Entropi ağı** çok kabaysa (ör. 1 × 1 × 1) kayma görünmez;
   3B modelde z yönünde de bölme kullanın.
5. **Parçacık sayısı:** Çevrim başına parçacık azsa (`K2-parcacik`) entropi gürültülüdür;
   birkaç bin parçacık kullanın.
6. **Yeniden koşun** ve paneldeki K1 satırının "kontrolü geçti" olduğunu görün.

Ayrıntılı yorum: [Kaynak yakınsaması](06-sonuclar.md#kaynak-yakinsamasi).

<a id="usl-hesaplanamadi"></a>
### "USL hesaplanamadı" — adım adım

Profil B seçiliyken panel (ve rapor eki) "USL hesaplanamadı: …" diyorsa:

1. **Bu bir model hatası değildir.** USL (üst alt-kritik sınır), hesap yönteminin kriter
   deneylerine karşı doğrulanmasından gelir. Sınır hesaplanamadığında koşunuzun k değeri bir
   alt-kritiklik sınırıyla **karşılaştırılmamıştır**; sonuç kritiklik güvenliği kanıtı olarak
   kullanılamaz, ama hesap kendi içinde yanlış değildir.
2. **Nedeni okuyun:** parantez içindeki neden şunlardan biridir:
   - "doğrulama (V&V) kümesi yok" — arayüz ve `uygunluk` komutu V&V özetini bugün denetime
     vermez (bkz. Profil B notu);
   - "kümede … vaka var (< 10): bağımsız vaka yetersiz" — o uygulanabilirlik alanında (AOA)
     yeterli bağımsız kriter yok (NUREG/CR-6698 §2.2);
   - "veri normal değil ve parametrik olmayan güven β ≤ %40: ek kriter verisi gerekli"
     (Tablo 2.2).
3. **Hangi AOA'lar için USL var:** [docs/VV.md](../../VV.md) tablosuna bakın. Bugünkü küme
   hızlı tayf metal sistemler ve termal tayf için USL verir; **LWR/LEU kafes**, yalnız Pu, yalnız
   U-233 ve ara tayf alt kümelerinde USL hesaplanamaz. Ayrıntı:
   [Doğrulama ve geçerleme](07-uygunluk.md#vv).
4. **V&V özetiyle denetim (Python):** kendi AOA'nızın filtresiyle özet alıp denetçiye verin:

   ```bash
   python -c "from cekirdek.vv import kume; print(kume.ozet(filtre={'tayf': 'termal'}))"
   ```

   Denetçide: `denetle(spec, kosu_dizini, ("B",), vv=kume.ozet(...), uygulama=kume.uygulama(spec, kosu_dizini))`
   (`cekirdek/uygunluk_denetimi/denetle.py`).
5. **Küme yetersizse:** uygulamanızı temsil eden bağımsız kriter deneylerini (ör.
   LEU-COMP-THERM serileri) ICSBEP el kitabından modelleyip kümeye eklemek gerekir
   ([docs/STANDARTLAR.md](../../STANDARTLAR.md) §5). Teknik gerekçeyle vaka alt sınırını
   düşürmek kullanıcı kuruluşun kararıdır; K10 yine uyarır.

<a id="kurulum-sorunlari"></a>
## 9.4 Kurulum ve ortam sorunları

Kaynak: [KURULUM.md](../../../KURULUM.md) "Sık karşılaşılanlar" ve `calistir.sh`.

| Belirti | Neden | Çözüm |
|---|---|---|
| `HATA: openmc PATH'te yok` | Conda ortamı etkin değil. | `conda activate openmc-env` |
| `openmc Python paketi bulunamadi` / `PySide6 bulunamadi` | Ortam eksik kurulmuş. | `conda env create -f environment.yml` ile ortamı yeniden kurun. |
| `OPENMC_CROSS_SECTIONS ayarli degil` (uyarı) ve doğrulamada `veri kutuphanesi` hatası | Nükleer veri indirilmemiş ya da yeni terminal açılmamış. | `./veri_indir.sh --bashrc`, sonra `source ~/.bashrc` ([Nükleer veri](01-kurulum.md#nukleer-veri)). |
| `Grafik oturum yok (DISPLAY/WAYLAND_DISPLAY bos)` | SSH ile bağlısınız ya da WSL'de grafik yok. | Masaüstü oturumunda açın; WSL için Windows 11 + `wsl --update`. Arayüzsüz çalışma: [Terminal](08-terminal.md#terminal). |
| Tükenme sayfası "zincir dosyası yok/yarım" diyor | Zincir indirilmemiş ya da indirme kesilmiş (bir kez %13'te sessizce kesildiği ölçüldü). | `./veri_indir.sh --yalniz-zincir` |
| `conda env create` çok uzun sürüyor | Eski çözücü. | `conda config --set solver libmamba` ya da `mamba env create -f environment.yml` |
| Testlerin bir kısmı atlanıyor (`veri` işaretli) | `OPENMC_CROSS_SECTIONS` yok. | Beklenen davranış; veriyi indirince koşarlar. |
| Uygulama bir hata koduyla kapandı | Yakalanmamış bir hata. | Terminalde yazan günlük dosyasını (`~/.local/state/openmc_arayuz/openmc_arayuz.log`) açın ve hatayı bu dosyayla bildirin. |
| Sonuçlar nereye yazıldı? | — | Kayıtlı projede projenin yanındaki `kosu` dizini; kaydedilmemiş projede `~/openmc_kosular` altı. Çalıştır sayfası tam yolu yazar. |

<a id="kosu-sorunlari"></a>
## 9.5 Koşu sorunları

| Belirti | Neden | Çözüm |
|---|---|---|
| ÇALIŞTIR düğmesi pasif: "Doğrulamada … hata var — önce bunları giderin." | Hata seviyesinde bulgu var. | Rozete tıklayıp bulguyu seçin, ilgili sayfada düzeltin ([9.2](#bulgu-turleri)). |
| ÇALIŞTIR düğmesi pasif: "Geometri önizlemesi henüz çizilmedi. Önce çiz, sonra çalıştır…" | Önizleme hâlâ çiziliyor ya da çizilemedi. | Bekleyin; çizilemediyse aşağıdaki satıra bakın ([Önce çiz, sonra çalıştır](06-sonuclar.md#once-ciz)). |
| "Önizleme başarısız: …" / önizlemede "Geometri kurulamadı" | Model OpenMC geometrisine çevrilemedi (tanımsız ad, sığmayan parça, eksik dolgu). | İletideki metni okuyun; doğrulama listesinde aynı konu genellikle bir hata olarak durur. |
| "Önceki projenin koşusu arka planda sürüyor…" | Başka bir proje açılırken eski koşu bitmedi. | Durdur ile eski koşuyu sonlandırın. |
| Koşu sonunda kayıp parçacık (K3 hatası) | Geometride boşluk ya da çakışan hücre. | Kesitleri inceleyin, sınır koşullarını denetleyin; gelişmiş geometride "Yokla". |
| Koşu sıcaklık hatasıyla duruyor | Bir malzemenin sıcaklığı veri aralığının dışında. Nötron verisi 250–2500 K, su S(α,β) yalnız 284–800 K. | Sıcaklığı aralıkta tutun; sıcaklık taramasında bitiş değerini kontrol edin ([Bilinen tuzaklar](06-sonuclar.md#tuzaklar)). |
| Uyarı: "Çalıştırılabilir. … uyarı var" | Uyarı seviyesinde bulgular. | Listeyi okuyun; sonucu etkileyebilir. |
| k-eff beklenenden çok farklı | Sık nedenler: S(α,β) eksik, yan sınır vakum (k∞ yerine k-eff), 2B model, zenginlik kısayolu %5 üstünde. | Doğrulama listesindeki uyarıları okuyun; [Sonuçları yorumlamak](06-sonuclar.md#sonuclar). |
| F_ΔH beklenenden büyük | Az istatistikte F_ΔH yukarı yanlıdır (bir maksimumdur). | Parçacık sayısını artırın; Normal ya da Hassas hassasiyet. |
| Tükenme sayfasında kırmızı "Eski sonuç (…): model o koşudan beri değişti" | Gösterilen sonuç şu anki modele ait değil. | Yeniden koşun ([Tükenme](04i-tukenme.md#tukenme)). |
| "Yarım kalmış koşu (…): … / … adım tamamlanmış" | Tükenme durdurulmuş ya da hâlâ sürüyor. | Tam sonuç için yeniden koşun (kaldığı yerden sürdürme yok). |
| "Önceki koşunun sonucu (…). Koşunun model kaydı yok…" | Koşu dizininde `tukenme_spec.json` yok. | Sonucun bu modele ait olduğu doğrulanamıyor; emin değilseniz yeniden koşun. |
| Uygunluk paneli "Denetlenemedi" | `uygunluk_girdisi.json` bozuk ya da okunamıyor. | Dosyayı JSON olarak düzeltin ya da silin; ayrıntı günlükte. |
| Uygunlukta çok sayıda "uygulanamadı" | Eşik ya da girdi yok (bkz. 9.3 "Eşikler"). | Beklenen davranış; `--siki` olmadan başarısızlık sayılmaz. |
| Terminalde `openmc-arayuz-kosu uygunluk` çıkış kodu 1 / 3 | 1: hata bulgusu var; 3: `--siki` ile değerlendirilemeyen kural var; 2: kullanım hatası. | Çıktıdaki listeyi okuyun ([Terminal](08-terminal.md#terminal)). |

Terminalden aynı denetim:

```bash
openmc-arayuz-kosu uygunluk kosu/ --profil A,D
openmc-arayuz-kosu uygunluk kosu/ --profil A,B,C,D --siki
```
