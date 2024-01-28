import os
import json
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QTreeWidgetItem
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import pyqtSignal
from qgis.utils import iface

from .utils import logMessage, readSetting, add_layer, icon


FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/addlayerv2.ui")
)


class AddLayerDialog(QtWidgets.QDialog, FORM_CLASS):
    """Dialog for Add Layers from List"""

    closingPlugin = pyqtSignal()

    def __init__(self, parent=iface.mainWindow()):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        super(AddLayerDialog, self).__init__(parent)
        # self.utils = Utilities
        self.setWindowIcon(icon("icon.png"))
        self._currentcrs = None
        self.setupUi(self)

        data_layer = readSetting("layers")
        try:
            self.populateDaftarLayer(data_layer)
        except Exception:
            logMessage("daftar layer gagal dimuat")

        self.cariDaftarLayer.valueChanged.connect(self.findLayer)
        self.pushButtonAddtoQGIS.clicked.connect(self.addToQGIS)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def set_crs(self):
        self._currentcrs = self.selectProj.crs()
        # print(self._currentcrs.description())

    def populateDaftarLayer(self, data):
        items = []
        for key, values in data.items():
            item = QTreeWidgetItem([key])
            for count, value in enumerate(values):
                nama_layer = value["Nama Layer"]
                tipe_layer = value["Tipe Layer"]
                style_path = value["Style Path"]
                try:
                    attr_theme = str(value["Attributes"][0])
                except IndexError:
                    attr_theme = None
                child = QTreeWidgetItem(
                    [nama_layer, tipe_layer, style_path, attr_theme]
                )
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                child.setCheckState(0, Qt.Unchecked)
                item.addChild(child)
            items.append(item)
        self.daftarLayer.insertTopLevelItems(0, items)

    def findLayer(self):
        textto_find = self.cariDaftarLayer.value()
        items = self.daftarLayer.findItems(
            textto_find, Qt.MatchContains | Qt.MatchRecursive
        )
        for item in items:
            item.setSelected(True)
            self.daftarLayer.setCurrentItem(item)
            self.daftarLayer.scrollToItem(
                item, QtWidgets.QAbstractItemView.PositionAtTop
            )

    def deleteSelection(self):
        root = self.daftarLayer.invisibleRootItem()
        group_count = root.childCount()
        for group in range(group_count):
            groupItem = root.child(group)
            layer_count = groupItem.childCount()
            for layer in range(layer_count):
                item = groupItem.child(layer)
                if item is not None:
                    item.setSelected(False)

    def addSelectedLayer(self):
        root = self.daftarLayer.invisibleRootItem()
        for item in self.daftarLayer.selectedItems():
            root.removeChild(item)
            self.layerTerpilih.insertTopLevelItem(0, item)

    def deleteSelectedLayer(self):
        root = self.layerTerpilih.invisibleRootItem()
        for item in self.layerTerpilih.selectedItems():
            root.removeChild(item)
            self.daftarLayer.insertTopLevelItem(0, item)

    def addToQGIS(self):
        root = self.daftarLayer.invisibleRootItem()
        group_count = root.childCount()
        for group in range(group_count):
            groupItem = root.child(group)
            layer_count = groupItem.childCount()
            for layer in range(layer_count):
                item = groupItem.child(layer)
                if item.checkState(0) != 0:
                    layername = item.text(0)
                    layertype = item.text(1)
                    layersymbology = item.text(2)
                    if item.text(3):
                        fields = json.loads(item.text(3).replace("'", '"'))
                    else:
                        fields = None
                    print(item.text(0), item.text(1), item.text(2), fields)
                    add_layer(layername, layertype, layersymbology, fields)
