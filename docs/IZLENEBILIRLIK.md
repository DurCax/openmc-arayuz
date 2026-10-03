# İzlenebilirlik matrisi (üretilir — elle düzenlemeyin)

Üreten: `python araclar/izlenebilirlik.py`. Gereksinimler: `docs/GEREKSINIMLER.md`; test işareti: `@gereksinim("R-…")` (`testler/ortak_test.py`). Bu matris bir uygunluk sertifikası değildir; hangi gereksinimin hangi testle ve hangi son sonuçla kanıtlandığını ve **nerede kanıt olmadığını** gösterir.

## Sonuç kaynakları

- `tam.xml` — 2026-10-03T22:27:30.287686+03:00, 1618 test

## Özet

- Gereksinim: 98 (geçti 92, inceleme 5, KALDI 1)
- Toplanan test: 1618; gereksinime bağlı: 210; bağsız: 1408

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
| R-M2-01 | T | geçti | `test_benchmark:test_kriter_olcumleri_tam` (hizli) — geçti<br>`test_benchmark:test_kriter_kabul` (hizli) — geçti<br>`test_benchmark:test_deney_hesap_ayri` (hizli) — geçti<br>`test_benchmark:test_vv_tablosu_json_ile_ayni` (hizli) — geçti |
| R-M3-01 | T | geçti | `test_ornekler:test_yavas_yeni_ornekler_kosar` (yavas) — geçti |
| R-M4-01 | İ | inceleme | — |
| R-M5-01 | T | geçti | `test_hata_yutma:test_tarayici_ornekleri` (hizli) — geçti<br>`test_hata_yutma:test_sessiz_hata_yutma` (hizli) — geçti |
| R-M5-02 | T | geçti | `test_altyapi:test_gunluk_yolu_ve_yazim` (hizli) — geçti<br>`test_altyapi:test_hata_yakalayici_loglar` (hizli) — geçti<br>`test_altyapi:test_hata_diyalogu` (hizli) — geçti |
| R-M6-01 | T | geçti | `test_kalite_altyapi:test_atlama_nedeni_eksikleri_birlikte_soyler` (hizli) — geçti<br>`test_kalite_altyapi:test_modul_basina_veri_listeleri` (hizli) — geçti |
| R-M6-02 | İ | inceleme | — |
| R-M7-01 | T | geçti | `test_altyapi:test_surum` (hizli) — geçti<br>`test_paket:test_surum_tek_kaynak` (hizli) — geçti<br>`test_paket:test_giris_noktalari` (hizli) — geçti<br>`test_rapor:test_cli_rapor` (hizli) — geçti |
| R-M8-01 | İ | geçti | `test_paket:test_lisans_dosyalari` (hizli) — geçti |
| R-M9-01 | T | geçti | `test_ceviri:test_ceviri_temel` (hizli) — geçti<br>`test_ceviri:test_ceviri_dil_secimi` (hizli) — geçti<br>`test_ceviri:test_katalog_derlenmis` (hizli) — geçti<br>`test_ceviri_cekirdek:test_bulgular_ingilizce` (hizli) — geçti<br>`test_ceviri_cekirdek:test_uygunluk_ve_rapor_ingilizce` (hizli) — geçti<br>`test_ceviri_cekirdek:test_sozluk_terim_tutarliligi` (hizli) — geçti |
| R-M9-02 | T | geçti | `test_dil:test_bulgu_metinleri` (hizli) — geçti<br>`test_dil:test_en_katalog` (hizli) — geçti |
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
| R-S-07 | T | geçti | `test_uygunluk_denetimi:test_k6_usl` (hizli) — geçti<br>`test_vv:test_profil_b_uctan_uca` (hizli) — geçti |
| R-S-08 | T | geçti | `test_uygunluk_denetimi:test_k8_k9_k10_k11` (hizli) — geçti |
| R-S-09 | T | geçti | `test_uygunluk_denetimi:test_k12_k6aoa_k13_k14` (hizli) — geçti<br>`test_vv:test_profil_b_uctan_uca` (hizli) — geçti |
| R-S-10 | T | geçti | `test_uygunluk_denetimi:test_k7_katsayilar` (hizli) — geçti<br>`test_uygunluk_denetimi:test_k7_kapatma_ve_faktorler` (hizli) — geçti |
| R-S-11 | T | geçti | `test_uygunluk_denetimi:test_yanlis_alarm_ornekler` (hizli) — geçti |
| R-S-12 | T | geçti | `test_uygunluk_arayuz:test_cli_uygunluk` (hizli) — geçti |
| R-S-13 | T | geçti | `test_uygunluk_arayuz:test_rapor_uygunluk_eki_html` (hizli) — geçti<br>`test_uygunluk_arayuz:test_rapor_uygunluk_eki_pdf` (hizli) — geçti<br>`test_uygunluk_arayuz:test_rapor_uygunluk_hatasi_raporu_durdurmaz` (hizli) — geçti |
| R-S-14 | T | geçti | `test_vv:test_nureg_ornegi_agirlikli` (hizli) — geçti<br>`test_vv:test_nureg_ornegi_egilim_bant` (hizli) — geçti<br>`test_vv:test_nureg_ornegi_parametrik_olmayan_normallik` (hizli) — geçti<br>`test_vv:test_tolerans_carpani_tablo` (hizli) — geçti<br>`test_vv:test_kurallar` (hizli) — geçti<br>`test_vv:test_yontem_secimi` (hizli) — geçti<br>`test_vv:test_kucuk_kume_usl_yok` (hizli) — geçti<br>`test_vv:test_kume_ozeti` (hizli) — geçti<br>`test_vv:test_profil_b_uctan_uca` (hizli) — geçti |
| R-S-15 | T | KALDI | `test_izlenebilirlik:test_gereksinim_isareti` (hizli) — geçti<br>`test_izlenebilirlik:test_gereksinim_belgesi` (hizli) — geçti<br>`test_izlenebilirlik:test_testler_tanimli_kimlik_kullanir` (hizli) — geçti<br>`test_izlenebilirlik:test_matris_sentetik` (hizli) — geçti<br>`test_izlenebilirlik:test_uretilen_belge_guncel` (hizli) — KALDI<br>`test_izlenebilirlik:test_komut_satiri` (hizli) — geçti |
| R-S-16 | T | geçti | `test_kapsul:test_kapsul_icerigi` (hizli) — geçti<br>`test_kapsul:test_dosya_kimligi_ve_zincir` (hizli) — geçti<br>`test_kapsul:test_ortam_kilidi_yedekleri` (hizli) — geçti<br>`test_kapsul:test_kosucu_kapsul_yazar` (hizli) — geçti<br>`test_kapsul:test_rapor_kapsul_satiri` (hizli) — geçti |
| R-S-17 | T | geçti | `test_kapsul:test_farklar` (hizli) — geçti<br>`test_kapsul:test_yeniden_kuru_calisma` (hizli) — geçti<br>`test_kapsul:test_yavas_yeniden_kosu` (yavas) — geçti |
| R-S-18 | İ | inceleme | — |
| R-V3-01 | T | geçti | `test_k1_akis:test_sifirdan_pin_kuru_calistirma` (hizli) — geçti<br>`test_k1_baslangic:test_yeni_spec_gercekten_bos_yalniz_kor_turu` (hizli) — geçti<br>`test_k1_baslangic:test_sifirdan_eksik_adim_sunumu_ve_kapi` (hizli) — geçti |
| R-V3-02 | T | geçti | `test_k1_akis:test_yavas_sifirdan_pin_kosusu` (yavas) — geçti |
| R-V3-03 | T | geçti | `test_k2_veri_yolu:test_ortam_degiskeni_once_gelir` (hizli) — geçti<br>`test_k2_veri_yolu:test_ayar_sonra_aday` (hizli) — geçti<br>`test_k2_veri_yolu:test_hicbiri_yoksa_yok` (hizli) — geçti |
| R-V3-04 | T | geçti | `test_k2_veri_indir:test_tam_indirme_atomik` (hizli) — geçti<br>`test_k2_veri_indir:test_kesinti_ve_surdurme` (hizli) — geçti<br>`test_k2_veri_indir:test_sha256_hatasi` (hizli) — geçti |
| R-V3-05 | T | geçti | `test_k2_veri_indir:test_url_politikasi` (hizli) — geçti |
| R-V3-06 | T | geçti | `test_k3_pin_tablosu:test_tablo_haritayla_ayni` (hizli) — geçti<br>`test_k3_pin_tablosu:test_tablo_toplami_toplam_guc` (hizli) — geçti |
| R-V3-07 | T | geçti | `test_k3_pin_tablosu:test_ceyrek_katlama` (hizli) — geçti |
| R-V3-08 | T | geçti | `test_k3_tukenme_guc:test_adim_basina_tablo` (hizli) — geçti<br>`test_k3_tukenme_guc:test_gercek_kosu_adim_basina_guc` (yavas) — geçti |
| R-V3-09 | T | geçti | `test_k4_yerel_k:test_yakitsiz_bin_fisil_degil_ama_ortalamaya_payda_olarak_girer` (hizli) — geçti<br>`test_k4_yerel_k:test_net_yok_olma_agirlikli_ortalama_uretim_toplami_oranina_esit` (hizli) — geçti<br>`test_k4_yerel_k:test_sonsuz_kafeste_yerel_k_ortalamasi_k_sonsuza_esit` (yavas) — geçti |
| R-V3-10 | T | geçti | `test_k4_demet_kinf:test_sihirbaz_modeli_elle_modelle_fiziksel_olarak_ozdes` (hizli) — geçti<br>`test_k4_demet_kinf:test_budama_yalniz_kullanilmayan_malzemeleri_atar` (hizli) — geçti |
| R-V3-11 | T | geçti | `test_k5_alt_model:test_cubuk_alt_modeli_yalniz_pinin_malzemeleri` (hizli) — geçti<br>`test_k5_alt_model:test_demet_alt_modeli_kapsam_disi_malzeme_yok` (hizli) — geçti |
| R-V3-12 | T | geçti | `test_h2_esdegerlik:test_malzeme_haritasi_esdeger` (hizli) — geçti<br>`test_h2_kapi:test_calistir_kapisi_ayni` (hizli) — geçti |
| R-V3-13 | T | geçti | `test_h1_hiz:test_tus_basina_tek_gezinti` (hizli) — geçti<br>`test_h1_hiz:test_buyuk_orneklerde_sureler` (yavas) — geçti |
| R-V3-14 | T | geçti | `test_k6_hesap:test_uranyum_vektoru_openmc_ile_ayni` (hizli) — geçti<br>`test_k6_hesap:test_uo2_turetilmis_degerler_el_hesabi` (hizli) — geçti |
| R-V3-15 | T | geçti | `test_k6_kullanici:test_bozuk_json_acik_hata_silinmez_yedeklenir` (hizli) — geçti |
| R-V3-16 | T | geçti | `test_y1_mesh_tanim:test_betik_esdegerligi_mesh_tanimlari` (hizli) — geçti<br>`test_y1_mesh_tanim:test_yavas_betik_esdegerligi_kosu` (yavas) — geçti |
| R-V3-17 | T | geçti | `test_y3_spektrum:test_dort_faktor_el_hesabi` (hizli) — geçti<br>`test_y3_spektrum:test_hizli_sistemde_dort_faktor_tanimsiz` (hizli) — geçti<br>`test_y3_spektrum:test_pin_hucre_dort_faktor_k_sonsuz` (yavas) — geçti |
| R-V3-18 | T | geçti | `test_y6_kinetik:test_inhour_cok_grup` (hizli) — geçti<br>`test_y6_kinetik:test_tek_grup_basamak_analitik` (hizli) — geçti<br>`test_y6_kinetik:test_alti_grup_basamak_matris_ustel` (hizli) — geçti |
| R-V3-19 | T | geçti | `test_y7_fizik:test_sabit_kaynak_yuzey_akimi_korunumu` (yavas) — geçti |
| R-V3-20 | T | geçti | `test_y7_fizik:test_foton_acik_isinma_skorlari` (yavas) — geçti<br>`test_y7_fizik:test_sicaklik_interpolasyonu_ara_sicaklik` (yavas) — geçti |
| R-V3-21 | T | geçti | `test_y4_cikti:test_bozunma_isisi_analitik` (hizli) — geçti |
| R-V3-22 | T | geçti | `test_y4_surdur:test_eklenen_adim` (hizli) — geçti<br>`test_y4_surdur:test_reddedilenler` (hizli) — geçti |
| R-V3-23 | T | geçti | `test_y5_dal:test_kosul_taramayla_ayni` (hizli) — geçti |
| R-V3-24 | T | geçti | `test_y5_bolme:test_gd_hacim_korunumu` (hizli) — geçti<br>`test_y5_bolme:test_betik_esdegerligi` (hizli) — geçti |
| R-V3-25 | T | geçti | `test_y8_k:test_iki_grup_yukari_sacilmasiz_el_formulu` (hizli) — geçti<br>`test_y8_k:test_iki_grup_yukari_sacilmali_determinant` (hizli) — geçti |
| R-V3-26 | T | geçti | `test_y9_triso:test_kurulan_modelde_paketleme_orani_hacim_sayimiyla_hedefe_yuzde_bir_icinde` (hizli) — geçti<br>`test_y9_triso:test_betik_ve_kurucu_ayni_parcaciklari_kurar` (hizli) — geçti |
| R-V3-27 | T | geçti | `test_y9_varyans:test_agirlik_penceresi_yanliliksiz_ve_fom_artar` (yavas) — geçti |
| R-V3-28 | T | geçti | `test_y10_kuyruk:test_uc_kosu_sirayla_biter` (hizli) — geçti<br>`test_y10_kuyruk:test_her_kosu_ayri_dizinde_ve_ayni_dizin_reddedilir` (hizli) — geçti<br>`test_y10_kuyruk:test_paralel_kosu_is_parcacigi_butcesini_asmaz` (hizli) — geçti |
| R-V3-29 | T | geçti | `test_p2_masaustu:test_kur_dosyalari_yazar_ve_kaldir_iz_birakmaz` (hizli) — geçti |
| R-V3-30 | T | geçti | `test_t2_yollar:test_paket_ve_veri_dizinleri` (hizli) — geçti |
| R-V3-31 | A | inceleme | — |
| R-V3-32 | İ | inceleme | — |

## Testsiz gereksinimler (yöntem T, bağlı test yok)

Yok.

## Test dışı doğrulanan gereksinimler (İ / A)

- R-M4-01 (İ) — Yeni ya da değişen kaynak dosyalar 800 satır tavanını aşmaz (aşan dosya gerekçesiyle listelenir).
- R-M6-02 (İ) — Sürekli tümleştirme (GitHub Actions) hızlı süiti her gönderimde koşar.
- R-S-18 (İ) — Belge seti (gereksinimler, tasarım, test planı/sonuçları, V&V, kılavuz, bilinen sınırlamalar, değişiklik günlüğü) listelenir ve eksikleri yazılır.
- R-V3-31 (A) — V&V kümesi 24 yeni LEU oksit kafes vakasıyla genişletildi; USL NUREG/CR-6698 ile hesaplanır ve bağımsızlık/normallik sınırlamaları belgelenir (sertifika değildir).
- R-V3-32 (İ) — v3 özellikleri bağımsız öğrenci QA (Q1) ve profesör/standart denetiminden (Q2) geçirildi; bulgular düzeltildi ya da açık nokta olarak yazıldı.

## Tanımsız kimliğe bağlı testler

Yok.

## Gereksinimsiz kritik testler

Kritik modüller: `test_capa`, `test_betik`, `test_betik_kacis`, `test_geometri_esdegerlik`, `test_altigen_esdeger`, `test_geometri_fizik`, `test_dogrulama_kapisi`, `test_goc`, `test_uygunluk_denetimi`, `test_uygunluk_arayuz`, `test_rapor`, `test_tukenme_temel`, `test_tukenme_hacim`, `test_guc`, `test_guc_kor`, `test_hata_yutma`, `test_benchmark`, `test_vv`, `test_kapsul`, `test_izlenebilirlik`.

- `test_altigen_esdeger:test_altigen_asimetrik_harita` (hizli)
- `test_altigen_esdeger:test_altigen_sinir_uyarilari` (hizli)
- `test_benchmark:test_yavas_godiva_kriter` (yavas)
- `test_benchmark:test_yavas_kriter_jezebel` (yavas)
- `test_benchmark:test_yavas_kriter_flattop25` (yavas)
- `test_benchmark:test_yavas_kriter_lct008` (yavas)
- `test_benchmark:test_yavas_kriter_vver1000_ugd` (yavas)
- `test_benchmark:test_yavas_kriter_umf001` (yavas)
- `test_benchmark:test_yavas_kriter_lst002a` (yavas)
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
- `test_vv:test_aoa_ealf_tayf` (hizli)
- `test_vv:test_aoa_spec_parametreleri` (hizli)
- `test_vv:test_vv_kriterleri_kapidan_gecer` (hizli)
