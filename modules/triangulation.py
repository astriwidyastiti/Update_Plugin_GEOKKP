import os
import math

from qgis.PyQt import QtWidgets, uic, QtGui, QtCore
from qgis.core import (
    QgsProject,
    QgsPointXY,
    QgsFeature,
    QgsGeometry,
    QgsVectorLayer,
    Qgis,
)

from qgis.PyQt.QtCore import pyqtSignal
from qgis.utils import iface
from qgis.gui import QgsVertexMarker, QgsMessageBar, QgsRubberBand

from .maptools import MapTool

# using utils
from .utils import icon


FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/triangulation.ui")
)


class TriangulationDialog(QtWidgets.QDialog, FORM_CLASS):
    """Dialog for Peta Bidang"""

    closingPlugin = pyqtSignal()

    def __init__(self, parent=iface.mainWindow()):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        super(TriangulationDialog, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(icon("icon.png"))

        self.list_vm = []
        self.list_rb_line = []

        self.dialog_bar = QgsMessageBar()
        self.dialog_bar.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed
        )
        self.layout().insertWidget(0, self.dialog_bar)

        self.canvas.extentsChanged.connect(self.canvas_changed)
        self.input_azimuth_1.textChanged.connect(self.update_azimuth_1)
        self.input_azimuth_2.textChanged.connect(self.update_azimuth_2)

    def on_triangulasi_titik_1_pressed(self):
        try:
            self.iface.mapCanvas().scene().removeItem(self.vm_1)
        except:  # noqa
            pass
        self.vm_1 = self.create_vertex_marker()
        self.list_vm.append(self.vm_1)
        self.point_tool_1 = MapTool(self.canvas, self.vm_1)
        self.point_tool_1.map_clicked.connect(self.update_titik_1)

        self.point_tool_1.isEmittingPoint = True
        self.iface.mapCanvas().setMapTool(self.point_tool_1)

    def update_titik_1(self, x, y):
        self.point_1 = QgsPointXY(x, y)
        self.triangulasi_koord_1.setText(str(round(x, 3)) + "," + str(round(y, 3)))
        self.iface.mapCanvas().unsetMapTool(self.point_tool_1)

        self.set_enabled([self.triangulasi_koord_1, self.input_azimuth_1])

    def update_azimuth_1(self):
        try:
            self.iface.mapCanvas().scene().removeItem(self.rb_line_1)
        except Exception:
            pass
        self.azimuth_1 = self.validate_az(self.input_azimuth_1.text())

        if self.azimuth_1 is not False:
            self.set_enabled([self.triangulasi_titik_2])
            self.rb_line_1 = self.create_rubberband_line()
            self.list_rb_line.append(self.rb_line_1)

            pmin, pmax = self.minmax_line(self.point_1, self.azimuth_1)
            if pmin and pmax:
                line_geom = QgsGeometry().fromPolylineXY([pmin, pmax])
                self.rb_line_1.setToGeometry(line_geom, None)
        else:
            self.set_disabled([self.triangulasi_titik_2])

    def on_triangulasi_titik_2_pressed(self):
        try:
            self.iface.mapCanvas().scene().removeItem(self.vm_2)
        except:  # noqa
            pass
        self.vm_2 = self.create_vertex_marker()
        self.list_vm.append(self.vm_2)
        self.point_tool_2 = MapTool(self.canvas, self.vm_2)
        self.point_tool_2.map_clicked.connect(self.update_titik_2)

        self.point_tool_2.isEmittingPoint = True
        self.iface.mapCanvas().setMapTool(self.point_tool_2)

    def update_titik_2(self, x, y):
        self.point_2 = QgsPointXY(x, y)
        self.triangulasi_koord_2.setText(str(round(x, 3)) + "," + str(round(y, 3)))
        self.iface.mapCanvas().unsetMapTool(self.point_tool_2)

        self.set_enabled([self.triangulasi_koord_2, self.input_azimuth_2])

    def update_azimuth_2(self):
        try:
            self.iface.mapCanvas().scene().removeItem(self.rb_line_2)
        except Exception:
            pass
        self.azimuth_2 = self.validate_az(self.input_azimuth_2.text())

        if self.azimuth_2 is not False:
            self.rb_line_2 = self.create_rubberband_line()
            self.list_rb_line.append(self.rb_line_2)

            pmin, pmax = self.minmax_line(self.point_2, self.azimuth_2)
            if pmin and pmax:
                line_geom = QgsGeometry().fromPolylineXY([pmin, pmax])
                self.rb_line_2.setToGeometry(line_geom, None)

            self.set_enabled([self.triangulasi_ok])
        else:
            self.set_disabled([self.triangulasi_ok])

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def on_triangulasi_cancel_pressed(self):
        self.clear()
        self.close()

    def on_triangulasi_ok_pressed(self):
        # create a memory vector
        project_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        project_epsg = project_crs.authid()
        vl = QgsVectorLayer(
            "Point?crs=" + project_epsg, "trilateration point", "memory"
        )

        p1 = self.point_1
        p2 = self.point_2

        az1 = self.azimuth_1
        az2 = self.azimuth_2

        if az1 and az2:
            pt = self.triangulate(p1, p2, az1, az2)

            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPointXY(pt))

            vl.startEditing()
            vl.addFeatures([feat])
            vl.commitChanges()

            QgsProject.instance().addMapLayer(vl)
            self.clear()
            self.close()
        else:
            pass

    def triangulate(self, p1, p2, az1, az2):
        x1 = p1.x()
        y1 = p1.y()

        x2 = p2.x()
        y2 = p2.y()

        m1 = 1 / math.tan(math.radians(az1))
        m2 = 1 / math.tan(math.radians(az2))

        a1 = 1
        b1 = -1 / m1
        c1 = -b1 * y1 - a1 * x1

        a2 = 1
        b2 = -1 / m2
        c2 = -b2 * y2 - a2 * x2

        # print('abcm1',a1,b1,c1,m1)
        # print('abcm2',a2,b2,c2,m2)

        x3 = ((b1 * c2) - (b2 * c1)) / ((a1 * b2) - (a2 * b1))
        y3 = ((c1 * a2) - (c2 * a1)) / ((a1 * b2) - (a2 * b1))

        # print('p3', x3,y3)

        return QgsPointXY(x3, y3)

    def minmax_line(self, pt, az):
        xmin = self.canvas.extent().xMinimum()
        ymin = self.canvas.extent().yMinimum()
        xmax = self.canvas.extent().xMaximum()
        ymax = self.canvas.extent().yMaximum()

        if az % 180 == 0:
            return QgsPointXY(pt.x(), ymin), QgsPointXY(pt.x(), ymax)
        elif az % 90 == 0:
            return QgsPointXY(xmin, pt.y()), QgsPointXY(xmax, pt.y())
        else:
            m = 1 / math.tan(math.radians(az))

            a = 1
            b = -1 / m
            c = -a * pt.x() - b * pt.y()

            pxmin_y = -(a * xmin + c) / b
            pymin_x = -(b * ymin + c) / a
            pxmax_y = -(a * xmax + c) / b
            pymax_x = -(b * ymax + c) / a

            point_list = []

            if pxmin_y >= ymin and pxmin_y <= ymax:
                point_list.append(QgsPointXY(xmin, pxmin_y))

            if pxmax_y >= ymin and pxmax_y <= ymax:
                point_list.append(QgsPointXY(xmax, pxmax_y))

            if pymin_x >= xmin and pymin_x <= xmax:
                point_list.append(QgsPointXY(pymin_x, ymin))

            if pymax_x >= xmin and pymax_x <= xmax:
                point_list.append(QgsPointXY(pymax_x, ymax))

            if len(point_list) == 2:
                return point_list
            else:
                return False

    def create_vertex_marker(self, type="BOX"):
        vm = QgsVertexMarker(self.canvas)

        if type == "BOX":
            icon_type = QgsVertexMarker.ICON_BOX
        elif type == "CIRCLE":
            icon_type = QgsVertexMarker.ICON_CIRCLE
        elif type == "CROSS":
            icon_type = QgsVertexMarker.ICON_CROSS
        else:
            icon_type = QgsVertexMarker.ICON_X

        vm.setIconType(icon_type)
        vm.setPenWidth(3)
        vm.setIconSize(7)
        return vm

    def create_rubberband_line(self):
        rb = QgsRubberBand(self.canvas, False)
        rb.setStrokeColor(QtGui.QColor(128, 128, 128, 180))  # grey
        rb.setFillColor(QtGui.QColor(0, 0, 0, 0))
        rb.setWidth(1)
        rb.setLineStyle(QtCore.Qt.DashLine)
        return rb

    def clear(self):
        self.triangulasi_koord_1.clear()
        self.triangulasi_koord_2.clear()

        self.input_azimuth_1.clear()
        self.input_azimuth_2.clear()

        for vm in self.list_vm:
            try:
                self.iface.mapCanvas().scene().removeItem(vm)
            except:  # noqa
                pass
        for rb in self.list_rb_line:
            try:
                self.iface.mapCanvas().scene().removeItem(rb)
            except:  # noqa
                pass

    def canvas_changed(self):
        if self.input_azimuth_1.text():
            self.update_azimuth_1()
        if self.input_azimuth_2.text():
            self.update_azimuth_2()

    def validate_az(self, az_str):
        if not az_str:
            return False
        az_split = az_str.strip().split(" ")

        if len(az_split) == 3:
            self.dialog_bar.clearWidgets()
            try:
                d = float(az_split[0])
                m = float(az_split[1])
                s = float(az_split[2])
            except ValueError:
                return False
            return d + (m / 60) + (s / 3600)

        elif len(az_split) == 1:
            self.dialog_bar.clearWidgets()
            try:
                return float(az_str)
            except ValueError:
                return False

        else:
            message = """
                        Format tidak dikenali. Gunakan spasi sebagai pemisah.
                        ('DD' atau 'D M S')
                        """
            self.dialog_bar.pushMessage("Warning", message, level=Qgis.Warning)
            return False

    def set_enabled(self, list_of_widget):
        for widget in list_of_widget:
            widget.setEnabled(True)

    def set_disabled(self, list_of_widget):
        for widget in list_of_widget:
            widget.setEnabled(False)
