import os
import json
import base64
from posixpath import expanduser

from qgis.PyQt import QtWidgets, uic

from qgis.PyQt.QtCore import pyqtSignal
from qgis.utils import iface

from ...api import endpoints
from ...utils import (
    export_layer_to_dxf,
    readSetting,
    get_project_crs,
    sdo_to_layer,
    get_layer_config,
    add_layer,
)
from ...create_pbt import CreatePBT
from ...memo import app_state
from ...topology import quick_check_topology
from ...desain_pbt import DesainPBT

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../../../ui/workpanel/tab_apbn.ui")
)


STACKWIDGET_LOKASI = 0
STACKWIDGET_RUTIN = 1


class TabApbn(QtWidgets.QWidget, FORM_CLASS):
    """Dialog for APBN"""

    closingPlugin = pyqtSignal()

    def __init__(self, parent=iface.mainWindow()):
        super(TabApbn, self).__init__(parent)

        self._process_available = False

        self._start = 0
        self._limit = 20
        self._count = -1
        self._current_document_pengukuran_id = None
        self._current_layers = []
        self._submitted_parcels = []

        self._pbt = {}

        self._text_nomor = ""
        self._text_tahun = ""
        self._text_kantor_id = ""
        self._text_kegiatan = ""

        self.setupUi(self)
        self._set_initial_toolbar_state()
        self.setup_workpanel()

        self.btn_buat.clicked.connect(self._handle_buat)
        self.btn_mulai.clicked.connect(self._handle_mulai)
        self.btn_cari.clicked.connect(self._handle_cari)
        self.btn_simpan.clicked.connect(self._handle_simpan)
        self.btn_first.clicked.connect(self._handle_first_page)
        self.btn_last.clicked.connect(self._handle_last_page)
        self.btn_next.clicked.connect(self._handle_next_page)
        self.btn_prev.clicked.connect(self._handle_prev_page)
        self.btn_tutup.clicked.connect(self._handle_tutup)
        self.btn_selesai.clicked.connect(self._handle_selesai)
        self.table_apbn.itemSelectionChanged.connect(self._handle_apbn_select)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        self.stackedWidget.setCurrentIndex(0)
        event.accept()

    def setup_workpanel(self):
        current_kantor = readSetting("kantorterpilih", {})
        if current_kantor and "kantorID" in current_kantor:
            self._text_kantor_id = current_kantor["kantorID"]

    def _handle_cari(self):
        self._start = 0
        self._count = -1

        self.btn_first.setDisabled(True)
        self.btn_last.setDisabled(True)
        self.btn_next.setDisabled(True)
        self.btn_prev.setDisabled(True)

        self._cari_berkas_apbn()

    def _cari_berkas_apbn(self):
        nomor_pbt = self.input_nomor_pbt.text()
        tahun = self.input_tahun.text()
        kegiatan = self.combo_kegiatan.currentData() or ""

        response = endpoints.get_pbt_for_apbn(
            nomor_pbt,
            tahun,
            self._text_kantor_id,
            kegiatan,
            "PBT",
            self._start,
            self._limit,
            self._count,
        )
        response_json = json.loads(response.content)
        print("cari", response_json)
        self._setup_pagination(response_json["JUMLAHTOTAL"])
        self._populate_berkas_apbn(response_json["PBTAPBN"])

    def _set_initial_toolbar_state(self):
        self.btn_mulai.setDisabled(True)
        self.btn_simpan.setDisabled(True)
        self.btn_link.setDisabled(True)
        self.btn_layout.setDisabled(True)
        self.btn_tutup.setDisabled(True)
        self.btn_selesai.setDisabled(True)

    def _setup_pagination(self, data):
        if not data:
            return

        if self._count == -1:
            self._count = data[0]["COUNT(1)"]
        print(self._count, self._start, self._limit)

        if self._count > 0:
            if self._start + self._limit >= self._count:
                page = f"{self._start + 1} - {self._count} dari {self._count}"

                self.btn_next.setDisabled(True)
                self.btn_last.setDisabled(True)
            else:
                page = f"{self._start + 1} - {self._start + self._limit} dari {self._count}"
                self.btn_next.setDisabled(False)
                self.btn_last.setDisabled(False)
        else:
            page = "0"
            self.btn_next.setDisabled(True)
            self.btn_prev.setDisabled(True)
            self.btn_first.setDisabled(True)
            self.btn_last.setDisabled(True)

        prev_btn_disabled = self._start == 0 or self._count == 0
        self.btn_prev.setDisabled(prev_btn_disabled)
        self.btn_first.setDisabled(self._start == 0)
        self.input_page.setText(page)

    def _handle_first_page(self):
        self._start = 0
        self._cari_berkas_apbn()

    def _handle_next_page(self):
        self._start += self._limit
        self._cari_berkas_apbn()

    def _handle_prev_page(self):
        self._start -= self._limit
        self._cari_berkas_apbn()

    def _handle_last_page(self):
        self._start = (self._count // self._limit) * self._limit
        if self._start >= self._count:
            self._start -= self._limit
        self._cari_berkas_apbn()

    def _handle_apbn_select(self):
        print(self.table_apbn.selectedItems())
        disabled = len(self.table_apbn.selectedItems()) == 0
        self.btn_mulai.setDisabled(disabled)

    def _populate_berkas_apbn(self, data):
        self.table_apbn.setRowCount(0)

        if not data:
            return

        columns = list(data[0].keys())
        self.table_apbn.setColumnCount(len(columns))
        self.table_apbn.setHorizontalHeaderLabels(columns)

        for item in data:
            pos = self.table_apbn.rowCount()
            self.table_apbn.insertRow(pos)

            for index, col in enumerate(columns):
                self.table_apbn.setItem(
                    pos, index, QtWidgets.QTableWidgetItem(str(item[col]))
                )

        self.table_apbn.setColumnHidden(0, True)
        self.table_apbn.setColumnHidden(4, True)
        self.table_apbn.setColumnHidden(5, True)

    def _set_button_enabled(self, enabled):
        self.btn_layout.setDisabled(not enabled)
        self.btn_tutup.setDisabled(not enabled)
        self.btn_link.setDisabled(not enabled)

    def _handle_buat(self):
        pbt_widget = CreatePBT("PBT")
        pbt_widget.show()
        pbt_widget.processed.connect(self._handle_process_buat_pbt)

    def _handle_process_buat_pbt(self, payload):
        pbt_data = payload["myPBT"]["PBT"]

        if pbt_data["errorStack"]:
            QtWidgets.QMessageBox.critical(
                None,
                "KKP Web",
                pbt_data["errorStack"][0],
            )
            return

        print(pbt_data)

        self.input_nomor_pbt.setText(pbt_data["nomor"])
        self.input_tahun.setText(pbt_data["tahun"])
        self.input_nomor_pbt.setDisabled(True)
        self.input_tahun.setDisabled(True)
        self._start = 0
        self._count = -1
        self.btn_first.setDisabled(True)
        self.btn_last.setDisabled(True)
        self.btn_next.setDisabled(True)
        self.btn_prev.setDisabled(True)

        self._cari_berkas_apbn()
        self._process_available = True

        self._current_document_pengukuran_id = pbt_data["dokumenPengukuranId"]
        self._set_button_enabled(True)
        self.input_nomor_pbt.setDisabled(True)
        self.input_tahun.setDisabled(True)
        self.btn_cari.setDisabled(True)
        self.btn_buat.setDisabled(True)
        self.btn_mulai.setDisabled(True)
        self.btn_simpan.setDisabled(False)

        QtWidgets.QMessageBox.information(
            None,
            "GeoKKP Web",
            f"Peta bidang telah dibuat dengan nomor : {pbt_data['nomor']}/{pbt_data['tahun']}",
        )

    def _handle_mulai(self):
        self.table_apbn.setColumnHidden(0, False)
        self.table_apbn.setColumnHidden(4, False)
        self.table_apbn.setColumnHidden(5, False)
        selected_apbn = self.table_apbn.selectedItems()
        self.table_apbn.setColumnHidden(0, True)
        self.table_apbn.setColumnHidden(4, True)
        self.table_apbn.setColumnHidden(5, True)
        username_state = app_state.get("username", "")
        username = username_state.value

        if not selected_apbn:
            QtWidgets.QMessageBox.warning(
                None,
                "Perhatian",
                f"Pilih Sebuah Berkas Yang Akan Diproses",
            )
            return

        self._current_document_pengukuran_id = selected_apbn[0].text()
        current_nomor_pbt = selected_apbn[1].text()
        current_tahun = selected_apbn[2].text()

        response = endpoints.start_edit_pbt_for_apbn(
            self._current_document_pengukuran_id, username
        )
        response_json = json.loads(response.content)
        self._pbt = response_json
        print(response_json)

        if (
            response_json["penggunaSpasial"]
            and response_json["penggunaSpasial"] != username
        ):
            user = response_json["penggunaSpasial"]
            QtWidgets.QMessageBox.warning(
                None, "Perhatian", f"Peta bidang sedang digunakan oleh {user}"
            )
            return

        self.btn_mulai.setDisabled(True)
        self._process_available = True

        gugus_ids = [response_json["gugusId"]]

        self._load_berkas_spasial(gugus_ids, False)
        self._set_button_enabled(True)

        disable_link = bool(response_json["mitraKerjaid"])
        self.btn_link.setDisabled(disable_link)
        self.input_nomor_pbt.setText(current_nomor_pbt)
        self.input_tahun.setText(current_tahun)
        self.input_nomor_pbt.setDisabled(True)
        self.input_tahun.setDisabled(True)
        self.btn_cari.setDisabled(True)
        self.btn_buat.setDisabled(True)
        self.btn_mulai.setDisabled(True)
        self.btn_simpan.setDisabled(False)

    def _load_berkas_spasial(self, gugus_ids, riwayat=False):
        response_spatial_sdo = endpoints.get_spatial_document_sdo(
            gugus_ids=gugus_ids, include_riwayat=riwayat
        )
        response_spatial_sdo_json = json.loads(response_spatial_sdo.content)
        print(response_spatial_sdo_json)

        if not response_spatial_sdo_json["status"]:
            QtWidgets.QMessageBox.critical(None, "Error", "Proses Unduh Geometri gagal")
            return

        epsg = get_project_crs()
        layer_config = get_layer_config(20100)

        if response_spatial_sdo_json["geoKkpPolygons"]:
            layer = sdo_to_layer(
                response_spatial_sdo_json["geoKkpPolygons"],
                name=layer_config["Nama Layer"],
                symbol=layer_config["Style Path"],
                crs=epsg,
                coords_field="boundary",
            )
        else:
            layer = add_layer(
                layer_config["Nama Layer"],
                layer_config["Tipe Layer"],
                layer_config["Style Path"],
                layer_config["Attributes"][0],
            )

        self._current_layers.append(layer)

    def _handle_simpan(self):
        topo_error_message = []
        for layer in self._current_layers:
            valid, num = quick_check_topology(layer)
            print(valid, num)
            if not valid:
                message = f"Ada {num} topology error di layer {layer.name()}"
                topo_error_message.append(message)

        if topo_error_message:
            QtWidgets.QMessageBox.warning(
                None, "Perhatian", "\n".join(topo_error_message)
            )
            return

        pd_widget = DesainPBT(
            peta_bidang=self._pbt,
            tipe_sistem_koordinat="TM3",
            is_invent=False,
            current_layers=self._current_layers,
        )
        pd_widget.show()
        pd_widget.processed.connect(self._handle_pbt_processed)

    def _handle_pbt_processed(self, payload):
        if payload["submittedParcel"]:
            self.btn_simpan.setDisabled(False)
            self.btn_link.setDisabled(False)
            self.btn_layout.setDisabled(False)
            self.btn_selesai.setDisabled(False)

            self._submitted_parcels = payload["submittedParcel"]
            self._pbt["wilayahId"] = payload["wilayahId"]
            self._pbt["newParcels"] = payload["submittedParcel"]
            self._pbt["gugusId"] = payload["gugusId"]

            if not self._pbt["mitraKerjaid"]:
                self.btn_link.setDisabled(True)

                file_name = f"pbt_{payload['nomor']}_{payload['tahun']}.dxf"
                output = os.path.join(expanduser("~"), file_name)
                result = export_layer_to_dxf(self._current_layers, output)
                if result:
                    with open(output, "rb") as f:
                        byte = f.read()
                        base64data = base64.b64encode(byte)
                        response = endpoints.upload_dxf_pbt_skb(
                            self._text_kantor_id,
                            self._pbt["mitraKerjaId"],
                            payload["dokumenPengukuranId"],
                            base64data,
                        )
                        response_json = json.loads(response.content)
                        print(response_json)
        else:
            if payload["autoClosed"]:
                self._handle_tutup()

    def _handle_tutup(self):
        response = endpoints.stop_pbt(self._current_document_pengukuran_id)
        print(response.content)
        stopped = response.content.decode("utf-8") == "true"

        if stopped:
            self._process_available = False
            self._set_button_enabled(False)
            self.input_nomor_pbt.setDisabled(False)
            self.input_tahun.setDisabled(False)
            self.btn_cari.setDisabled(False)
            self.btn_buat.setDisabled(False)
            self.btn_simpan.setDisabled(True)
            self.btn_mulai.setDisabled(True)
            self.btn_tutup.setDisabled(True)
            self.btn_selesai.setDisabled(True)
            self.btn_link.setDisabled(True)
            self.btn_layout.setDisabled(True)

            self._pbt = None
            QtWidgets.QMessageBox.information(
                None, "Informasi", "Proses spasial sudah dihentikan"
            )
        else:
            QtWidgets.QMessageBox.critical(
                None, "Error", "Proses spasial tidak dapat dihentikan"
            )

    def _handle_selesai(self):
        if self._submitted_parcels:
            parcels = [str(f) for f in self._submitted_parcels]
            force_mapping = True

            already_mapped = endpoints.cek_mapping(parcels)
            print(already_mapped.content)

            if already_mapped.content.lower() != "true":
                if not force_mapping:
                    result = QtWidgets.QMessageBox.question(
                        self,
                        "Selesai Berkas",
                        "Persil belum dipetakan\nApakah akan menyelesaikan berkas?",
                    )
                    if result != QtWidgets.QMessageBox.Yes:
                        return
                else:
                    QtWidgets.QMessageBox.information(
                        None,
                        "Selesai Berkas",
                        "Persil belum dipetakan\nUntuk menyelesaikan berkas lakukan proses Map Placing terlebih dahulu",
                    )

        response = endpoints.finish_pbt(self._current_document_pengukuran_id)
        if response.content.decode("utf-8").split(":")[0] == "OK":
            self._process_available = False
            self._set_button_enabled(False)
            self.input_nomor_pbt.setDisabled(False)
            self.input_tahun.setDisabled(False)
            self.btn_cari.setDisabled(False)
            self.btn_buat.setDisabled(False)
            self.btn_simpan.setDisabled(True)
            self.btn_mulai.setDisabled(True)
            self.btn_tutup.setDisabled(True)
            self.btn_link.setDisabled(True)
            self.btn_layout.setDisabled(True)

            self._pbt = None
            QtWidgets.QMessageBox.information(
                None,
                "Informasi",
                "Proses spasial sudah selesai",
            )
            self._cari_berkas_apbn()
        else:
            QtWidgets.QMessageBox.critical(
                None,
                "Error",
                response.content.decode("utf-8"),
            )
