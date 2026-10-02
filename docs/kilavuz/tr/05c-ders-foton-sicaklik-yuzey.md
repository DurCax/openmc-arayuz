<a id="ders-foton-sicaklik-yuzey"></a>
## 5.16 Foton ısınması, sıcaklık interpolasyonu ve yüzey akımı

**Örnek dosyalar:** `ornekler/pwr_pinhucre.json`, `ornekler/zirh_kure.json` · **Seviye:** orta ·
**Tahmini süre:** 25 dakika (koşular 1–3 dakika)

**Amaç.** Üç ayrı fizik sorusunu aynı araçla yanıtlamak: (1) gama enerjisi ısıya nasıl katılır
ve `heating`, `heating-local`, `kappa-fission` neden farklıdır; (2) kütüphanede olmayan bir
sıcaklıkta k nasıl hesaplanır; (3) bir bölgeye giren ve çıkan nötron akımı soğurmayla nasıl
dengelenir. Alanlar: [Gelişmiş](04f-hesap-ayarlari.md#ayar-gelismis),
[yüzey akımı tally'leri](04f-hesap-ayarlari.md#ayar-yuzey),
[yüzey akımı kartı](04g-calistir.md#calistir-yuzey).

### A. Foton taşınımı ve ısınma skorları

1. `ornekler/pwr_pinhucre.json`'u açın. **Hesap ayarları** › **Tally'ler** › **+ Tally**,
   **Ne ölçülsün** = **Özel**, skorlar: ısınma (heating), yerel ısınma (heating-local),
   kappa-fission, damage-energy.
2. **Çalıştır** (Normal). Sonra **Gelişmiş** › **Foton taşınımı (gama ısınması)** açın ve
   yeniden çalıştırın.

**Tanımlar** (OpenMC `docs/methods/energy_deposition.rst`):
- `heating`, foton **kapalı**: yalnız nötron KERMA'sı (MT301); fisyon ve yakalama gamalarının
  enerjisi yoktur. Foton **açık**: nötron KERMA'sı (gama hariç) + fotonların çarpışma başına
  bıraktığı enerji (çarpışma tahmincisi).
- `heating-local`: nötron için, gama enerjisi çarpışma yerinde bırakılmış sayılır (MT901).
- `kappa-fission`: geri kazanılabilir fisyon enerjisi (nötrinosuz, gamalar yerel); **yakalama
  gamalarını içermez**.

**Ölçülen** (pin hücre, yansıtıcı sınır; 2 000 × 30 / 10, ENDF/B-VIII.0, OpenMC 0.16,
`testler/test_y7_fizik.py`):

| Büyüklük [eV / kaynak nötronu] | foton kapalı | foton açık |
|---|---|---|
| heating (H) | 9.97e7 | 1.101e8 |
| — nötron payı H_n | 9.97e7 | 9.90e7 |
| — gama payı H_γ | 0 | 1.11e7 (%10.1) |
| heating-local | 1.107e8 | 1.099e8 |
| kappa-fission (κF) | 1.076e8 | 1.069e8 |

Yorum: foton kapalıyken `heating` toplam ısının yaklaşık %10'unu kaybeder (H / H_local = 0.90).
Foton açıkken H = H_n + H_γ ve sonsuz kafeste hiçbir gama kaçmadığı için H ≈ `heating-local`
(fark %0.2). H / κF = **1.030**: fark başlıca (n,γ) yakalama gamalarıdır (κF onları saymaz).
Bu oran modele bağlıdır; eşit beklenmez ve **sertifika değildir**. `damage-energy` (MT444) foton
kipinden bağımsızdır (3σ içinde).

### B. Sıcaklık interpolasyonu ile ara sıcaklık

ENDF/B-VIII.0 nötron verisi yalnız 250, 294, 600, 900, 1200, 2500 K'de vardır.

3. **Malzemeler**'de `uo2` sıcaklığını 750 K yapın. **Hesap ayarları** › **Sıcaklık yöntemi**
   **En yakın sıcaklık**: doğrulama **hata** verir ("750 K için kütüphanede veri yok …"; OpenMC
   koşu başında durur). **Sıcaklık toleransı**'nı 200 K yaparsanız hata **uyarı**ya döner: "yalnız
   kütüphane sıcaklığı kullanılır: 600 K" — fizik 750 K'nin değildir.
4. **Ara değer (interpolation)** seçin: doğrulama **bilgi** yazar ("600–900 K arasında stokastik
   interpolasyon"). Her çarpışmada iki komşu sıcaklıktan biri kT'ye göre doğrusal olasılıkla seçilir.
5. Yakıt 600, 750, 900 K ile üç koşu yapın (30 000 × 100 / 20).

**Ölçülen:** k(600) = 1.34498 ± 0.00067, k(750) = 1.34029 ± 0.00067, k(900) = 1.33541 ± 0.00063.
Monoton (her adım ~7σ); k(750) iki komşunun doğrusal ortasından 10 pcm (sınır 3σ = 243 pcm).
Yakıt Doppler katsayısı (600–900 K) ≈ **−1.8 pcm/K**. Su S(α,β) verisi 284–800 K'dir; suyu bu
aralığın dışına çıkarmak koşuyu durdurur.

### C. Yüzey akımı ve korunum (sabit kaynak)

6. `ornekler/zirh_kure.json`'u açın (14 MeV füzyon nokta kaynağı, su + çelik küre, vakum sınır,
   şiddet 10¹² 1/s). **+ Tally** › **Tür** = **Yüzey: model sınırı (kaçak)**, **Enerji grupları**
   açık: `1e-5, 0.625, 1e5, 1e6, 2e7`.
7. **+ Tally** › **Tür** = **Yüzey: kutu ağı (giren / çıkan)**, **Kutu sınırları** alt
   `-10, -10, -10`, üst `10, 10, 10` (kaynak içeride). Bir tane daha: `12, -6, -6` … `24, 6, 6`
   (kaynak dışarıda). **Çalıştır**.

**Denge** (kutunun dış yüzleri; iç yüzler birbirini götürür):

    S + J_giren − J_çıkan + U = A

S kutudaki kaynak (nokta kaynak içerideyse şiddet), U = nu-scatter − scatter (saçılmada net
nötron üretimi: (n,xn) **ve** kesirli verimli MT5; sabit kaynakta + nu-fission), A soğurma.
OpenMC "out" hücreden çıkan, "in" giren kısmi akımdır. Model sınırında OpenMC net akımı yüzey
normaline göre işaretler (+ normal yönü); vakumdan her geçiş dışarı olduğundan yüzey başına
\|J\| kaçaktır.

**Ölçülen** (4 000 × 5, şiddet 10¹² 1/s):

| Kutu | S | J_giren | J_çıkan | U | A | artık |
|---|---|---|---|---|---|---|
| içinde kaynak | 1.000e12 | 4.993e11 | 1.2812e12 | 1.0e8 | 2.1815e11 | 0 (yuvarlama) |
| dışında | 0 | 1.470e11 | 1.3545e11 | 0 | 1.155e10 | 0 (yuvarlama) |

Model sınırı kaçağı 2.557e11 1/s = OpenMC global sızıntısı × şiddet (aynı olaylar); kaynak
parçacığı başına **0.245**. Tüm model: S − L + U − A = 0 (bağıl 1e−14). Denge analog
tahminciyle her geçmişte tamdır; kartta yazan ± korelasyonsuz üst sınırdır.

> ⚠ **Neden yalnız (n,xn) yetmez?** ENDF/B-VIII.0'da Fe56'nın MT5 (n,anything) kanalının nötron
> verimi 14 MeV'de 0.46'dır (Fe54 0.84, Mn55 0.65): bu tepkime "absorption" sayılmaz ama nötron
> kaybettirir. Yalnız (n,xn) kanallarıyla kurulan denge bu modelde %0.15 tutmuyordu; U =
> nu-scatter − scatter her kanalı kapsar.

**Kaynaklar.** OpenMC 0.16 kaynak kodu (`src/nuclide.cpp`, `src/thermal.cpp`,
`src/tallies/tally_scoring.cpp`, `src/particle.cpp`) ve belgesi (`energy_deposition.rst`,
`usersguide/tallies.rst`); Lamarsh & Baratta, *Introduction to Nuclear Engineering* (Doppler
genişlemesi, nötron dengesi). Ölçümler yukarıdaki koşullarda tek tohumla alındı; farklı ayarla
2–3σ fark olağandır.
