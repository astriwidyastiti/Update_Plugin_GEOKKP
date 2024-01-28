import os
import xml.etree.ElementTree as ET

from qgis.PyQt import QtWidgets, uic
from qgis.core import QgsProject
from qgis.PyQt.QtCore import pyqtSignal
from qgis.utils import iface

from .utils import dialogBox, logMessage


FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/openaerialmap.ui")
)


class OAMDialog(QtWidgets.QDialog, FORM_CLASS):
    """Dialog for Login"""

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        super(OAMDialog, self).__init__(parent)
        self.setupUi(self)
        self.project = QgsProject

        # clear
        self.OAMLink.clear()
        self.OAMLayerName.clear()

        self.LoadOAMButton.clicked.connect(self.loadWMTS)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def loadWMTS(self):
        url = self.OAMLink.text()
        name = self.OAMLayerName.text()
        # dialogBox(self.url)
        # self.parse_capabilities()
        params = (
            "crs=EPSG:3857&dpiMode=7&format=image/png"
            + "&layers=None&styles=default&tileMatrixSet=GoogleMapsCompatible&url="
        )
        full_url = params + url

        oam_layer = iface.addRasterLayer(full_url, name, "wms")

        if oam_layer.isValid():
            logMessage("OAM raster is valid")
        else:
            dialogBox(
                "Link OAM tidak valid. Periksa tautan WMTS yang diinputkan!", "Warning"
            )

        self.accept()

    """
    TODO: Sanitize input and read layer from capabilities
    """

    def parse_capabilities(self):
        self.url = self.OAMLink.text()
        capabilities_url = self.url + "?"
        print("capab", capabilities_url)
        tree = ET.parse(capabilities_url)
        root = tree.getroot()
        layers = root.findall("ows:Title")
        for title in layers:
            print(title.text)


# uri="url=https://tiles.openaerialmap.org/5da45f5336266f000578cc3a/0/5da45f5336266f000578cc3b/{z}/{x}/{y}&zmax=19&zmin=0"  # noqa 121
