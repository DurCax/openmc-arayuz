<a id="kavramlar"></a>
# 3. Kavramlar

Arayüzdeki her sayfa bir kavrama karşılık gelir ve kavramlar birbirinin içine yerleşir:
**malzeme → çubuk (ya da plaka) → demet → kor**. Gelişmiş modda bu zincir serbest bir
**geometri ağacına** dönüşür. Bu bölüm her kavramı bir çizimle anlatır ve sonda "hangi düzeneği
hangi düğümlerle kurarım" tablosunu verir. Kavramların JSON karşılıkları bölüm 4'te,
tasarım ayrıntıları [GEOMETRI_MODELI.md](../../GEOMETRI_MODELI.md)'dedir.

## 3.1 Model (spec)

Bir **model**, tek bir JSON dosyasıdır (`*.json`). Malzemeler, parçalar, demetler, geometri,
hesap ayarları, tally'ler, güç dağılımı ve tükenme ayarları bu dosyanın bölümleridir
(`malzemeler`, `cubuklar`, `plakalar`, `demetler`, `kor`, `geometri`, `ayarlar`, `tallyler`,
`guc_dagilimi`, `tukenme`, `calistirma`). Arayüz bu dosyayı düzenler; OpenMC modeli her koşuda
ondan yeniden kurulur. Tanımlayıcılar (adlar, `tur` değerleri) ASCII'dir; görünen açıklamalar
Türkçe olabilir.

## 3.2 Malzeme

Bir **malzeme** bileşimi (nüklid ya da element, atom ya da ağırlık oranıyla), yoğunluğu,
sıcaklığı ve gerekiyorsa termal saçılma verisi (S(α,β)) olan bir maddedir. Kütüphanedeki hazır
malzemeler (UO₂, su, Zircaloy-4, B₄C…) parametreleriyle saklanır: sıcaklığı ya da zenginliği
değiştirdiğinizde yoğunluk ve bileşim yeniden hesaplanır.

Her malzemenin bir **rolü** vardır (yakıt, soğutucu, moderatör, emici, yapısal, gaz); rol
bileşimden çıkarılır ve hangi taramaların, güç dağılımının ve tükenmenin sunulacağını belirler.
Ayrılmış ad `bosluk`, malzemesiz bölgeyi (void) gösterir.

## 3.3 Çubuk (pin) ve plaka

```
      yakıt çubuğu (yandan kesit)          hücre (adım p)
          ┌───────────────┐            ┌─────────────────┐
          │   ┌───────┐   │            │    ╭───────╮    │
          │   │ ┌───┐ │   │            │   │ ╭───╮ │    │
          │   │ │UO₂│ │ ← kılıf         │   │ │ ● │ │    │  ← su (en dış bölge
          │   │ └───┘ │   │            │   │ ╰───╯ │    │     hücreyi doldurur)
          │   └───────┘   │            │    ╰───────╯    │
          └───────────────┘            └─────────────────┘
       r₁ < r₂ < r₃ (içten dışa)           dış bölge yarıçapı < p/2
```

Bir **çubuk** (pin), eş merkezli **bölgelerden** oluşan bir hücredir: içten dışa yakıt, gaz
aralığı, kılıf ve hücrenin geri kalanını dolduran soğutucu. Kesit silindir, kare ya da altıgen
olabilir. Kontrol çubuğu ayrı bir türdür: yalnız 3B modelde, yukarıdan **daldırılır**
(%0 çekilmiş, %100 tam dalmış). **Plaka elemanı** (MTR) ise düz plakalardan oluşan bir kutudur.

## 3.4 Demet (assembly)

```
   kare demet (17×17, adım 1.26 cm)       altıgen demet (halka sayısı 4)
   y y y y y y y y y y ...                       ⬡ ⬡ ⬡ ⬡
   y y y y y k y y k ...                       ⬡ ⬡ ⬡ ⬡ ⬡
   y y y k y y y y y ...                     ⬡ ⬡ ⬡ ⬡ ⬡ ⬡
   ...                                      ⬡ ⬡ ⬡ ⬡ ⬡ ⬡ ⬡   ← merkez dahil 37 konum
   y = yakıt çubuğu, k = kılavuz boru       ...
```

Bir **demet**, çubukların bir **kafeste** (lattice) tekrarlanmasıdır. Kafes kare
(`RectLattice`) ya da altıgendir (`HexLattice`). Harita her konuma bir harf koyar; harf anahtarı
harfi bir çubuğa bağlar (arayüzde palet ile boyanır, harfler arka planda tutulur). Altıgen kafes
**halkalarla** tanımlanır (merkez = 1. halka) ve bir **yönelimi** vardır (`x` ya da `y`).
Altıgen demetin dış kılıfı (duct) isteğe bağlıdır.

## 3.5 Kor

```
   kare kor haritası (5×5)          tamburlu kor (kesit)
   . A B A .                        ╭──────── yansıtıcı kuşak ───────╮
   A B A B A                       │   ◐          ◐          ◐      │
   B A B A B   + yansıtıcı kuşak   │        ┌──────────┐            │
   A B A B A                       │   ◐    │   kor    │    ◐       │  ◐ = tambur
   . A B A .                       │        └──────────┘            │  (emici yay ◖)
   . = demet yok (su)               ╰────────────────────────────────╯
```

**Kor**, modelin en dış yapısıdır. Şablon (sihirbaz) modunda bir **kor türü** seçilir:

| Kor türü | Ne kurar |
|---|---|
| `tek_cubuk` | tek pin hücre (yansıtıcı sınırla k∞) |
| `tek_plaka` | tek plaka elemanı |
| `tek_demet` | tek demet (kare ya da altıgen) |
| `kare_kafes` | demetlerden kare kor haritası (+ yansıtıcı kuşak) |
| `altigen_kafes` | demetlerden altıgen kor haritası (+ yansıtıcı kuşak) |
| `tamburlu` | silindirik kor + yansıtıcı kuşak + kuşağa gömülü dönen tamburlar |
| `kuresel` | eş merkezli küresel kabuklar (Godiva tipi kriterler, zırhlama) |
| `agac` | gelişmiş geometri: serbest düğüm ağacı (aşağıda) |

**Kontrol tamburu**: yansıtıcı kuşağa gömülü, bir yayı emici kaplı dönen silindirdir.
**Dönme 0°** emici kora bakar (daldırılmış, en düşük k); **180°** emici dışa bakar (çekilmiş,
en yüksek k).

**Sınır koşulu** modelin dış yüzeyinde nötronun ne olacağını söyler: **vakum** (`vacuum`) kaçar,
**yansıtıcı** (`reflective`) aynadaki gibi döner (sonsuz tekrar; k∞), **periyodik** (`periodic`)
karşı yüzden girer, **beyaz** (`white`) rastgele yönde döner. Kare ve altıgen dış sınırda her
yüze ayrı koşul verilebilir (çeyrek kor simetrisi).

## 3.6 Eksenel katman ve yükseklik

```
   z ↑   ┌──────────────┐  üst yansıtıcı (su)        Üç ayrı yükseklik:
         ├──────────────┤  plenum                    - toplam model  = katman toplamı
         ├──────────────┤  üst blanket (doğal U)      - fisil aralık  = fisil katmanlar
         │              │                             - hedef çubuk aralığı
         │ aktif yakıt  │                               = o çubuğun bulunduğu katmanlar
         │              │
         ├──────────────┤  alt blanket
         └──────────────┘  alt yansıtıcı (su)
```

Model **2B** (sonsuz yükseklik; eksenel sızıntı yok), **3B tek bölge** ya da **3B katmanlı**
olabilir. **Eksenel katmanlar** alttan üste dizilir; her katmanın bir yüksekliği ve dolgusu
vardır (boş bırakılırsa korun ana dolgusu). Katmanlıyken modelin yüksekliği katmanların
toplamıdır. İç katman arayüzleri her zaman geçirgendir; sınır koşulu yalnız en alt ve en üst
yüzeye uygulanır.

## 3.7 Geometri ağacı (gelişmiş geometri)

Şablon türleri yetmediğinde — kare çekirdeği altıgen bloklarla sarmak, tamburu kare bir korun
yansıtıcısına koymak, karışık kafesler — model bir **düğüm ağacı** olarak kurulur. Kullanıcı beş
düğüm türü görür:

| Düğüm | Ne yapar | Örnek |
|---|---|---|
| `malzeme` | bir bölgeyi tek malzemeyle doldurur | su, `bosluk` |
| `bilesen` | kütüphanedeki bir tanımı (çubuk, plaka, demet, tambur, parça) kullanır | `demet_24` |
| `kafes` | kare ya da altıgen kafes; her konuma bir düğüm | kor haritası |
| `kap` | bir şekil (dikdörtgen, silindir, altıgen, küre) + eş merkezli **halkalar** + **yerleşimler** | kök kap, yansıtıcı halka |
| `eksenel` | z yönünde katman yığını | alt su / aktif / üst kuşak |

```
   Kök kap (altıgen, vakum sınır)
    ├─ İç: kafes "blok_kafesi" (altıgen, adım 30 cm)  B → celik_blok (parça)
    │      └─ Yerleşim "kare_cekirdek" (liste, kare delik) → kafes 5×5 demet
    └─ Halka 1 (20 cm su)
```

**Tanım ve kullanım.** Kütüphane bölümleri (çubuklar, demetler, tamburlar, parçalar) *tanımdır*;
ağaçtaki `bilesen` düğümü bir tanımın *kullanımıdır*. Aynı tanım kaç kez kullanılırsa
kullanılsın OpenMC'de tek bir universe kurulur — güç dağılımı (distribcell) ve tükenme bu
paylaşıma dayanır. Birden fazla yerde kullanılan bir alt ağaç bu yüzden **parçaya** çıkarılmalıdır.

**Yerleşim** (`yerlesim`), bir kap bölgesinden bir **delik** oyar ve içine bir düğüm koyar:
tamburlar, deney kanalları, kontrol çubuğu kanalları ve bir altıgen kafesin ortasındaki kare
çekirdek aynı mekanizmayla yerleşir. Üç mod vardır: `halka` (n örnek bir çember üzerinde),
`liste` (verilen konumlar), `kafes_konumu` (bir kafesteki belirli bir harfin konumları).
Yerleştirilen içeriğin ön yüzü kora bakar ("kora bakış").

**Grup**, birden çok yerleşimi ya da kontrol çubuğunu tek bir değerle sürer: `donme` grubu
tamburları birlikte döndürür, `daldirma` grubu kontrol çubuklarını birlikte daldırır. Tarama ve
kritik arama hedefi gruptur (`grup_donme`, `grup_daldirma`).

**Kesik konum.** Bir kafes elemanı onu içeren bölgenin sınırıyla kırpılıyorsa "kesik" sayılır:
geometri doğrudur ama analitik hacim hesaplanamaz (stokastiğe düşer) ve güç haritasında ayrı
işaretlenir. Bu bir **uyarıdır**; kare bir deliği altıgen kafesle sararken kaçınılmazdır.

Şablondan gelişmiş moda geçiş **tek yönlüdür** (dönüş yalnız Geri Al ile). Editörün bütün
formları: [4.5 Gelişmiş geometri editörü](04e-geometri-gelismis.md#geometri-gelismis).

<a id="karar-tablosu"></a>
## 3.8 Hangi düzeneği hangi düğümlerle kurarım

| İstediğiniz düzenek | Şablon (sihirbaz) | Gelişmiş ağaç | Örnek / ders |
|---|---|---|---|
| Tek pin hücre, k∞ | `tek_cubuk` | — | `ornekler/pwr_pinhucre.json` |
| Tek demet (kare/altıgen), k∞ | `tek_demet` | — | `ornekler/pwr_17x17.json`, [ders](05-dersler.md#ders-demet) |
| Kare tam kor + yansıtıcı | `kare_kafes` | — | `ornekler/pwr_smr_kor.json`, [ders](05-dersler.md#ders-tam-kor) |
| Çeyrek kor (iki yüz yansıtıcı, iki yüz vakum) | `kare_kafes` + yüz başına sınır | — | `ornekler/pwr_ceyrek_kor.json` |
| Altıgen tam kor (VVER, SFR) | `altigen_kafes` | — | `ornekler/vver1000_kor.json`, [ders](05-dersler.md#ders-altigen-kor) |
| Plaka elemanı / MTR koru | `tek_plaka` / `kare_kafes` | — | `ornekler/mtr_plaka.json`, `ornekler/mtr_kor.json` |
| Silindirik kor + tamburlu yansıtıcı | `tamburlu` | — | `ornekler/tamburlu_kor.json` |
| Kritik küre, zırh kabukları | `kuresel` (kabuklar JSON'dan) | — | `ornekler/godiva_kriter.json`, `ornekler/zirh_kure.json` |
| Kare çekirdek + altıgen blok halkası | şablon "Kare çekirdek + altıgen halka" | kök kap (altıgen) ← kafes (altıgen bloklar) + liste yerleşimi (kare delik ← kare kafes) + su halkası | `ornekler/pwr_kare_altigen_halka.json`, [ders](05-dersler.md#ders-kare-altigen) |
| Altıgen kor + yansıtıcıda tambur halkası | şablon "Altıgen çekirdek + tambur halkası" | kök kap (`kafes_zarfi`) ← altıgen kor kafesi + halka (yansıtıcı) ← `halka` yerleşimi (tambur) + `donme` grubu | `ornekler/altigen_tambur_halkasi.json`, [ders](05-dersler.md#ders-tambur) |
| Kare kor + silindirik yansıtıcıda tambur | şablon "Kafesli çekirdek + tamburlu yansıtıcı" | kök kap (dikdörtgen) ← kare kafes + halka (silindir dış kesit) ← `halka` ya da `liste` yerleşimi (tambur) + `donme` grubu | `ornekler/kafes_tamburlu_yansitici.json` |
| Herhangi bir bölgeye deney kanalı | — | ilgili kap ya da halkaya `liste` yerleşimi (silindir delik ← malzeme) | [4.5](04e-geometri-gelismis.md#geometri-gelismis) |
| Kontrol çubuğu bankaları | parçalarda kontrol çubuğu (3B) | `kafes_konumu` yerleşimi + `daldirma` grubu | `ornekler/pwr_kontrol.json` |
| Eksenel blanket / plenum / zenginlik kuşakları | 3B katmanlı (her şablonda) | `eksenel` düğümü (her düzeyde) | `ornekler/pwr_eksenel.json` |

Bir düzeneği önce şablonla kurmaya çalışın: daha az alan, daha çok denetim. Şablon yetmiyorsa
en yakın şablonu kurup **Gelişmiş geometriye geç** ile ağaca dönüştürün ve oradan düzenleyin;
sıfırdan ağaç kurmak en son çaredir.
