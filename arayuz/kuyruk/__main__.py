# -*- coding: utf-8 -*-
"""`python -m arayuz.kuyruk [model.json]` -- is akisi penceresi tek basina (Y10)."""

import sys

from PySide6 import QtWidgets


def main(argv: "list | None" = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    from cekirdek import sema
    from arayuz import tema
    from arayuz.kuyruk import pencere
    uyg = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv[:1])
    tema.uygula(uyg)
    spec = sema.yukle(argv[0]) if argv else None
    p = pencere.ac(None, spec)
    p.show()
    return uyg.exec()


if __name__ == "__main__":
    sys.exit(main())
