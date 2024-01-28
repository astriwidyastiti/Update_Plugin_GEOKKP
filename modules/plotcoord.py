import os

from qgis.core import Qgis, QgsCoordinateTransform, QgsGeometry, QgsFeature, QgsProject
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtGui import QTextCursor, QTextCharFormat
from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.utils import iface

# using utils
from .utils import (
    icon,
    validate_raw_coordinates,
    parse_raw_coordinate,
    display_message_bar,
    logMessage,
)

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/plot_coordinate.ui")
)


class CoordErrorHighlight:
    def __init__(self, text_editor=None):
        self._text_editor = text_editor
        self._highlight = QTextCharFormat()
        self._highlight.setBackground(Qt.yellow)

    def _highlight_error(self, error):
        if self._text_editor:
            start, end = self._get_error_position(error)
            cursor = self._text_editor.textCursor()
            cursor.setPosition(start, QTextCursor.MoveAnchor)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            cursor.setCharFormat(self._highlight)

    def _get_error_position(self, error):
        end = error.col + error.row
        start = end - len(error.error_value)
        return start, end

    def set_errors(self, errors):
        if errors:
            for error in errors:
                self._highlight_error(error)


class PlotCoordinateDialog(QtWidgets.QDialog, FORM_CLASS):
    """Dialog for Coordinate Plot"""

    closingPlugin = pyqtSignal()

    def __init__(self, parent=iface.mainWindow()):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        super(PlotCoordinateDialog, self).__init__(parent)
        self.project = QgsProject

        self.setWindowIcon(icon("icon.png"))

        self._currentcrs = None

        self._coordinate_validation = None

        self.setupUi(self)
        # self.buttonBox.accepted.connect(self.start_plot)
        self.listCoordsProj.crsChanged.connect(self.set_crs)
        self.list_coords.cursorPositionChanged.connect(self.update_status_cursor)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def set_crs(self):
        self._currentcrs = self.listCoordsProj.crs()
        # print(self._currentcrs.description())

    def accept(self):
        # prefent from closing to show message bar
        self.start_plot()

    def update_status_cursor(self):
        cursor = self.list_coords.textCursor()
        row = cursor.blockNumber()
        col = cursor.positionInBlock()
        self.current_row.setText(str(row))
        self.current_col.setText(str(col))

    def start_plot(self):
        # read the input and validate it
        raw_coords = self.list_coords.toPlainText()
        error_highlight = CoordErrorHighlight(text_editor=self.list_coords)
        self._coordinate_validation = validate_raw_coordinates(raw_coords)
        if not self._coordinate_validation.is_valid:
            error_highlight.set_errors(self._coordinate_validation.errors)
            display_message_bar(
                parent=self.messageBar,
                tag="Error",
                message=f"{len(self._coordinate_validation.errors)} errors in coordinate list",
                level=Qgis.Warning,
                duration=0,
            )
            error_message = "\t\n".join(
                (
                    f"row: {error.row}, col: {error.col}, value: {error.error_value}"
                    for error in self._coordinate_validation.errors
                )
            )
            logMessage(
                f"Raw coordinate invalid, unexpected value on:\n{error_message}",
                Qgis.Critical,
            )
            return

        # transform coordinates
        source_crs = self._currentcrs
        canvas_crs = self.canvas.mapSettings().destinationCrs()
        tr = QgsCoordinateTransform(
            source_crs, canvas_crs, self.project.instance().transformContext()
        )

        # extract coordinate pairs
        coords = parse_raw_coordinate(raw_coords)

        layer = self.project.instance().mapLayersByName("Persil")[0]
        feat = QgsFeature()
        feat.setGeometry(QgsGeometry.fromPolygonXY([coords]))
        prov = layer.dataProvider()
        prov.addFeatures([feat])
        # layer.setCrs(source_crs)
        layer.updateExtents()
        # uri = os.path.join(os.path.dirname(__file__), '../styles/dimension.qml')
        # layer.loadNamedStyle(uri)
        # layer = self.iface.activeLayer()
        # print(layer.name())
        # self.project.instance().addMapLayers([layer])
        self.close()
        layer.triggerRepaint()
        extent = layer.extent()
        self.canvas.setExtent(tr.transform(extent))
        # polygon = QgsRubberBand(self.canvas)
        # polygon.setToGeometry(QgsGeometry.fromPolygonXY([list_coordinates]), None)
        # polygon.setColor(QColor(0, 0, 255))
        # polygon.setFillColor(QColor(255,255,0))
        # polygon.setWidth(3)
        # self.canvas.setCenter(list_coordinates[0])

        # print("then, {}".format(coords[3].split(",")[0]))
        # print("then, {}".format(coords[3].split(",")[1]))
        # self.zoomTo(self._currentcrs, lat, lon)
        # except Exception:
        #   pass
