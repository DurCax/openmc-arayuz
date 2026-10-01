# İzlenebilirlik matrisi (üretilir — elle düzenlemeyin)

Üreten: `python araclar/izlenebilirlik.py`. Gereksinimler: `docs/GEREKSINIMLER.md`; test işareti: `@gereksinim("R-…")` (`testler/ortak_test.py`). Bu matris bir uygunluk sertifikası değildir; hangi gereksinimin hangi testle ve hangi son sonuçla kanıtlandığını ve **nerede kanıt olmadığını** gösterir.

## Sonuç kaynakları

- `s4_hizli.xml` — 2026-10-01T15:05:11.591476+03:00, 545 test
- `s4_yavas.xml` — 2026-10-01T15:09:06.473516+03:00, 30 test

## Özet

- Gereksinim: 66 (geçti 60, TESTSİZ 2, inceleme 4)
- Toplanan test: 616; gereksinime bağlı: 133; bağsız: 483

## Gereksinim → test → son sonuç

| Kimlik | Yöntem | Durum | Testler |
|---|---|---|---|
| R-FZ-01 | T | geçti | `test_capa:test_regresyon_cipasi` (yavas) — geçti |
| R-FZ-02 | T | geçti | `test_capa:test_godiva_kriteri` (yavas) — geçti |
| R-FZ-03 | T | geçti | `test_altigen_kor:test_altigen_betik_esdegerligi` (yavas) — geçti<br>`test_betik:test_betik_esdegerligi` (yavas) — geçti<br>`test_betik:test_altigen_betik_esdegerligi` (yavas) — geçti<br>`test_guc_coklu:test_cok_tur_betik_esdegerligi` (yavas) — geçti<br>`test_tukenme_temel:test_tukenme_betik_esdegerligi` (yavas) — geçti |
| R-FZ-04 | T | geçti | `test_geometri_esdegerlik:test_betik_xml_kucuk` (hizli) — geçti<br>`test_geometri_esdegerlik:test_betik_xml_hepsi` (yavas) — geçti |
| R-A1-01 | T | geçti | `test_altigen_kor:test_altigen_kor_sema_ve_kurallar` (hizli) — geçti<br>`test_altigen_kor:test_altigen_kor_dogrulama` (hizli) — geçti<br>`test_altigen_kor:test_altigen_kor_geometri` (hizli) — geçti |
| R-A1-02 | T | geçti | `test_altigen_esdeger:test_altigen_nokta_esdegerligi` (hizli) — geçti<br>`test_altigen_esdeger:test_altigen_kilifli_mc_esdegerligi` (yavas) — geçti<br>`test_altigen_kor:test_altigen_analitik_esdegerlik` (yavas) — geçti |
| R-A1-03 | T | geçti | `test_altigen_kor:test_altigen_kor_yonelim_olcumu` (hizli) — geçti |
| R-A2-01 | T | geçti | `test_nuklid_secici:test_normallestirme_ve_oneri` (hizli) — geçti<br>`test_nuklid_secici:test_dogrulama_yazim_hatasi` (hizli) — geçti |
| R-A2-02 | T | geçti | `test_nuklid_secici:test_sonuc_oku_bulunamayan` (hizli) — geçti |
| R-A2-03 | T | geçti | `test_nuklid_secici:test_eski_json_izlenen` (hizli) — geçti<br>`test_nuklid_secici:test_sekme_onceki_sonuc_yeni_secim` (hizli) — geçti |
| R-A2-04 | T | geçti | `test_nuklid_secici:test_csv_bicimi` (hizli) — geçti |
| R-A3-01 | T | geçti | `test_dogrulama_kapisi:test_ornekler_kapidan_gecer` (hizli) — geçti<br>`test_ornekler:test_butun_ornekler_kapidan_gecer` (hizli) — geçti |
| R-A3-02 | T | geçti | `test_ornek_bilgi:test_ornekler_meta_temiz` (hizli) — geçti<br>`test_ornek_bilgi:test_dogrula_meta_hatalari` (hizli) — geçti |
| R-A4-01 | T | geçti | `test_tasarim:test_kontrast_wcag` (hizli) — geçti |
| R-A4-02 | T | geçti | `test_tasarim_kurallari:test_sabit_renk_tabani` (hizli) — geçti |
| R-A4-03 | T | geçti | `test_tasarim_kurallari:test_sahipsiz_qlayout_yok` (hizli) — geçti |
| R-M1-01 | T | geçti | `test_guc_kor:test_kare_kor_anahtar_sentetik` (hizli) — geçti<br>`test_guc_kor:test_altigen_ic_ice_anahtar_sentetik` (hizli) — geçti<br>`test_guc_kor:test_kare_kor_2x2_mc` (yavas) — geçti<br>`test_guc_kor:test_altigen_ic_ice_mc` (yavas) — geçti |
| R-M1-02 | T | geçti | `test_guc:test_tepe_faktorleri_sentetik` (hizli) — geçti<br>`test_guc_kor:test_tepe_faktorleri_tam_kor` (hizli) — geçti |
| R-M1-03 | T | geçti | `test_guc_coklu:test_kurucu_tur_basina_tally` (hizli) — geçti<br>`test_guc_coklu:test_dagilim_birlestirme_sentetik` (hizli) — geçti<br>`test_guc_coklu:test_uc_zenginlik_mc_fdh` (yavas) — geçti |
| R-M1-04 | T | geçti | `test_guc:test_guc_esdegerlik_ve_korunum` (yavas) — geçti |
| R-M2-01 | T | TESTSİZ | — |
| R-M3-01 | T | geçti | `test_ornekler:test_yavas_yeni_ornekler_kosar` (yavas) — geçti |
| R-M4-01 | İ | inceleme | — |
| R-M5-01 | T | geçti | `test_hata_yutma:test_tarayici_ornekleri` (hizli) — geçti<br>`test_hata_yutma:test_sessiz_hata_yutma` (hizli) — geçti |
| R-M5-02 | T | geçti | `test_altyapi:test_gunluk_yolu_ve_yazim` (hizli) — geçti<br>`test_altyapi:test_hata_yakalayici_loglar` (hizli) — geçti<br>`test_altyapi:test_hata_diyalogu` (hizli) — geçti |
| R-M6-01 | T | geçti | `test_kalite_altyapi:test_atlama_nedeni_eksikleri_birlikte_soyler` (hizli) — geçti<br>`test_kalite_altyapi:test_modul_basina_veri_listeleri` (hizli) — geçti |
| R-M6-02 | İ | inceleme | — |
| R-M7-01 | T | geçti | `test_altyapi:test_surum` (hizli) — geçti<br>`test_rapor:test_cli_rapor` (hizli) — geçti |
| R-M8-01 | İ | inceleme | — |
| R-M9-01 | T | geçti | `test_ceviri:test_ceviri_temel` (hizli) — geçti<br>`test_ceviri:test_ceviri_dil_secimi` (hizli) — geçti<br>`test_ceviri:test_katalog_derlenmis` (hizli) — geçti |
| R-M9-02 | T | geçti | `test_dil:test_bulgu_metinleri` (hizli) — geçti |
| R-M10-01 | T | geçti | `test_rapor:test_rapor_html_fixture` (hizli) — geçti<br>`test_rapor:test_rapor_sayilar_birebir` (hizli) — geçti<br>`test_rapor:test_rapor_pdf_ve_sure` (hizli) — geçti |
| R-M10-02 | T | geçti | `test_kapsul:test_rapor_kapsul_satiri` (hizli) — geçti<br>`test_rapor:test_tekrarlanabilirlik` (hizli) — geçti |
| R-M10-03 | T | geçti | `test_rapor:test_cli_rapor` (hizli) — geçti |
| R-TK-01 | T | geçti | `test_tukenme_temel:test_bateman_bozunum` (yavas) — geçti |
| R-TK-02 | T | geçti | `test_altigen_kor:test_altigen_tukenme_hacmi_stokastik` (yavas) — geçti<br>`test_tukenme_hacim:test_ornek_hacimleri` (hizli) — geçti<br>`test_tukenme_hacim:test_hacim_stokastik` (yavas) — geçti<br>`test_tukenme_temel:test_tukenme_hacimleri` (hizli) — geçti |
| R-TK-03 | T | geçti | `test_tukenme_temel:test_zincir_butunlugu` (hizli) — geçti<br>`test_tukenme_temel:test_tukenme_zincir_secimi` (hizli) — geçti |
| R-G-01 | T | geçti | `test_geometri_esdegerlik:test_iz_kayit_1` (hizli) — geçti<br>`test_geometri_esdegerlik:test_iz_kayit_2` (hizli) — geçti<br>`test_geometri_esdegerlik:test_iz_kayit_3` (hizli) — geçti<br>`test_geometri_esdegerlik:test_iz_kayit_4` (hizli) — geçti<br>`test_geometri_esdegerlik:test_yapi` (hizli) — geçti<br>`test_geometri_esdegerlik:test_hacim` (hizli) — geçti<br>`test_geometri_esdegerlik:test_yavas_kayit_tam` (yavas) — geçti |
| R-G-02 | T | geçti | `test_goc:test_goc_zinciri_saf` (hizli) — geçti<br>`test_goc:test_goc_hatalari` (hizli) — geçti<br>`test_goc:test_goc_yukle_ve_yedek` (hizli) — geçti<br>`test_goc:test_goc_ornekler` (hizli) — geçti |
| R-G-03 | T | geçti | `test_geometri_ui:test_gelismise_gecis_tek_adimda_geri_alinir` (hizli) — geçti |
| R-G-04 | T | geçti | `test_geometri_agac:test_a_kesik_ve_nokta` (hizli) — geçti<br>`test_geometri_dogrulama:test_kesik_ve_gizli` (hizli) — geçti |
| R-G-05 | T | geçti | `test_geometri_fizik:test_yavas_pin_kesiti_hacmi` (yavas) — geçti<br>`test_geometri_yonelim:test_pin_kesiti_olcumu` (hizli) — geçti<br>`test_tukenme_hacim:test_bolge_alani` (hizli) — geçti |
| R-G-06 | T | geçti | `test_geometri_agac:test_yuz_basina_sinir` (hizli) — geçti<br>`test_geometri_agac:test_ceyrek_tam_esit` (yavas) — geçti<br>`test_ornekler:test_yavas_ceyrek_tam_esit` (yavas) — geçti |
| R-G-07 | T | geçti | `test_geometri_agac:test_kontrol_cubugu_ayri_ornek` (hizli) — geçti |
| R-G-08 | T | geçti | `test_geometri_dogrulama:test_ortusme_yakalanir` (hizli) — geçti<br>`test_geometri_dogrulama:test_bosluk_yakalanir` (hizli) — geçti<br>`test_geometri_dogrulama:test_yavas_geometri_hata_ayikla` (yavas) — geçti |
| R-G-09 | T | geçti | `test_geometri_fizik:test_yeni_ornek_hacimleri_analitik` (hizli) — geçti<br>`test_geometri_fizik:test_yavas_sonsuz_ortam` (yavas) — geçti<br>`test_geometri_fizik:test_yavas_tamburlu_kor_agacta` (yavas) — geçti<br>`test_geometri_fizik:test_yavas_tambur_monoton` (yavas) — geçti<br>`test_geometri_fizik:test_yavas_simetri_60` (yavas) — geçti<br>`test_geometri_fizik:test_yavas_yeni_ornek_hacimleri` (yavas) — geçti |
| R-G-10 | T | geçti | `test_betik_kacis:test_betik_ad_kacisi_fuzz` (hizli) — geçti<br>`test_betik_kacis:test_yorum_ve_dokuman_kacisi` (hizli) — geçti |
| R-G-11 | T | geçti | `test_geometri_agac:test_duzenekler_kurulur` (hizli) — geçti<br>`test_geometri_agac:test_duzenekler_kosar` (yavas) — geçti |
| R-S-01 | T | geçti | `test_uygunluk_arayuz:test_rapor_uygunluk_eki_html` (hizli) — geçti<br>`test_uygunluk_denetimi:test_api_sozlesmesi` (hizli) — geçti |
| R-S-02 | T | geçti | `test_uygunluk_denetimi:test_k1_entropi` (hizli) — geçti<br>`test_uygunluk_denetimi:test_k1_entropi_kapali_ve_bozuk` (hizli) — geçti |
| R-S-03 | T | geçti | `test_uygunluk_denetimi:test_k2_istatistik` (hizli) — geçti |
| R-S-04 | T | geçti | `test_uygunluk_arayuz:test_calistir_sayfasi_panel_ve_m5` (hizli) — geçti<br>`test_uygunluk_denetimi:test_ayristir_log` (hizli) — geçti<br>`test_uygunluk_denetimi:test_kosucu_kayip_parcacik` (hizli) — geçti<br>`test_uygunluk_denetimi:test_k3_kayip_parcacik` (hizli) — geçti |
| R-S-05 | T | geçti | `test_rapor:test_tekrarlanabilirlik` (hizli) — geçti<br>`test_uygunluk_denetimi:test_k4_izlenebilirlik` (hizli) — geçti |
| R-S-06 | T | geçti | `test_uygunluk_arayuz:test_rapor_k5_temiz` (hizli) — geçti<br>`test_uygunluk_denetimi:test_k5_belirsizlik` (hizli) — geçti |
| R-S-07 | T | geçti | `test_uygunluk_denetimi:test_k6_usl` (hizli) — geçti |
| R-S-08 | T | geçti | `test_uygunluk_denetimi:test_k8_k9_k10_k11` (hizli) — geçti |
| R-S-09 | T | geçti | `test_uygunluk_denetimi:test_k12_k6aoa_k13_k14` (hizli) — geçti |
| R-S-10 | T | geçti | `test_uygunluk_denetimi:test_k7_katsayilar` (hizli) — geçti<br>`test_uygunluk_denetimi:test_k7_kapatma_ve_faktorler` (hizli) — geçti |
| R-S-11 | T | geçti | `test_uygunluk_denetimi:test_yanlis_alarm_ornekler` (hizli) — geçti |
| R-S-12 | T | geçti | `test_uygunluk_arayuz:test_cli_uygunluk` (hizli) — geçti |
| R-S-13 | T | geçti | `test_uygunluk_arayuz:test_rapor_uygunluk_eki_html` (hizli) — geçti<br>`test_uygunluk_arayuz:test_rapor_uygunluk_eki_pdf` (hizli) — geçti<br>`test_uygunluk_arayuz:test_rapor_uygunluk_hatasi_raporu_durdurmaz` (hizli) — geçti |
| R-S-14 | T | TESTSİZ | — |
| R-S-15 | T | geçti | `test_izlenebilirlik:test_gereksinim_isareti` (hizli) — geçti<br>`test_izlenebilirlik:test_gereksinim_belgesi` (hizli) — geçti<br>`test_izlenebilirlik:test_testler_tanimli_kimlik_kullanir` (hizli) — geçti<br>`test_izlenebilirlik:test_matris_sentetik` (hizli) — geçti<br>`test_izlenebilirlik:test_uretilen_belge_guncel` (hizli) — geçti<br>`test_izlenebilirlik:test_komut_satiri` (hizli) — geçti |
| R-S-16 | T | geçti | `test_kapsul:test_kapsul_icerigi` (hizli) — geçti<br>`test_kapsul:test_dosya_kimligi_ve_zincir` (hizli) — geçti<br>`test_kapsul:test_ortam_kilidi_yedekleri` (hizli) — geçti<br>`test_kapsul:test_kosucu_kapsul_yazar` (hizli) — geçti<br>`test_kapsul:test_rapor_kapsul_satiri` (hizli) — geçti |
| R-S-17 | T | geçti | `test_kapsul:test_farklar` (hizli) — geçti<br>`test_kapsul:test_yeniden_kuru_calisma` (hizli) — geçti<br>`test_kapsul:test_yavas_yeniden_kosu` (yavas) — geçti |
| R-S-18 | İ | inceleme | — |

## Testsiz gereksinimler (yöntem T, bağlı test yok)

- R-M2-01 — Her benchmark için hesap/deney oranı (C/E) ve fark σ cinsinden V&V tablosunda kayıtlı ve kaynak JSON ile tutarlıdır.
- R-S-14 — Benchmark kümesinden yanlılık, yanlılık belirsizliği ve USL NUREG/CR-6698 yöntemiyle hesaplanır.

## Test dışı doğrulanan gereksinimler (İ / A)

- R-M4-01 (İ) — Yeni ya da değişen kaynak dosyalar 800 satır tavanını aşmaz (aşan dosya gerekçesiyle listelenir).
- R-M6-02 (İ) — Sürekli tümleştirme (GitHub Actions) hızlı süiti her gönderimde koşar.
- R-M8-01 (İ) — Depoda lisans dosyası ve üçüncü taraf lisans listesi bulunur.
- R-S-18 (İ) — Belge seti (gereksinimler, tasarım, test planı/sonuçları, V&V, kılavuz, bilinen sınırlamalar, değişiklik günlüğü) listelenir ve eksikleri yazılır.

## Tanımsız kimliğe bağlı testler

Yok.

## Gereksinimsiz kritik testler

Kritik modüller: `test_capa`, `test_betik`, `test_betik_kacis`, `test_geometri_esdegerlik`, `test_altigen_esdeger`, `test_geometri_fizik`, `test_dogrulama_kapisi`, `test_goc`, `test_uygunluk_denetimi`, `test_uygunluk_arayuz`, `test_rapor`, `test_tukenme_temel`, `test_tukenme_hacim`, `test_guc`, `test_guc_kor`, `test_hata_yutma`, `test_benchmark`, `test_vv`, `test_kapsul`, `test_izlenebilirlik`.

- `test_altigen_esdeger:test_altigen_asimetrik_harita` (hizli)
- `test_altigen_esdeger:test_altigen_sinir_uyarilari` (hizli)
- `test_benchmark:test_kriter_olcumleri_tam` (hizli)
- `test_benchmark:test_kriter_kabul` (hizli)
- `test_benchmark:test_deney_hesap_ayri` (hizli)
- `test_benchmark:test_vv_tablosu_json_ile_ayni` (hizli)
- `test_benchmark:test_yavas_godiva_kriter` (yavas)
- `test_benchmark:test_yavas_kriter_jezebel` (yavas)
- `test_benchmark:test_yavas_kriter_flattop25` (yavas)
- `test_benchmark:test_yavas_kriter_lct008` (yavas)
- `test_benchmark:test_yavas_kriter_vver1000_ugd` (yavas)
- `test_dogrulama_kapisi:test_kapi_hatali_spec` (hizli)
- `test_dogrulama_kapisi:test_kapi_gecerli_spec` (hizli)
- `test_dogrulama_kapisi:test_kapi_spec_degistirmez` (hizli)
- `test_geometri_fizik:test_yeni_ornekler` (hizli)
- `test_geometri_fizik:test_fiksturler` (hizli)
- `test_goc:test_agac_modu_yukseklik` (hizli)
- `test_guc:test_distribcell_ornek_sayisi` (hizli)
- `test_guc:test_altigen_distribcell_koprusu` (hizli)
- `test_guc:test_mutlak_guc` (hizli)
- `test_guc:test_guc_dogrulama` (hizli)
- `test_guc_kor:test_tek_demet_geriye_uyum_sentetik` (hizli)
- `test_guc_kor:test_katmanli_ayni_konum_toplanir` (hizli)
- `test_guc_kor:test_konum_metni_ic_ice` (hizli)
- `test_guc_kor:test_cubuk_merkezi_kare` (hizli)
- `test_guc_kor:test_referans_eksik_demet_uyarisi` (hizli)
- `test_guc_kor:test_arayuz_tam_kor_gorunumleri` (hizli)
- `test_guc_kor:test_arayuz_altigen_kor` (hizli)
- `test_guc_kor:test_arayuz_tek_demet_degismedi` (hizli)
- `test_hata_yutma:test_hata_metni_atamasi` (hizli)
- `test_hata_yutma:test_modul_nitelikli_anahtar` (hizli)
- `test_hata_yutma:test_dar_tip_gerekcesiz_bilgi` (hizli)
- `test_rapor:test_cekirdek_qt_siz` (hizli)
- `test_rapor:test_derleme_bilgisi` (hizli)
- `test_rapor:test_rapor_yalniz_model` (hizli)
- `test_rapor:test_rapor_hatalar` (hizli)
- `test_rapor:test_rapor_tukenme_bolumu` (hizli)
- `test_rapor:test_rapor_dayaniklilik` (hizli)
- `test_tukenme_hacim:test_dogrudan_malzeme_hacmi` (hizli)
- `test_tukenme_hacim:test_tukenme_dogrulama_dogrudan` (hizli)
- `test_tukenme_hacim:test_ornek_hacimleri_ic_ice_katmanli` (hizli)
- `test_tukenme_hacim:test_ornek_hacimleri_2b_ve_tek_ornek` (hizli)
- `test_tukenme_hacim:test_yanabilir_bor` (hizli)
- `test_tukenme_hacim:test_hacimsiz_zehir` (hizli)
- `test_tukenme_hacim:test_calistir_kapisi` (hizli)
- `test_tukenme_hacim:test_terminal_kapisi` (hizli)
- `test_tukenme_hacim:test_ornek_hacimleri_dogrudan` (hizli)
- `test_tukenme_hacim:test_ornek_hacimleri_hatalar` (hizli)
- `test_tukenme_hacim:test_nokta_yolu` (hizli)
- `test_tukenme_hacim:test_hazirla` (hizli)
- `test_tukenme_hacim:test_ornek_sirasi_openmc` (yavas)
- `test_tukenme_hacim:test_cubuk_cubuk_tukenme` (yavas)
- `test_tukenme_temel:test_tukenme_dogrulama` (hizli)
- `test_tukenme_temel:test_tukenme_eskime` (hizli)
- `test_tukenme_temel:test_arayuz_tukenme_gidip_gelme` (hizli)
- `test_tukenme_temel:test_tukenme_kosu` (yavas)
- `test_uygunluk_arayuz:test_belirsizlik_bicimi_buyuk_sigma` (hizli)
- `test_uygunluk_arayuz:test_profil_secimi_spec` (hizli)
- `test_uygunluk_arayuz:test_ornekler_gidis_donus_bozulmaz` (hizli)
- `test_uygunluk_arayuz:test_panel_bulgular` (hizli)
- `test_uygunluk_arayuz:test_panel_profil_secimi` (hizli)
- `test_uygunluk_arayuz:test_qprocess_yolu_gunluk_ve_uyarilar` (hizli)
- `test_uygunluk_denetimi:test_profiller` (hizli)
