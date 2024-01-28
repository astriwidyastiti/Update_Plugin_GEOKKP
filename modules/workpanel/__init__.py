import os
import json

from qgis.PyQt import QtWidgets, uic
from qgis.core import QgsProject
from qgis.PyQt.QtGui import QDesktopServices

from qgis.PyQt.QtCore import pyqtSignal, QUrl
from qgis.utils import iface

from ..login import LoginDialog
from ..memo import app_state
from ..topology import quick_check_topology

from .tabs.tab_apbn import TabApbn
from .tabs.tab_gambar_denah import TabGambarDenah
from .tabs.tab_invent import TabInvent
from .tabs.tab_lokasi import TabLokasi
from .tabs.tab_partisipatif import TabPartisipatif
from .tabs.tab_pemetaan_persil import TabPemetaanPersil
from .tabs.tab_rutin import TabRutin
from .tabs.tab_surat_ukur import TabSuratUkut
from .tabs.tab_unduh_persil import TabUnduhPersil

# using utils
from ..utils import (
    icon,
    readSetting,
    storeSetting,
    get_epsg_from_tm3_zone,
    set_project_crs_by_epsg,
    get_project_crs,
    sdo_to_layer,
)
from ..api import endpoints

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../../ui/workpanel/panel_kerja.ui")
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

        self._main_dock = None
        self._main_tab = None
        self._setup_workpanel()

        self.mulaiGeokkp.clicked.connect(self.login_geokkp)
        self.bantuanGeokkp.clicked.connect(self.openhelp)

        login_state = app_state.get("logged_in")
        login_state.changed.connect(self._handle_login_callback)

    def _setup_workpanel(self):
        self._main_dock = self.stackedWidget.findChild(QtWidgets.QWidget, "main_dock")
        self._main_tab = self._main_dock.findChild(QtWidgets.QWidget, "main_tab")
        self._main_tab.addTab(TabLokasi(), "Lokasi")
        self._main_tab.addTab(TabRutin(), "Rutin")
        self._main_tab.addTab(TabApbn(), "APBN")
        self._main_tab.addTab(TabInvent(), "Invent")
        self._main_tab.addTab(TabPemetaanPersil(), "Pemetaan Persil")
        self._main_tab.addTab(TabSuratUkut(), "Surat Ukur")
        self._main_tab.addTab(TabGambarDenah(), "Gambar Denah")
        self._main_tab.addTab(TabUnduhPersil(), "Unduh Persil")
        self._main_tab.addTab(TabPartisipatif(), "Partisipatif")

        self._main_tab.currentChanged.connect(self._handle_tab_changed)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        self.stackedWidget.setCurrentIndex(0)
        event.accept()

    def login_geokkp(self):
        if self.loginaction is None:
            self.loginaction = LoginDialog()
        self.loginaction.show()

    def show_workpanel(self):
        self.stackedWidget.setCurrentWidget(self._main_dock)

    def switch_panel(self, page):
        self.stackedWidget.setCurrentIndex(page)

    def current_widget(self):
        return self.stackedWidget.currentWidget()

    def _handle_login_callback(self, success):
        if success:
            current_index = self._main_tab.currentIndex()
            self._handle_tab_changed(current_index)

    def _handle_tab_changed(self, index):
        current_tab = self._main_tab.widget(index)
        current_tab.setup_workpanel()

    def openhelp(self):
        QDesktopServices.openUrl(QUrl("https://geokkp-gis.github.io/docs/"))
        pass
