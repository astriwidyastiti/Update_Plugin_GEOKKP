import os
import json

from qgis.PyQt import QtWidgets, uic

from qgis.PyQt.QtCore import pyqtSignal
from qgis.utils import iface

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/create_pbt.ui")
)

from .utils import readSetting, storeSetting
from .api import endpoints
from .memo import app_state


class CreatePBT(QtWidgets.QDialog, FORM_CLASS):
    """Dialog for Create Peta Bidang Tanah"""

    closingPlugin = pyqtSignal()
    processed = pyqtSignal(object)

    def __init__(
        self, tipe_pbt="", kendalisiptid="", proyek="", parent=iface.mainWindow()
    ):
        super(CreatePBT, self).__init__(parent)

        self._current_kantor_id = ""
        self._berkas_id = ""
        self._kendalisiptid = kendalisiptid
        self._proyek = proyek
        self._tipe_pbt = tipe_pbt

        self.setupUi(self)
        self.setup_workpanel()

        self.btn_process.clicked.connect(self._handle_process)
        self.btn_batal.clicked.connect(self.close)
        self.combo_provinsi.currentIndexChanged.connect(self._populate_kabupaten)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def setup_workpanel(self):
        current_kantor = readSetting("kantorterpilih", {})
        if not current_kantor or "kantorID" not in current_kantor:
            return

        self._current_kantor_id = current_kantor["kantorID"]
        self._current_tipe_kantor_id = str(current_kantor["tipeKantorId"])

        self._populate_program()
        self._populate_provinsi()

    def _populate_program(self):
        kantor_id = self._current_kantor_id
        self.combo_kegiatan.clear()
        if self._kendalisiptid and self._proyek:
            self.combo_kegiatan.addItem(self._proyek, self._kendalisiptid)
        else:
            program = readSetting("listprogram", {})
            if not program or kantor_id not in program:
                response = endpoints.get_program_by_kantor(kantor_id)
                response_json = json.loads(response.content)
                program[kantor_id] = response_json["PROGRAM"]
                storeSetting("listprogram", program)

            for item in program[kantor_id]:
                self.combo_kegiatan.addItem(item["NAMA"], item["PROGRAMID"])

    def _populate_provinsi(self):
        kantor_id = self._current_kantor_id
        tipe_kantor_id = self._current_tipe_kantor_id
        self.combo_provinsi.clear()
        response = endpoints.get_provinsi_by_kantor(
            kantor_id=kantor_id, tipe_kantor_id=tipe_kantor_id
        )
        response_json = json.loads(response.content)

        for data in response_json["PROPINSI"]:
            self.combo_provinsi.addItem(data["PROPNAMA"], data["PROPINSIID"])
        self._populate_kabupaten()

    def _populate_kabupaten(self):
        provinsi_id = self.combo_provinsi.currentData()
        print("provinsi_id", provinsi_id)
        kantor_id = self._current_kantor_id
        tipe_kantor_id = self._current_tipe_kantor_id
        self.combo_kabupaten.clear()
        response = endpoints.get_kabupaten_by_kantor(
            kantor_id=kantor_id, tipe_kantor_id=tipe_kantor_id, propinsi_id=provinsi_id
        )
        response_json = json.loads(response.content)

        for data in response_json["KABUPATEN"]:
            self.combo_kabupaten.addItem(data["KABUNAMA"], data["KABUPATENID"])

    def _handle_process(self):
        pegawai_state = app_state.get("pegawai", {})
        pegawai = pegawai_state.value
        if not pegawai or "userId" not in pegawai or "pegawaiID" not in pegawai:
            return

        self.btn_process.setDisabled(True)

        program_id = self.combo_kegiatan.currentData()
        wilayah_id = self.combo_kabupaten.currentData()

        try:
            if self._kendalisiptid and self._proyek:
                response = endpoints.create_new_peta_normatif(
                    pegawai["userId"],
                    self._kendalisiptid,
                    self._berkas_id,
                    wilayah_id,
                    self._current_kantor_id,
                    pegawai["pegawaiID"],
                )

                response_json = json.loads(response.content)
                print(response_json)
                payload = {"PBT": response_json}
                self.processed.emit({"myPBT": payload})
            else:
                response = endpoints.create_new_pbt_for_apbn(
                    pegawai["userId"],
                    program_id,
                    wilayah_id,
                    self._current_kantor_id,
                    self._tipe_pbt,
                )
                response_json = json.loads(response.content)
                print(response_json)
                payload = {"PBT": response_json}
                self.processed.emit({"myPBT": payload})
        except Exception as err:
            payload = {
                "valid": False,
                "nomor": None,
                "tahun": None,
                "wilayahId": wilayah_id,
                "newParcels": [],
                "gugusId": None,
                "errorStack": str(err),
                "status": "",
                "penggunaSpasial": pegawai["userId"],
                "tglDiumumkan": "",
                "dokumenPengukuranId": None,
                "tglSelesaiDiumumkan": "",
                "programId": program_id,
                "noSeq": None,
                "mitraKerjaid": None,
                "tipeProdukId": None,
            }
            self.processed.emit({"myPBT": payload})

        self.close()
