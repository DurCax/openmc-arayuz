# -*- coding: utf-8 -*-
"""
k2_sahte_sunucu.py -- K2 testleri icin AGSIZ sahte HTTP sunucusu.

http.server.ThreadingHTTPServer bir is parcaciginda 127.0.0.1'de (rastgele
port) calisir; icerik bellektedir. Davranis dugmeleri (dosya basina):
  kes      : bu kadar bayt gonderip baglantiyi keser (kesinti taklidi;
             yalniz ILK istekte, sonrakiler tam gonderir)
  aralik   : False ise Range basligini yok sayar (200 + tam govde)
  yonlendir: bu URL'ye 302 verir
Gelen her istegin (yol, Range) cifti `istekler`e yazilir.
"""

import http.server
import threading


class SahteSunucu:

    def __init__(self):
        self.dosyalar = {}          # yol -> bytes
        self.ayar = {}              # yol -> {kes, aralik, yonlendir}
        self.istekler = []
        self._kesildi = set()
        sunucu = self

        class _Isleyici(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):          # test ciktisini kirletmesin
                return

            def do_GET(self):                   # noqa: N802 (http.server adi)
                sunucu._isle(self)

        self._httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Isleyici)
        self.port = self._httpd.server_address[1]
        self._is = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    def url(self, yol, ana="127.0.0.1"):
        return "http://%s:%d%s" % (ana, self.port, yol)

    def __enter__(self):
        self._is.start()
        return self

    def __exit__(self, *a):
        self._httpd.shutdown()
        self._httpd.server_close()

    # ------------------------------------------------------------------
    def _isle(self, h):
        yol = h.path
        aralik = h.headers.get("Range")
        self.istekler.append((yol, aralik))
        ayar = self.ayar.get(yol, {})
        if ayar.get("yonlendir"):
            h.send_response(302)
            h.send_header("Location", ayar["yonlendir"])
            h.send_header("Content-Length", "0")
            h.end_headers()
            return
        if yol not in self.dosyalar:
            h.send_response(404)
            h.send_header("Content-Length", "0")
            h.end_headers()
            return
        veri = self.dosyalar[yol]
        bas = 0
        if aralik and ayar.get("aralik", True):
            bas = int(aralik.split("=")[1].split("-")[0])
            if bas >= len(veri):
                h.send_response(416)
                h.send_header("Content-Range", "bytes */%d" % len(veri))
                h.send_header("Content-Length", "0")
                h.end_headers()
                return
            h.send_response(206)
            h.send_header("Content-Range", "bytes %d-%d/%d" % (bas, len(veri) - 1, len(veri)))
        else:
            h.send_response(200)
        govde = veri[bas:]
        h.send_header("Content-Length", str(len(govde)))
        h.end_headers()
        kes = ayar.get("kes")
        if kes is not None and yol not in self._kesildi:
            self._kesildi.add(yol)
            h.wfile.write(govde[:kes])
            h.wfile.flush()
            h.close_connection = True
            return
        h.wfile.write(govde)
