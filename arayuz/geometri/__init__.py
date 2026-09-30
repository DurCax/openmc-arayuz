# -*- coding: utf-8 -*-
"""
arayuz/geometri -- Geometri sayfasinin gelismis (agac) editoru (Dalga G-3).

  duzenle.py     saf agac islemleri (yeni agac doner; geri al yigini icin)
  cizim.py       agactan sematik xy / xz kesit ogeleri (saf geometri + QPainterPath)
  kesit_gorunumu.py  kesit cizim widget'i: tiklayinca yol secer, secili vurgulu
  agac_paneli.py     dugum agaci: ekle / sil / yeniden adlandir / surukle-birak
  formlar*.py        secili ogenin ozellik formu (sayi + birim kutulari)
  sinir_formu.py     yuz basina sinir kosulu formu (sablon ve gelismis)
  sablonlar.py       uc yeni duzenek sablonu (agac ureten saf islevler)
  editor.py          uc panelli gelismis editor
Tasarim: docs/GEOMETRI_MODELI.md §10, §15, §16.
"""
