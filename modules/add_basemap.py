import os

# from qgis.PyQt.QtCore import Qt, QTimer
# from qgis.PyQt.QtWidgets import QTreeWidgetItem
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem

from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import pyqtSignal
from qgis.utils import iface

from .utils import logMessage, readSetting, loadXYZ

# using utils
from .utils import icon


FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/basemap.ui")
)


class AddBasemapDialog(QtWidgets.QDialog, FORM_CLASS):
    """Dialog for Add Basemap from List"""

    closingPlugin = pyqtSignal()

    def __init__(self, parent=iface.mainWindow()):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        super(AddBasemapDialog, self).__init__(parent)
        # self.utils = Utilities
        self.setWindowIcon(icon("icon.png"))
        self.setupUi(self)
        data_basemap = readSetting("basemaps")
        self.populateDaftarBasemap(data_basemap)
        self.buttonTambahLayer.clicked.connect(self.addToQGIS)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def set_crs(self):
        self._currentcrs = self.selectProj.crs()

    def populateDaftarBasemap(self, data):
        if data:
            self.model = QStandardItemModel(self.daftarBasemap)
            for key, values in data.items():
                for count, value in enumerate(values):
                    icons = value["icon"]
                    item = QStandardItem(value["nama"])
                    item.setData(value["url"], 256)
                    item.setIcon(icon(f"../images/basemap_icons/{icons}"))
                    self.model.appendRow(item)
            self.daftarBasemap.setModel(self.model)
        else:
            logMessage("data tidak dijumpai pada memory")

    def addToQGIS(self):
        for index in self.daftarBasemap.selectedIndexes():
            url = index.data(256)
            name = index.data()
            # print(index.row(), index.data(256))
            loadXYZ(url, name)
