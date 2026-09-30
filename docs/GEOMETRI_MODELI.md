# Esnek Geometri Modeli (Dalga G) — Tasarım Belgesi

**Durum:** Taslak (G-0). **KAPI G-A:** kullanıcı şemayı ve arayüz eskizini onaylamadan kodlama başlamaz.
**Tarih:** 30.09.2026 · **Kapsam:** `spec` şema sürümü 3, `cekirdek/geometri/` paketi, tüketiciler, arayüz.

## 0. Özet

1. `kor.tur` kapalı listesi yerine, iç içe geçen **altı düğüm türü** var: `malzeme`, `bilesen`, `kafes`, `kap`, `eksenel`, `referans`. Buna iki alt yapı eklenir: yerleşim (`yerlesim`) ve dönüşüm (`donusum`).
2. Tambur, kontrol çubuğu, deney kanalı ve merkezdeki kare kafes aynı mekanizmayla yerleşir. Bu mekanizma yerleşimdir: bir kap bölgesinden bir kesit oyulur ve içine bir düğüm konur.
3. Mevcut 7 kor türü **şablon** olarak kalır. Çalışma anında saf bir işlevle ağaca genişler; diske ağaç yalnız "Gelişmiş" modda yazılır.
4. Tek kurucu vardır (`geometri.kur`). Betik aynı gezintiden ikinci bir "yapıcı" ile üretilir; iki kod yolu artık ayrışamaz.
5. Eşdeğerlik kapısı kimlikten bağımsız bir karşılaştırma kullanır: malzeme, kafes indeksleri, öteleme ve distribcell örnek sırası. Eski kurucu silindikten sonra da kayıtlı "parmak izi" dosyasıyla çalışmaya devam eder.

## 1. Amaç ve kapsam sınırı

**Amaç.** Kullanıcının isteği: "Geometri modeli çok esnek olmalı: kare kafesin etrafını altıgen kafesle çevirmek, tambur kullanımını sadece örneğe göre değil her geometride kullanabilmek gibi." Yeni bir düzenek için yeni kor türü ya da yeni kurucu dalı yazılmamalı.

**Kapsamda:**
- kare/altıgen kafeslerin iç içe ve yan yana karışımı;
- farklı şekilli eş merkezli halkalar (kare kor + silindirik yansıtıcı gibi);
- herhangi bir bölgeye tambur, kanal ya da alt kafes yerleştirme;
- adlandırılmış yeniden kullanılabilir parçalar;
- herhangi bir düzeyde eksenel yığın;
- tambur ve kontrol çubuğu grupları;
- bütün modeli döndürme (simetri testi için).

**Kapsam dışı (İ-listesi):**
- ham CSG hücresi (yüzey ve bölge ifadesi yazdırma);
- DAGMC/CAD;
- yüz başına yan sınır koşulu (çeyrek kor simetrisi);
- kare kafes için basamaklı `kafes_zarfi`;
- dairesel olmayan bir deliğin döndürülmesi;
- simetri kısaltma sihirbazı.

Bu bir CSG editörü değildir. Kullanıcı yüzey yazmaz; her düğüm OpenMC'de bilinen, doğrulanabilir tek bir yapıya karşılık gelir.

## 2. Temel kavramlar

- **Tanım ve kullanım.** Kütüphane bölümleri (`cubuklar`, `plakalar`, `demetler`, `tamburlar`, `geometri.parcalar`) *tanımdır*. Ağaçtaki `bilesen` düğümü bir tanımın *kullanımıdır*.
  - Aynı ad kaç kez kullanılırsa kullanılsın OpenMC'de **tek bir Universe** kurulur.
  - Distribcell güç tally'si ve tükenmede örnek ayırma buna dayanır (bugünkü `universeler[ad]` önbelleğiyle aynı ilke).
- **Yuva.** Bir düğümün konabileceği yerdir: `kap.ic`, `kap.dis`, `halka.icerik`, `kafes.anahtar[harf]`, `kafes.dis`, `eksenel.icerik`, `katman.icerik`, `yerlesim.icerik`.
  - Yuvaya bir düğüm nesnesi ya da **dize kısaltması** yazılabilir.
  - Kısaltma, bugünkü `_universe_uret` sırasıyla çözülür: çubuk → plaka → demet → tambur → parça → malzeme. `"bosluk"` void anlamına gelir.
  - Arayüz her zaman açık düğüm yazar; kısaltma yalnız elle yazılan JSON içindir.
- **Kimlik (`id`).** İsteğe bağlı ama ağaç içinde tekil bir kısa kimliktir. Editör `d1, d2…` atar; `genislet` belirleyici kimlikler üretir (`kok`, `kor_kafesi`, `tamburlar`…). Arayüz seçimi, doğrulama "yer" etiketi ve hücre adları bunu kullanır.
- **Yol.** JSON-işaretçisi biçimidir: `/kok/halkalar/0/yerlesimler/1`. Kalıcı başvurularda `id`, geçici işlemlerde yol kullanılır.
- **Birimler ve eksenler.**
  - Uzunluk cm, açı derece; pozitif açı saat yönünün tersidir.
  - Her düğüm kendi yerel çerçevesinde merkezlenir (0, 0); eksenel yığın z = 0 etrafında merkezlenir.
- **İki yönelim anlamı (karıştırılmamalı):**
  - `kafes.yonelim` → **HexLattice** anlamındadır (`'x'`: komşular 0°, 60°…; `'y'`: komşular 30°, 90°…).
  - `kesit.yonelim` → **HexagonalPrism** anlamındadır (`'y'`: düz yüzler sağda/solda, düşey).
  - Bir altıgen kafesi *saran* kesitin yönelimi kafes yönelimiyle aynıdır (ölçüldü: `kurucu._altigen_sinir`, `altigen_kor` yansıtıcı zarfı).
  - Bir altıgen kafesin *eleman hücresinin* şekli `ters(kafes.yonelim)` yönelimli bir prizmadır (ölçüldü: `altigen_kor` başlık notu).

## 3. Düğüm şeması

### 3.1 Spec düzeyi (sürüm 3)

```json
{
  "surum": 3,
  "kor": {"tur": "agac"},
  "cubuklar": [], "plakalar": [], "demetler": [],
  "tamburlar": [
    {"ad": "tambur_b4c", "yaricap": 6.0, "govde_malzeme": "celik",
     "emici_malzeme": "b4c", "emici_ic_yaricap": 4.5, "emici_aci": 120.0}
  ],
  "geometri": {
    "kok": {"tur": "kap", "...": "..."},
    "parcalar": [{"ad": "celik_blok", "dugum": {"tur": "kap", "...": "..."}}],
    "gruplar": [{"ad": "tamburlar", "tur": "donme", "deger": 180.0, "uyeler": ["tambur_halkasi"]}]
  }
}
```

- **Şablon modu:** `kor.tur` 7 şablondan biridir (bugünkü alanlar aynen kalır). `geometri` ve `tamburlar` yoktur ya da boştur. Ağaç, `geometri.genislet(spec)` ile her istendiğinde türetilir.
- **Gelişmiş mod:** `kor.tur == "agac"`, `kor`da başka alan yoktur. Tek gerçek kaynak `geometri`dir.
- **Tambur tanımı:** `tamburlar` tanımı geometri + malzemedir (`cekirdek/tambur.py` alanları). Yerleşim alanları (`sayi`, `merkez_yaricap`, `donme`, `baslangic_acisi`) artık yerleşim ve gruptadır.

### 3.2 Ortak alanlar

| Alan | Tür | Anlam |
|---|---|---|
| `tur` | dize, zorunlu | `malzeme` \| `bilesen` \| `kafes` \| `kap` \| `eksenel` \| `referans` |
| `id` | dize | tekil kimlik (hücre adı, seçim, doğrulama yeri) |
| `ad` | dize | görünen ad |
| `donusum` | `{"donme": derece, "oteleme": [x, y]}` | yuvaya konurken uygulanır. `malzeme` düğümünde HATA: OpenMC malzeme dolgulu hücreyi döndürmez |

### 3.3 `malzeme` (yaprak)

```json
{"tur": "malzeme", "ad": "su"}
```

`ad` ya bir malzeme adıdır ya da `"bosluk"`tur (void).

### 3.4 `bilesen` (kütüphane başvurusu)

```json
{"tur": "bilesen", "ad": "demet_24", "donusum": {"donme": 0.0}}
```

`ad` şunlardan birinde aranır: `cubuklar`, `plakalar`, `demetler`, `tamburlar`, `geometri.parcalar`. İki bölümde aynı ad varsa **HATA** verilir; açık düğümde belirsizliğe izin verilmez.

### 3.5 `kafes`

```json
{"tur": "kafes", "id": "cekirdek_kafesi", "sekil": "kare", "adim": 21.42,
 "boyut": [5, 5], "harita": ["BABAB", "ABABA", "BABAB", "ABABA", "BABAB"],
 "anahtar": {"A": "demet_24", "B": {"tur": "bilesen", "ad": "demet_31"}},
 "dis": {"tur": "malzeme", "ad": "su"}}
```

```json
{"tur": "kafes", "id": "blok_kafesi", "sekil": "altigen", "adim": 30.0,
 "halka_sayisi": 3, "yonelim": "x",
 "harita": ["BBBBBBBBBBBB", "BBBBBB", "."],
 "anahtar": {"B": "celik_blok"}, "dis": {"tur": "malzeme", "ad": "su"}}
```

- **Kare kafes:** `harita` satır satırdır (ilk satır en üst). `boyut = [nx, ny]`.
- **Altıgen kafes:** harita dıştan içe halka listesidir; her halka bugünkü `altigen.konumlar` sırasıyla yazılır ('y' tepeden, 'x' sağdan başlar, saat yönünde).
- **`.` karakteri** konumu `dis` ile doldurur (düzensiz kor, gizli konum).
- **`dis` zorunludur.** OpenMC'de kafesin dışı ve `.` konumları buraya düşer. Tek istisna R3b'dir (aşağıda).
- **Adım:** kare kafeste hücre kenarı, altıgen kafeste düz yüzden düz yüze ölçüdür.

### 3.6 `kap` (şekil + halkalar + delikler)

```json
{"tur": "kap", "id": "kok",
 "kesit": {"sekil": "silindir", "yaricap": 16.0},
 "ic": {"tur": "malzeme", "ad": "u10mo"},
 "yerlesimler": [],
 "halkalar": [
   {"kalinlik": 12.0, "icerik": {"tur": "malzeme", "ad": "berilyum"}, "yerlesimler": []}
 ],
 "dis": null,
 "yukseklik": 45.0,
 "sinir": {"yan": "vacuum", "alt": "vacuum", "ust": "vacuum"}}
```

**Kesit türleri** (`kesit` ve `halka.dis`):

| `sekil` | Alanlar | OpenMC |
|---|---|---|
| `dikdortgen` | `boyut: [gx, gy]` | `openmc.model.RectangularPrism(gx, gy)` |
| `silindir` | `yaricap` | `ZCylinder` |
| `altigen` | `apotem`, `yonelim` (prizma anlamı) | `HexagonalPrism(edge_length = 2·apotem/√3)` |
| `kure` | `yaricap` | `Sphere` (yalnız kök; `yukseklik` yok) |
| `kafes_zarfi` | — | yalnız `ic`i altıgen kafes olan **kök** kapta; bkz. R3b |

**Halka:** `{"kalinlik": k}` ya da `{"dis": kesit}` alanlarından **tam olarak biri** verilir, ayrıca `icerik` ve isteğe bağlı `yerlesimler`.
- `kalinlik` aynı şekli düzgün büyütür: dikdörtgende `boyut + 2k`, silindir ve kürede `r + k`, altıgende `apotem + k`.
- `kafes_zarfi` üzerinde `kalinlik` kullanılamaz (HATA); `dis` verilmelidir.

**Kök kap kuralları:**
- `yukseklik` ve `sinir` yalnız kökte bulunur.
- Kökte `dis` yasaktır.
- Kök olmayan kapta `dis` zorunludur (kabın dışı ile yuvanın sınırı arası).

**Yükseklik:**
- `yukseklik: null` ve ağaçta eksenel yığın yoksa model 2B'dir.
- Kökün `ic`inde eksenel yığın varsa `yukseklik` null olmalı; model yüksekliği yığının toplamıdır ("tek gerçek kaynak" kuralı bugünkü gibi).

### 3.7 `eksenel` (z yığını)

```json
{"tur": "eksenel", "id": "kor_eksen",
 "icerik": {"tur": "kafes", "id": "kor_kafesi", "...": "..."},
 "katmanlar": [
   {"ad": "alt su", "yukseklik": 20.0, "icerik": {"tur": "malzeme", "ad": "su"}},
   {"ad": "aktif", "yukseklik": 200.0, "icerik": null},
   {"ad": "üst kuşak", "yukseklik": 30.0, "icerik": null, "anahtar": {"A": "demet_24_ust"}}
 ]}
```

- Katmanlar alttan üste sıralanır; yığın z = 0 etrafında merkezlenir.
- `icerik: null` → varsayılan `icerik` kullanılır.
- `anahtar` yalnız varsayılan içerik (çözüldükten sonra) bir `kafes` ise geçerlidir. Katmana özgü eşleme harita aynı kalarak uygulanır (bugünkü eksenel zenginlik kuşaklaması).
- Yüksekliği 0 ya da daha az olan katman atlanır ve BİLGİ verilir (bugünkü `eksenel_katmanlar` davranışı).
- Kök dışındaki bir yığının toplamı model yüksekliğine **eşit olmalıdır** (HATA). Aksi hâlde son katman sessizce uzardı.

### 3.8 Yerleşim (kap bölgesinin alt yapısı; düğüm değil)

Yerleşim, sahibi olan bölgeden (kabın `ic`i ya da bir halka) bir **delik** oyar ve deliğe `icerik` koyar.

```json
{"ad": "tambur_halkasi", "mod": "halka",
 "sayi": 6, "merkez_yaricap": 36.0, "baslangic_acisi": 30.0,
 "icerik": {"tur": "bilesen", "ad": "tambur_b4c"},
 "kesit": null,
 "bakis": {"tur": "merkez", "merkez": [0.0, 0.0]},
 "donme_ofset": 0.0}
```

| `mod` | Alanlar | Örnek merkezleri (x_i, y_i) |
|---|---|---|
| `halka` | `sayi`, `merkez_yaricap`, `baslangic_acisi` | fi_i = baslangic + 360·i/n; (R·cos fi_i, R·sin fi_i) |
| `liste` | `konumlar: [[x, y], ...]` | aynen |
| `kafes_konumu` | `kafes` (kafes `id`), `harf` | o kafesteki `harf` konumlarının merkezleri, kabın çerçevesinde. Kafes ya kabın `ic`i ya da aynı kaptaki bir halkanın içeriği olmalı ve dönüşümsüz olmalı |

- **`kesit`:** deliğin şeklidir.
  - `null` yalnız doğal kesiti olan içerikte geçerlidir (tambur: yarıçapı `yaricap` olan daire). Diğer içeriklerde zorunludur.
  - Daire dışı bir delik bakış ya da dönme ile döndürülemez (HATA; G-1 kapsamı).
- **`kafes_konumu`:** alttaki kafes konumu yerinde kalır; delik onun içinden oyulur. Delik konum hücresinin içinde kalmalıdır.

**"Kora bakan yön" konvansiyonu (bütün modlar):**
- Her yerleştirilen içeriğin **ön yüzü yerel +x yönüdür**. Tamburda emici yay yerel +x'te ortalanmıştır (`tambur.universe`).
- Örnek i için dönme açısı:
  - `halka` modunda: **ψ_i = fi_i + 180 + D**. Bu, bugünkü `tambur.yerlesim` ile bit düzeyinde aynıdır; eşdeğerlik için atan2 ile yeniden hesaplanmaz.
  - `liste` ve `kafes_konumu` modunda, `bakis.tur == "merkez"` ise: **ψ_i = atan2(m_y − y_i, m_x − x_i) + D**.
  - `bakis.tur == "sabit"` ise: **ψ_i = bakis.aci + D**.
  - Bakış verilmemişse: **ψ_i = içeriğin `donusum.donme` değeri**.
- Burada **D = (üye olduğu dönme grubunun `deger`i, yoksa 0) + `donme_ofset`**.
- Varsayılan `bakis`: içerik tambur ise `{"tur": "merkez", "merkez": [0, 0]}`, değilse yok.
- Merkez ve örnek konumları sahibi olan kabın yerel çerçevesindedir. Kabın kendisi bir üst dönüşümle döndürülürse bütün yerleşim birlikte döner ve "kora bakan" özelliği korunur.
- Örnek merkezi `merkez` ile çakışırsa yön tanımsızdır (HATA; "sabit" bakış seçilmeli).
- Sonuç: `donme = 0` emici kora bakıyor (daldırılmış, en düşük k); `donme = 180` emici dışa bakıyor (çekilmiş).

### 3.9 Parçalar (`geometri.parcalar`)

- Adlandırılmış alt ağaçlardır: `{"ad": "...", "dugum": <düğüm>}`.
- `bilesen` ile başvurulur; aynı parça tek bir Universe olur.
- Birden fazla kez kullanılan bir alt ağaç **parça olmalıdır**. Satır içi bir düğümü iki yuvaya kopyalamak iki ayrı Universe üretir; distribcell ve tükenme örnek sayımı bölünür. Aynı içerikli iki satır içi alt ağaç bulunursa UYARI verilir.
- Parça kendini doğrudan ya da dolaylı içeremez (döngü → HATA).

### 3.10 Gruplar (`geometri.gruplar`)

```json
[{"ad": "tamburlar", "tur": "donme", "deger": 180.0, "uyeler": ["tambur_halkasi"]},
 {"ad": "Banka A", "tur": "daldirma", "deger": 40.0, "uyeler": ["kc_a"]}]
```

- **Değer yalnız grupta tutulur** (tek kaynak).
- `donme` grubunun üyeleri yerleşim adlarıdır; yerleşimin bütün örnekleri döner.
- `daldirma` grubunun üyeleri kontrol çubuğu tanımlarıdır (`cubuklar[].tur == "kontrol"`). Üye çubuğun kendi `daldirma` alanı yok sayılır; farklıysa BİLGİ verilir.
- Bir üye aynı türden en çok bir gruptadır (HATA).
- Aynı geometride iki banka için iki ayrı kontrol çubuğu tanımı gerekir (arayüzde "Kopyala"). Yerleşim başına daldırma açık soru 5'tedir.
- Tarama ve kritik arama hedefi artık gruptur: `grup_donme` ve `grup_daldirma`.

### 3.11 `referans`

`{"tur": "referans", "id": "..."}`: ağaçta aynı kimlikli düğüme işaret eder. Yalnız **parçaya çıkarma** işleminin ara durumu içindir; kaydedilen dosyada bulunursa `normalize` onu parçaya çevirir. Kullanıcıya gösterilmez.

> Not: Türler listesinde `referans` bulunur ama kullanıcı yalnız beş türü (malzeme, bilesen, kafes, kap, eksenel) görür.

## 4. Üç hedef düzenek (tam `geometri` JSON'u)

Malzeme, çubuk ve demet tanımları kütüphanededir: `demet_24` ve `demet_31` `pwr_ceyrek_kor.json`'daki 17×17 demetlerdir (adım 21.42); `demet_hex` `sfr_altigen.json`'daki 7 halkalı pin kafesidir (pin 'y'). Sayılar tasarım içindir; G-4 örnekleri bu yapıyla kurar ve ölçüleri kaydeder.

### 4.1 (a) Kare çekirdek (5×5) + altıgen blok halkası

```json
{
  "surum": 3,
  "kor": {"tur": "agac"},
  "tamburlar": [],
  "geometri": {
    "parcalar": [
      {"ad": "celik_blok", "dugum": {
        "tur": "kap", "id": "blok",
        "kesit": {"sekil": "altigen", "yonelim": "y", "apotem": 14.8},
        "ic": {"tur": "malzeme", "ad": "ss304"},
        "yerlesimler": [
          {"ad": "blok_kanali", "mod": "liste", "konumlar": [[0.0, 0.0]],
           "kesit": {"sekil": "silindir", "yaricap": 3.0},
           "icerik": {"tur": "malzeme", "ad": "su"}}
        ],
        "halkalar": [],
        "dis": {"tur": "malzeme", "ad": "su"}
      }}
    ],
    "kok": {
      "tur": "kap", "id": "kok",
      "kesit": {"sekil": "altigen", "yonelim": "x", "apotem": 121.2436},
      "ic": {
        "tur": "kafes", "id": "blok_kafesi", "sekil": "altigen",
        "adim": 30.0, "halka_sayisi": 5, "yonelim": "x",
        "harita": [
          "BBBBBBBBBBBBBBBBBBBBBBBB",
          "BBBBBBBBBBBBBBBBBB",
          "BBBBBBBBBBBB",
          "......",
          "."
        ],
        "anahtar": {"B": {"tur": "bilesen", "ad": "celik_blok"}},
        "dis": {"tur": "malzeme", "ad": "su"}
      },
      "yerlesimler": [
        {"ad": "kare_cekirdek", "mod": "liste", "konumlar": [[0.0, 0.0]],
         "kesit": {"sekil": "dikdortgen", "boyut": [107.1, 107.1]},
         "icerik": {
           "tur": "kafes", "id": "cekirdek_kafesi", "sekil": "kare",
           "adim": 21.42, "boyut": [5, 5],
           "harita": ["BABAB", "ABABA", "BABAB", "ABABA", "BABAB"],
           "anahtar": {"A": {"tur": "bilesen", "ad": "demet_24"},
                       "B": {"tur": "bilesen", "ad": "demet_31"}},
           "dis": {"tur": "malzeme", "ad": "su"}
         }}
      ],
      "halkalar": [{"kalinlik": 20.0, "icerik": {"tur": "malzeme", "ad": "su"}}],
      "yukseklik": null,
      "sinir": {"yan": "vacuum"}
    },
    "gruplar": []
  }
}
```

- **Ölçüler:**
  - Kök apotemi = `zarf_apotemi(5, 30) = 4·30·√3/2 + 30/√3 = 121.2436`; kesit yönelimi = kafes yönelimi 'x'.
  - Blok prizması 'y' = ters(kafes 'x'): blok eleman hücresine oturur ve 0.2 cm su aralığı kalır.
- **Beklenen doğrulama sonucu:**
  - 1. halka ve merkez deliğin altında tamamen gizlidir; `.` yazıldı, BİLGİ verilir.
  - 2. halkadaki bloklar kare delikle kırpılır: **UYARI "kesik blok"**. Bu istenen davranıştır; kare kafesin etrafını altıgen kafesle çevirmek kırpmasız mümkün değildir.

### 4.2 (b) Altıgen kor + yansıtıcı halkada 6 tambur

```json
{
  "surum": 3,
  "kor": {"tur": "agac"},
  "tamburlar": [
    {"ad": "tambur_b4c", "yaricap": 6.0, "govde_malzeme": "celik",
     "emici_malzeme": "b4c", "emici_ic_yaricap": 4.5, "emici_aci": 120.0}
  ],
  "geometri": {
    "parcalar": [],
    "kok": {
      "tur": "kap", "id": "kok",
      "kesit": {"sekil": "kafes_zarfi"},
      "ic": {
        "tur": "kafes", "id": "kor_kafesi", "sekil": "altigen",
        "adim": 10.26, "halka_sayisi": 3, "yonelim": "x",
        "harita": ["DDDDDDDDDDDD", "DDDDDD", "D"],
        "anahtar": {"D": {"tur": "bilesen", "ad": "demet_hex"}},
        "dis": {"tur": "malzeme", "ad": "bosluk"}
      },
      "yerlesimler": [],
      "halkalar": [
        {"dis": {"sekil": "altigen", "yonelim": "x", "apotem": 48.69},
         "icerik": {"tur": "malzeme", "ad": "celik"},
         "yerlesimler": [
           {"ad": "tambur_halkasi", "mod": "halka", "sayi": 6,
            "merkez_yaricap": 36.0, "baslangic_acisi": 30.0,
            "icerik": {"tur": "bilesen", "ad": "tambur_b4c"},
            "bakis": {"tur": "merkez", "merkez": [0.0, 0.0]}}
         ]}
      ],
      "yukseklik": 80.0,
      "sinir": {"yan": "vacuum", "alt": "vacuum", "ust": "vacuum"}
    },
    "gruplar": [
      {"ad": "tamburlar", "tur": "donme", "deger": 180.0, "uyeler": ["tambur_halkasi"]}
    ]
  }
}
```

- **Kor ölçüleri:**
  - Pin kafesi 'y', kor 'x' (90°, mevcut kural).
  - Zarf apotemi `zarf_apotemi(3, 10.26) = 23.694`.
  - Korun en uzak noktası ≤ 2P + P/√3 = 26.44.
- **Tambur açıklıkları:**
  - Tambur iç kenarı 30 (açıklık 3.56); dış kenarı 42 < 48.69 (tamburlar düz yüzlere, 30° + 60k yönüne bakıyor).
  - Komşu tamburlar arası 36 > 12.

### 4.3 (c) Kare kafesli kor + silindirik yansıtıcıda 4 tambur

```json
{
  "surum": 3,
  "kor": {"tur": "agac"},
  "tamburlar": [
    {"ad": "tambur_b4c", "yaricap": 8.0, "govde_malzeme": "berilyum",
     "emici_malzeme": "b4c", "emici_ic_yaricap": 6.5, "emici_aci": 120.0}
  ],
  "geometri": {
    "parcalar": [],
    "kok": {
      "tur": "kap", "id": "kok",
      "kesit": {"sekil": "dikdortgen", "boyut": [64.26, 64.26]},
      "ic": {
        "tur": "kafes", "id": "kor_kafesi", "sekil": "kare",
        "adim": 21.42, "boyut": [3, 3],
        "harita": ["ABA", "BAB", "ABA"],
        "anahtar": {"A": {"tur": "bilesen", "ad": "demet_24"},
                    "B": {"tur": "bilesen", "ad": "demet_31"}},
        "dis": {"tur": "malzeme", "ad": "berilyum"}
      },
      "yerlesimler": [],
      "halkalar": [
        {"dis": {"sekil": "silindir", "yaricap": 80.0},
         "icerik": {"tur": "malzeme", "ad": "berilyum"},
         "yerlesimler": [
           {"ad": "tamburlar4", "mod": "halka", "sayi": 4,
            "merkez_yaricap": 60.0, "baslangic_acisi": 45.0,
            "icerik": {"tur": "bilesen", "ad": "tambur_b4c"}}
         ]}
      ],
      "yukseklik": 200.0,
      "sinir": {"yan": "vacuum", "alt": "vacuum", "ust": "vacuum"}
    },
    "gruplar": [
      {"ad": "tamburlar", "tur": "donme", "deger": 180.0, "uyeler": ["tamburlar4"]}
    ]
  }
}
```

- Kare kor köşesi 45.44'te; tambur iç kenarı 52; dış kenar 68 < 80.
- `bakis` yazılmadı: tambur içeriğinde varsayılan olarak merkeze bakar.

## 5. OpenMC'ye çevirme kuralları

**R1 — Kurulum biçimi.** Her düğüm ya **satır içi** (üst bölgeyle kesişen hücreler) ya da **Universe/Lattice** olarak kurulur.
- `malzeme` her zaman satır içidir.
- Bir kap bölgesinin doğrudan içindeki `eksenel` satır içidir: katman hücreleri = bölge ∩ z dilimi. Bu bugünkü `_eksenel_hucreler` ile aynıdır.
- `bilesen` ve `kafes` bir hücrenin `fill`idir.
- Satır içi kurma, bugünkü yapıyı (ve izleme hızını) korumak için zorunludur.

**R2 — Paylaşım.** `bilesen` ad başına tek Universe olarak kurulur (`universeler[ad]`). Katman anahtarlı kafes türevleri `(kafes id, katman anahtarı)` başına bir kez kurulur.

**R3 — Kafes.**
- Kare → `RectLattice(pitch=(P, P), lower_left=(−P·nx/2, −P·ny/2), universes=satırlar, outer=dis)`.
- Altıgen → `HexLattice(center=(0, 0), pitch=(P,), orientation=yonelim, universes=halkalar, outer=dis)`.
- `.` → `dis` universe'i.

**R3b — Kök altıgen kafes (konum hücreleri).** Kök kabın kesiti `kafes_zarfi` ve `ic`i (ya da `ic`teki eksenel yığının varsayılan içeriği) altıgen kafes ise, kafes HexLattice olarak **kurulmaz**. `altigen_kor.altigen_kor_hucreleri` ile her konum kendi prizmasıyla bir kök hücre olur.
- Paylaşılan iç düzlemler tek nesnedir; sınır yüzleri ayrı ve BC'lidir.
- Katmanlar konum × katman hücreleridir.
- Halka[0] "yansıtıcı" bölgesi = −dış prizma ∩ ¬(dış halka konumları); bu bölgeye yerleşim delikleri eklenir.
- Bu, bugünkü `altigen_kafes`ın kırık çizgi sınırını ve vadileri dolduran yansıtıcısını birebir verir. `kafes.dis` burada kullanılmaz (BİLGİ).

**R4 — Kap.**
- Yüzey havuzu (`YuzeyHavuzu`): halka i'nin dış yüzeyi, halka i+1'in iç yüzeyi ile **aynı nesnedir**; aynı katsayılı yüzeyler tek nesnedir.
- Kök kapta en dış yüzey ile alt/üst `ZPlane`ler BC'lidir; diğer bütün yüzeyler `transmission`'dır.
- BC'li bir yüzey, yalnız en dış bölge hücresinin sınırında kullanılır; başka bir hücrenin içinden geçmez (`altigen_kor` dersi).
- Kök olmayan kabın universe'inde ek bir `+en_dış_yüzey` hücresi vardır, `fill = dis`; universe her yerde tanımlıdır.

**R5 — Yerleşim.** Her örnek i için:
- delik yüzeyi (daire: `ZCylinder(x0, y0, r)`; dikdörtgen/altıgen: ötelenmiş prizma, transmission);
- örnek hücresi `region = −delik` (kökte ve 3B ise ∩ z aralığı), `fill = icerik`;
- `translation = (x_i, y_i, 0)` ve `rotation = (0, 0, ψ_i)`; yalnız fill Universe/Lattice ise yazılır;
- sahip bölge hücresine `∩ +delik` eklenir (prizma deliklerde `∩ ~(−prizma)`).

**R6 — Dönüşüm.**
- `donusum` yuvayı tutan hücreye `translation`/`rotation` olarak yazılır. OpenMC sırası: yerel = R·(x − t).
- `donme = +θ` içeriği saat yönünün tersine θ döndürür (tamburda ölçüldü: ψ = 45 → yay 44.5°).
- G-1 bunu liste ve kafes konumu modlarında **yeniden ölçer**.

**R7 — Eksenel.**
- İç katman düzlemleri transmission'dır; BC yalnız kökün alt/üst düzlemindedir.
- Kök dışındaki yığında ilk ve son katman ±∞'a açıktır (üst bölge sınırlar). Toplam eşitliği (§3.7) bunun güvencesidir.
- Tamburlar ve halkalar kökün `ic`indeki yığına girmez; tam yükseklik kaplar (bugünkü davranış). Bir tambur eksenel yapı isterse, tamburu eksenel yığın içeren bir parça yapmak gerekir.

**R8 — Kontrol çubuğu.** Daldırma, **modelin** aktif (fisil) eksenel aralığına göre tanımlıdır. Bu aralık ağaçtaki bütün eksenel yığınlardan hesaplanır (`geometri.aktif_aralik`); çubuk hangi düzeyde olursa olsun aynı tanımdır (bugünkü `aktif_eksenel_aralik` genellemesi).

**R9 — Karışık kafes kuralları:**
1. **Kırpma kendiliğindendir.** Kafes elemanının sınırı, içine konan universe'i keser. Kare blok altıgen elemana, altıgen demet kare elemana konabilir.
2. **Tam oturma koşulları** (doğrulama bunlarla "kesik konum" hesaplar):
   - Kenarı `a` olan, eksene hizalı kare, adımı `P_h` olan altıgen elemana ancak **a ≤ (√3 − 1)·P_h ≈ 0.732·P_h** ise sığar (iki yönelimde de).
   - Düz yüzden düz yüze ölçüsü `d` olan altıgen, kenarı `a` olan kare elemana ancak ölçüleri uygunsa sığar: 'y' prizmada genişlik d, yükseklik 2d/√3; ikisi de ≤ a olmalı.
3. **Yönelim:**
   - Altıgen bir demet/kafes, altıgen bir kafes elemanına ancak `ic.yonelim == ters(ust.yonelim)` ise oturur.
   - Demet (pin kafesi, zarf ≈ adım) için aynı yönelim **HATA**dır (ölçüldü: +1640 pcm). Diğer durumlarda kırpma analizi UYARI verir.
4. **Her kafesin `dis`i tanımlıdır;** her kök olmayan kabın `dis`i tanımlıdır. Tanımsız nokta = kayıp parçacık = HATA.

**R10 — Adlar.**
- Kafeslere ve yerleşim örneği hücrelerine `name = "g:<id>"` ve `"g:<id>#<i>"` yazılır.
- Katman ve yaprak hücrelerinin adları bugünkü gibi kalır.
- `guc` ve önizleme konumu buradan okur. Referans XML testleri yalnız `name` farkıyla bir kez güncellenir.

**R11 — Dizin.** `kur` bir `GeometriDizini` döndürür:
- `hucre → düğüm yolu`, `kafes → düğüm yolu`;
- `hucre → analitik kesit alanı` (ağaçtan; bölge ayrıştırmadan değil);
- `kesik konumlar`.

**R12 — Betik.** Betik ayrı bir kod yolu değildir. `kur.py`'deki gezinti, bir `Yapici` arayüzüne yazar:
- `NesneYapici` OpenMC nesnesi üretir;
- `BetikYapici` aynı çağrıları okunur Python satırı olarak yazar (`%r` kaçışlı; M3 fuzz testi).
- Bugünkü tamburlu betik hatası (§12, R-4) bu yapıda oluşamaz.

## 6. Şema sürümü 3 ve göç

**Zincir:** `cekirdek/goc.py`, `{1: goc_1_2, 2: goc_2_3}`, her adım saf bir işlevdir.
- **1→2 (M2):** `guc_dagilimi` yeni biçime çevrilir (bugün `tamamla` yapıyor, göçe taşınır); içerik değişmez. Bozuk dosya koruması: sayısal olmayan `surum`, eksik zorunlu bölüm → açık hata; yedek `*.json.bak` yazılır.
- **2→3:** `geometri: null`, `tamburlar: []` eklenir. **Diskteki kor değişmez.** Şablonlar çalışma anında genişletilir, yani göçün kendisi risksizdir.
- `surum > 3` → "Bu dosya daha yeni bir sürümle yazılmış" hatası verilir; sessizce alan düşürülmez.

**Modlar ve geçiş:**
- "Gelişmiş moda geç" işlemi: `geometri = genislet(spec)`, `kor = {"tur": "agac"}`, tamburlar kütüphaneye taşınır.
- Geçiş tek yönlüdür; geri al/yinele ile dönülür (açık soru 1).
- Şablon modunda `genislet` düğümlere `_kaynak` (form alanı yolu) notu ekler; doğrulama mesajları böylece forma işaret eder. `_kaynak` diske yazılmaz.

**Genişletme kuralları** (`geometri.genislet(spec) -> dict`, girdi değişmez):

| `kor.tur` | `kok.kesit` | `kok.ic` | `halkalar` | Yerleşim / grup |
|---|---|---|---|---|
| `tek_cubuk` | dikdörtgen `[adim, adim]` | çubuk bileşeni | — | — |
| `tek_plaka` | dikdörtgen `[n(2z+e)+(n+1)k, G+2y]` | plaka bileşeni | — | — |
| `tek_demet` (kare demet) | dikdörtgen `[P·nx, P·ny]` | demet bileşeni | yansıtıcı açıksa `[{kalinlik}]` | — |
| `tek_demet` (altıgen) | altıgen, yönelim = demet yönelimi, apotem = (n−1)P√3/2 + P/2 (kılıflıysa dış ölçü/2) | demet bileşeni | aynı | — |
| `kare_kafes` | dikdörtgen `[P·nx, P·ny]` | kare kafes, `dis` = yansıtıcı malzemesi ya da `bosluk` | yansıtıcı açıksa `[{kalinlik}]` | — |
| `altigen_kafes` | `kafes_zarfi` | altıgen kafes (kor yönelimi) | yansıtıcı açıksa `[{dis: altıgen, yönelim = kor yönelimi, apotem = zarf_apotemi + kalınlık}]` | — |
| `kuresel` | küre r₁ | malzeme k₁ | `[{dis: küre r_i, icerik: k_i}]`, i ≥ 2 | — |
| `tamburlu` | silindir `kor_yaricap` | dolgu (türü çözülmüş düğüm) | `[{kalinlik, icerik: yansıtıcı, yerlesimler: [...]}]` (yansıtıcı zorunlu) | tambur sayısı > 0 ise halka yerleşimi + `tamburlar` grubu |

**Ortak kurallar:**
- **Eksenel:** katmanlama açıksa `ic = {"tur": "eksenel", "icerik": <ic>, "katmanlar": [...]}` ve `kok.yukseklik = null`; değilse `kok.yukseklik = kor.yukseklik`.
- **Sınır:** `sinir` aynen taşınır; kürede yalnız `yan`.
- **Dolgu adları:** bugünkü `_universe_uret` sırasıyla çözülüp açık düğüm olarak yazılır.

**Tam örnekler:**

`tek_cubuk` (adım 1.26, 2B):
```json
{"kok": {"tur": "kap", "id": "kok", "kesit": {"sekil": "dikdortgen", "boyut": [1.26, 1.26]},
         "ic": {"tur": "bilesen", "ad": "yakit_cubugu"}, "yerlesimler": [], "halkalar": [],
         "yukseklik": null, "sinir": {"yan": "reflective", "alt": "reflective", "ust": "reflective"}},
 "parcalar": [], "gruplar": []}
```

`tek_plaka` (örnek değerlerle: 18 plaka, et 0.051, zarf 0.038, kanal 0.295, genişlik 6.0, yan levha 0.45):
```json
{"kok": {"tur": "kap", "id": "kok", "kesit": {"sekil": "dikdortgen", "boyut": [7.891, 6.9]},
         "ic": {"tur": "bilesen", "ad": "mtr_eleman"}, "yerlesimler": [], "halkalar": [],
         "yukseklik": null, "sinir": {"yan": "reflective", "alt": "reflective", "ust": "reflective"}},
 "parcalar": [], "gruplar": []}
```

`tek_demet`, altıgen (`sfr_altigen.json`: adım 0.9, 7 halka, 'y', kılıfsız, yansıtıcı kapalı; apotem = 6·0.9·√3/2 + 0.45):
```json
{"kok": {"tur": "kap", "id": "kok",
         "kesit": {"sekil": "altigen", "yonelim": "y", "apotem": 5.1265},
         "ic": {"tur": "bilesen", "ad": "demet_hex"}, "yerlesimler": [], "halkalar": [],
         "yukseklik": null, "sinir": {"yan": "reflective", "alt": "reflective", "ust": "reflective"}},
 "parcalar": [], "gruplar": []}
```

`kare_kafes` + eksenel (`pwr_ceyrek_kor.json`):
```json
{"kok": {"tur": "kap", "id": "kok", "kesit": {"sekil": "dikdortgen", "boyut": [128.52, 128.52]},
  "ic": {"tur": "eksenel", "id": "kor_eksen",
    "icerik": {"tur": "kafes", "id": "kor_kafesi", "sekil": "kare", "adim": 21.42, "boyut": [6, 6],
      "harita": ["AAABss", "AABBss", "ABBsss", "BBssss", "ssssss", "ssssss"],
      "anahtar": {"A": {"tur": "bilesen", "ad": "demet_24"}, "B": {"tur": "bilesen", "ad": "demet_31"},
                  "s": {"tur": "malzeme", "ad": "su"}},
      "dis": {"tur": "malzeme", "ad": "bosluk"}},
    "katmanlar": [
      {"ad": "alt su", "yukseklik": 20.0, "icerik": {"tur": "malzeme", "ad": "su"}},
      {"ad": "aktif", "yukseklik": 200.0, "icerik": null},
      {"ad": "üst su", "yukseklik": 20.0, "icerik": {"tur": "malzeme", "ad": "su"}}]},
  "yerlesimler": [], "halkalar": [], "yukseklik": null,
  "sinir": {"yan": "reflective", "alt": "vacuum", "ust": "vacuum"}},
 "parcalar": [], "gruplar": []}
```
(Sınır değerleri dosyadakilerle aynen taşınır; burada alt/üst örnek olarak yazıldı.) Katmana özgü eşleme örneği: `{"ad": "üst kuşak", "yukseklik": 30.0, "icerik": null, "anahtar": {"A": "demet_24_ust"}}`.

`altigen_kafes` + yansıtıcı + eksenel (`vver1000_kor.json`; apotem = `zarf_apotemi(8, 23.6) + 20 = 176.6929`):
```json
{"kok": {"tur": "kap", "id": "kok", "kesit": {"sekil": "kafes_zarfi"},
  "ic": {"tur": "eksenel", "id": "kor_eksen",
    "icerik": {"tur": "kafes", "id": "kor_kafesi", "sekil": "altigen", "adim": 23.6,
      "halka_sayisi": 8, "yonelim": "x",
      "harita": ["RCCCCCCRCCCCCCRCCCCCCRCCCCCCRCCCCCCRCCCCCC", "ABAB…(36)", "BABA…(30)",
                 "ABAB…(24)", "BABA…(18)", "ABABABABABAB", "BABABA", "A"],
      "anahtar": {"A": {"tur": "bilesen", "ad": "tvs_a20"}, "B": {"tur": "bilesen", "ad": "tvs_b30"},
                  "C": {"tur": "bilesen", "ad": "tvs_c44"},
                  "R": {"tur": "malzeme", "ad": "yansitici_celik_su"}},
      "dis": {"tur": "malzeme", "ad": "bosluk"}},
    "katmanlar": [
      {"ad": "alt su", "yukseklik": 20.0, "icerik": {"tur": "malzeme", "ad": "su"}},
      {"ad": "aktif kor", "yukseklik": 355.0, "icerik": null},
      {"ad": "üst su", "yukseklik": 20.0, "icerik": {"tur": "malzeme", "ad": "su"}}]},
  "yerlesimler": [],
  "halkalar": [{"dis": {"sekil": "altigen", "yonelim": "x", "apotem": 176.6929},
                "icerik": {"tur": "malzeme", "ad": "yansitici_celik_su"}}],
  "yukseklik": null, "sinir": {"yan": "…", "alt": "…", "ust": "…"}},
 "parcalar": [], "gruplar": []}
```
(Harita dosyadan aynen kopyalanır; burada kısaltıldı. `genislet` apotemi tam duyarlıkla yazar.)

`kuresel` (örnek değerlerle, üç kabuk):
```json
{"kok": {"tur": "kap", "id": "kok", "kesit": {"sekil": "kure", "yaricap": 5.0},
         "ic": {"tur": "malzeme", "ad": "kaynak"}, "yerlesimler": [],
         "halkalar": [{"dis": {"sekil": "kure", "yaricap": 10.0}, "icerik": {"tur": "malzeme", "ad": "polietilen"}},
                      {"dis": {"sekil": "kure", "yaricap": 30.0}, "icerik": {"tur": "malzeme", "ad": "beton"}}],
         "yukseklik": null, "sinir": {"yan": "vacuum"}},
 "parcalar": [], "gruplar": []}
```

`tamburlu` (`tamburlu_kor.json`):
```json
{"kok": {"tur": "kap", "id": "kok", "kesit": {"sekil": "silindir", "yaricap": 16.0},
  "ic": {"tur": "malzeme", "ad": "u10mo"}, "yerlesimler": [],
  "halkalar": [{"kalinlik": 12.0, "icerik": {"tur": "malzeme", "ad": "berilyum"},
    "yerlesimler": [{"ad": "tamburlar", "mod": "halka", "sayi": 8, "merkez_yaricap": 21.5,
                     "baslangic_acisi": 0.0, "icerik": {"tur": "bilesen", "ad": "tambur"},
                     "bakis": {"tur": "merkez", "merkez": [0.0, 0.0]}}]}],
  "yukseklik": 45.0, "sinir": {"yan": "vacuum", "alt": "vacuum", "ust": "vacuum"}},
 "parcalar": [],
 "gruplar": [{"ad": "tamburlar", "tur": "donme", "deger": 180.0, "uyeler": ["tamburlar"]}],
 "_uretilen_tanimlar": {"tamburlar": [{"ad": "tambur", "yaricap": 4.0, "govde_malzeme": "berilyum",
   "emici_malzeme": "b4c", "emici_ic_yaricap": 2.6, "emici_aci": 120.0}]}}
```
Şablon modunda üretilen tambur tanımı `_uretilen_tanimlar`da kalır; ad çakışırsa `tambur_2` olur. `kriter_lct008` (tambur sayısı 0, dolgu 93×93 kare demet) yerleşimsiz ve grupsuz genişler. Bu, **kafesin silindirle kırpılmasının** mevcut kanıtıdır.

## 7. Tüketici API'leri

**G-1 genel API** (`cekirdek/geometri/__init__.py`). G-1 birleşince **dondurulur**; G-2 ve G-3 yalnız bunu kullanır:

```python
def model(spec: dict) -> GeometriModeli            # şablon/ağaç -> normalize edilmiş, dondurulmuş model
def genislet(spec: dict) -> dict                    # saf; §6
def yapisal_denetim(spec: dict) -> list[Bulgu]      # tür/alan/başvuru/döngü/derinlik (kurulum önkoşulu)
def kur(spec, nesneler, universeler) -> tuple[openmc.Universe, tuple[float, float], GeometriDizini]
def betik(spec, yazici: BetikYazici) -> tuple[float, float, dict[str, str]]
def gez(m: GeometriModeli) -> Iterator[Ziyaret]     # Ziyaret(yol, dugum, carpan, z_araligi, kesik, ust_yollar)
def icerik(m) -> dict[str, set[str]]                # uygunluk.geometri_icerigi ile AYNI biçim
def yukseklik(m) -> float | None
def eksenel_dilimler(m) -> list[Dilim]              # (z0, z1, katman adı, içerik adları)
def aktif_aralik(spec) -> tuple[float, float] | None
def hedef_araligi(spec, adlar: list[str]) -> tuple[float, float] | None   # cubuk_eksenel_aralik genellemesi
def hedef_yuksekligi(spec, adlar) -> float | None                        # guc_yuksekligi genellemesi
def sinir_bilgisi(m) -> SinirBilgisi                # yuzey: kare|altigen|silindir|kure|kirik; yan/alt/ust; periyodik_uygun
def sinir_kutusu(m) -> tuple[float, float]
def ic_olcusu(m) -> tuple[float, float]             # kök kesitinin kutusu (halkalar hariç) -> kaynak kutusu
def gruplar(m) -> tuple[Grup, ...]
def grup_degeri_yaz(spec, grup: str, deger: float) -> dict   # yeni spec; şablonda kor.tambur.donme'ye yazar
def basvurular(spec) -> list[Basvuru]               # (yol, tur, ad): malzeme_adini_degistir ve kullanilan_malzemeler için
def ad_degistir(spec, tur: str, eski: str, yeni: str) -> dict  # saf; malzeme/çubuk/demet/tambur/parça
```

- `GeometriModeli` dondurulmuş bir dataclass'tır: `kok`, `parcalar`, `gruplar`, `tanimlar`, `sablon`, `kaynaklar`.
- **Geçiş süresince uyumluluk:** `kurucu.kor_kur`, `aktif_eksenel_aralik`, `guc_yuksekligi`, `cubuk_eksenel_aralik` ve `kor_ic_olcusu` ince sarmalayıcı olarak kalır; G-2 sonunda silinir.
- **Gelişmiş modda yüksek sesle hata:** `sema.kor_yuksekligi(kor)` gelişmiş modda `AgacModuHatasi` fırlatır. Göç etmemiş bir okuyucu sessizce yanlış değer değil, testte hata üretir. Yeni ad: `sema.model_yuksekligi(spec)`.

| Tüketici | Değişiklik (sahip) | İmza |
|---|---|---|
| `uygunluk` | `geometri_icerigi` → `geometri.icerik`; `yan_yuzey` → `sinir_bilgisi().yuzey`; `sinir_secenekleri`: periodic yalnız en dış kesit dikdörtgen/altıgense ve sınıra değen delik yoksa; `kor_turleri` + `"agac"`; `gecerli_hedefler(spec, "grup_donme")` grup adları (G-2) | imzalar aynı |
| `dogrula/kor` | Şablon denetimleri kalır (form mesajları). Hata yoksa `dogrula/agac.agac_kontrol` çalışır; aynı konuyu ikisi bildirmez (G-2) | `agac_kontrol(spec) -> list[Bulgu]` |
| `tukenme`, `tukenme_hacim` | `_kor_sayimi`, `dogrudan_yerlesim`, tambur emici hacmi → `geometri.hacim`. `ornek_hacmi` önce `GeometriDizini.hucre_alani`, sonra bölge ayrıştırması. Kırpılan örnek → `KESIN_DEGIL` → stokastik (G-2) | `hacim.analitik(m, ad) -> HacimKaydi`; `hacim.ornek_sayisi(m, ad) -> int` |
| `guc`, `guc_kor` | Anahtar = yol üstündeki her kafes düzeyinin indeksi + her çok örnekli yerleşimin `(ad, i)`'si (`g:` adlarından). `guc_kor`un geometriden çıkarımı eski koşular için yedek kalır. Kesik çubuk F_ΔH'ye girmez, ayrıca sayılır (G-2) | `dizin.konum_anahtari(satir, geometri) -> tuple` |
| `tarama`, `kritik_arama` | Yeni türler `grup_donme`, `grup_daldirma` (hedef = grup). `tambur_donme` takma addır (tek dönme grubu yoksa HATA "grup seçin"). Ağaçta `kor_adim` → hedef kafes `id`; `yansitici_kalinlik` → hedef halka yolu (G-2) | `parametre_uygula(spec, tur, hedef, deger, taban=None)` aynı |
| `ice_aktar` | OpenMC XML'den ağaç: kurucunun ürettiği desenler tanınır (eş merkezli pin, Rect/HexLattice, eş merkezli prizma/silindir halkaları, halka içinde ötelenmiş silindirler). Tanınmayan desende gerekçeli red (G-2) | `geometri.ice_aktar.xml_den(geo) -> tuple[dict | None, list[str]]` |
| `kaynak`, `rapor`, `ornek_bilgi` | Yükseklik, sınır ve tür okumaları API'ye geçer (G-2) | — |
| `kod_uret` | `cekirdek/kod_uret/` paketine bölünür; geometri bölümü `geometri.betik` (G-1) | `uret(spec, ...)` aynı |
| `onizleme` | `kurucu.kur` aynen. Tıklama → `openmc.lib` hücre kimliği → `dizin` → düğüm yolu; seçili düğümün hücreleri vurgulanır, kesik konumlar taranır (G-3) | `vurgula(yol)`, sinyal `dugum_secildi(yol)` |
| `sekme_kor`, `kor_altigen`, `izgara`, `guc_harita` | Sihirbaz + gelişmiş editör; çok düzeyli karışık harita çizimi (G-3) | — |

## 8. Doğrulama kuralları

**HATA (kurulum/koşu engellenir):**
1. Bilinmeyen düğüm türü, eksik zorunlu alan, yanlış türde değer.
2. Tanımsız başvuru (malzeme, bileşen, parça, grup üyesi, `kafes_konumu.kafes`).
3. Belirsiz ad (aynı ad iki kütüphane bölümünde).
4. Döngü: parça kendini içeriyor. Derinlik 10 düzeyden fazla.
5. Kafes: harita boyutu ya da halka uzunluğu tutmuyor; tanımsız harf; `dis` eksik (R3b hariç); adım ≤ 0.
6. Kap: halka `dis` kesiti öncekini kapsamıyor; kalınlık ≤ 0; `kafes_zarfi` + `kalinlik`; `kafes_zarfi` kök dışında ya da altıgen olmayan kafeste; kök olmayan kapta `dis` yok; kökte `dis` var.
7. Yerleşim: delik sahip bölgeden taşıyor (iç sınıra, halkanın dış sınırına ya da kafes zarfına değiyor); iki delik örtüşüyor (bugünkü `tambur.geometri_kontrol`un genel hâli); merkezde "kora bakan" yön tanımsız; daire dışı delik döndürülüyor; `kafes_konumu` deliği konum hücresinden taşıyor.
8. Eksenel: 2B modelde yığın; kök dışı yığının toplamı model yüksekliğine eşit değil; kökte hem `yukseklik` hem yığın farklı toplamlı; katman `anahtar`ı kafes olmayan içerikte.
9. Kontrol çubuğu 2B modelde (bugünkü kural).
10. Altıgen demet, altıgen kafes elemanında aynı yönelimle (bugünkü kural).
11. `malzeme` düğümünde `donusum`; bir üye aynı türden iki grupta; grup türü ile üye türü uyuşmuyor.
12. Sınır: uygun olmayan yüzeyde periodic (bugünkü `sinir_secenekleri` kuralları, `sinir_bilgisi` üzerinden); `malzemeleri_ayir` açıkken kesik yakıt örneği (örnek hacmi kesin değil).

**UYARI:**
1. **Kesik konum:** kafes elemanı ya da bileşen üst bölgeyle kırpılıyor (sayı ve ilk 5 konum yazılır). Hacim stokastiğe düşer; güç haritasında "kesik" etiketi.
2. Kesik çubuk (pin, üst hücre sınırıyla kesiliyor).
3. Aynı içerikli iki satır içi alt ağaç ("parçaya çevirin": distribcell bölünür).
4. İç içe derinlik 6'dan fazla (izleme yavaşlar); bir bölgede 50'den fazla delik (hücre arama yavaşlar).
5. Kök içinde `bosluk` bölge.
6. Tek üyeli grup; boş grup.
7. 2B modelde tambur (bugünkü not).
8. Güç hedefi yalnız kesik konumlarda.

**BİLGİ:**
- tamamen gizli konum (delik altında);
- kullanılmayan tanım;
- yok sayılan `kafes.dis` (R3b);
- 0 cm katman atlandı;
- grup üyesi çubuğun kendi daldırma değeri yok sayılıyor.

**Geometri yoklaması (M1, G-2):**
- `nokta_yoklama(geo, n=20000, tohum)`: her noktada ulaşılan her universe'te kaç hücrenin noktayı içerdiğini sayar. 0 ise boşluk, 1'den fazlaysa örtüşme; ilk 5 nokta düğüm yoluyla raporlanır.
- İsteğe bağlı "Derin doğrulama": kısa `openmc --geometry-debug` koşusu.
- Kasıtlı örtüşen ve kasıtlı boş modeller test fikstürüdür (önce kırmızı, sonra yeşil).

**Mevcut denetimlerin yeri:**
- *Kalanlar:* tek çubukta dış çap > adım, tamburlu, küresel ve kare/altıgen harita denetimleri şablon düzeyinde kalır (form mesajı).
- *Genelleşenler:* ağaçtaki karşılıkları (bileşen sığması, yerleşim sığması/örtüşmesi, halka kapsama, kafes) G-2'de yazılır; aynı konu iki kez bildirilmez.
- *Değişmeyenler:* sınır ve periodic kuralları, `_sonsuz_ve_2b` ve `_karisik_katmanlar` `sinir_bilgisi` ve `eksenel_dilimler` üzerinden aynen korunur.
- *Silinen:* `_kurulmayan_alanlar` yalnız şablonda anlamlıdır; gelişmiş modda yoktur.

## 9. Eşdeğerlik kapısı (G-1 kabulü)

**Düzenek:**
- G-1'in ilk işi bugünkü `kor_kur` ve yardımcılarını `cekirdek/_eski_kurucu.py` olarak **dondurmaktır** (davranış değişmez; yalnız test kullanır).
- Test: `testler/test_geometri_esdegerlik.py`. Parametreler:
  - `ornekler/*.json` (**27 örnek**; plandaki 21 eski sayı);
  - sentetik fikstürler: her şablon × {2B, 3B, eksenel, katman anahtarı, yansıtıcı açık/kapalı, kılıf, kontrol çubuğu, tambur sayısı 0 ve 8, her sınır türü, silindirle kırpılan kafes}.

**A — Nokta parmak izi (zorunlu, %100 eşit):**
- Noktalar:
  - sınır kutusunda sabit tohumla rastgele noktalar (hızlı süit 2·10³, yavaş süit 10⁵);
  - her kafes elemanının köşe ve yüz ortalarının ±10⁻⁶ cm komşuları;
  - her silindir ve düzlem üzerinde 8 nokta ±10⁻⁶ cm.
- Her nokta için karşılaştırılan (kimlikten bağımsız):
  - `(malzeme adı | None, sahip bileşen/kap yolu, kafes indeksleri dizisi, öteleme dizisi (10⁻⁹ yuvarlanmış), dönme dizisi, yaprak hücrenin distribcell örnek sırası)`.
  - Örnek sırası = `hucre.paths.index(yol)` (C++ sırasıyla aynı; TH10). Hızlı yol `openmc.lib.find_cell`, yedek yol `tukenme_hacim.nokta_yolu`.

**B — Yapı (zorunlu):**
- hücre, universe ve kafes sayıları;
- her malzemenin `num_instances`'ı;
- `sinir_kutu`, kaynak kutusu (`ic_olcusu`), aktif aralık (göreli fark ≤ 10⁻¹²);
- yüzey sayısı yalnız raporlanır (havuz daha az yüzey üretebilir).

**C — Hacim:** `tukenme.hacimler(spec)` eski ve yeni yolda aynıdır (göreli fark ≤ 10⁻¹²).

**D — Betik:** betik ile kurucu XML'i, `id` yeniden numaralandırılıp `name` öznitelikleri ayıklanarak kanonik biçimde aynıdır (mevcut betik eşdeğerliği testleri genişletilir).

**E — Fizik (yavaş süit):**
- k∞ çıpası 1.3570 ± 0.0020 ve Godiva değişmez.
- Seçilmiş 6 örnekte aynı tohumla |Δk| ≤ 2σ. Aynı yapıda k'nın bit düzeyinde aynı çıkması hedeflenir ve gözlenir, ama kabul ölçütü değildir.

**F — Süre ve süit:** hızlı süit en çok %10 yavaşlar; süit aynı sayıda geçer.

**Kapı sonrası:** kapı geçince `_eski_kurucu.py` silinir. A–C'nin çıktıları örnek başına özetlenip `testler/veri/geometri_parmak_izi.json`a yazılır; kapı eski kurucu olmadan da çalışmaya devam eder.

**Yeni düzenek ölçümleri (G-1):**
- (a), (b), (c) kurulur; yapısal ve geometrik denetimden temiz geçer (beklenen UYARI'lar hariç); kısa koşu yapılır.
- **Yönelim ölçümleri:** kare kafes → altıgen eleman, altıgen demet → kare eleman ve altıgen → altıgen (iki yönelim). Eleman merkezi ile her yüz normali yönünde 0.99 apotemde beklenen alt indeks ölçülür; çizim kaydedilir.
- **Bakış ölçümü:**
  - Kapsam: her mod (`halka`, `liste`, `kafes_konumu`) × üst dönme {0°, 60°} × D {0°, 90°, 180°}.
  - Ölçüm noktası: c + ½(r_iç + R)·û. D = 0'da û kora doğru, D = 180'de dışa doğru → emici; karşı yön → gövde. D = 90'da yan.
  - `halka` modunda ψ bugünkü formülle bit düzeyinde aynı olmalı.

## 10. Arayüz eskizi (G-3)

**Geometri sekmesi, sihirbaz görünümü** (bugünkü Kor sekmesinin yerini alır):

```
┌─ Geometri ─────────────────────────────────────────────────────────────────┐
│ Düzenek şablonu: [Tamburlu kompakt kor                           ▼]        │
│   Tek çubuk · Tek plaka · Tek demet · Kare kafesli tam kor ·               │
│   Altıgen kafesli tam kor · Küresel · Tamburlu kompakt kor ·               │
│   Kare çekirdek + altıgen halka · Altıgen çekirdek + tambur halkası ·      │
│   Kafesli çekirdek + tamburlu yansıtıcı                                    │
├──────────────────────────────────────┬─────────────────────────────────────┤
│ Kor dolgusu     [u10mo          ▼]   │                                     │
│ Kor yarıçapı    [ 16.000 ] cm        │        (xy kesit önizlemesi)        │
│ Yansıtıcı       [ 12.000 ] cm [Be ▼] │                                     │
│ Tambur tanımı   [tambur ▼] [Düzenle] │                                     │
│ Tambur sayısı   [ 8 ]  merkez [21.5] │                                     │
│ Dönme (grup)    [180.0]° ═══════○    │  [xy|xz]  z = [ 0.0 ] cm            │
│ Yükseklik       [ 45.0 ] cm          │                                     │
│ Eksenel katmanlar  [+][−][▲][▼]      │                                     │
│ Sınır  yan[Vakum▼] alt[Vakum▼] üst[▼]│                                     │
├──────────────────────────────────────┴─────────────────────────────────────┤
│ [ Gelişmiş geometriye geç … ]        Doğrulama: 0 hata · 0 uyarı           │
└────────────────────────────────────────────────────────────────────────────┘
```

"Gelişmiş geometriye geç" bir onay penceresi açar: "Şablon ağaca dönüştürülecek. Sonra sihirbaz kapanır; Geri Al ile dönebilirsiniz."

**Gelişmiş görünüm** (ağaç + kesit + özellik formu):

```
┌─ Geometri (gelişmiş) ──────────────────────────────────────────────────────┐
│ [+ Düğüm ▼][+ Halka][+ Yerleşim][Parçaya çıkar][Sarmala][Sil][▲][▼] ↶ ↷    │
├──────────────────────┬──────────────────────────────┬──────────────────────┤
│ Ağaç                 │ Kesit [xy|xz] z=[0.0] [Hızlı]│ Özellikler           │
│ ▾ ■ Kök kap (altıgen)│                              │ Yerleşim             │
│   ▾ İç: kafes blok.. │        ⬡⬡⬡⬡⬡                 │  Ad    [tambur_hal.] │
│      B → celik_blok  │      ⬡⬡▓▓▓⬡⬡                 │  Mod   (●) Halka     │
│      . → dış         │     ⬡⬡▓▓▓▓▓⬡⬡  ○ ← seçili    │        ( ) Liste     │
│      dış: su         │      ⬡⬡▓▓▓⬡⬡     (vurgulu)   │        ( ) Kafes kon.│
│   ▾ Yerleşim: kare_ç │        ⬡⬡⬡⬡⬡                 │  Sayı  [ 6 ]         │
│      ▸ kafes 5×5     │  ▒ = kesik konum (uyarı)     │  Merkez yarıçapı     │
│   ▾ Halka 1 (20 cm)  │                              │        [ 36.000 ] cm │
│      su              │  tıklama → ağaçta seçer      │  Başlangıç [30.0]°   │
│      ▸ Yerleşim: tam │                              │  İçerik [tambur_b4c▼]│
│ ▸ Parçalar (1)       │                              │  Kesit  (doğal)      │
│ ▸ Gruplar (1)        │                              │  Kora bakış          │
│                      │                              │  (●) merkeze (0, 0)  │
│                      │                              │  ( ) sabit [  0.0]°  │
│                      │                              │  Grup  [tamburlar ▼] │
│                      │                              │  Ofset [  0.0]°      │
├──────────────────────┴──────────────────────────────┴──────────────────────┤
│ ⚠ 2. halkada 12 kesik blok (kare delik)   ⓘ 7 gizli konum   [Git] [Yokla]  │
└────────────────────────────────────────────────────────────────────────────┘
```

**Etkileşim kuralları:**
- **Ağaç:**
  - Sürükle-bırak yalnız uyumlu yuvaya yapılır; bırakma hedefi vurgulanır. Sağ tık aynı eylemleri gösterir.
  - "Parçaya çıkar", seçili alt ağacı adlandırıp başvuruya çevirir. "Sarmala", seçiliyi yeni bir kabın `ic`ine alır.
- **Kesit:** fare tekerleğiyle yakınlaştırma; seçili düğümün hücreleri renkli, diğerleri soluk; kesik konumlar taralı; xz'de katman sınırları kesikli çizgi.
- **Form:**
  - Her sayı kutusu birimlidir (cm, °).
  - Kafes seçilince harita düzenleyicisi açılır (kare: bugünkü ızgara; altıgen: `kor_altigen`). Harf paletinde "." = dış.
- **Gruplar formu:** ad, tür (Dönme/Daldırma), değer kaydırıcısı, üye onay listesi.
- **Geçmiş:** her ağaç işlemi `duzenle.py` saf işlevinin döndürdüğü yeni ağaçtır; `pencere/gecmis.py` onu yığar.
- Yeni kodda her QLayout bir widget'a bağlıdır.

**Sihirbazın üç yeni şablon formu:**
- *Kare çekirdek + altıgen halka:* çekirdek demetleri + n×n harita; blok adımı; halka sayısı; blok içeriği; dış yansıtıcı.
- *Altıgen çekirdek + tambur halkası:* demet; kor halka sayısı; yansıtıcı apotemi; tambur tanımı, sayısı, merkezi, başlangıç açısı.
- *Kafesli çekirdek + tamburlu yansıtıcı:* kare kafes; yansıtıcı yarıçapı; tambur alanları.

## 11. G-1..G-4 iş kırılımı ve sahiplik

Sıra: **G-0 → KAPI G-A → G-1a → G-1b → (G-2 ‖ G-3) → G-4 → birleşik inceleme + profesör denetimi.** Aynı anda en çok 2 ajan çalışır.

| Ajan | Sahip olduğu dosyalar | İş | Kabul |
|---|---|---|---|
| **G-1a** | `cekirdek/goc.py` (yeni), `sema.py`, `geometri/{__init__, sema, genislet, kesit, yerlesim}.py`, `_eski_kurucu.py`, `testler/{test_goc, test_geometri_genislet, test_geometri_esdegerlik}.py`, `testler/geometri_ortak.py` | M2 zinciri, v3 alanları, şema + normalize + yapısal denetim, genişletici, eşdeğerlik düzeneği (henüz eski = eski) | göç testleri; `genislet` 27 örnekte hatasız ve saf (girdi değişmez) |
| **G-1b** | `geometri/{kur, yapici, dizin, gez, eksenel}.py`, `kurucu.py` (yalnız `kor_kur` + sarmalayıcılar), `kod_uret/` (bölünmüş), `altigen_kor.py`, `tambur.py`, `testler/{test_geometri_agac, test_geometri_yonelim}.py` | kurucu ve betik yapıcıları, dizin, R1–R12, M3 fuzz | §9 A–F; (a)(b)(c) kurulur; yönelim ve bakış ölçümleri; dosyalar ≤ 800 satır |
| **G-2** | `dogrula/{kor, agac (yeni), geometri, eksenel, referans, __init__}.py`, `uygunluk.py`, `tukenme.py`, `tukenme_hacim.py`, `guc.py`, `guc_kor.py`, `tarama.py`, `kritik_arama.py`, `ice_aktar.py`, `kaynak.py`, `rapor.py`, `rapor_sablon/grafik.py`, `ornek_bilgi.py`, `geometri/{hacim, yoklama, ice_aktar}.py`, `testler/test_geometri_tuketici.py`; son adımda `kurucu.py` sarmalayıcılarını silme izni | §7 ve §8; ağaç modu okuyucuları | Dalga 2'nin güç, tükenme hacmi ve tarama testleri ağaçla aynı; içe aktarma gidiş-dönüşü: her örnek dışa aktarılıp içe aktarılınca §9-A geçer; `AgacModuHatasi` hiçbir testte tetiklenmez |
| **G-3** | `arayuz/geometri/` (yeni), `geometri/duzenle.py`, `arayuz/{sekme_kor, kor_altigen, onizleme, izgara, guc_harita, baslangic, sekme_ayar}.py`, `arayuz/analiz/adlar.py`, `arayuz/pencere/{model_islemleri, gecmis}.py`, `arayuz/cubuk/*` (yalnız `kor` okumaları), `testler/test_geometri_ui.py` | §10 | kabuk testleri; her şablon sihirbazdan kurulur; ağaç işlemleri geri alınabilir |
| **G-4** | `ornekler/` (3 yeni JSON), `docs/ORNEKLER.md`, `testler/test_geometri_fizik.py` | 3 örnek + plandaki 5 fizik kabulü | plan ölçütleri; süre ve k kaydedilir |

**Çakışma riskleri ve kurallar:**
- `geometri/__init__.py` G-1 sonunda dondurulur; değişiklik gerekirse orkestratör üzerinden istenir.
- `uygunluk.py` G-2'nindir. G-3 yalnız çağırır; G-2 imzaları korur.
- `kurucu.py` sarmalayıcı silme işi G-2'nin son işidir ve G-3 birleştikten sonra yapılır.
- `.po` çeviri dosyalarını ajanlar düzenlemez; orkestratör birleştirmeden sonra yeniden üretir.
- `testler/geometri_ortak.py` G-1'indir; diğerleri yalnız okur.
- `sema.py` yalnız G-1'dedir; `malzeme_adini_degistir` ve `kullanilan_malzemeler` `geometri.basvurular` üzerinden ağacı da gezer. Bugünkü "yeni alan eklenirse buraya da ekle" notu böylece kapanır.

## 12. Riskler

| No | Risk | Önlem |
|---|---|---|
| R-1 | R3b (altıgen konum hücreleri) özel yolu eşdeğerlikte en kırılgan yer | `altigen_kor_hucreleri` değiştirilmeden kullanılır; vver1000 ve sfr_met1000 örnekleri nokta parmak iziyle kapıdadır |
| R-2 | Kayan nokta boşlukları/örtüşmeleri (halka ve delik sınırları) | yüzey havuzu (aynı yüzey tek nesne); ±10⁻⁶ komşu noktaları; M1 yoklaması |
| R-3 | Distribcell sırası değişirse tükenme örnek hacimleri ve güç anahtarları yer değiştirir (toplam denetimi yakalamaz) | §9-A örnek sırası karşılaştırması + TH10 |
| R-4 | **Mevcut hata:** `kod_uret` tamburlu dalı eksenel katmanları betiğe yazmıyor (`_hucreler = [Cell(fill=ic, region=-kor_silindir…)]`), kurucu yazıyor. Tamburlu + eksenel modelde betik farklı model kurar; iki tamburlu örnekte eksenel olmadığı için testler görmüyor | G-1b'de betik tek gezintiden üretilir (R12); kapıda bu fikstür için §9-D eski betiğe karşı değil kurucuya karşı karşılaştırılır. Hata raporda "düzeltildi" olarak yazılır |
| R-5 | Tamburlu dalda betiğin sınır varsayılanı `vacuum`, kurucununki `reflective` (yalnız eksik sözlükte etkili) | tek gezinti ile ortadan kalkar |
| R-6 | Derin iç içe yapı ve çok sayıda delik izlemeyi yavaşlatır | satır içi kurma kuralı (R1), derinlik ve delik UYARI'ları, §9-F süre ölçütü |
| R-7 | `g:` adları referans XML'lerini değiştirir | tek seferlik, gözden geçirilmiş güncelleme; §9-D `name`i ayıklar |
| R-8 | Göç etmemiş `spec["kor"]` okuyucusu gelişmiş modda sessizce yanlış çalışır | `AgacModuHatasi`; gelişmiş modda bir örnekle bütün süit; G-sonunda AST denetimi (izinli modüller dışında `["kor"]` okuması yok) |
| R-9 | Arayüz kapsamı kayar (tam CSG editörüne dönüşür) | beş kullanıcı düğümü, ham hücre İ-listesinde; sihirbaz önce |
| R-10 | Kırpılan konumlarda analitik hacim ve güç anlamsızlaşır | kesik konumlar UYARI + stokastik hacim + F_ΔH dışı; `malzemeleri_ayir` ile HATA |
| R-11 | Aynı alt ağacın satır içi kopyaları distribcell'i böler | "parçaya çevir" UYARI'sı + editörde kopyala yerine parça önerisi |

## 13. Planla ayrıldığım noktalar ve nedenleri

1. **`yerlestirme` düğüm değil, bölgenin alt listesi.** OpenMC'de yerleşim, belli bir bölge hücresinden delik oymaktır; o bölgeye aittir. Ayrı düğüm olsaydı "içi nedir, hangi bölgeyi oyar" sorusu belirsiz kalırdı. Delik şekli (`kesit`) eklendi: kare çekirdeği altıgen kafesin içine koymak da, tambur da aynı mekanizmayla çözülüyor.
2. **`eksenel` ayrı düğüm türü; `donusum` düğüm değil, yuva özelliği.** Plan, eksenel yığını "her düğüme uygulanan bir özellik" olarak tanımlıyordu. Ama katmanların içerikleri farklıdır, yani yığın çocuk taşıyan bir kaptır. Dönüşüm tek bir hücre özelliğidir; ayrı düğüm olsaydı ağaç gereksiz derinleşirdi.
3. **Ağaç diskte yalnız gelişmiş modda saklanır.** Şablon modunda çalışma anında genişletilir. 2→3 göçü dosyaya dokunmaz (risk sıfıra iner); sihirbaz formu tek gerçek kaynak olarak kalır. Plandaki "tek kurucu" ilkesi korunur: tüketiciler her zaman ağacı görür.
4. **Adlandırılmış parçalar eklendi.** Aynı alt ağacın çok kez kullanımında tek Universe gerekir (distribcell, tükenme). Plan bunu ele almıyordu.
5. **`tamburlar` kütüphanesi ve değeri tek yerde tutan gruplar.** Plan `grup.donme` diyordu ama değerin nerede tutulduğunu belirtmiyordu. Değer grupta, üyelik grupta; bir üye aynı türden tek grupta.
6. **`kafes_zarfi` kesiti ve R3b.** Bugünkü altıgen tam kor HexLattice değil, konum hücreleridir (kırık çizgi sınırı, vadileri dolduran yansıtıcı). Eşdeğerlik için bu yol ağaçta açıkça adlandırılmalıydı.
7. **Eşdeğerlik "hücre yolu aynı" yerine kimlikten bağımsız parmak izi.** Ham hücre kimlikleri yapı aynı olsa bile değişebilir. Örnek sırası ayrıca karşılaştırılır, kapı eski kurucu silindikten sonra parmak izi dosyasıyla sürer.
8. **"Kora bakan yön" genel formülü.** Halka modunda bugünkü formül bit düzeyinde korunur; liste ve kafes konumu modunda atan2 kullanılır. "Kafes konumu" deliği kafes konum merkezlerinden oyar (plan belirsizdi).
9. **Sayılar ve sahiplik güncellendi.** 21 yerine 27 örnek; şema sürümü bugün 1 (M2 yok), bu yüzden G-1a önce 2'yi sonra 3'ü yapar. Planda sahipsiz kalan tüketiciler (`tukenme`, `kaynak`, `rapor`, `dogrula/eksenel`, `dogrula/referans`, `kor_altigen`, `guc_harita`…) dağıtıldı. G-1 a/b olarak bölündü.
10. **`duzenle.py` G-3'e verildi.** Saf çekirdek kodu ama yalnız arayüz kullanıyor; G-1'i küçük tutar.

## 14. Kullanıcıya sorulacak açık sorular

1. Gelişmiş moda geçiş **tek yönlü** olsun mu? Ağaç düzenlendikten sonra sihirbaz kapanır, dönüş yalnız Geri Al ile olur.
2. **Kesik (kırpılan) blok/çubuk** UYARI mı kalsın, HATA mı olsun? Öneri: UYARI; hacim stokastiğe düşer, güç haritasında ayrı işaretlenir, cubuk cubuk yanmada HATA verilir.
3. Hedef (a) düzenekte altıgen bloklar **yansıtıcı blok** (çelik + su kanalı) mı olsun, **yakıt** (altıgen demet) mı? Aklınızda belirli bir reaktör ya da kriter var mı?
4. **Yüz başına yan sınır koşulu** (çeyrek kor: iki yüz yansıtıcı, iki yüz vakum) Dalga G'ye girsin mi, İ-listesinde mi kalsın? Bugün `pwr_ceyrek_kor` dört yüzü yansıtıcıyla yaklaşık kuruluyor.
5. Kontrol çubuğu bankaları için "her banka ayrı bir çubuk tanımı" (Kopyala ile) yeterli mi, yoksa aynı tanımın **konum başına farklı daldırılması** isteniyor mu? İkincisi yeni bir yerleşim alanı ve güç haritası anahtarı gerektirir.