import os
import json

from qgis.PyQt import QtWidgets, uic
from qgis.core import QgsProject
from qgis.PyQt.QtGui import QDesktopServices

from qgis.PyQt.QtCore import pyqtSignal, QUrl
from qgis.utils import iface

from .login import LoginDialog
from .memo import app_state
from .topology import quick_check_topology

# using utils
from .utils import (
    icon,
    readSetting,
    storeSetting,
    get_epsg_from_tm3_zone,
    set_project_crs_by_epsg,
    get_project_crs,
    sdo_to_layer,
)
from .api import endpoints

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/panel_kerjav2.ui")
)


STACKWIDGET_LOKASI = 0
STACKWIDGET_RUTIN = 1


class Workpanel(QtWidgets.QDockWidget, FORM_CLASS):
    """Dialog for Peta Bidang"""

    closingPlugin = pyqtSignal()

    def __init__(self, parent=iface.mainWindow()):
        super(Workpanel, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(icon("icon.png"))
        self.stackedWidget.setCurrentIndex(0)
        self.project = QgsProject

        self.loginaction = LoginDialog()

        self.current_kantor_id = None
        self.current_tipe_kantor_id = None
        self.current_provinsi_id = None
        self.current_kabupaten_id = None
        self.current_kecamatan_id = None
        self.current_kelurahan_id = None

        self.current_berkas = None
        self.current_layers = []

        self.mulaiGeokkp.clicked.connect(self.login_geokkp)
        self.bantuanGeokkp.clicked.connect(self.openhelp)
        self.btn_simpan_area_kerja.clicked.connect(self.simpan_area_kerja)
        self.main_tab.currentChanged.connect(self.setup_workpanel)

        self.combo_kantor.currentIndexChanged.connect(self.kantor_changed)
        self.combo_provinsi.currentIndexChanged.connect(self.provinsi_changed)
        self.combo_kabupaten.currentIndexChanged.connect(self.kabupaten_changed)
        self.combo_kecamatan.currentIndexChanged.connect(self.kecamatan_changed)
        self.combo_kelurahan.currentIndexChanged.connect(self.kelurahan_changed)

        self.btn_rutin_cari.clicked.connect(self.cari_berkas_rutin)
        self.btn_rutin_mulai.clicked.connect(self.mulai_berkas_rutin)
        self.btn_rutin_tutup.clicked.connect(self.tutup_berkas_rutin)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        self.stackedWidget.setCurrentIndex(0)
        event.accept()

    def login_geokkp(self):
        if self.loginaction is None:
            self.loginaction = LoginDialog()
        self.loginaction.show()

    def show_workpanel(self):
        workspace = readSetting("workspace_terpilih", "rutin")
        widget = getattr(self, workspace, self.rutin)
        self.stackedWidget.setCurrentWidget(widget)

    def switch_panel(self, page):
        self.stackedWidget.setCurrentIndex(page)

    def openhelp(self):
        QDesktopServices.openUrl(QUrl("https://geokkp-gis.github.io/docs/"))
        pass

    def setup_workpanel(self, index):
        print(index)
        if index == STACKWIDGET_LOKASI:
            self.setup_workspace_lokasi()

    def setup_workspace_lokasi(self):
        self.populate_kantor()

    def kantor_changed(self, index):
        data_kantor = readSetting("listkantor", [])
        kantor = data_kantor[index]
        self.current_kantor_id = kantor["kantorID"]
        self.current_tipe_kantor_id = kantor["tipeKantorId"]
        storeSetting("kantorterpilih", kantor)
        self.populate_provinsi(self.current_kantor_id, self.current_tipe_kantor_id)

    def provinsi_changed(self, index):
        data_provinsi = readSetting("listprovinsi", [])
        provinsi = data_provinsi[index]
        self.current_provinsi_id = provinsi["PROPINSIID"]
        storeSetting("provinsiterpilih", provinsi)
        self.populate_kabupaten(
            self.current_kantor_id,
            self.current_tipe_kantor_id,
            self.current_provinsi_id,
        )

    def kabupaten_changed(self, index):
        data_kabupaten = readSetting("listkabupaten", [])
        kabupaten = data_kabupaten[index]
        self.current_kabupaten_id = kabupaten["KABUPATENID"]
        storeSetting("kabupatenterpilih", kabupaten)
        self.populate_kecamatan(
            self.current_kantor_id,
            self.current_tipe_kantor_id,
            self.current_kabupaten_id,
        )

    def kecamatan_changed(self, index):
        data_kecamatan = readSetting("listkecamatan", [])
        kecamatan = data_kecamatan[index]
        self.current_kecamatan_id = kecamatan["KECAMATANID"]
        storeSetting("kecamatanterpilih", kecamatan)
        self.populate_kelurahan(
            self.current_kantor_id,
            self.current_tipe_kantor_id,
            self.current_kecamatan_id,
        )

    def kelurahan_changed(self, index):
        data_kelurahan = readSetting("listkelurahan", [])
        kelurahan = data_kelurahan[index]
        self.current_kelurahan_id = kelurahan["DESAID"]
        storeSetting("kelurahanterpilih", kelurahan)

    def populate_kantor(self):
        self.combo_kantor.clear()
        data_kantor = readSetting("listkantor", [])
        for kantor in data_kantor:
            self.combo_kantor.addItem(kantor["nama"])

    def populate_provinsi(self, kantor_id, tipe_kantor_id):
        self.combo_provinsi.clear()
        response = endpoints.get_provinsi_by_kantor(kantor_id, str(tipe_kantor_id))
        response_json = json.loads(response.content)
        if response_json and len(response_json["PROPINSI"]):
            data_provinsi = response_json["PROPINSI"]
            storeSetting("listprovinsi", data_provinsi)
            for provinsi in data_provinsi:
                self.combo_provinsi.addItem(provinsi["PROPNAMA"])

    def populate_kabupaten(self, kantor_id, tipe_kantor_id, provinsi_id):
        self.combo_kabupaten.clear()
        response = endpoints.get_kabupaten_by_kantor(
            kantor_id, str(tipe_kantor_id), provinsi_id
        )
        response_json = json.loads(response.content)
        if response_json and len(response_json["KABUPATEN"]):
            data_kabupaten = response_json["KABUPATEN"]
            storeSetting("listkabupaten", data_kabupaten)
            for kabupaten in data_kabupaten:
                self.combo_kabupaten.addItem(kabupaten["KABUNAMA"])

    def populate_kecamatan(self, kantor_id, tipe_kantor_id, kabupaten_id):
        self.combo_kecamatan.clear()
        response = endpoints.get_kecamatan_by_kantor(
            kantor_id, str(tipe_kantor_id), kabupaten_id
        )
        response_json = json.loads(response.content)
        if response_json and len(response_json["KECAMATAN"]):
            data_kecamatan = response_json["KECAMATAN"]
            storeSetting("listkecamatan", data_kecamatan)
            for kecamatan in data_kecamatan:
                self.combo_kecamatan.addItem(kecamatan["KECANAMA"])

    def populate_kelurahan(self, kantor_id, tipe_kantor_id, kecamatan_id):
        self.combo_kelurahan.clear()
        response = endpoints.get_desa_by_kantor(
            kantor_id, str(tipe_kantor_id), kecamatan_id
        )
        response_json = json.loads(response.content)
        if response_json and len(response_json["DESA"]):
            data_kelurahan = response_json["DESA"]
            storeSetting("listkelurahan", data_kelurahan)
            for kelurahan in data_kelurahan:
                self.combo_kelurahan.addItem(kelurahan["DESANAMA"])

    def simpan_area_kerja(self):
        kabupaten = readSetting("kabupatenterpilih")
        kelurahan = readSetting("kelurahanterpilih")
        tm3_zone = (
            kelurahan["ZONATM3"] if kelurahan["ZONATM3"] else kabupaten["ZONATM3"]
        )
        if tm3_zone:
            epsg = get_epsg_from_tm3_zone(tm3_zone, False)
            self.set_project_crs(epsg)
            self.get_batas_desa(kelurahan["DESAID"], epsg)
        else:
            QtWidgets.QMessageBox.critical(
                None, "Error", "Zona TM3 Tidak tersedia di server"
            )

    def set_project_crs(self, epsg):
        set_project_crs_by_epsg(f"EPSG:{epsg}")

    def get_batas_desa(self, wilayah_id, epsg):
        response = endpoints.get_wilayah_sdo(wilayah_id, "Desa", epsg)
        response_json = json.loads(response.content)
        if response_json["status"] and len(response_json["wilayahs"]):
            layer = sdo_to_layer(
                response_json["wilayahs"], "Batas Desa", f"EPSG:{epsg}"
            )
            layer.setReadOnly(True)
            QgsProject.instance().addMapLayer(layer)
        else:
            QtWidgets.QMessageBox.critical(None, "Error", "Desa tidak ditemukan")

    def cari_berkas_rutin(self):
        # TODO implement pagiation
        no_berkas = self.input_rutin_no_berkas.text()
        th_berkas = self.input_rutin_th_berkas.text()
        response = endpoints.get_berkas(
            nomor_berkas=no_berkas,
            tahun_berkas=th_berkas,
            kantor_id=self.current_kantor_id,
            tipe_kantor_id=str(self.current_tipe_kantor_id),
        )
        response_json = json.loads(response.content)
        self.populate_berkas_rutin(response_json["BERKASSPATIAL"])

    def populate_berkas_rutin(self, data):
        self.table_rutin.setRowCount(0)
        # self.table_rutin.setColumnCount(4)
        # self.table_rutin.setColumnHidden(0, True)
        for item in data:
            pos = self.table_rutin.rowCount()
            self.table_rutin.insertRow(pos)

            self.table_rutin.setItem(
                pos, 0, QtWidgets.QTableWidgetItem(str(item["NOMOR"]))
            )
            self.table_rutin.setItem(
                pos, 1, QtWidgets.QTableWidgetItem(str(item["TAHUN"]))
            )
            self.table_rutin.setItem(
                pos, 2, QtWidgets.QTableWidgetItem(item["OPERASISPASIAL"])
            )

    def mulai_berkas_rutin(self):
        if self.current_berkas is not None:
            QtWidgets.QMessageBox.critical(
                None,
                "Tutup berkas",
                "Tutup berkas yang sedang dikerjakan terlebih dahulu",
            )
            return
        selected_row = self.table_rutin.selectedItems()
        no_berkas = selected_row[0].text()
        th_berkas = selected_row[1].text()
        username = app_state.get("username").value

        response_start_berkas = endpoints.start_berkas_spasial(
            nomor_berkas=no_berkas,
            tahun_berkas=th_berkas,
            kantor_id=self.current_kantor_id,
            tipe_kantor_id=str(self.current_tipe_kantor_id),
            username=username,
        )
        response_start_berkas_json = json.loads(response_start_berkas.content)
        self.current_berkas = response_start_berkas_json
        print(self.current_berkas)

        if self.current_berkas["valid"]:
            lanjut_blanko = True
            is_e_sertifikat = readSetting("isESertifikat")
            if is_e_sertifikat and self.tipe_kantor_id not in ["1", "2"]:
                response_blanko = endpoints.get_blanko_by_berkas_id(
                    berkas_id=self.current_berkas["BERKASID"]
                )
                response_blanko_json = json.loads(response_blanko.content)
                if len(response_blanko_json["BLANKO"]) > 0:
                    lanjut_blanko = True
                else:
                    lanjut_blanko = False

            if (
                self.current_berkas["kodeSpopp"]
                in [
                    "SPOPP-3.46.3",
                    "SPOPP-3.09.9",
                    "SPOPP-3.09.1",
                    "SPOPP-3.09.2",
                    "SPOPP-3.18.1",
                    "SPOPP-3.12.1",
                ]
                or lanjut_blanko
            ):
                if self.current_berkas["newGugusId"] != "":
                    if self.current_berkas["tipeBerkas"] != "DAG":
                        gugus_id = self.current_berkas["newGugusId"]
                        response_spatial_sdo = endpoints.get_spatial_document_sdo(
                            gugus_ids=[gugus_id]
                        )
                        response_spatial_sdo_json = json.loads(
                            response_spatial_sdo.content
                        )
                        print(response_spatial_sdo_json)

                        epsg = get_project_crs()
                        layer = sdo_to_layer(
                            response_spatial_sdo_json["geoKkpPolygons"],
                            name="Batas Persil",
                            symbol="simplepersil.qml",
                            crs=epsg,
                        )
                        self.current_layers.append(layer)
                else:
                    if self.current_berkas["oldGugusIds"]:
                        gugus_ids = [
                            str(id) for id in self.current_berkas["oldGugusIds"]
                        ]
                        response_spatial_sdo = endpoints.get_spatial_document_sdo(
                            gugus_ids=[gugus_id], include_riwayat=True
                        )
                        response_spatial_sdo_json = json.loads(
                            response_spatial_sdo.content
                        )
                        print(response_spatial_sdo_json)
                        epsg = get_project_crs()
                        layer = sdo_to_layer(
                            response_spatial_sdo_json["geoKkpPolygons"],
                            name="Batas Persil",
                            symbol="simplepersil.qml",
                            crs=epsg,
                        )
                        self.current_layers.append(layer)
                    else:
                        # TODO: Add new blank layer
                        pass

                self.btn_rutin_cari.setDisabled(True)
                self.btn_rutin_mulai.setDisabled(True)
                self.input_rutin_no_berkas.setDisabled(True)
                self.input_rutin_th_berkas.setDisabled(True)

                if self.current_berkas["tipeBerkas"] == "DAG":
                    # TODO: Add input gambar denah
                    pass
            else:
                QtWidgets.QMessageBox.warning(
                    None, "Perhatian", "Lakukan registrasi blanko terlebih dahulu"
                )
        else:
            message = "\n".join(self.current_berkas["errorStack"])
            QtWidgets.QMessageBox.critical(None, "Error", message)

    def simpan_berkas_rutin(self):
        if self.current_berkas and self.current_berkas["tipeBerkas"] == "DAG":
            # TODO: Add input gambar denah
            return

        topo_error_message = []
        for layer in self.current_layers:
            valid, num = quick_check_topology(layer)
            if not valid:
                message = f"Ada {num} topology error di layer {layer.name()}"
                topo_error_message.append(message)

        if topo_error_message:
            QtWidgets.QMessageBox.warning(
                None, "Perhatian", topo_error_message.join("\n")
            )
            return

    def tutup_berkas_rutin(self):
        response_tutup_berkas = endpoints.stop_berkas(
            nomor_berkas=self.current_berkas["nomorBerkas"],
            tahun_berkas=self.current_berkas["tahunBerkas"],
            kantor_id=self.current_kantor_id,
        )
        response_tutup_berkas_json = json.loads(response_tutup_berkas.content)
        if response_tutup_berkas_json:
            self.current_berkas = None
            layer_ids = [layer.id() for layer in self.current_layers]
            self.project.instance().removeMapLayers(layer_ids)
            iface.mapCanvas().refresh()
