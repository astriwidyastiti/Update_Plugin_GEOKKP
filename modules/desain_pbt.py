import os

from qgis.PyQt import QtWidgets, uic

from qgis.PyQt.QtCore import pyqtSignal
from qgis.utils import iface

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/desain_pbt.ui")
)

from .import_peta_bidang import ImportPetaBidang
from .import_peta_bidang_sipt import ImportPetaBidangSIPT

STACKWIDGET_LOKASI = 0
STACKWIDGET_RUTIN = 1


class DesainPBT(QtWidgets.QDialog, FORM_CLASS):
    """Dialog for Desain PBT"""

    closingPlugin = pyqtSignal()
    processed = pyqtSignal(object)

    def __init__(
        self,
        peta_bidang,
        tipe_sistem_koordinat="TM3",
        is_invent=False,
        kendali_id="",
        berkas_id="",
        penggunaan="",
        is_keliling=False,
        is_rincikan=False,
        current_layers=[],
        parent=iface.mainWindow(),
    ):
        super(DesainPBT, self).__init__(parent)

        self._pbt = peta_bidang
        self._tipe_sistem_koordinat = tipe_sistem_koordinat
        self._is_invent = is_invent
        self._kendali_id = kendali_id
        self._berkas_id = berkas_id
        self._penggunaan = penggunaan
        self._is_keliling = is_keliling
        self._is_rincikan = is_rincikan
        self._is_pengadaan = bool(kendali_id)
        self._current_layers = current_layers

        self.setupUi(self)
        self.setup_workpanel()

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def setup_workpanel(self):
        layout = QtWidgets.QVBoxLayout(self.tab_desain)
        if not self._is_pengadaan:
            ipb = ImportPetaBidang(
                self._pbt,
                self._tipe_sistem_koordinat,
                self._is_invent,
                current_layers=self._current_layers,
                parent=self.tab_desain,
            )
        else:
            ipb = ImportPetaBidangSIPT(
                self._pbt,
                self._kendali_id,
                self._berkas_id,
                self._penggunaan,
                self._is_keliling,
                self._is_rincikan,
                parent=self.tab_desain,
            )
        ipb.writeErrorLog.connect(self._handle_write_error)
        ipb.writeRightStatus.connect(self._handle_write_right_status)
        ipb.writeLeftStatus.connect(self._handle_write_left_status)
        ipb.changeTabIndex.connect(self._handle_change_tab_index)
        ipb.processed.connect(self._handle_processed)

        layout.addWidget(ipb)
        self.tab_desain.layout().addLayout(layout)

    def _handle_write_error(self, error):
        self.error_log.setText(error)

    def _handle_write_right_status(self, status):
        self.label_status_r.setText(status)

    def _handle_write_left_status(self, status):
        self.label_status_l.setText(status)

    def _handle_change_tab_index(self, index):
        self.tabWidget.setCurrentIndex(index)

    def _handle_processed(self, payload):
        print("desain processd", payload)
        self.processed.emit(payload)
