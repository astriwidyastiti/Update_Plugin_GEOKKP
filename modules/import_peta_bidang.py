import os
import json
import shapely
import shapely.wkt
import hashlib

from qgis.PyQt import QtWidgets, uic
from qgis.core import QgsProject, QgsWkbTypes, QgsVectorLayer
from qgis.PyQt.QtCore import pyqtSignal
from qgis.utils import iface

from .utils import (
    readSetting,
    storeSetting,
    get_nlp,
    get_nlp_index,
    get_epsg_from_tm3_zone,
)
from .api import endpoints
from .memo import app_state

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/import_peta_bidang.ui")
)

DS_PERSIL_EDIT_COLUMNS = [
    "OID",
    "REGID",
    "NIB",
    "LUAST",
    "LABEL",
    "AREA",
    "BOUNDARY",
    "TEXT",
    "KETERANGAN",
    "HEIGHT",
    "ORIENTATION",
    "NOLEMBAR",
    "KOTAK",
]
DS_PERSIL_BARU_COLUMNS = [
    "OID",
    "LABEL",
    "AREA",
    "BOUNDARY",
    "TEXT",
    "KETERANGAN",
    "HEIGHT",
    "ORIENTATION",
    "URUT",
    "NOLEMBAR",
    "KOTAK",
]
DS_PERSIL_POLIGON_COLUMNS = [
    "Key",
    "Type",
    "Label",
    "Height",
    "Orientation",
    "Boundary",
    "Text",
]


class ImportPetaBidang(QtWidgets.QWidget, FORM_CLASS):
    """Dialog for Peta Bidang"""

    closingPlugin = pyqtSignal()
    writeLeftStatus = pyqtSignal(str)
    writeRightStatus = pyqtSignal(str)
    writeErrorLog = pyqtSignal(str)
    changeTabIndex = pyqtSignal(int)
    processed = pyqtSignal(object)

    def __init__(
        self,
        peta_bidang,
        tipe_sistem_koordinat="TM3",
        is_invent=False,
        current_layers=[],
        parent=iface.mainWindow(),
    ):
        super(ImportPetaBidang, self).__init__(parent)

        self._ent_dataset = {
            "PersilEdit": [],
            "PersilBaru": [],
            "PersilInventaris": [],
            "Poligon": [],
            "Garis": [],
            "Teks": [],
            "Titik": [],
            "Dimensi": [],
        }
        self._current_kantor_id = ""
        self._current_tipe_kantor_id = ""
        self._current_table = ""
        self._current_layers = current_layers

        self._pbt = peta_bidang
        self._sistem_koordinat = tipe_sistem_koordinat
        self._is_invent = is_invent
        self._jml_rincikan = 0

        if peta_bidang:
            self._desa_id = peta_bidang["wilayahId"]
            self._gugus_id = peta_bidang["gugusId"]
            self._new_parcels = peta_bidang["newParcels"]
            self._dokumen_pengukuran_id = peta_bidang["dokumenPengukuranId"]
            self._dt_wilayah = self._get_wilayah_prior(peta_bidang["wilayahId"])
        else:
            self._desa_id = ""
            self._gugus_id = ""
            self._new_parcels = []
            self._dokumen_pengukuran_id = ""
            self._dt_wilayah = []

        self.setupUi(self)

        self.combo_lihat_data.currentIndexChanged.connect(self._lihat_data_changed)
        self.combo_provinsi.currentIndexChanged.connect(self._provinsi_changed)
        self.combo_kabupaten.currentIndexChanged.connect(self._kabupaten_changed)
        self.combo_kecamatan.currentIndexChanged.connect(self._kecamatan_changed)
        self.btn_validasi.clicked.connect(self._handle_validasi)
        self.btn_proses.clicked.connect(self._handle_process)

        self._get_current_settings()
        self.setup_workpanel()

    def _get_wilayah_prior(self, wilayah_id=None):
        if not wilayah_id:
            return []

        response = endpoints.get_wilayah_prior(wilayah_id)
        self._wilayah_prior = json.loads(response.content)
        return self._wilayah_prior

    def closeEvent(self, event):
        self.closingPlugin.emit()
        self.stackedWidget.setCurrentIndex(0)
        event.accept()

    def setup_workpanel(self):

        self._populate_tm3()
        self._populate_program(self._pbt["programId"])
        self.combo_kegiatan.setDisabled(True)

        if self._pbt["tipeProdukId"] == "67":
            self.combo_kecamatan.hide()
            self.combo_kelurahan.hide()
            self.label_kelurahan.hide()
            self.label_kelurahan.hide()

        print(self._dt_wilayah)

        if not self._desa_id and len(self._dt_wilayah) == 4:
            provinsi = [f for f in self._dt_wilayah if f["TIPEWILAYAHID"] == 1]
            if provinsi:
                self.combo_provinsi.addItem(
                    provinsi[0]["NAMA"], provinsi[0]["WILAYAHID"]
                )

            kabupaten = [f for f in self._dt_wilayah if f["TIPEWILAYAHID"] in [2, 3, 4]]
            if kabupaten:
                self.combo_kabupaten.addItem(
                    kabupaten[0]["NAMA"], kabupaten[0]["WILAYAHID"]
                )

            kecamatan = [f for f in self._dt_wilayah if f["TIPEWILAYAHID"] == 5]
            if kecamatan:
                self.combo_kecamatan.addItem(
                    kecamatan[0]["NAMA"], kecamatan[0]["WILAYAHID"]
                )

            kelurahan = [f for f in self._dt_wilayah if f["TIPEWILAYAHID"] in [6, 7]]
            if kelurahan:
                self.combo_kelurahan.addItem(
                    kelurahan[0]["NAMA"], kelurahan[0]["WILAYAHID"]
                )
        else:
            self._populate_provinsi(
                self._current_kantor_id, self._current_tipe_kantor_id
            )

        if not self._is_invent:
            self.combo_lihat_data.addItems(["Persil Baru", "Persil Edit"])
            self._fill_new_persil()

            self._hapus_persil_terdaftar()
            self._autofill_persildata()
            self._populate_table()

            if self._ent_dataset["PersilEdit"]:
                self.combo_provinsi.setDisabled(True)
                self.combo_kabupaten.setDisabled(True)
                self.combo_kecamatan.setDisabled(True)
                self.combo_kelurahan.setDisabled(True)
                self.spin_jumlah_bidang.setValue(len(self._ent_dataset["PersilEdit"]))

                self.combo_lihat_data.setCurrentIndex(1)
        else:
            self.combo_lihat_data.addItem("Persil Inventaris")
            self._fill_new_rincikan()
            self._fill_persil_rincikan()
            self._fill_pemilik_rincikan()

    def _get_current_settings(self):
        self._current_kantor = readSetting("kantorterpilih")
        self._provinsi_by_kantor = readSetting("provinsibykantor", {})
        self._kabupaten_by_provinsi = readSetting("kabupatenbyprovinsi", {})
        self._kecamatan_by_kabupaten = readSetting("kecamatanbykabupaten", {})
        self._kelurahan_by_kecamatan = readSetting("kelurahanbykecamatan", {})

        if not self._current_kantor or "kantorID" not in self._current_kantor:
            return

        self._current_kantor_id = self._current_kantor["kantorID"]
        self._current_tipe_kantor_id = str(self._current_kantor["tipeKantorId"])

    def _lihat_data_changed(self):
        table_name = self.combo_lihat_data.currentText().replace(" ", "")
        self._current_table = table_name
        self._populate_table()

    def _clear_combobox(self, level):
        combo = [
            self.combo_kelurahan,
            self.combo_kecamatan,
            self.combo_kabupaten,
            self.combo_provinsi,
        ]
        for i in range(0, level):
            combo[i].blockSignals(True)
        for i in range(0, level):
            combo[i].clear()
        for i in range(0, level):
            combo[i].blockSignals(False)

    def _populate_provinsi(self, kantor_id, tipe_kantor_id):
        self._clear_combobox(4)
        if (
            kantor_id in self._provinsi_by_kantor.keys()
            and self._provinsi_by_kantor[kantor_id]
        ):
            data_provinsi = self._provinsi_by_kantor[kantor_id]
        else:
            response = endpoints.get_provinsi_by_kantor(kantor_id, str(tipe_kantor_id))
            response_json = json.loads(response.content)
            if response_json and len(response_json["PROPINSI"]):
                data_provinsi = response_json["PROPINSI"]
                self._provinsi_by_kantor[kantor_id] = data_provinsi
                storeSetting("provinsibykantor", self._provinsi_by_kantor)
            else:
                QtWidgets.QMessageBox.warning(
                    None,
                    "Data Provinsi",
                    "Tidak bisa membaca data provinsi dari server",
                )
                return

        for provinsi in data_provinsi:
            self.combo_provinsi.addItem(provinsi["PROPNAMA"], provinsi["PROPINSIID"])

    def _populate_kabupaten(self, kantor_id, tipe_kantor_id, provinsi_id):
        self._clear_combobox(3)
        if (
            provinsi_id in self._kabupaten_by_provinsi.keys()
            and self._kabupaten_by_provinsi[provinsi_id]
        ):
            data_kabupaten = self._kabupaten_by_provinsi[provinsi_id]
        else:
            response = endpoints.get_kabupaten_by_kantor(
                kantor_id, str(tipe_kantor_id), provinsi_id
            )
            response_json = json.loads(response.content)
            if response_json and len(response_json["KABUPATEN"]):
                data_kabupaten = response_json["KABUPATEN"]
                self._kabupaten_by_provinsi[provinsi_id] = data_kabupaten
                storeSetting("kabupatenbyprovinsi", self._kabupaten_by_provinsi)
            else:
                QtWidgets.QMessageBox.warning(
                    None,
                    "Data Kabupaten",
                    "Tidak bisa membaca data kabupaten dari server",
                )
                return

        for kabupaten in data_kabupaten:
            self.combo_kabupaten.addItem(
                kabupaten["KABUNAMA"], kabupaten["KABUPATENID"]
            )

    def _populate_kecamatan(self, kantor_id, tipe_kantor_id, kabupaten_id):
        self._clear_combobox(2)
        if (
            kabupaten_id in self._kecamatan_by_kabupaten.keys()
            and self._kecamatan_by_kabupaten[kabupaten_id]
        ):
            data_kecamatan = self._kecamatan_by_kabupaten[kabupaten_id]
        else:
            response = endpoints.get_kecamatan_by_kantor(
                kantor_id, str(tipe_kantor_id), kabupaten_id
            )
            response_json = json.loads(response.content)
            if response_json and len(response_json["KECAMATAN"]):
                data_kecamatan = response_json["KECAMATAN"]
                self._kecamatan_by_kabupaten[kabupaten_id] = data_kecamatan
                storeSetting("kecamatanbykabupaten", self._kecamatan_by_kabupaten)

            else:
                QtWidgets.QMessageBox.warning(
                    None,
                    "Data Kabupaten",
                    "Tidak bisa membaca data kabupaten dari server",
                )
                return

        for kecamatan in data_kecamatan:
            self.combo_kecamatan.addItem(
                kecamatan["KECANAMA"], kecamatan["KECAMATANID"]
            )

    def _populate_kelurahan(self, kantor_id, tipe_kantor_id, kecamatan_id):
        self._clear_combobox(1)
        if (
            kecamatan_id in self._kelurahan_by_kecamatan.keys()
            and self._kelurahan_by_kecamatan[kecamatan_id]
        ):
            data_kelurahan = self._kelurahan_by_kecamatan[kecamatan_id]
        else:
            response = endpoints.get_desa_by_kantor(
                kantor_id, str(tipe_kantor_id), kecamatan_id
            )
            response_json = json.loads(response.content)
            if response_json and len(response_json["DESA"]):
                data_kelurahan = response_json["DESA"]
                self._kelurahan_by_kecamatan[kecamatan_id] = data_kelurahan
                storeSetting("kelurahanbykecamatan", self._kelurahan_by_kecamatan)
            else:
                QtWidgets.QMessageBox.warning(
                    None,
                    "Data Kabupaten",
                    "Tidak bisa membaca data kabupaten dari server",
                )
                return

        for kelurahan in data_kelurahan:
            self.combo_kelurahan.addItem(kelurahan["DESANAMA"], kelurahan["DESAID"])

    def _provinsi_changed(self):
        current_provinsi_id = self.combo_provinsi.currentData()
        self._populate_kabupaten(
            self._current_kantor_id, self._current_tipe_kantor_id, current_provinsi_id
        )

    def _kabupaten_changed(self):
        current_kabupaten_id = self.combo_kabupaten.currentData()
        self._populate_kecamatan(
            self._current_kantor_id, self._current_tipe_kantor_id, current_kabupaten_id
        )

    def _kecamatan_changed(self):
        current_kecamatan_id = self.combo_kecamatan.currentData()
        self._populate_kelurahan(
            self._current_kantor_id, self._current_tipe_kantor_id, current_kecamatan_id
        )

    def _fill_new_rincikan(self):
        response = endpoints.get_rincikan_by_pbt(self._dokumen_pengukuran_id)
        response_json = json.loads(response.content)

        self._jml_rincikan = len(response_json["RINCIKANBARU"])
        for data in response_json["RINCIKANBARU"]:
            columns = list(data.keys())
            row = {
                "REGID": data[columns[0]],
                "NOMOR": data[columns[1]],
                "LUAST": data[columns[2]],
                "STATUS": data[columns[3]],
            }
            self._ent_dataset.append(row)

    def _fill_persil_rincikan(self):
        # TODO fill persil rincikan
        pass

    def _fill_pemilik_rincikan(self):
        # TODO fill persil rincikan
        pass

    def _populate_table(self):
        self.tabel_desain.setRowCount(0)
        data = self._ent_dataset[self._current_table]
        if data:
            columns = [col for col in data[0].keys() if col not in ["BOUNDARY", "TEXT"]]

            self.tabel_desain.setColumnCount(len(columns))
            self.tabel_desain.setHorizontalHeaderLabels(columns)

            for item in data:
                pos = self.tabel_desain.rowCount()
                self.tabel_desain.insertRow(pos)

                for index, col in enumerate(columns):
                    self.tabel_desain.setItem(
                        pos, index, QtWidgets.QTableWidgetItem(str(item[col]))
                    )

        jml_all = self.tabel_desain.rowCount()
        status = f"Jumlah {self.combo_lihat_data.currentText()} {jml_all}"
        print(status)
        self.writeRightStatus.emit(status)

    def _fill_new_persil(self):
        if not self._new_parcels:
            return

        parcels = [str(f) for f in self._new_parcels]
        response = endpoints.get_parcels(parcels)
        response_json = json.loads(response.content)

        for persil in response_json["PERSILBARU"]:
            columns = list(persil.keys())
            self._ent_dataset["PersilEdit"].append(
                {
                    "OID": persil[columns[0]],
                    "REGID": persil[columns[1]],
                    "NIB": persil[columns[2]],
                    "LUAST": 0,
                    "LABEL": "",
                    "AREA": 0,
                    "BOUNDARY": None,
                    "TEXT": "",
                    "KETERANGAN": "",
                    "HEIGHT": 0,
                    "ORIENTATION": 0,
                    "NOLEMBAR": "",
                    "KOTAK": "",
                }
            )

    def _autofill_persildata(self):
        for layer in self._current_layers:
            if not layer.name().startswith("(20100)"):
                continue

            features = layer.getFeatures()
            for feature in features:
                identifier = f"{layer.id()}|{feature.id()}".encode("utf-8")
                objectid = hashlib.md5(identifier).hexdigest().upper()

                point = feature.geometry().pointOnSurface().asPoint()
                teks = self.get_sdo_point(point)
                poli = self.get_sdo_polygon(feature)

                nib = feature.attribute("label") if feature.attribute("label") else ""
                height = (
                    float(feature.attribute("height"))
                    if feature.attribute("height")
                    else 0
                )
                orientation = (
                    float(feature.attribute("rotation"))
                    if feature.attribute("rotation")
                    else 0
                )

                if poli["batas"]:
                    row = {}
                    if len(self._ent_dataset["PersilEdit"]):
                        filtered = [
                            f
                            for f in self._ent_dataset["PersilEdit"]
                            if f["NIB"] == nib
                        ]
                        if filtered:
                            row = filtered[0]
                    luas_round = str(round(poli["luas"], 3))

                    sheet_number = get_nlp("250", point.x(), point.y())
                    box_number = ""
                    if len(sheet_number) == 15:
                        sheet_number = sheet_number[0:11]
                        box_number = get_nlp_index("1000", point.x(), point.y())

                    if row:
                        row[DS_PERSIL_EDIT_COLUMNS[0]] = objectid
                        row[DS_PERSIL_EDIT_COLUMNS[4]] = nib
                        row[DS_PERSIL_EDIT_COLUMNS[5]] = luas_round
                        row[DS_PERSIL_EDIT_COLUMNS[6]] = poli["batas"]
                        row[DS_PERSIL_EDIT_COLUMNS[7]] = teks
                        row[DS_PERSIL_EDIT_COLUMNS[8]] = "Tunggal"
                        row[DS_PERSIL_EDIT_COLUMNS[9]] = height
                        row[DS_PERSIL_EDIT_COLUMNS[10]] = orientation
                        row[DS_PERSIL_EDIT_COLUMNS[11]] = sheet_number
                        row[DS_PERSIL_EDIT_COLUMNS[12]] = box_number
                        self._ent_dataset["PersilEdit"].append(row)
                    else:
                        row[DS_PERSIL_BARU_COLUMNS[0]] = objectid
                        row[DS_PERSIL_BARU_COLUMNS[1]] = nib
                        row[DS_PERSIL_BARU_COLUMNS[2]] = luas_round
                        row[DS_PERSIL_BARU_COLUMNS[3]] = poli["batas"]
                        row[DS_PERSIL_BARU_COLUMNS[4]] = teks
                        row[DS_PERSIL_BARU_COLUMNS[5]] = "Tunggal"
                        row[DS_PERSIL_BARU_COLUMNS[6]] = height
                        row[DS_PERSIL_BARU_COLUMNS[7]] = orientation
                        try:
                            urut = int(nib.replace("#", ""))
                        except:
                            urut = 0
                        row[DS_PERSIL_BARU_COLUMNS[8]] = urut
                        row[DS_PERSIL_BARU_COLUMNS[9]] = sheet_number
                        row[DS_PERSIL_BARU_COLUMNS[10]] = box_number
                        self._ent_dataset["PersilBaru"].append(row)
                else:
                    continue

    def _hapus_persil_terdaftar(self):
        for layer in self._current_layers:
            if not layer.name().startswith("(20100)"):
                continue

            features = layer.getFeatures()
            for feature in features:
                identifier = f"{layer.id()}|{feature.id()}".encode("utf-8")
                objectid = hashlib.md5(identifier).hexdigest().upper()
                poli = self.get_sdo_polygon(feature)

                nib = feature.attribute("label") if feature.attribute("label") else ""
                height = (
                    float(feature.attribute("height"))
                    if feature.attribute("height")
                    else 0
                )
                orientation = (
                    float(feature.attribute("rotation"))
                    if feature.attribute("rotation")
                    else 0
                )

                if poli["batas"]:
                    row = {}
                    row[DS_PERSIL_POLIGON_COLUMNS[0]] = objectid
                    row[DS_PERSIL_POLIGON_COLUMNS[1]] = "BidangTanah"
                    row[DS_PERSIL_POLIGON_COLUMNS[2]] = nib
                    row[DS_PERSIL_POLIGON_COLUMNS[3]] = height
                    row[DS_PERSIL_POLIGON_COLUMNS[4]] = orientation
                    row[DS_PERSIL_POLIGON_COLUMNS[5]] = poli["batas"]
                    row[DS_PERSIL_POLIGON_COLUMNS[6]] = nib
                    self._ent_dataset["Poligon"].append(row)

    def get_sdo_point(self, point, srid=24091960):
        parcel_geom = {}
        parcel_geom["ElemArrayOfInts"] = None
        parcel_geom["OrdinatesArrayOfDoubles"] = None
        parcel_geom["Dimensionality"] = 0
        parcel_geom["LRS"] = 0
        parcel_geom["GeometryType"] = 0
        parcel_geom["SdoElemInfo"] = [1, 1, 1]
        parcel_geom["SdoOrdinates"] = [point.x(), point.y()]
        parcel_geom["SdoGtype"] = 2001
        parcel_geom["SdoSRID"] = srid
        parcel_geom["SdoSRIDAsInt"] = srid
        parcel_geom["SdoPoint"] = None
        return parcel_geom

    def _get_sdo_linestring(self, feature, srid=24091960):
        geom = {}
        geom["ElemArrayOfInts"] = None
        geom["OrdinatesArrayOfDoubles"] = None
        geom["Dimensionality"] = 0
        geom["LRS"] = 0
        geom["GeometryType"] = 0
        geom["SdoElemInfo"] = [1, 2, 1]
        geom["SdoGtype"] = 2002
        geom["SdoSRID"] = srid
        geom["SdoSRIDAsInt"] = srid
        geom["SdoPoint"] = None

        if feature.geometry().isMultipart():
            linestrings = feature.geometry().asMultiPolyline()
        else:
            linestrings = [feature.geometry().asPolyline()]

        coordinates = []
        for linestring in linestrings:
            for point in linestring:
                coordinates.append(point.x())
                coordinates.append(point.y())
        geom["SdoOrdinates"] = coordinates

        return geom

    def get_sdo_polygon(self, feature, srid=24091960):
        polygon_info = {"id": "", "batas": "", "luas": ""}

        polygon_info["batas"], polygon_info["luas"] = self.build_sdo_from_polygon(
            feature, srid
        )
        return polygon_info

    def build_sdo_from_polygon(self, feature, srid):
        geom_wkt = feature.geometry().asWkt()
        geom_shapely = shapely.wkt.loads(geom_wkt)
        geom_shapely_ccw = shapely.geometry.polygon.orient(geom_shapely, 1.0)

        luas = geom_shapely_ccw.area
        exterior = geom_shapely_ccw.exterior
        interiors = geom_shapely_ccw.interiors

        parcel_geom = {}
        parcel_geom["ElemArrayOfInts"] = None
        parcel_geom["OrdinatesArrayOfDoubles"] = None
        parcel_geom["Dimensionality"] = 0
        parcel_geom["LRS"] = 0
        parcel_geom["GeometryType"] = 0
        parcel_geom["SdoElemInfo"] = [1, 1003, 1]  # start from index 1
        prev_end = len(exterior.coords) * 2
        for interior in interiors:
            curr_start = prev_end + 1
            parcel_geom["SdoElemInfo"].append(
                curr_start
            )  # continue after exterior position
            parcel_geom["SdoElemInfo"].append(2003)
            parcel_geom["SdoElemInfo"].append(1)
            prev_end += len(interior.coords) * 2

        parcel_geom["SdoOrdinates"] = []
        parcel_geom["SdoGtype"] = 2003

        for coord in exterior.coords:
            parcel_geom["SdoOrdinates"] += coord

        for interior in interiors:
            for coord in interior.coords:
                parcel_geom["SdoOrdinates"] += coord

        parcel_geom["SdoSRID"] = srid
        parcel_geom["SdoSRIDAsInt"] = srid

        return parcel_geom, luas

    def _populate_tm3(self):
        for i in range(46, 55):
            for j in range(2, 0, -1):
                self.combo_tm3.addItem(f"TM3-{i}.{j}")

    def _populate_program(self, selected_id=None):
        kantor_id = self._current_kantor_id
        self.combo_kegiatan.clear()

        program = readSetting("listprogram", {})
        if not program or kantor_id not in program:
            response = endpoints.get_program_by_kantor(kantor_id)
            response_json = json.loads(response.content)
            program[kantor_id] = response_json["PROGRAM"]
            storeSetting("listprogram", program)

        selected_index = 0
        for index, item in enumerate(program[kantor_id]):
            self.combo_kegiatan.addItem(item["NAMA"], item["PROGRAMID"])
            if item["PROGRAMID"] == selected_id:
                selected_index = index
        self.combo_kegiatan.setCurrentIndex(selected_index)

    def _handle_validasi(self):
        valid = True
        msg = ""
        # TODO: extent check

        if self.combo_kegiatan.count() < 1:
            valid = False
            msg += "\nTidak ada SK Penlok yang sedang aktif, silahkan dibuat terlebih dahulu"

        if not self._is_invent:
            total_persil = len(
                self._ent_dataset["PersilBaru"] + self._ent_dataset["PersilEdit"]
            )
            response_limit_persil = endpoints.get_limit_persil_pbt(
                self._dokumen_pengukuran_id, self._current_kantor_id
            )
            limit_persil = int(response_limit_persil.content)

            if total_persil == 0:
                valid = False
                msg += "\nTidak ditemukan bidang tanah"
            if total_persil > limit_persil:
                valid = False
                msg += f"\nJumlah bidang tanah {total_persil} melebihi batas {limit_persil}"

            if self.spin_jumlah_bidang.value() != total_persil:
                valid = False
                msg += "\nJumlah bidang tanah tidak sesuai"

            for row in self._ent_dataset["PersilEdit"]:
                if not row["BOUNDARY"]:
                    valid = False
                    msg += "\nAda Persil Edit yang tidak memiliki geometry!"
                    break
                if not row["REGID"]:
                    valid = False
                    msg += "\nAda Persil Edit yang tidak memiliki regid!"
                    break
        else:
            total_invent = len(self._ent_dataset["PersilInventaris"])
            if self.spin_jumlah_bidang.value() != total_invent:
                valid = False
                msg += "\nJumlah bidang inventaris tidak sesuai"
            for row in self._ent_dataset["PersilInventaris"]:
                if not row["BOUNDARY"]:
                    valid = False
                    msg += "\nAda Persil Inventaris yang tidak memiliki geometry!"
                    break

        if self._pbt:
            if self._pbt["tglSelesaiDiumumkan"]:
                valid = False
                tanggal_diumumkan = self._pbt["tglSelesaiDiumumkan"]
                msg += f"\nPeta bidang ini telah diumumkan tanggal {tanggal_diumumkan} proses tidak bisa dilanjutkan"

            if self._pbt["tglDiumumkan"] and self._ent_dataset["PersilBaru"]:
                valid = False
                msg += "\nPeta Bidang ini sedang diumumkan. Penyisipan persil baru tidak diijinkan"

        if valid:
            self.btn_proses.setDisabled(False)
            self.writeLeftStatus.emit("Silahkan simpan data")
        else:
            self.writeLeftStatus.emit("Ada kesalahan, cek error log")
            self.writeErrorLog.emit(msg)
            self.changeTabIndex.emit(1)

    def _handle_process(self):
        self.btn_proses.setDisabled(True)
        self.btn_validasi.setDisabled(True)

        sts = {}
        lines = self._fill_entity_data_table()
        texts = self._fill_text_entity()
        # TODO: fill point
        # TODO: fill dimension

        sts["Garis"] = lines
        sts["Teks"] = texts

        msg = ""
        if self._pbt["tipeProdukId"] != "67":
            kelurahan = self.combo_kelurahan.currentText()
            kecamatan = self.combo_kecamatan.currentText()
            msg = f"Anda akan melakukan integrasi di Desa/Kelurahan {kelurahan}, Kecamatan {kecamatan}.\nApakah anda akan melanjutkan?"
            desa_id = self.combo_kelurahan.currentData()
        else:
            kabupaten = self.combo_kabupaten.currentText()
            provinsi = self.combo_provinsi.currentText()
            msg = f"Anda akan melakukan integrasi di Kabupaten {kabupaten}, Provinsi {provinsi}.\nApakah anda akan melanjutkan?"
            desa_id = self.combo_kabupaten.currentData()

        lanjut_integrasi = True
        if not self._ent_dataset["PersilEdit"]:
            result = QtWidgets.QMessageBox.question(self, "Perhatian", msg)
            if result != QtWidgets.QMessageBox.Yes:
                lanjut_integrasi = False

        if lanjut_integrasi:
            pd = {
                "wilayahId": "",
                "submittedParcel": [],
                "status": False,
                "nomor": "",
                "dokumenPengukuranId": "",
                "gigisId": "",
                "errorMessage": "",
                "autoClosed": False,
            }

            lspb = []
            for row in self._ent_dataset["PersilBaru"]:
                spb = {
                    "OID": row["OID"],
                    "Label": row["LABEL"],
                    "Area": float(row["AREA"].replace(",", ".")) if row["AREA"] else 0,
                    "Boundary": row["BOUNDARY"],
                    "Text": row["TEXT"],
                    "Keterangan": row["KETERANGAN"],
                    "Height": row["HEIGHT"],
                    "Orientation": row["ORIENTATION"],
                    "Lembar": row["NOLEMBAR"],
                    "Kotak": row["KOTAK"],
                }
                lspb.append(spb)
            sts["PersilBaru"] = lspb

            lspe = []
            for row in self._ent_dataset["PersilEdit"]:
                spe = {
                    "OID": row["OID"],
                    "REGID": row["REGID"],
                    "NIB": row["NIB"],
                    "Luast": row["LUAST"],
                    "Label": row["LABEL"],
                    "Area": float(row["AREA"].replace(",", ".")) if row["AREA"] else 0,
                    "Boundary": row["BOUNDARY"],
                    "Text": row["TEXT"],
                    "Keterangan": row["KETERANGAN"],
                    "Height": row["HEIGHT"],
                    "Orientation": row["ORIENTATION"],
                    "Lembar": row["NOLEMBAR"],
                    "Kotak": row["KOTAK"],
                }
                lspe.append(spe)
            sts["PersilEdit"] = lspe

            lspr = []
            for row in self._ent_dataset["PersilInventaris"]:
                spr = {
                    "OID": row["OID"],
                    "REGID": row["REGID"],
                    "Label": row["NOMOR"],
                    "Luast": row["LUAST"] if row["LUAST"] else 0,
                    "Area": float(row["AREA"].replace(",", ".")) if row["AREA"] else 0,
                    "Boundary": row["BOUNDARY"],
                    "Text": row["TEXT"],
                    "Height": row["HEIGHT"],
                    "Orientation": row["ORIENTATION"],
                    "Pemilik": row["PEMILIK"],
                }
                lspr.append(spr)
            sts["PersilRincikan"] = lspr

        program_id = self.combo_kegiatan.currentData()
        tm3 = self.combo_tm3.currentText()
        tm3_zone = tm3.replace("TM3-", "")
        srid = get_epsg_from_tm3_zone(tm3_zone, False)

        pegawai_state = app_state.get("pegawai", {})
        pegawai = pegawai_state.value
        user_id = pegawai["userId"] if "userId" in pegawai else ""
        jml_persil = self.spin_jumlah_bidang.value()

        response = endpoints.submit_for_ptsl_kt_redis(
            self._dokumen_pengukuran_id,
            program_id,
            self._current_kantor_id,
            desa_id,
            srid,
            "",
            user_id,
            sts,
            self._gugus_id,
            "",
            user_id,
            str(jml_persil),
        )
        response_json = json.loads(response.content)
        print(response_json)
        if not response_json:
            pd["wilayahId"] = self._desa_id
            pd["status"] = False
            pd["autoClosed"] = True
            pd["SubmittedParcel"] = None
            self.processed.emit(pd)
            QtWidgets.QMessageBox.critical(
                None,
                "GeoKKP Web",
                "Integrasi gagal!\nCek service berkas spatial di server sudah dijalankan!",
            )
            return
        if response_json["Error"]:
            pd["wilayahId"] = self._desa_id
            pd["status"] = False
            pd["autoClosed"] = True
            pd["SubmittedParcel"] = None
            self.processed.emit(pd)
            # TODO: Add zoom to object

            QtWidgets.QMessageBox.critical(
                None, "GeoKKP Web", response_json["Error"][0]["message"].split("|")[0]
            )
            return
        else:
            submitted_parcel = [f["regid"] for f in response_json["PersilBaru"]]

            pd["wilayahId"] = self._desa_id
            pd["status"] = True
            pd["submittedParcel"] = submitted_parcel
            pd["gugusId"] = response_json["GugusGeometri"][0]["gugusid"]
            pd["nomor"] = response_json["Sukses"][0]["nomor"]
            pd["tahun"] = response_json["Sukses"][0]["tahun"]
            pd["dokumenPengukuranId"] = response_json["Sukses"][0][
                "dokumenPengukuranId"
            ]
            self.processed.emit(pd)
            self.writeLeftStatus.emit(response_json["Sukses"][0]["message"])
            # TODO: Add draw result

            result_oid_map = {}
            for row in response_json["PersilBaru"]:
                result_oid_map[row["oid"]] = row["nib"]

            for layer in self._current_layers:
                field_index = layer.fields().indexOf("label")
                print("field_index", field_index)
                features = layer.getFeatures()
                for feature in features:
                    identifier = f"{layer.id()}|{feature.id()}".encode("utf-8")
                    objectid = hashlib.md5(identifier).hexdigest().upper()
                    print("objectid", objectid)
                    if objectid not in result_oid_map:
                        continue

                    layer.startEditing()
                    layer.changeAttributeValue(
                        feature.id(), field_index, result_oid_map[objectid]
                    )
                    layer.commitChanges()

    def _fill_text_entity(self):
        layers = QgsProject.instance().mapLayers()

        points = []
        for layer in layers.values():
            if (
                isinstance(layer, QgsVectorLayer)
                and "point" not in QgsWkbTypes.displayString(layer.wkbType()).lower()
            ):
                continue

            code, object_type = self.identify_layer_object(layer.name())
            if not code and not object_type:
                continue

            object_type = object_type if object_type else "TeksLain"

            features = layer.getFeatures()
            for feature in features:
                identifier = f"{layer.id()}|{feature.id()}".encode("utf-8")
                objectid = hashlib.md5(identifier).hexdigest().upper()

                point = self.get_sdo_point(feature)

                label = feature.attribute("label") if feature.attribute("label") else ""
                height = (
                    float(feature.attribute("height"))
                    if feature.attribute("height")
                    else 0
                )
                orientation = (
                    float(feature.attribute("rotation"))
                    if feature.attribute("rotation")
                    else 0
                )

                if point and (code.startsWith("08") or object_type == "TeksLain"):
                    row = {
                        "Key": objectid,
                        "Type": object_type,
                        "Height": height,
                        "Orientation": orientation,
                        "Label": label,
                        "Position": point,
                    }
                    points.append(row)
        return points

    def _fill_entity_data_table(self):
        layers = QgsProject.instance().mapLayers()

        lines = []
        for layer in layers.values():
            if (
                isinstance(layer, QgsVectorLayer)
                and "line" not in QgsWkbTypes.displayString(layer.wkbType()).lower()
            ):
                continue

            code, object_type = self.identify_layer_object(layer.name())
            if not code and not object_type:
                continue
            object_type = object_type if object_type else "GarisLain"

            features = layer.getFeatures()
            for feature in features:
                identifier = f"{layer.id()}|{feature.id()}".encode("utf-8")
                objectid = hashlib.md5(identifier).hexdigest().upper()

                line = self._get_sdo_linestring(feature)

                if line and (code.startsWith("08") or object_type == "GarisLain"):
                    row = {"Key": objectid, "Type": object_type, "Line": line}
                    lines.append(row)
        return lines

    def identify_layer_object(self, layer_name):
        layer_raw = layer_name.split(") ")
        if len(layer_raw) != 2:
            return None, None

        code_raw, object_raw = layer_name

        try:
            code = code_raw.replace("(", "")[-1]
        except:
            code = None

        try:
            object_type = object_raw.split("/")[0].replace(" ", "")
        except:
            object_type = None

        return code, object_type
