import json
import os
from datetime import datetime

from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import pyqtSignal
from qgis.utils import iface

from .api import endpoints
from .utils import readSetting, storeSetting
from .memo import app_state

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/informasi_persil.ui")
)


class InformasiPersil(QtWidgets.QDialog, FORM_CLASS):
    """Dialog for Informasi Persil"""

    closingPlugin = pyqtSignal()

    def __init__(
        self,
        nomor_berkas,
        tahun_berkas,
        kantor_id,
        tipe_berkas,
        sistem_koordinat,
        jumlah_persil_baru,
        desa_id,
        gambar_ukur,
        new_parcels,
        old_parcels,
        parent=iface.mainWindow(),
    ):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        super(InformasiPersil, self).__init__(parent)
        self.setupUi(self)

        self._nomor_berkas = nomor_berkas
        self._tahun_berkas = tahun_berkas
        self._kantor_id = kantor_id
        self._tipe_berkas = tipe_berkas
        self._sistem_koordinat = "TM-3" if sistem_koordinat == "TM3" else "Non TM-3"
        self._jumlah_persil_baru = jumlah_persil_baru
        self._desa_id = desa_id
        self._gambar_ukur = gambar_ukur
        self._new_parcels = new_parcels
        self._old_parcels = old_parcels

        self._data_spasial = {}
        self._data_spasial_parcels = {}
        self._landuse_data = {}
        self._alat_ukur = []
        self._metode_ukur = []

        self._setup_workpanel()

        self.table_daftar_persil.itemClicked.connect(self._handle_persil_selected)
        self.combo_penggunaan_umum.currentIndexChanged.connect(
            self._populate_penggunaan_khusus
        )
        self.btn_simpan.clicked.connect(self.simpan)
        self.btn_tutup.clicked.connect(self.close)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def _fetch_process_info(self):
        response = endpoints.get_process_info(
            self._nomor_berkas,
            self._tahun_berkas,
            self._kantor_id,
            self._desa_id,
            self._gambar_ukur,
        )
        process_info = json.loads(response.content)
        print("process_info", process_info)
        self._data_spasial = process_info

    def _fetch_landuse_data(self):
        landuse_data = readSetting("landusedata", {})
        if not landuse_data:
            response = endpoints.get_landuse_data()
            landuse_data = json.loads(response.content)
            storeSetting("landusedata", landuse_data)
        print("landuse_data", landuse_data)
        self._landuse_data = landuse_data
        return landuse_data

    def _fetch_alat_ukur(self):
        alat_ukur = readSetting("alatukur", [])
        if not alat_ukur:
            response = endpoints.get_alat_ukur()
            alat_ukur = json.loads(response.content)
            storeSetting("alatukur", alat_ukur)
        print("alat_ukur", alat_ukur)
        self._alat_ukur = alat_ukur
        return alat_ukur

    def _fetch_metode_ukur(self):
        metode_ukur = readSetting("metodeukur", [])
        if not metode_ukur:
            response = endpoints.get_metode_ukur()
            metode_ukur = json.loads(response.content)
            storeSetting("metodeukur", metode_ukur)
        print("metode_ukur", metode_ukur)
        self._metode_ukur = metode_ukur
        return metode_ukur

    def _fetch_persil(self, persil_ids):
        response = endpoints.get_parcels(persil_ids)
        response_json = json.loads(response.content)
        print("data spasial persil", response_json)
        self._data_spasial_parcels = response_json
        return response_json

    def _setup_workpanel(self):
        self._fetch_process_info()

        self._populate_penggunaan_umum()
        self._populate_penggunaan_khusus()
        self._populate_alat_ukur()
        self._populate_metode_ukur()
        self._populate_table_persil()

    def _populate_penggunaan_umum(self):
        self.combo_penggunaan_umum.clear()
        if not self._landuse_data:
            self._fetch_landuse_data()

        tipe_land_generik = (
            self._landuse_data["TIPELANDGENERIK"]
            if "TIPELANDGENERIK" in self._landuse_data
            else []
        )
        for tipe in tipe_land_generik:
            self.combo_penggunaan_umum.addItem(tipe["KETERANGAN"])

    def _populate_penggunaan_khusus(self, landuse_id=None):
        self.combo_penggunaan_khusus.clear()
        current_umum_index = self.combo_penggunaan_umum.currentIndex()
        penggunaan_umum = self._landuse_data["TIPELANDGENERIK"][current_umum_index]

        selected_index = 0
        index = -1
        for row in self._landuse_data["TIPELANDUSE"]:
            if row["TIPEUSECODE"] == penggunaan_umum["TIPEUSECODE"]:
                self.combo_penggunaan_khusus.addItem(
                    row["LANDUSENAME"], {"landuse_id": row["LANDUSEID"]}
                )
                index += 1
            if row["LANDUSEID"] == landuse_id:
                selected_index == index
        self.combo_penggunaan_khusus.setCurrentIndex(selected_index)

    def _populate_alat_ukur(self):
        self.combo_alat_ukur.clear()
        if not self._alat_ukur:
            self._fetch_alat_ukur()

        for alat in self._alat_ukur:
            self.combo_alat_ukur.addItem(alat["ALATUKUR"])

    def _populate_metode_ukur(self):
        self.combo_metode_ukur.clear()
        if not self._metode_ukur:
            self._fetch_metode_ukur()

        for metode in self._metode_ukur:
            self.combo_metode_ukur.addItem(metode["METODUKUR"])

    def _populate_table_persil(self):
        self.table_daftar_persil.setRowCount(0)

        n_parcels = 0
        parcels = []
        if self._new_parcels:
            n_parcels += len(self._new_parcels)
            parcels = [str(p) for p in self._new_parcels]
        if self._old_parcels:
            n_parcels += len(self._old_parcels)
            for p in self._old_parcels:
                parcels.append(str(p))

        if not n_parcels:
            return

        parcels = self._fetch_persil(parcels)
        new_parcels = parcels["PERSILBARU"]
        if not new_parcels:
            return

        columns = [
            col
            for index, col in enumerate(new_parcels[0].keys())
            # if index not in [0, 4, 5]
        ]
        self.table_daftar_persil.setColumnCount(len(columns))
        self.table_daftar_persil.setHorizontalHeaderLabels(columns)

        for item in new_parcels:
            pos = self.table_daftar_persil.rowCount()
            self.table_daftar_persil.insertRow(pos)

            for index, col in enumerate(columns):
                self.table_daftar_persil.setItem(
                    pos, index, QtWidgets.QTableWidgetItem(str(item[col]))
                )

        self.table_daftar_persil.setColumnHidden(0, True)
        self.table_daftar_persil.setColumnHidden(4, True)
        self.table_daftar_persil.setColumnHidden(5, True)

    def _handle_persil_selected(self, selected):
        print("triggered")
        if (
            not selected
            or "PERSILBARU" not in self._data_spasial_parcels
            or not self._data_spasial_parcels["PERSILBARU"]
        ):
            return

        self.table_daftar_persil.setColumnHidden(0, False)
        selected_row = self.table_daftar_persil.selectedItems()
        current_persil = selected_row[0].text()
        self.table_daftar_persil.setColumnHidden(0, True)
        response = endpoints.get_parcel_info(current_persil)
        response_json = json.loads(response.content)
        print("parcel info", response_json)

        if "PERSILBARU" not in response_json:
            return

        self.input_nama_jalan.setText(response_json["PERSILBARU"][0]["NAMAJALAN"])
        self.input_nomor.setText(response_json["PERSILBARU"][0]["NOMORBANGUNAN"])
        self.input_alamat_tambahan.setText(
            response_json["PERSILBARU"][0]["ALAMATTAMBAHAN"]
        )
        self.input_peta.setText(response_json["PERSILBARU"][0]["PETA"])
        self.input_nomor_peta_lokal.setText(response_json["PERSILBARU"][0]["NOPETA"])
        self.input_nomor_lembar.setText(response_json["PERSILBARU"][0]["LEMBAR"])
        self.input_nomor_kotak.setText(response_json["PERSILBARU"][0]["KOTAK"])

        landuse_id = response_json["PERSILBARU"][0]["GUNATANAHKHUSUSID"]
        print("landuse_id", landuse_id)
        if landuse_id:
            # self.combo_penggunaan_umum
            guna_tanah_umum_id = response_json["PERSILBARU"][0]["GUNATANAHUMUMID"]
            print("guna_tanah_umum_id", guna_tanah_umum_id)
            for index, row in enumerate(self._landuse_data["TIPELANDGENERIK"]):
                if row["TIPEUSECODE"] == guna_tanah_umum_id:
                    self.combo_penggunaan_umum.setCurrentIndex(index)
                    break
            self._populate_penggunaan_khusus(landuse_id)

    def simpan(self):
        data = {"PERSIL": [], "GUNATANAH": [], "ALAMAT": []}

        now = datetime.now().isoformat()
        self.table_daftar_persil.setColumnHidden(0, False)
        selected_row = self.table_daftar_persil.selectedItems()

        if not selected_row:
            return

        selected_persil_id = selected_row[0].text()

        selected_persil = [
            row
            for row in self._data_spasial_parcels["PERSILBARU"]
            if row["PERSILID"] == selected_persil_id
        ]
        if not selected_persil:
            return

        nomor = ""
        if selected_persil[0]["NOMOR"]:
            nomor = str(selected_persil[0]["NOMOR"])
        if nomor and len(nomor) == 14:
            nomor = nomor[5:14]

        user = app_state.get("pegawai", {})
        user_id = (
            user.value["userId"]
            if user.value and "userId" in user.value.keys() and user.value["userId"]
            else ""
        )

        data["PERSIL"].append(
            {
                "PERSILID": selected_persil[0]["PERSILID"],
                "WILAYAHID": selected_persil[0]["WILAYAHID"],
                "NOMOR": nomor,
                "ALAMATID": selected_persil[0]["ALAMATID"],
                "PETA": self.input_peta.text(),
                "TIPEHAK": "",
                "VALIDSEJAK": "",
                "VALIDSAMPAI": "",
                "NOPETA": self.input_nomor_peta_lokal.text(),
                "USERUPDATE": user_id,
                "LASTUPDATE": now,
            }
        )

        data["ALAMAT"].append(
            {
                "ALAMATID": (
                    selected_persil[0]["ALAMATID"]
                    if selected_persil[0]["ALAMATID"]
                    else ""
                ),
                "NAMAJALAN": self.input_nama_jalan.text(),
                "NOMORBANGUNAN": self.input_nomor.text(),
                "ALAMATTAMBAHAN": self.input_alamat_tambahan.text(),
                "KODEPOS": self.input_kode_pos.text(),
                "WILAYAHID": selected_persil[0]["WILAYAHID"],
                "USERUPDATE": user_id,
                "LASTUPDATE": now,
            }
        )

        gunatanah_khusus = self.combo_penggunaan_khusus.currentData()
        data["GUNATANAH"].append(
            {
                "PENGGUNAANTANAHID": "",
                "PERSILID": selected_persil[0]["PERSILID"],
                "GUNATANAHKHUSUSID": gunatanah_khusus["landuse_id"],
                "USERUPDATE": user_id,
                "LASTUPDATE": now,
            }
        )

        response = endpoints.update_persil(data)
        print(response.content)
        response_str = response.content.decode("UTF-8")
        if response_str.split(":")[-1] == "OK":
            QtWidgets.QMessageBox.information(self, "Sukses", "Persil telah di simpan")
        else:
            QtWidgets.QMessageBox.critical(self, "Error", response_str)
