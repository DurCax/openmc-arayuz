# Paketleme secenekleri (P1 degerlendirmesi, 03.10.2026)

| Secenek | Boyut (olculen/tahmin) | Artilari | Eksileri |
|---|---|---|---|
| **conda constructor .sh (SECILDI)** | 409 MB dosya; kurulu 1,7 GB | Tek dosya, cevrimdisi, kok yetkisi yok, lisans metni gosterir, post_install kancasi (P2), conda-forge paketlerini oldugu gibi kullanir (RPATH goreli, tasinabilir onek), `-b` ile otomasyon | Kurulu boyut buyuk; Qt/OpenMC kutuphaneleri paylasimli degil |
| conda-pack tarball | 577 MB (olculdu) | Hazir ortami oldugu gibi tasir | Kullanici `conda-pack`/tar bilmeli; lisans/kanca/kaldirma yok; onek degisince `conda-unpack` gerekir; kurulum sonrasi adimlar elle |
| AppImage | ~600-800 MB tahmin (SquashFS ile sikisir) | Cift tikla calisir, kurulum yok | PySide6 + openmc + HDF5 + libstdc++ + Qt platform eklentileri gomulmeli (linuxdeploy-plugin-qt conda ortamiyla uyumsuz: RPATH/conda onek), FUSE2 gereksinimi (Ubuntu 22.04+'da yok), ilk acilista tukenme alt sureci `python -m` icin ortam sarmalayici gerekir, her acilista ~1,7 GB SquashFS baglama; uygulama calisma dizinine yazar (AppImage salt okunur) |

Karar: constructor birincil. conda-pack ve AppImage uretilmedi; AppImage'in
asil engeli FUSE2 ve conda ortaminin linuxdeploy ile yeniden paketlenmesidir.
glibc alt siniri: 2.28 (olcum: paket/constructor/OLCUMLER.md).
