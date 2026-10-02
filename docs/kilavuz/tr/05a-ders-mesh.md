<a id="ders-mesh"></a>
## 5.11 Ağ (mesh) akı ve güç haritası, ParaView

**Örnek:** `ornekler/pwr_mesh_aki.json` · **Seviye:** orta · **Ön koşul:** [5.1](05-dersler.md#ders-demet)
· **Başvuru:** [4.10 Ağ (mesh) tally'si](04j-mesh-tally.md#mesh-tally)

Amaç: 17 × 17 PWR demetinde pin pin güç haritası ve iki grup akı haritası çıkarmak, istatistiğin
yeterli olup olmadığını σ haritasıyla sınamak ve sonucu ParaView'e aktarmak.

<a id="ders-mesh-1"></a>
### Adım 1: ağı incele

1. Başlangıç ekranından **PWR 17×17 demeti: mesh akı ve güç haritası** örneğini açın.
2. **Hesap ayarları › Tally'ler** kartında `mesh_aki_guc` tally'sini seçin: skorlar akı ve
   kappa-fission, **Enerji grupları** açık ve **Grup yapısı** CASMO-2 (0.625 eV sınırı),
   **Ağ (mesh) tally'si** açık, **Ağ türü** Düzenli, **Ağ bölmeleri** 17 × 17.
   **Sınırları modelden al** açıkken öneri satırı ±10.71 cm yazar: ağ hücresi = 21.42 / 17 =
   1.26 cm = çubuk adımı, yani her hücre bir çubuk hücresidir. Ağ çubuk adımıyla örtüşmeseydi
   bir hücre iki çubuğun parçasını toplardı.
3. `silindirik_aki` tally'sini seçin: **Silindirik (r, φ, z)**, 8 halka × 12 dilim. Kare demette
   silindirik ağ köşeleri kaçırır (r = 10.71 cm iç teğet daire); demette radyal profili görmek
   için yine de işe yarar.

<a id="ders-mesh-2"></a>
### Adım 2: koş ve haritayı oku

**Çalıştır**'a basın. Ölçüm (5000 parçacık × 60 çevrim / 20 pasif, 6 iş parçacığı, ENDF/B-VIII.0,
OpenMC 0.16.0): ~34 s, k∞ = 1.1829 ± 0.0024. **Ağ (mesh) haritası** kartında:

* **Skor** kappa-fission, **Normalizasyon** Ortalamaya bağıl: 25 hücre boş ve × işaretli —
  24 kılavuz boru ve 1 enstrüman borusu, fisyon yok. Tepe ≈ 1.10, kılavuz boruların yanındaki
  çubuklarda (su fazla, termal akı yüksek); en düşük ≈ 0.88, demet kenarına yakın. Bağıl hata
  medyanı %2.7, en büyüğü %4.2: hiçbir yakıt hücresi %10 eşiğini aşmaz.
* **Skor** flux, **Enerji grubu** Grup 1 (termal) ve Grup 2 (hızlı): termal/hızlı akı oranı
  kılavuz boruda ≈ 0.20, köşe yakıt çubuğunda ≈ 0.16 — su ıslatma (moderasyon) etkisini görürsünüz.
* **Gösterim** Bağıl hata: termal grubun bağıl hata medyanı %2.4, hızlı grubun %1.0.
* Silindirik tally'de halka ortalamaları 0.994–1.004: sonsuz kafeste radyal profil düzdür
  (yansıtıcı sınır), bu bir **sağlama**dır.

Aynı ayarla farklı tohum ±1–2σ fark verir; daha az parçacıkla (ör. 1000 × 20) çok sayıda ×
görürsünüz — bağıl hata ≈ 1/√N.

<a id="ders-mesh-3"></a>
### Adım 3: mutlak güç yoğunluğu

**Normalizasyon** Mutlak (toplam güçten) seçin. Model 2B'dir (eksenel sonsuz) ve ağ yüksekliği
2 × 10⁴ cm'dir; **Toplam güç** = çizgisel güç × 20 000 cm. 3400 MWth / 193 demet / 366 cm =
48.1 kW/cm → 9.6 × 10⁸ W girin. Ölçüm: ağdaki ısınma toplamı H = 9.38 × 10⁷ eV / kaynak nötronu
(≈ 193 MeV × k/ν ≈ 0.486 fisyon/kaynak: sağlama), yakıt hücrelerinin ortalaması 114.5 W/cm³ =
48.1 kW/cm / 264 çubuk / 1.5876 cm² (çubuk hücresi alanı). Harita bu ortalamanın 0.88–1.10 katıdır.

<a id="ders-mesh-4"></a>
### Adım 4: ParaView

**VTK dışa aktar…** ile `mesh_aki_guc.vtk` yazın, ParaView'de açın (**File › Open**, **Apply**).
Renklendirmede `kappa_fission_toplam`, **Threshold** ile `kappa_fission_toplam_bagil_hata`
> 0.1 hücreleri ayıklayın (bu örnekte yakıtta boş kalır). 3B modelde (ör. `pwr_3b`) z bölmesi
ekleyip **Slice** ile eksenel dilim alabilirsiniz.

![Silindirik ağda akının bağıl hata haritası](../resimler/tr/mesh-harita-silindirik.png)

**Kontrol listesi:** ağ çubuk adımıyla örtüşüyor; × işaretli yakıt hücresi yok; bağıl tepe değeri
beklenen aralıkta; mutlak normalizasyonda ağ bütün fisil bölgeyi kapsıyor. Sonuç bir eğitim
hesabıdır, lisanslama hesabı değildir (sertifika değildir).
