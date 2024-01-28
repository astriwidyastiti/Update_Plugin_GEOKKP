import os

from qgis.PyQt.QtCore import Qt, QTimer
from qgis.gui import QgsRubberBand

from qgis.core import (
    QgsCoordinateTransform,
    QgsRectangle,
    QgsPoint,
    QgsPointXY,
    QgsGeometry,
    QgsWkbTypes,
    QgsProject,
)
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import pyqtSignal
from qgis.utils import iface

# using utils
from .utils import icon, parse_raw_coordinate

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "../ui/goto.ui"))


class GotoXYDialog(QtWidgets.QDialog, FORM_CLASS):
    """Dialog for Zoom to Location"""

    closingPlugin = pyqtSignal()

    def __init__(self, parent=iface.mainWindow()):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        super(GotoXYDialog, self).__init__(parent)
        # self.utils = Utilities
        self.crossRb = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.crossRb.setColor(Qt.red)
        self.setWindowIcon(icon("icon.png"))

        self._currentcrs = None

        self.setupUi(self)
        self.buttonBox.accepted.connect(self.zoomtodialog)
        self.selectProj.crsChanged.connect(self.set_crs)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def set_crs(self):
        self._currentcrs = self.selectProj.crs()
        # print(self._currentcrs.description())

    def parse_coordinate(self):
        coordinate_text = self.mLineEditXY.text()
        points = parse_raw_coordinate(coordinate_text)
        # TODO: Extend with more than one coordinates
        first_point = next(points)
        return first_point

    def zoomtodialog(self):
        point = self.parse_coordinate()
        lon = point.x()
        lat = point.y()
        self.zoomTo(self._currentcrs, lat, lon)

    def zoomTo(self, src_crs, lat, lon):
        self.canvas.zoomScale(1000)
        canvas_crs = self.canvas.mapSettings().destinationCrs()
        transform = QgsCoordinateTransform(src_crs, canvas_crs, QgsProject.instance())
        x, y = transform.transform(float(lon), float(lat))

        rect = QgsRectangle(x, y, x, y)
        self.canvas.setExtent(rect)

        pt = QgsPointXY(x, y)
        self.highlight(pt)
        self.canvas.refresh()

    def highlight(self, point):

        currExt = self.canvas.extent()

        leftPt = QgsPoint(currExt.xMinimum(), point.y())
        rightPt = QgsPoint(currExt.xMaximum(), point.y())

        topPt = QgsPoint(point.x(), currExt.yMaximum())
        bottomPt = QgsPoint(point.x(), currExt.yMinimum())

        horizLine = QgsGeometry.fromPolyline([leftPt, rightPt])
        vertLine = QgsGeometry.fromPolyline([topPt, bottomPt])

        self.crossRb.reset(QgsWkbTypes.LineGeometry)
        self.crossRb.addGeometry(horizLine, None)
        self.crossRb.addGeometry(vertLine, None)

        QTimer.singleShot(1000, self.resetRubberbands)

    def resetRubberbands(self):
        self.crossRb.reset()
