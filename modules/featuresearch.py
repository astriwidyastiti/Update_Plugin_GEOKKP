import os
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import pyqtSignal
from qgis.utils import iface

from qgis.core import QgsMapLayerProxyModel


FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/pencarian_fitur.ui")
)


class FeatureSearchDialog(QtWidgets.QDialog, FORM_CLASS):
    """Dialog for FeatureSearch"""

    closingPlugin = pyqtSignal()

    def __init__(self, parent=iface.mainWindow()):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        super(FeatureSearchDialog, self).__init__(parent)
        # self.utils = Utilities

        self.setupUi(self)

        # PyQt Bug. See issue https://github.com/qgis/QGIS/issues/38472
        self.layerAsal.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        layer_asal = self.layerAsal.currentLayer()
        print(layer_asal)
        self.cariFitur.layer = layer_asal
        self.populateComboBox()

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def populateComboBox(self):
        pass
        # self.cariFitur.featureChanged(print(self.cariFitur.feature()))
