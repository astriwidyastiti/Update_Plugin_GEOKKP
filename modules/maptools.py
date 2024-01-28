from qgis.gui import QgsMapTool  # , QgsVertexMarker

# from qgis.core import QgsPointXY
# from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import pyqtSignal


class MapTool(QgsMapTool):
    """
    Docstring is needed here
    """

    map_clicked = pyqtSignal(float, float)

    def __init__(self, canvas, vm):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas
        self.vertexmarker = vm

        self.reset()
        self.isEmittingPoint = True
        print("is emitting ", self.isEmittingPoint)

    def reset(self):
        self.isEmittingPoint = False

    def canvasMoveEvent(self, event):
        if self.isEmittingPoint:
            self.point_snap = self.snapping_point(event.pos())
            self.vertexmarker.setCenter(self.point_snap)

    def canvasReleaseEvent(self, event):
        self.isEmittingPoint = False
        self.vertexmarker.setCenter(self.point_snap)
        self.map_clicked.emit(self.point_snap.x(), self.point_snap.y())

    def deactivate(self):
        QgsMapTool.deactivate(self)

    def snapping_point(self, point):
        snapped = self.canvas.snappingUtils().snapToMap(point)

        if snapped.isValid():
            return snapped.point()
        else:
            return self.canvas.getCoordinateTransform().toMapCoordinates(point)
