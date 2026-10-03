# -*- coding: utf-8 -*-
"""python -m cekirdek.masaustu kur|kaldir|durum  (cikis: 0 tamam, 1 hata, 2 kullanim)."""

import argparse
import logging
import sys

from cekirdek.ceviri import _
from typing import List, Optional

from cekirdek.masaustu import kurulum


def _ayristirici() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m cekirdek.masaustu",
        description="OpenMC arayuzu masaustu butunlesmesi (kullanici duzeyi, kok gerekmez).")
    alt = p.add_subparsers(dest="komut", required=True)
    k = alt.add_parser("kur", help="menu girdisi + simge + MIME turu kur (tekrar calistirilabilir)")
    k.add_argument("--exec", dest="calistirilabilir", default=None, metavar="YOL",
                   help="Exec= satirinda kullanilacak openmc-arayuz yolu "
                        "(varsayilan: bu yorumlayicinin yanindaki betik, yoksa PATH)")
    k.add_argument("--varsayilan-yapma", action="store_true",
                   help="uygulamayi proje turunun varsayilan acicisi yapma")
    k.add_argument("--simulasyon", action="store_true", help="yalniz ne yapilacagini yaz")
    alt.add_parser("kaldir", help="kurulan dosyalari manifestten sil (baska hicbir dosyaya dokunmaz)")
    alt.add_parser("durum", help="kurulu mu? (cikis 0 = kurulu, 1 = degil)")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _ayristirici().parse_args(argv)
    try:
        if args.komut == "kur":
            kurulum.kur(calistirilabilir=args.calistirilabilir,
                        varsayilan_yap=not args.varsayilan_yapma,
                        simulasyon=args.simulasyon)
        elif args.komut == "kaldir":
            kurulum.kaldir()
        else:
            kurulu = kurulum.durum().kurulu
            # Cikis kodu ayni (0 kurulu, 1 degil); yaninda okunur bir satir (Q1-27)
            print(_("Masaüstü bütünleşmesi kurulu.") if kurulu
                  else _("Masaüstü bütünleşmesi kurulu değil (kurmak için: kur)."))
            return 0 if kurulu else 1
    except kurulum.MasaustuHatasi as hata:
        logging.getLogger(__name__).error("hata: %s", hata)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
