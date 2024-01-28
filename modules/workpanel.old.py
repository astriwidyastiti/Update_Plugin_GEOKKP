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
    os.path.join(os.path.dirname(__file__), "../ui/workpanel/panel_kerja.ui")
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

        self._setup_workpanel()

    def _setup_workpanel(self):
        pass

    def closeEvent(self, event):
        self.closingPlugin.emit()
        self.stackedWidget.setCurrentIndex(0)
        event.accept()
