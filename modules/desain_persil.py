import os
import json
import hashlib
import shapely
import shapely.wkt

from qgis.PyQt import QtWidgets, uic

from qgis.PyQt.QtCore import pyqtSignal
from qgis.utils import iface

from .utils import get_nlp, get_nlp_index, readSetting, storeSetting
from .api import endpoints
from .memo import app_state

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/desain_persil.ui")
)


LIHAT_DATA_PERSIL_BARU = "Persil Baru"
LIHAT_DATA_PERSIL_EDIT = "Persil Edit"
LIHAT_DATA_PERSIL_INDUK = "Persil Induk"
LIHAT_DATA_APARTEMENT_BARU = "Apartemen Baru"
LIHAT_DATA_APARTEMENT_EDIT = "Apartemen Edit"

DS_PERSIL_BARU = "PersilBaru"
DS_PERSIL_EDIT = "PersilEdit"
DS_PERSIL_INDUK = "PersilInduk"
DS_APARTEMEN_BARU = "ApartemenBaru"
DS_APARTEMEN_EDIT = "ApartemenEdit"

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
DS_PERSIL_INDUK_COLUMNS = [
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
]
DS_APARTEMEN_BARU_COLUMN = [
    "OID",
    "LABEL",
    "AREA",
    "BOUNDARY",
    "TEXT",
    "KETERANGAN",
    "HEIGHT",
    "ORIENTATION",
]
DS_APARTEMEN_EDIT_COLUMN = [
    "OID",
    "REGID",
    "NOGD",
    "LUAST",
    "AREA",
    "BOUNDARY",
    "TEXT",
    "KETERANGAN",
    "HEIGHT",
    "ORIENTATION",
]

DS_COLUMN_MAP = {
    DS_PERSIL_BARU: DS_PERSIL_BARU_COLUMNS,
    DS_PERSIL_EDIT: DS_PERSIL_EDIT_COLUMNS,
    DS_PERSIL_INDUK: DS_PERSIL_INDUK_COLUMNS,
    DS_APARTEMEN_BARU: DS_APARTEMEN_BARU_COLUMN,
    DS_APARTEMEN_EDIT: DS_APARTEMEN_EDIT_COLUMN,
}


class DesainPersil(QtWidgets.QDialog, FORM_CLASS):
    """Dialog for Desain Persil"""

    closingPlugin = pyqtSignal()
    ganti_desa = pyqtSignal(object)
    integrasi = pyqtSignal(object)

    def __init__(
        self,
        parent=iface.mainWindow(),
        nomor_berkas=None,
        tahun_berkas=None,
        kantor_id=None,
        tipe_kantor_id=None,
        tipe_berkas=None,
        gambar_ukur_id=None,
        wilayah_id=None,
        tipe_sistem_koordinat=None,
        new_parcel_number=None,
        new_apartment_number=None,
        new_parcels=[],
        old_parcels=[],
        new_apartments=[],
        old_apartments=[],
        ganti_desa=None,
    ):
        super(DesainPersil, self).__init__(parent)
        self.setupUi(self)
        self.btn_proses.setDisabled(True)
        self._parent = parent
        self._current_parcel_table = ""
        self._provinsi_first_load = True
        self._kabupaten_first_load = True
        self._kecamatan_first_load = True
        self._kelurahan_first_load = True

        self._current_kantor = {}
        self._provinsi_by_kantor = {}
        self._kabupaten_by_kantor = {}
        self._kecamatan_by_kantor = {}
        self._kelurahan_by_kecamatan = {}

        self._wilayah_prior = {}
        self._ds_parcel = {
            DS_PERSIL_BARU: [],  # OID, LABEL, AREA, BOUNDARY, TEXT, KETERANGAN, HEIGHT, ORIENTATION, URUT, NOLEMBAR, KOTAK
            DS_PERSIL_EDIT: [],  # OID, REGID, NIB, LUAST, LABEL, AREA, BOUNDARY, TEXT, KETERANGAN, HEIGHT, ORIENTATION, NOLEMBAR, KOTAK
            DS_PERSIL_INDUK: [],  # OID, LABEL, AREA, BOUNDARY, TEXT, KETERANGAN, HEIGHT, ORIENTATION
            DS_APARTEMEN_BARU: [],  # OID, LABEL, AREA, BOUNDARY, TEXT, KETERANGAN, HEIGHT, ORIENTATION
            DS_APARTEMEN_EDIT: [],  # OID, REGID, NOGD, LUAST, AREA, BOUNDARY, TEXT, KETERANGAN, HEIGHT, ORIENTATION
        }  # TODO: Create dedicated data structure

        self._process_parcels = False

        self._nomor_berkas = nomor_berkas
        self._tahun_berkas = tahun_berkas
        self._kantor_id = kantor_id
        self._tipe_kantor_id = tipe_kantor_id
        self._tipe_berkas = tipe_berkas
        self._gambar_ukur_id = gambar_ukur_id
        self._wilayah_id = wilayah_id
        self._tipe_sistem_koordinat = tipe_sistem_koordinat
        self._new_parcel_number = int(new_parcel_number)
        self._new_apartment_number = int(new_apartment_number)
        self._new_parcels = new_parcels
        self._old_parcels = old_parcels
        self._new_apartments = new_apartments
        self._old_apartments = old_apartments
        self._ganti_desa = ganti_desa

        self._get_current_settings()

        self.combo_lihat_data.currentTextChanged.connect(
            self._handle_lihat_data_changed
        )
        self.combo_provinsi.currentIndexChanged.connect(self.provinsi_changed)
        self.combo_kabupaten.currentIndexChanged.connect(self.kabupaten_changed)
        self.combo_kecamatan.currentIndexChanged.connect(self.kecamatan_changed)
        self.combo_kelurahan.currentIndexChanged.connect(self.kelurahan_changed)
        self.btn_proses.clicked.connect(self._handle_process)
        self.btn_validasi.clicked.connect(self._handle_validate)
        self.btn_batal.clicked.connect(self._handle_batal)
        self.btn_ganti_desa.clicked.connect(self._handle_ganti_desa)
        self.check_nib.stateChanged.connect(self._handle_check_nib)
        self._setup_workpanel()

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def _get_current_settings(self):
        self._current_kantor = readSetting("kantorterpilih")
        self._provinsi_by_kantor = readSetting("provinsibykantor", {})
        self._kabupaten_by_provinsi = readSetting("kabupatenbyprovinsi", {})
        self._kecamatan_by_kabupaten = readSetting("kecamatanbykabupaten", {})
        self._kelurahan_by_kecamatan = readSetting("kelurahanbykecamatan", {})

    def _setup_workpanel(self):
        self._process_parcels = True

        self.combo_lihat_data.clear()
        if self._tipe_berkas in ["NPG", "VPG", "SPL", "UNI", "SUB", "DIV"]:
            self.combo_lihat_data.addItems(
                [LIHAT_DATA_PERSIL_BARU, LIHAT_DATA_PERSIL_EDIT]
            )
            self._current_parcel_table = "PersilBaru"
            self._fill_new_persil()
            if self._tipe_berkas in ["DIV", "SPL"]:
                self.combo_lihat_data.addItem(LIHAT_DATA_PERSIL_INDUK)
                self._fill_old_persil(DS_PERSIL_INDUK)
        elif self._tipe_berkas in ["DEG", "NPR"]:
            if len(self._old_parcels) > 0:
                self.combo_lihat_data.addItem(LIHAT_DATA_PERSIL_EDIT)
                self._current_parcel_table = "PersilEdit"
                self._fill_old_persil(DS_PERSIL_EDIT)
            else:
                self._process_parcels = False
                self.combo_lihat_data.addItem(LIHAT_DATA_APARTEMENT_EDIT)
                self._current_parcel_table = "ApartemenEdit"
                self._fill_old_apartment(DS_APARTEMEN_EDIT)
        elif self._tipe_berkas == "NME":
            self.combo_lihat_data.addItem(LIHAT_DATA_PERSIL_INDUK)
            self._current_parcel_table = "PersilInduk"
            self._fill_old_persil(DS_PERSIL_INDUK)
        elif self._tipe_berkas == "DAG":
            self._process_parcels = False
            self.combo_lihat_data.addItems(
                [LIHAT_DATA_APARTEMENT_BARU, LIHAT_DATA_APARTEMENT_EDIT]
            )
            self._current_parcel_table = "ApartemenBaru"
            self._fill_new_apartment()

        if self._kantor_id is None and self._tipe_kantor_id is not None:
            return

        self.get_wilayah_prior(self._wilayah_id)

        self.populate_provinsi(self._kantor_id, str(self._tipe_kantor_id))

        if self._process_parcels:
            self._autofill_persil_data()
        else:
            self._autofill_apartemen_data()

        if not self._validate_extent():
            if self._tipe_sistem_koordinat == "TM3":
                QtWidgets.QMessageBox.warning(
                    None,
                    "KKP Web",
                    "Koordinat diluar TM3!",
                )
            else:
                QtWidgets.QMessageBox.warning(
                    None,
                    "KKP Web",
                    "Koordinat diluar area penggambaran!",
                )
            return

        if (
            len(self._ds_parcel[DS_PERSIL_EDIT]) > 0
            or len(self._ds_parcel[DS_APARTEMEN_EDIT]) > 0
        ):
            self.combo_provinsi.setDisabled(True)
            self.combo_kabupaten.setDisabled(True)
            self.combo_kecamatan.setDisabled(True)
            self.combo_kelurahan.setDisabled(True)
        else:
            self.combo_provinsi.setDisabled(False)
            self.combo_kabupaten.setDisabled(False)
            self.combo_kecamatan.setDisabled(False)
            self.combo_kelurahan.setDisabled(False)

        if len(self._wilayah_prior) <= 2:
            self.label_kecamatan.hide()
            self.combo_kecamatan.hide()
            self.label_kelurahan.hide()
            self.combo_kelurahan.hide()
            self.check_simpan_bidang.setCheckState(2)

        if (
            len(self._ds_parcel[DS_PERSIL_EDIT]) == 0
            and len(self._ds_parcel[DS_PERSIL_INDUK]) == 0
            and len(self._ds_parcel[DS_APARTEMEN_EDIT]) == 0
        ) or self._tipe_berkas == "DAG":
            self.check_reset_di302.hide()

        edit_null_count = len(
            [
                p
                for p in self._ds_parcel[DS_PERSIL_EDIT]
                if "NIB" not in p.keys() or not p["NIB"]
            ]
        )
        induk_null_count = len(
            [
                p
                for p in self._ds_parcel[DS_PERSIL_INDUK]
                if "NIB" not in p.keys() or not p["NIB"]
            ]
        )

        print(edit_null_count, induk_null_count)
        print(self._ds_parcel[DS_PERSIL_EDIT])
        print(self._ds_parcel[DS_PERSIL_INDUK])

        if edit_null_count > 0 or induk_null_count > 0:
            self.label_status_l.setText("Ada kesalahan, cek error log")
            self.error_log.setHtml(
                "Persil Edit atau Persil Induk dalam proses ini tidak memiliki NIB.<br/>"
                + "Silahkan periksa data buku tanah yang dimasukkan dalam proses ini terlebih dahulu.<br/>"
                + "Apabila memiliki NIB, perbaiki data buku tanah sesuai fisiknya. Jika tidak, "
                + "silahkan memilih Lengkapi NIB untuk melanjutkan proses ini."
                + "<br/>Jika memilih Lengkapi NIB maka GeoKKPWeb akan memberikan NIB yang baru"
            )
            self.tabWidget.setCurrentIndex(1)
            self.btn_validasi.setDisabled(True)
        else:
            self.btn_validasi.setDisabled(False)
            self.check_nib.show()

    def _validate_extent(self):
        min_x = 0
        min_y = 0
        max_x = 0
        max_y = 0
        for layer in self._parent.current_layers:
            if not layer.name().startswith("(20100)"):
                continue
            extent = layer.extent()
            min_x = min(min_x, extent.xMinimum())
            min_y = min(min_y, extent.yMinimum())
            max_x = max(max_x, extent.xMaximum())
            max_y = max(max_y, extent.xMaximum())

        if self._tipe_sistem_koordinat == "TM3":
            return not (
                min_x < 32000 - 10000
                and max_x > 368000 + 10000
                and min_y < 282000 - 10000
                and max_y > 2166000 + 10000
            )
        else:
            return not (
                min_x < -2200000
                and max_x > 2200000
                and min_y < -2200000
                and max_y > 2200000
            )

    def _handle_lihat_data_changed(self):
        self.refresh_status()
        self.set_context_menu_visibility()

    def set_context_menu_visibility(self):
        if self._current_parcel_table == "PersilBaru":
            self.btn_ganti_desa.hide()
            # TODO: miEditedParcel
            # TODO: miNewParcel
            # TODO: btnDelete
            if self._tipe_berkas in ["DIV", "SPL"]:
                # TODO: miParentParcel
                pass
            else:
                # TODO: miParentParcel
                pass

            # TODO: miEditedApartment
            # TODO: miNewApartment
        elif self._current_parcel_table == "PersilEdit":
            # TODO: miEditedParcel
            # TODO: miMerge
            # TODO: miNewParcel
            # TODO: btnDelete
            if self._tipe_berkas in ["DIV", "SPL"]:
                # TODO: miParentParcel
                pass
            else:
                # TODO: miParentParcel
                pass

            if self._tipe_berkas in ["DEG", "NME", "DIV"]:
                if self._ganti_desa == "0":
                    self.btn_ganti_desa.show()
                else:
                    self.btn_ganti_desa.hide()
            else:
                self.btn_ganti_desa.hide()

            # TODO: miEditedApartment
            # TODO: miNewApartment
        elif self._current_parcel_table == "PersilInduk":
            # TODO: miEditedParcel
            # TODO: miMerge
            # TODO: miNewParcel
            # TODO: btnDelete

            if self._ganti_desa == "0":
                self.btn_ganti_desa.show()
            else:
                self.btn_ganti_desa.hide()

            # TODO: miEditedApartment
            # TODO: miNewApartment
        elif self._current_parcel_table == "ApaartemenBaru":
            self.btn_ganti_desa.hide()
            # TODO: miEditedParcel
            # TODO: miMerge
            # TODO: miNewParcel
            # TODO: btnDelete
            # TODO: miParentParel

            # TODO: miEditedApartment
            # TODO: miNewApartment
        else:
            self.btn_ganti_desa.hide()
            # TODO: miEditedParcel
            # TODO: miMerge
            # TODO: miNewParcel
            # TODO: btnDelete
            # TODO: miParentParel

            # TODO: miEditedApartment
            # TODO: miNewApartment

    def refresh_status(self):
        jml_persil = 0
        msg_status = ""
        label = self.combo_lihat_data.currentText()
        if label == "Persil Baru":
            self._current_parcel_table = "PersilBaru"
            jml_persil = self._new_parcel_number - len(self._new_parcels)
            msg_status = "Jumlah Persil Baru"
        elif label == "Persil Edit":
            self._current_parcel_table = "PersilEdit"
            if self._tipe_berkas == "DEG":
                jml_persil = len(self._old_parcels)
            else:
                jml_persil = len(self._new_parcels)
            msg_status = "Jumlah Persil Edit"
        elif label == "Persil Induk":
            self._current_parcel_table = "PersilInduk"
            jml_persil = 1
            msg_status = "Jumlah Persil Induk"
        elif label == "Apartemen Baru":
            self._current_parcel_table = "ApartemenBaru"
            jml_persil = len(self._new_apartments)
            msg_status = "Jumlah Apartemen"
        elif label == "Apartemen Edit":
            self._current_parcel_table = "ApartemenEdit"
            jml_persil = len(self._new_apartments)
            msg_status = "Jumlah Apartemen"

        self.populate_tabel_persil()
        jml_all = len(self._ds_parcel[self._current_parcel_table])
        self.label_status_r.setText(f"{jml_all}/{jml_persil}")
        self.label_status_r.setToolTip(f"{msg_status}/Jumlah seharusnya")

    def populate_tabel_persil(self):
        self.tabel_desain_persil.setRowCount(0)
        data = self._ds_parcel[self._current_parcel_table]
        if not data:
            return
        columns = [
            col
            for col in data[0].keys()
            if col not in ["HEIGHT", "ORIENTATION", "BOUNDARY", "TEXT"]
        ]
        self.tabel_desain_persil.setColumnCount(len(columns))
        self.tabel_desain_persil.setHorizontalHeaderLabels(columns)

        for item in data:
            pos = self.tabel_desain_persil.rowCount()
            self.tabel_desain_persil.insertRow(pos)

            for index, col in enumerate(columns):
                self.tabel_desain_persil.setItem(
                    pos, index, QtWidgets.QTableWidgetItem(str(item[col]))
                )

    def get_wilayah_prior(self, kelurahan_id=None):
        if not kelurahan_id:
            return

        response = endpoints.get_wilayah_prior(kelurahan_id)
        self._wilayah_prior = json.loads(response.content)
        print("_wilayah_prior", self._wilayah_prior)
        return self._wilayah_prior

    def _autofill_persil_data(self):
        for layer in self._parent.current_layers:
            if layer.name().startswith("(20100)"):
                features = layer.getFeatures()
                for feature in features:
                    identifier = f"{layer.id()}|{feature.id()}".encode("utf-8")
                    objectid = hashlib.md5(identifier).hexdigest().upper()

                    # TODO: freeze qgis layer in here to avoid editing
                    point = feature.geometry().pointOnSurface().asPoint()
                    teks = self.get_sdo_point(point)
                    poli = self.get_sdo_polygon(feature)

                    sheet_number = get_nlp("250", point.x(), point.y())
                    box_number = get_nlp_index("250", point.x(), point.y())

                    if not poli["batas"]:
                        continue
                    data_row = None
                    nib = (
                        feature.attribute("label") if feature.attribute("label") else ""
                    )
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
                    luas_round = str(round(poli["luas"], 3))
                    if len(self._ds_parcel[DS_PERSIL_EDIT]) > 0:
                        filter_ds = [
                            row
                            for row in self._ds_parcel[DS_PERSIL_EDIT]
                            if row["NIB"] == nib
                        ]
                        if filter_ds:
                            data_row = filter_ds[0]
                            data_row[DS_COLUMN_MAP[DS_PERSIL_EDIT][11]] = sheet_number
                            data_row[DS_COLUMN_MAP[DS_PERSIL_EDIT][12]] = box_number

                    if len(self._ds_parcel[DS_PERSIL_INDUK]) > 0:
                        filter_ds = [
                            row
                            for row in self._ds_parcel[DS_PERSIL_INDUK]
                            if row["NIB"] == nib
                        ]
                        if filter_ds:
                            data_row = filter_ds[0]

                    if data_row is not None:
                        data_row[
                            DS_COLUMN_MAP[DS_PERSIL_EDIT][0]
                        ] = objectid  # 32 char md5 hash of layer id + feature id
                        data_row[DS_COLUMN_MAP[DS_PERSIL_EDIT][4]] = nib
                        data_row[DS_COLUMN_MAP[DS_PERSIL_EDIT][5]] = luas_round
                        data_row[DS_COLUMN_MAP[DS_PERSIL_EDIT][6]] = poli["batas"]
                        data_row[DS_COLUMN_MAP[DS_PERSIL_EDIT][7]] = teks
                        data_row[DS_COLUMN_MAP[DS_PERSIL_EDIT][8]] = "Tunggal"
                        data_row[DS_COLUMN_MAP[DS_PERSIL_EDIT][9]] = height
                        data_row[DS_COLUMN_MAP[DS_PERSIL_EDIT][10]] = orientation
                    else:
                        if self._tipe_berkas in ["DAG", "NPR"]:
                            a_row = {}
                            for index, col in enumerate(DS_COLUMN_MAP[DS_PERSIL_EDIT]):
                                a_row[col] = None
                            a_row[DS_COLUMN_MAP[DS_PERSIL_EDIT][0]] = objectid
                            a_row[DS_COLUMN_MAP[DS_PERSIL_EDIT][4]] = nib
                            a_row[DS_COLUMN_MAP[DS_PERSIL_EDIT][5]] = luas_round
                            a_row[DS_COLUMN_MAP[DS_PERSIL_EDIT][6]] = poli["batas"]
                            a_row[DS_COLUMN_MAP[DS_PERSIL_EDIT][7]] = teks
                            a_row[DS_COLUMN_MAP[DS_PERSIL_EDIT][8]] = "Tunggal"
                            a_row[DS_COLUMN_MAP[DS_PERSIL_EDIT][9]] = height
                            a_row[DS_COLUMN_MAP[DS_PERSIL_EDIT][10]] = orientation
                            a_row[DS_COLUMN_MAP[DS_PERSIL_EDIT][11]] = sheet_number
                            a_row[DS_COLUMN_MAP[DS_PERSIL_EDIT][12]] = box_number
                            self._ds_parcel[DS_PERSIL_EDIT].append(a_row)
                        elif self._tipe_berkas == "NME":
                            a_row = {}
                            for index, col in enumerate(DS_COLUMN_MAP[DS_PERSIL_INDUK]):
                                a_row[col] = None
                            a_row[DS_COLUMN_MAP[DS_PERSIL_INDUK][0]] = objectid
                            a_row[DS_COLUMN_MAP[DS_PERSIL_INDUK][4]] = nib
                            a_row[DS_COLUMN_MAP[DS_PERSIL_INDUK][5]] = luas_round
                            a_row[DS_COLUMN_MAP[DS_PERSIL_INDUK][6]] = poli["batas"]
                            a_row[DS_COLUMN_MAP[DS_PERSIL_INDUK][7]] = teks
                            a_row[DS_COLUMN_MAP[DS_PERSIL_INDUK][8]] = "Tunggal"
                            a_row[DS_COLUMN_MAP[DS_PERSIL_INDUK][9]] = height
                            a_row[DS_COLUMN_MAP[DS_PERSIL_INDUK][10]] = orientation
                            self._ds_parcel[DS_PERSIL_INDUK].append(a_row)
                        else:
                            a_row = {}
                            for index, col in enumerate(DS_COLUMN_MAP[DS_PERSIL_BARU]):
                                a_row[col] = None
                            a_row[DS_COLUMN_MAP[DS_PERSIL_BARU][0]] = objectid
                            a_row[DS_COLUMN_MAP[DS_PERSIL_BARU][1]] = nib
                            a_row[DS_COLUMN_MAP[DS_PERSIL_BARU][2]] = luas_round
                            a_row[DS_COLUMN_MAP[DS_PERSIL_BARU][3]] = poli["batas"]
                            a_row[DS_COLUMN_MAP[DS_PERSIL_BARU][4]] = teks
                            a_row[DS_COLUMN_MAP[DS_PERSIL_BARU][5]] = "Tunggal"
                            a_row[DS_COLUMN_MAP[DS_PERSIL_BARU][6]] = 1
                            a_row[DS_COLUMN_MAP[DS_PERSIL_BARU][7]] = 0
                            try:
                                a_row[DS_COLUMN_MAP[DS_PERSIL_BARU][8]] = int(
                                    teks.replace("#", "")
                                )
                            except:
                                a_row[DS_COLUMN_MAP[DS_PERSIL_BARU][8]] = 0
                            a_row[DS_COLUMN_MAP[DS_PERSIL_BARU][9]] = box_number
                            a_row[DS_COLUMN_MAP[DS_PERSIL_BARU][10]] = sheet_number
                            self._ds_parcel[DS_PERSIL_BARU].append(a_row)

        if self._ds_parcel[DS_PERSIL_BARU]:
            persil_baru_sorted = list(
                sorted(self._ds_parcel[DS_PERSIL_BARU], key=lambda d: d["URUT"])
            )
            self._ds_parcel[DS_PERSIL_BARU] = persil_baru_sorted

    def _autofill_apartemen_data(self):
        for layer in self._parent.current_layers:
            if layer.name().startswith("(20100)"):
                features = layer.getFeatures()
                for feature in features:
                    identifier = f"{layer.id()}|{feature.id()}".encode("utf-8")
                    objectid = hashlib.md5(identifier).hexdigest().upper()

                    point = feature.geometry().pointOnSurface().asPoint()
                    teks = self.get_sdo_point(point)
                    poli = self.get_sdo_polygon(feature)
                    if not poli["batas"]:
                        continue
                    data_row = None
                    nogd = (
                        feature.attribute("label") if feature.attribute("label") else ""
                    )
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
                    luas_round = str(round(poli["luas"], 3))
                    if len(self._ds_parcel[DS_APARTEMEN_EDIT]) > 0:
                        filter_ds = [
                            row
                            for row in self._ds_parcel[DS_APARTEMEN_EDIT]
                            if row["NOGD"] == nogd
                        ]
                        if filter_ds:
                            data_row = filter_ds[0]
                    if data_row is not None:
                        data_row[
                            DS_COLUMN_MAP[DS_APARTEMEN_EDIT][0]
                        ] = objectid  # 32 char md5 hash of layer id + feature id
                        data_row[DS_COLUMN_MAP[DS_APARTEMEN_EDIT][4]] = nogd
                        data_row[DS_COLUMN_MAP[DS_APARTEMEN_EDIT][5]] = luas_round
                        data_row[DS_COLUMN_MAP[DS_APARTEMEN_EDIT][6]] = poli["batas"]
                        data_row[DS_COLUMN_MAP[DS_APARTEMEN_EDIT][7]] = teks
                        data_row[DS_COLUMN_MAP[DS_APARTEMEN_EDIT][8]] = "Tunggal"
                        data_row[DS_COLUMN_MAP[DS_APARTEMEN_EDIT][9]] = height
                        data_row[DS_COLUMN_MAP[DS_APARTEMEN_EDIT][10]] = orientation
                    else:
                        if self._tipe_berkas == "DEG":
                            a_row = {}
                            for col in DS_COLUMN_MAP[DS_APARTEMEN_EDIT]:
                                a_row[col] = None
                            a_row[DS_COLUMN_MAP[DS_APARTEMEN_EDIT][0]] = objectid
                            a_row[DS_COLUMN_MAP[DS_APARTEMEN_EDIT][4]] = nogd
                            a_row[DS_COLUMN_MAP[DS_APARTEMEN_EDIT][5]] = luas_round
                            a_row[DS_COLUMN_MAP[DS_APARTEMEN_EDIT][6]] = poli["batas"]
                            a_row[DS_COLUMN_MAP[DS_APARTEMEN_EDIT][7]] = teks
                            a_row[DS_COLUMN_MAP[DS_APARTEMEN_EDIT][8]] = "Tunggal"
                            a_row[DS_COLUMN_MAP[DS_APARTEMEN_EDIT][9]] = height
                            a_row[DS_COLUMN_MAP[DS_APARTEMEN_EDIT][10]] = orientation
                            self._ds_parcel[DS_APARTEMEN_EDIT].append(a_row)
                        else:
                            a_row = {}
                            for col in DS_COLUMN_MAP[DS_APARTEMEN_BARU]:
                                a_row[col] = None
                            a_row[DS_COLUMN_MAP[DS_APARTEMEN_BARU][0]] = objectid
                            a_row[DS_COLUMN_MAP[DS_APARTEMEN_BARU][1]] = nogd
                            a_row[DS_COLUMN_MAP[DS_APARTEMEN_BARU][2]] = luas_round
                            a_row[DS_COLUMN_MAP[DS_APARTEMEN_BARU][3]] = poli["batas"]
                            a_row[DS_COLUMN_MAP[DS_APARTEMEN_BARU][4]] = teks
                            a_row[DS_COLUMN_MAP[DS_APARTEMEN_BARU][5]] = "Tunggal"
                            a_row[DS_COLUMN_MAP[DS_APARTEMEN_BARU][6]] = 1
                            a_row[DS_COLUMN_MAP[DS_APARTEMEN_BARU][7]] = 0
                            self._ds_parcel[DS_APARTEMEN_BARU].append(a_row)

        if self._ds_parcel[DS_APARTEMEN_BARU]:
            apartemen_baru_sorted = list(
                sorted(self._ds_parcel[DS_APARTEMEN_BARU], key=lambda d: d["URUT"])
            )
            self._ds_parcel[DS_APARTEMEN_BARU] = apartemen_baru_sorted

    def _fill_new_persil(self):
        if not self._new_parcels:
            return
        persil_ids = [str(p) for p in self._new_parcels]

        response = endpoints.get_parcels(persil_ids)
        response_json = json.loads(response.content)
        print("new_persil", response_json)
        column_defs = DS_COLUMN_MAP[DS_PERSIL_EDIT]
        column_defs_res = list(response_json["PERSILBARU"][0].keys())

        template = {}
        for col in column_defs:
            template[col] = None

        for row in response_json["PERSILBARU"]:
            a_row = template.copy()
            a_row[column_defs[1]] = row[column_defs_res[0]]
            a_row[column_defs[2]] = row[column_defs_res[1]][9:]
            a_row[column_defs[3]] = row[column_defs_res[2]]
            self._ds_parcel[DS_PERSIL_EDIT].append(a_row)

    def _fill_old_persil(self, name):
        if not self._old_parcels:
            return
        persil_ids = [str(p) for p in self._old_parcels]
        response = endpoints.get_parcels(persil_ids)
        response_json = json.loads(response.content)
        print("old_persil", response_json)
        column_defs = DS_COLUMN_MAP[name]
        column_defs_res = list(response_json["PERSILBARU"][0].keys())

        template = {}
        for col in column_defs:
            template[col] = None

        for row in response_json["PERSILBARU"]:
            a_row = template.copy()
            a_row[column_defs[1]] = row[column_defs_res[0]]
            a_row[column_defs[2]] = row[column_defs_res[1]][9:]
            a_row[column_defs[3]] = row[column_defs_res[2]]
            self._ds_parcel[name].append(a_row)

    def _fill_new_apartment(self):
        if not self._new_apartments:
            return
        apartment_ids = [str(a) for a in self._new_apartments]

        response = endpoints.get_apartments(apartment_ids)
        response_json = json.loads(response.content)
        print("new_apartments", response_json)
        column_defs = DS_COLUMN_MAP[DS_APARTEMEN_EDIT]
        column_defs_res = list(response_json["APARTEMENBARU"][0].keys())

        template = {}
        for col in column_defs:
            template[col] = None

        for row in response_json["APARTEMENBARU"]:
            a_row = template.copy()
            a_row[column_defs[1]] = row[column_defs_res[0]]
            a_row[column_defs[2]] = row[column_defs_res[1]]
            a_row[column_defs[3]] = row[column_defs_res[2]]
            self._ds_parcel[DS_APARTEMEN_EDIT].append(a_row)

    def _fill_old_apartment(self, name):
        if not self._new_apartments:
            return
        apartment_ids = [str(a) for a in self._new_apartments]

        response = endpoints.get_apartments(apartment_ids)
        response_json = json.loads(response.content)
        print("new_apartments", response_json)
        column_defs = DS_COLUMN_MAP[DS_APARTEMEN_EDIT]
        column_defs_res = list(response_json["APARTEMENBARU"][0].keys())

        template = {}
        for col in column_defs:
            template[col] = None

        for row in response_json["APARTEMENBARU"]:
            a_row = template.copy()
            a_row[column_defs[1]] = row[column_defs_res[0]]
            a_row[column_defs[2]] = row[column_defs_res[1]]
            a_row[column_defs[3]] = row[column_defs_res[2]]
            self._ds_parcel[name].append(a_row)

    def clear_combobox(self, level):
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

    def populate_provinsi(self, kantor_id, tipe_kantor_id):
        self.clear_combobox(4)
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

        prior = [f for f in self._wilayah_prior if f["TIPEWILAYAHID"] == 1]
        current_index = 0
        for index, provinsi in enumerate(data_provinsi):
            if provinsi["PROPINSIID"] == prior[0]["WILAYAHID"]:
                current_index = index
            self.combo_provinsi.addItem(provinsi["PROPNAMA"], provinsi["PROPINSIID"])
        if self._provinsi_first_load:
            self.combo_provinsi.setCurrentIndex(current_index)
            self._provinsi_first_load = False

    def populate_kabupaten(self, kantor_id, tipe_kantor_id, provinsi_id):
        self.clear_combobox(3)
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

        prior = [f for f in self._wilayah_prior if f["TIPEWILAYAHID"] in (2, 3, 4)]
        current_index = 0
        for index, kabupaten in enumerate(data_kabupaten):
            if kabupaten["KABUPATENID"] == prior[0]["WILAYAHID"]:
                current_index = index
            self.combo_kabupaten.addItem(
                kabupaten["KABUNAMA"], kabupaten["KABUPATENID"]
            )
        if self._kabupaten_first_load:
            self.combo_kabupaten.setCurrentIndex(current_index)
            self._kabupaten_first_load = False

    def populate_kecamatan(self, kantor_id, tipe_kantor_id, kabupaten_id):
        self.clear_combobox(2)
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
                    "Data Kecamatan",
                    "Tidak bisa membaca data kecamatan dari server",
                )
                return

        prior = [f for f in self._wilayah_prior if f["TIPEWILAYAHID"] == 5]
        current_index = 0
        for index, kecamatan in enumerate(data_kecamatan):
            if kecamatan["KECAMATANID"] == prior[0]["WILAYAHID"]:
                current_index = index
            self.combo_kecamatan.addItem(
                kecamatan["KECANAMA"], kecamatan["KECAMATANID"]
            )

        if self._kecamatan_first_load:
            self.combo_kecamatan.setCurrentIndex(current_index)
            self._kecamatan_first_load = False

    def populate_kelurahan(self, kantor_id, tipe_kantor_id, kecamatan_id):
        self.clear_combobox(1)
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
                    "Data Kelurahan",
                    "Tidak bisa membaca data kelurahan dari server",
                )
                return

        prior = [f for f in self._wilayah_prior if f["TIPEWILAYAHID"] in [6, 7]]
        current_index = 0
        for index, kelurahan in enumerate(data_kelurahan):
            if kelurahan["DESAID"] == prior[0]["WILAYAHID"]:
                current_index = index
            self.combo_kelurahan.addItem(kelurahan["DESANAMA"], kelurahan["DESAID"])

        if self._kelurahan_first_load:
            self.combo_kelurahan.setCurrentIndex(current_index)
            self._kelurahan_first_load = False

    def provinsi_changed(self):
        if self._kantor_id not in self._provinsi_by_kantor.keys():
            return
        current_provinsi_id = self.combo_provinsi.currentData()
        self.populate_kabupaten(
            self._kantor_id, self._tipe_kantor_id, current_provinsi_id
        )

    def kabupaten_changed(self):
        current_provinsi_id = self.combo_provinsi.currentData()
        if current_provinsi_id not in self._kabupaten_by_provinsi.keys():
            return

        current_kabupaten_id = self.combo_kabupaten.currentData()
        self.populate_kecamatan(
            self._kantor_id, self._tipe_kantor_id, current_kabupaten_id
        )

    def kecamatan_changed(self, index):
        current_kabupaten_id = self.combo_kabupaten.currentData()
        if current_kabupaten_id not in self._kecamatan_by_kabupaten.keys():
            return

        current_kecamatan_id = self.combo_kecamatan.currentData()
        self.populate_kelurahan(
            self._kantor_id, self._tipe_kantor_id, current_kecamatan_id
        )

    def kelurahan_changed(self, index):
        current_kecamatan_id = self.combo_kecamatan.currentData()
        if current_kecamatan_id not in self._kelurahan_by_kecamatan.keys():
            return

    def _handle_process(self):
        if (
            len(self._ds_parcel[DS_PERSIL_BARU]) > 0
            or len(self._ds_parcel[DS_APARTEMEN_BARU]) > 0
        ):
            msg = ""
            if len(self._wilayah_prior) == 2:
                msg = (
                    f"Anda akan melakukan integrasi di Kabupaten / Kota {self.combo_kabupaten.currentText()}, "
                    + f"Provinsi {self.combo_provinsi.currentText()}.\nApakah anda akan melanjutkan?"
                )
            else:
                msg = (
                    f"Anda akan melakukan integrasi di Desa {self.combo_kelurahan.currentText()}, "
                    + f"Kecamatan {self.combo_kecamatan.currentText()}.\nApakah anda akan melanjutkan?"
                )

            result = QtWidgets.QMessageBox.question(self, "Perhatian", msg)
            if result == QtWidgets.QMessageBox.Yes:
                parcel_design = {
                    "wilayah_id": "",
                    "ds_parcel": {},
                    "old_parcel": [],
                    "ganti_desa": "",
                    "reset_302": False,
                }
                if len(self._wilayah_prior) > 2:
                    parcel_design["wilayah_id"] = self.current_kelurahan["DESAID"]
                else:
                    parcel_design["wilayah_id"] = self.current_kabupaten["KABUPATENID"]

                parcel_design["ds_parcel"] = self._ds_parcel
                parcel_design["old_parcel"] = self._old_parcels
                parcel_design["ganti_desa"] = self._ganti_desa
                parcel_design["reset_302"] = self.check_reset_di302.isChecked()
                self.integrasi.emit(parcel_design)
        else:
            parcel_design = {
                "wilayah_id": "",
                "ds_parcel": {},
                "old_parcel": [],
                "ganti_desa": "",
                "reset_302": False,
            }
            if len(self._wilayah_prior) > 2:
                parcel_design["wilayah_id"] = self.combo_kelurahan.currentData()
            else:
                parcel_design["wilayah_id"] = self.combo_kabupaten.currentData()

            parcel_design["ds_parcel"] = self._ds_parcel
            parcel_design["old_parcel"] = self._old_parcels
            parcel_design["ganti_desa"] = self._ganti_desa
            parcel_design["reset_302"] = self.check_reset_di302.isChecked()
            self.integrasi.emit(parcel_design)
        self.close()

    def _handle_validate(self):
        valid = True
        msg = ""
        if self._new_parcel_number > 0:
            if (
                len(self._ds_parcel[DS_PERSIL_BARU])
                + len(self._ds_parcel[DS_PERSIL_EDIT])
                != self._new_parcel_number
            ):
                valid = False
                msg = "Jumlah persil baru tidak sesuai!"
        else:
            if len(self._ds_parcel[DS_PERSIL_BARU]) > 0:
                valid = False
                msg = "Maaf, proses ini tidak membuat persil baru"

        if self._new_parcels or self._old_parcels:
            for row in self._ds_parcel[DS_PERSIL_EDIT]:
                if not row["BOUNDARY"]:
                    valid = False
                    msg = "Ada Persil Edit yang tidak memiliki geometri!"
                    break
                if not row["REGID"]:
                    valid = False
                    msg = "Ada Persil Edit yang tidak memiliki REGID!"
                    break

        if self._new_apartments or self._old_apartments:
            for row in self._ds_parcel[DS_PERSIL_EDIT]:
                if not row["BOUNDARY"]:
                    valid = False
                    msg = "Ada Apartemen Edit yang tidak memiliki geometri!"
                    break
                if not row["REGID"]:
                    valid = False
                    msg = "Ada Apartemen Edit yang tidak memiliki REGID!"
                    break

        if self._tipe_berkas in ["DIV", "NME", "SPL"]:
            persil_induk_count = len(self._ds_parcel[DS_PERSIL_INDUK])
            if self._tipe_berkas in ["DIV", "SPL"] and persil_induk_count != 1:
                valid = False
                msg = "Prosedur DIV/SPL jumlah persil induk harus ada 1!"
            elif self._tipe_berkas == "NME" and persil_induk_count < 1:
                valid = False
                msg = "Prosedur NME jumlah persil induk harus ada minimal 1!"
            else:
                for row in self._ds_parcel[DS_PERSIL_INDUK]:
                    if not row["REGID"]:
                        valid = False
                        msg = "Persil Induk tidak memiliki REGID!"
                        break

        if self._tipe_berkas == "DAG":
            if self._new_apartment_number > 0:
                if (
                    len(self._ds_parcel[DS_APARTEMEN_BARU])
                    + len(self._ds_parcel[DS_APARTEMEN_EDIT])
                    != self._new_apartment_number
                ):
                    valid = False
                    msg = "Jumlah apartemen tidak sesuai!"
                for row in self._ds_parcel[DS_APARTEMEN_EDIT]:
                    if not row["BOUNDARY"]:
                        valid = False
                        msg = "Ada Apartemen Edit yang tidak memiliki geometri!"
                        break
                    if not row["REGID"]:
                        valid = False
                        msg = "Ada Apartemen Edit yang tidak memiliki REGID!"
                        break

        if valid:
            self.btn_proses.setDisabled(False)
            self.label_status_l.setText("Lakukan Integrasi")
        else:
            self.label_status_l.setText("Ada kesalahan, cek error log")
            self.error_log.setText(msg)
            self.tabWidget.setCurrentIndex(1)

    def _handle_ganti_desa(self):
        if (
            not self.combo_kelurahan.isEnabled()
            and not self.combo_kecamatan.isEnabled()
        ):
            QtWidgets.QMessageBox.warning(
                None, "Perhatian", "Pilih Desa Tujuan, Kemudian Klik Ganti Desa Lagi"
            )

            self.combo_kecamatan.setDisabled(False)
            self.combo_kelurahan.setDisabled(False)
            self.combo_lihat_data.setDisabled(True)
            self.btn_validasi.setDisabled(True)
            self.btn_proses.setDisabled(True)
        else:
            msg = (
                f"Anda akan melakukan perubahan data persil, su, dan hak ke desa {self.combo_kelurahan.currentText()} "
                + f", Kecamatan {self.combo_kecamatan.currentText()}. \nApakah anda akan melanjutkan?"
            )
            result = QtWidgets.QMessageBox.question(self, "Perhatian", msg)

            if result == QtWidgets.QMessageBox.Yes:
                selected_parcels = [str(p) for p in self._old_parcels]
                user = app_state.get("pegawai", {})
                user_id = (
                    user.value["userId"]
                    if user.value
                    and "userId" in user.value.keys()
                    and user.value["userId"]
                    else ""
                )
                current_kelurahan_id = self.combo_kelurahan.currentData()
                response = endpoints.ganti_desa(
                    self._nomor_berkas,
                    self._tahun_berkas,
                    self._kantor_id,
                    self._tipe_kantor_id,
                    current_kelurahan_id,
                    "Persil",
                    selected_parcels,
                    user_id,
                )
                response_json = json.loads(response.content)
                print("ganti desa", response_json)

                if len(response_json["Error"]) > 0:
                    msg = response_json["Error"][0]["message"]
                    QtWidgets.QMessageBox.critical(self, "Error", msg)
                else:
                    parcels = [str(p) for p in self._old_parcels]
                    kelurahan_id = self.combo_kelurahan.currentData()
                    table_name = self.combo_lihat_data.currentText().replace(" ", "")

                    msg = "Ganti desa berhasil dilakukan"

                    # TODO: change this to column based, the source only use key index instead of key
                    cols = response_json["DataBaru"].keys()
                    for row in response_json["DataBaru"]:
                        if row[cols[6]] in self._old_parcels:
                            self._old_parcels.remove(row[cols[6]])
                            self._old_parcels.append(row[cols[7]])

                            my_rows = [
                                x
                                for x in self._ds_parcel[table_name]
                                if x["REGID"] == cols[6]
                            ]
                            my_rows[0]["REGID"] = row[cols[7]]
                            my_rows[0]["NIB"] = row[cols[1]].split(".")[1]
                            msg += f"\nNIB {row[cols[0]]} ==> {row[cols[1]]}"
                            msg += f"\nSU {row[cols[2]]} ==> {row[cols[3]]}"
                            msg += f"\nHAK {row[cols[4]]} ==> {row[cols[5]]}"

                    # TODO: refresh table desain persil

                    parcel_design = {
                        "wilayah_id": current_kelurahan_id,
                        "ds_parcel": {},
                        "old_parcel": self._old_parcels,
                        "ganti_desa": "1",
                        "reset_302": False,
                    }
                    self.ganti_desa.emit(parcel_design)

                    QtWidgets.QMessageBox.information(None, "Perhatian", msg)

                    self.check_nib.show()
                    self.btn_validasi.setDisabled(False)
                    self.btn_proses.setDisabled(True)
                    self.btn_ganti_desa.setDisabled(True)

                self.combo_kecamatan.setDisabled(True)
                self.combo_kelurahan.setDisabled(True)
                self.combo_lihat_data.setDisabled(False)
            else:
                self.combo_kecamatan.setDisabled(True)
                self.combo_kelurahan.setDisabled(True)
                self.combo_lihat_data.setDisabled(False)

                self.btn_validasi.setDisabled(False)
                self.btn_proses.setDisabled(True)
                self.btn_ganti_desa.setDisabled(False)

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

    def _handle_check_nib(self, checked):
        edit_null_count = len(
            [
                p
                for p in self._ds_parcel[DS_PERSIL_EDIT]
                if "NIB" not in p.keys() or not p["NIB"]
            ]
        )
        induk_null_count = len(
            [
                p
                for p in self._ds_parcel[DS_PERSIL_INDUK]
                if "NIB" not in p.keys() or not p["NIB"]
            ]
        )
        print(checked, edit_null_count, induk_null_count)
        print(self._ds_parcel[DS_PERSIL_EDIT])
        print(self._ds_parcel[DS_PERSIL_INDUK])

        if edit_null_count > 0 or induk_null_count > 0:
            if checked:
                self.btn_validasi.setDisabled(False)
                self.tabWidget.setCurrentIndex(0)
                self.label_status_l.setText("")
            else:
                self.btn_validasi.setDisabled(True)
                self.label_status_l.setText("Ada Kesalahan, cek error log")

    def _handle_batal(self):
        self.close()
