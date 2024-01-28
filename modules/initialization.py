import os
import json
import locale

from qgis.utils import iface
from .utils import (
    dialogBox,
    storeSetting,
)


# Konstanta lokasi berkas
layer_json_file = os.path.join(os.path.dirname(__file__), "../config/layers.json")
basemap_json_file = os.path.join(os.path.dirname(__file__), "../config/basemap.json")
boundary_idn = os.path.join(os.path.dirname(__file__), "../config/daftar_kantor.json")
default_layout_json = os.path.join(
    os.path.dirname(__file__), "../config/default_qpt_layout.json"
)


class Initialize:
    """
    Inisiasi awal Plugin GeoKKP-GIS
    ===========================================

    Pengisian project-wide settings: basemaps, layers, lokasi kantor, etc.
    untuk dipanggil di geokkp.py pada saat inisiasi

    """

    def __init__(self):
        self.iface = iface

        # Comment out for removing a bug
        # self.set_locale()
        self.simpan_layer_settings()
        self.simpan_basemap_settings()
        self.simpan_boundary_settings()
        self.simpan_default_layout_settings()

    def set_locale(self):
        locale.setlocale(locale.LC_NUMERIC, "en_US")

    def simpan_layer_settings(self):
        """
        Panggil daftar layer dan simbologi dari file layers.json, simpan ke dalam pengaturan lokal
        """
        f = open(
            layer_json_file,
        )
        data = json.load(f)
        f.close()
        storeSetting("layers", data["layers"])

    def simpan_basemap_settings(self):
        """
        Panggil daftar basemap dari file basemap.json, simpan ke dalam pengaturan lokal
        """
        f = open(
            basemap_json_file,
        )
        data = json.load(f)
        f.close()
        storeSetting("basemaps", data["basemaps"])

    def simpan_boundary_settings(self):
        """
        Panggil TopoJSON batas administrasi Indonesia level-2 (Kabupaten/Kantah)
        """
        try:
            f = open(
                boundary_idn,
            )
            data = json.load(f)
        except Exception as e:
            dialogBox("Gagal membaca data dari berkas: ", e)
        storeSetting("list_kantor_id", data)
        f.close()

    def simpan_default_layout_settings(self):
        """
        Panggil daftar layout default dari default_qpt_layout.json
        """
        f = open(default_layout_json)
        data = json.load(f)
        f.close()
        storeSetting("layout", data["default_layout"])
