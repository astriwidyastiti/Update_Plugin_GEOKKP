import os

from qgis.PyQt import QtWidgets, uic

from qgis.PyQt.QtCore import pyqtSignal
from qgis.utils import iface

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/import_peta_bidang_sipt.ui")
)


STACKWIDGET_LOKASI = 0
STACKWIDGET_RUTIN = 1


class ImportPetaBidangSIPT(QtWidgets.QWidget, FORM_CLASS):
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
        kendali_id="",
        berkas_id="",
        penggunaan="",
        is_keliling=False,
        is_rincikan=False,
        parent=iface.mainWindow(),
    ):
        super(ImportPetaBidangSIPT, self).__init__(parent)

        self._pbt = peta_bidang
        self._kendali_id = kendali_id
        self._berkas_id = berkas_id
        self._penggunaan = penggunaan
        self._is_keliling = is_keliling
        self._is_rincikan = is_rincikan

        self.setupUi(self)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        self.stackedWidget.setCurrentIndex(0)
        event.accept()

    def setup_workpanel(self):
        pass
