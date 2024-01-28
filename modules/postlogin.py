import os
import json

from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import QDockWidget
from qgis.utils import iface
from qgis.core import QgsProject

from .utils import (
    add_google_basemap,
    logMessage,
    readSetting,
    storeSetting,
    get_epsg_from_tm3_zone,
    set_project_crs_by_epsg,
)

from .api import endpoints
from .memo import app_state
from .pengaturan_lokasi import PengaturanLokasiDialog

# file constants
layer_json_file = os.path.join(os.path.dirname(__file__), "../config/layers.json")
basemap_json_file = os.path.join(os.path.dirname(__file__), "../config/basemap.json")

# class UI form
FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/postlogin2.ui")
)


jsonKantor = readSetting("listkantor")


class PostLoginDock(QtWidgets.QDialog, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=iface.mainWindow()):
        """Constructor"""
        super(PostLoginDock, self).__init__(parent)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.setupUi(self)
        self.project = QgsProject

        # login_state = app_state.get('logged_in')

        for panel in self.iface.mainWindow().findChildren(QDockWidget):
            if panel.windowTitle() == "Panel Kerja GeoKKP-GIS":
                self.panel = panel
            else:
                logMessage("panel tidak terdeteksi atau tidak aktif")

        # read settings: Jumlah Kantah Terdaftar atas nama user yang login
        # if login_state.value:
        self.jsonKantor = readSetting("listkantor")
        if self.jsonKantor is not None:
            self.jumlahKantor = len(self.jsonKantor)
            self.populateKantah(int(self.jumlahKantor))
            print("daftar kantor", self.jsonKantor[0])

        self.atur_lokasi = PengaturanLokasiDialog()

        # if readSetting("jumlahkantor") is not None:
        #    jumlah_kantor = int(readSetting("jumlahkantor"))
        #    self.jsonKantor = readSetting("listkantor")
        #    self.populateKantah(jumlah_kantor)
        # self.simpanLayerSettings()
        # self.simpanBasemapSettings()

        self.buttonLanjut_3.clicked.connect(self.pengaturan_lokasi)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def populateKantah(self, jsonkantor):
        self.comboBoxKantah_3.clear()
        # print(jsonkantor)
        try:
            for i in jsonkantor:
                self.comboBoxKantah_3.addItem(i["nama"])
            if len(jsonkantor) > 1:
                self.labelSatuKantah_3.hide()
                self.labelBeberapaKantah_4.show()
            else:
                self.labelSatuKantah_3.show()
                self.labelBeberapaKantah_4.hide()
            # self.buttonLanjut_3.clicked.connect(self.simpanKantorSettings)
        except Exception:
            logMessage("Jumlah kantor tidak terbaca")
        if self.comboBoxKantah_3.count() > 0:
            return True

    def pengaturan_lokasi(self):
        self.accept()
        if self.atur_lokasi is None:
            self.atur_lokasi = PengaturanLokasiDialog()
        add_google_basemap()
        self.atur_lokasi.show()

    def simpanKantorSettings(self):
        index = self.comboBoxKantah_3.currentIndex()
        kantor = self.jsonKantor[index]
        namaKantorTerpilih = kantor["nama"]
        idKantorTerpilih = kantor["kantorID"]
        idTipeKantorTerpilih = kantor["tipeKantorId"]

        storeSetting("kantorterpilih", kantor)

        provinsi = self.simpanProvinsiSettings(idKantorTerpilih, idTipeKantorTerpilih)
        kabupaten = self.simpanKabupatenSettings(
            idKantorTerpilih, idTipeKantorTerpilih, provinsi["PROPINSIID"]
        )
        kecamatan = self.simpanKecamatanSettings(
            idKantorTerpilih, idTipeKantorTerpilih, kabupaten["KABUPATENID"]
        )
        desa = self.simpanDesaSettings(
            idKantorTerpilih, idTipeKantorTerpilih, kecamatan["KECAMATANID"]
        )

        self.simpanSistemKoordinat(desa["ZONATM3"])
        self.simpanUserSettings()
        self.accept()
        self.panel.switch_panel(1)

    def simpanProvinsiSettings(self, kantor_id, tipe_kantor_id):
        response = endpoints.get_provinsi_by_kantor(kantor_id, str(tipe_kantor_id))
        response_json = json.loads(response.content)
        provinsi = None
        if response_json and len(response_json["PROPINSI"]):
            provinsi = response_json["PROPINSI"][0]
            storeSetting("provinsiterpilih", provinsi)
        return provinsi

    def simpanKabupatenSettings(self, kantor_id, tipe_kantor_id, provinsi_id):
        response = endpoints.get_kabupaten_by_kantor(
            kantor_id, str(tipe_kantor_id), provinsi_id
        )
        response_json = json.loads(response.content)
        kabupaten = None
        print(len(response_json["KABUPATEN"]))
        if response_json and len(response_json["KABUPATEN"]):
            kabupaten = response_json["KABUPATEN"][0]
            storeSetting("kabupatenterpilih", kabupaten)
        return kabupaten

    def simpanKecamatanSettings(self, kantor_id, tipe_kantor_id, kabupaten_id):
        response = endpoints.get_kecamatan_by_kantor(
            kantor_id, str(tipe_kantor_id), kabupaten_id
        )
        response_json = json.loads(response.content)
        kecamatan = None
        print(len(response_json["KECAMATAN"]))
        if response_json and len(response_json["KECAMATAN"]):
            kecamatan = response_json["KECAMATAN"][0]
            storeSetting("kecamatanterpilih", kecamatan)
        return kecamatan

    def simpanDesaSettings(self, kantor_id, tipe_kantor_id, kecamatan_id):
        response = endpoints.get_desa_by_kantor(
            kantor_id, str(tipe_kantor_id), kecamatan_id
        )
        response_json = json.loads(response.content)
        desa = None
        # print("========================", response_json['DESA'][0])
        if response_json and len(response_json["DESA"]):
            desa = response_json["DESA"][0]
            storeSetting("desaterpilih", desa)
        return desa

    def simpanSistemKoordinat(self, tm3_zone):
        print("ZONA TM-3", tm3_zone)
        try:
            epsg = get_epsg_from_tm3_zone(tm3_zone)
            set_project_crs_by_epsg(epsg)
        except Exception:
            logMessage("Zona TM-3 tidak ditemukan pada data Desa di Server")

    def simpanUserSettings(self):
        username = app_state.get("username")
        kantorID = readSetting("kantorterpilih")[0]
        print(username, kantorID)
        # response = endpoints.get_user_entity_by_username(username.value, kantorID)
        # response_json = json.loads(response.content)
        # print(response_json[0]["nama"])
        # storeSetting("listkantor", response_json)
