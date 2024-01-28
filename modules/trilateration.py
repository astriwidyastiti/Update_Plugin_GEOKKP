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
    os.path.join(os.path.dirname(__file__), "../ui/trilateration.ui")
)


class TrilaterationDialog(QtWidgets.QDialog, FORM_CLASS):
    """Dialog for Peta Bidang"""

    closingPlugin = pyqtSignal()

    def __init__(self, parent=iface.mainWindow()):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        super(TrilaterationDialog, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(icon("icon.png"))

        self.dialog_bar = QgsMessageBar()
        self.dialog_bar.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed
        )
        self.layout().insertWidget(0, self.dialog_bar)

        self.trilaterasi_ok.pressed.connect(self.accepted)
        self.trilaterasi_cancel.pressed.connect(self.rejected)

        self.input_jarak_1.textChanged.connect(self.update_jarak_1)
        self.input_jarak_2.textChanged.connect(self.update_jarak_2)
        self.input_jarak_3.textChanged.connect(self.update_jarak_3)

        self.list_vm = []
        self.list_rb = []

        self.two_point_flag = False
        self.three_point_flag = False

    def on_trilaterasi_titik_1_pressed(self):
        try:
            self.iface.mapCanvas().scene().removeItem(self.vm_1)
            self.iface.mapCanvas().scene().removeItem(self.rb_1)
        except:  # noqa
            pass
        self.vm_1 = self.create_vertex_marker()
        self.list_vm.append(self.vm_1)
        self.point_tool_1 = MapTool(self.canvas, self.vm_1)
        self.rb_1 = self.create_rubberband()
        self.list_rb.append(self.rb_1)

        self.point_tool_1.map_clicked.connect(self.update_titik_1)

        self.point_tool_1.isEmittingPoint = True
        self.iface.mapCanvas().setMapTool(self.point_tool_1)

    def update_titik_1(self, x, y):
        self.point_1 = QgsPointXY(x, y)
        self.trilaterasi_koord_1.setText(str(round(x, 3)) + "," + str(round(y, 3)))
        self.iface.mapCanvas().unsetMapTool(self.point_tool_1)

    def update_jarak_1(self):
        next_widget = [
            self.trilaterasi_koord_2,
            self.input_jarak_2,
            self.trilaterasi_titik_2,
        ]
        try:
            self.jarak_1 = float(self.input_jarak_1.text())
            self.dialog_bar.clearWidgets()
            self.set_enabled(next_widget)
            pt = QgsPointXY(self.point_1)
            # circle_geom = QgsCircle(pt, self.jarak_1, 0).toCircularString()
            buff_geom = QgsGeometry().fromPointXY(pt).buffer(self.jarak_1, 20)
            self.rb_1.setToGeometry(buff_geom, None)

        except ValueError:
            self.dialog_bar.clearWidgets()
            message = """Terdapat kesalahan format jarak."""
            self.dialog_bar.pushMessage("Warning", message, level=Qgis.Warning)
            self.set_disabled(next_widget)
            self.set_disabled([self.trilaterasi_ok])

    def on_trilaterasi_titik_2_pressed(self):
        try:
            self.iface.mapCanvas().scene().removeItem(self.vm_2)
            self.iface.mapCanvas().scene().removeItem(self.rb_2)
        except:  # noqa
            pass
        self.vm_2 = self.create_vertex_marker()
        self.list_vm.append(self.vm_2)
        self.rb_2 = self.create_rubberband()
        self.list_rb.append(self.rb_2)

        self.point_tool_2 = MapTool(self.canvas, self.vm_2)
        self.point_tool_2.map_clicked.connect(self.update_titik_2)

        self.point_tool_2.isEmittingPoint = True
        self.iface.mapCanvas().setMapTool(self.point_tool_2)

    def update_titik_2(self, x, y):
        self.point_2 = QgsPointXY(x, y)
        self.trilaterasi_koord_2.setText(str(round(x, 3)) + "," + str(round(y, 3)))
        self.iface.mapCanvas().unsetMapTool(self.point_tool_2)

    def update_jarak_2(self):
        next_widget = [
            self.trilaterasi_koord_3,
            self.input_jarak_3,
            self.trilaterasi_titik_3,
            self.clear_titik_3,
            self.trilaterasi_ok,
        ]
        try:
            self.jarak_2 = float(self.input_jarak_2.text())
            self.set_enabled(next_widget)

            pt = QgsPointXY(self.point_2)
            buff_geom = QgsGeometry().fromPointXY(pt).buffer(self.jarak_2, 20)
            # circle_geom = QgsCircle(QgsPoint(pt), self.jarak_2, 0)
            self.rb_2.setToGeometry(buff_geom, None)

            self.two_point_flag = True

            self.dialog_bar.clearWidgets()
            message = """Klik OK untuk menggunakan mode dua titik atau tambahkan
                        titik ketiga"""
            self.dialog_bar.pushMessage("Info", message, level=Qgis.Info)
        except ValueError:
            self.dialog_bar.clearWidgets()
            message = """Terdapat kesalahan format jarak."""
            self.dialog_bar.pushMessage("Warning", message, level=Qgis.Warning)
            self.set_disabled(next_widget)
            self.two_point_flag = False

    def on_trilaterasi_titik_3_pressed(self):
        try:
            self.iface.mapCanvas().scene().removeItem(self.vm_3)
            self.iface.mapCanvas().scene().removeItem(self.rb_3)
        except Exception:
            pass
        self.vm_3 = self.create_vertex_marker()
        self.list_vm.append(self.vm_3)
        self.rb_3 = self.create_rubberband()
        self.list_rb.append(self.rb_3)

        self.point_tool_3 = MapTool(self.canvas, self.vm_3)
        self.point_tool_3.map_clicked.connect(self.update_titik_3)

        self.point_tool_3.isEmittingPoint = True
        self.iface.mapCanvas().setMapTool(self.point_tool_3)

    def update_titik_3(self, x, y):
        self.point_3 = QgsPointXY(x, y)
        self.trilaterasi_koord_3.setText(str(round(x, 3)) + "," + str(round(y, 3)))
        self.iface.mapCanvas().unsetMapTool(self.point_tool_3)

    def update_jarak_3(self):
        try:
            self.jarak_3 = float(self.input_jarak_3.text())
            self.dialog_bar.clearWidgets()

            pt = QgsPointXY(self.point_3)
            buff_geom = QgsGeometry().fromPointXY(pt).buffer(self.jarak_3, 20)
            # circle_geom = QgsCircle(QgsPoint(pt), self.jarak_3, 0)
            self.rb_3.setToGeometry(buff_geom, None)

            self.three_point_flag = True
        except ValueError:
            self.dialog_bar.clearWidgets()
            message = """Terdapat kesalahan format jarak."""
            self.dialog_bar.pushMessage("Warning", message, level=Qgis.Warning)
            self.three_point_flag = False

    def check_minimum_input(self):
        try:
            float(self.input_jarak_1.text())
            float(self.input_jarak_2.text())
            self.trilaterasi_ok.setEnabled(True)
        except ValueError:
            self.trilaterasi_ok.setEnabled(False)

    def set_enabled(self, list_of_widget):
        for widget in list_of_widget:
            widget.setEnabled(True)

    def set_disabled(self, list_of_widget):
        for widget in list_of_widget:
            widget.setEnabled(False)

    def on_clear_titik_3_pressed(self):
        self.trilaterasi_koord_3.clear()
        self.input_jarak_3.clear()
        self.dialog_bar.clearWidgets()
        self.iface.mapCanvas().scene().removeItem(self.vm_3)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def rejected(self):
        print("cancel triggered")
        self.clear()
        self.reject()

    def accepted(self):
        # create a memory vector
        project_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        project_epsg = project_crs.authid()
        vl = QgsVectorLayer(
            "Point?crs=" + project_epsg, "trilateration point", "memory"
        )

        if self.three_point_flag:
            d1 = self.jarak_1
            d2 = self.jarak_2
            d3 = self.jarak_3

            p1 = self.point_1
            p2 = self.point_2
            p3 = self.point_3

            pt = self.three_points(p1, p2, p3, d1, d2, d3)

            feat_pt = QgsFeature()
            feat_pt.setGeometry(QgsGeometry.fromPointXY(pt))

            vl.startEditing()
            vl.addFeatures([feat_pt])
            vl.commitChanges()
        elif self.two_point_flag:
            p1 = self.point_1
            p2 = self.point_2

            d1 = self.jarak_1
            d2 = self.jarak_2
            a, b = self.two_points(p1, p2, d1, d2)

            feat_a = QgsFeature()
            feat_a.setGeometry(QgsGeometry.fromPointXY(a))
            feat_b = QgsFeature()
            feat_b.setGeometry(QgsGeometry.fromPointXY(b))

            vl.startEditing()
            vl.addFeatures([feat_a, feat_b])
            vl.commitChanges()
        else:
            print("not enough inputs")

        QgsProject.instance().addMapLayer(vl)
        self.clear()
        self.accept()

    def two_points(self, p1, p2, d1, d2):
        """Calculate two solutions of two points trilateration."""
        d = math.sqrt(p1.sqrDist(p2))

        a = (d1 * d1 - d2 * d2 + d * d) / (2 * d)
        h = math.sqrt(d1 * d1 - a * a)

        x1 = p1.x()
        y1 = p1.y()

        x2 = p2.x()
        y2 = p2.y()

        xo = x1 + a * (x2 - x1) / d
        yo = y1 + a * (y2 - y1) / d

        x3a = xo + h * (y2 - y1) / d
        y3a = yo - h * (x2 - x1) / d

        x3b = xo - h * (y2 - y1) / d
        y3b = yo + h * (x2 - x1) / d

        print(a, h, d)

        return QgsPointXY(x3a, y3a), QgsPointXY(x3b, y3b)

    def three_points(self, p1, p2, p3, d1, d2, d3):

        x1 = p1.x()
        y1 = p1.y()
        x2 = p2.x()
        y2 = p2.y()
        x3 = p3.x()
        y3 = p3.y()

        m = x1 - x2
        n = y2 - y1
        o = x1 * x1 - x2 * x2
        p = y1 * y1 - y2 * y2
        q = d2 * d2 - d1 * d1

        r = x1 - x3
        s = y3 - y1
        t = x1 * x1 - x3 * x3
        u = y1 * y1 - y3 * y3
        v = d3 * d3 - d1 * d1

        y = (r * (o + p + q) - m * (t + u + v)) / (2 * (s * m - n * r))
        x = (2 * y * n + o + p + q) / (2 * m)

        return QgsPointXY(x, y)

    def check_distance(self, pt1, pt2, dist_1, dist_2):
        """Fungsi untuk mengecek jarak minimum trilaterasi.

        Untuk mendapatkan solusi yg valid, jumlah jarak yg diinput pengguna
        harus lebih dari jarak antara kedua titik input.

        Args:
            pt1 (QgsPointXY): Titik cek pertama
            pt2 (QgsPointXY): Titik cek kedua
            dist_1 (float): jarak dari titik cek pertama
            dist_2 (float): jarak dari titik cek kedua
        """
        pt_dist = math.sqrt(pt1.sqrDist(pt2))
        input_dist = dist_1 + dist_2
        if input_dist > pt_dist:
            return True
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

    def create_rubberband(self):
        rb = QgsRubberBand(self.canvas, False)
        rb.setStrokeColor(QtGui.QColor(128, 128, 128, 180))  # grey
        rb.setFillColor(QtGui.QColor(0, 0, 0, 0))
        rb.setWidth(1)
        rb.setLineStyle(QtCore.Qt.DashLine)
        return rb

    def clear(self):
        self.trilaterasi_koord_1.clear()
        self.trilaterasi_koord_2.clear()
        self.trilaterasi_koord_3.clear()

        self.input_jarak_1.clear()
        self.input_jarak_2.clear()
        self.input_jarak_3.clear()

        list_of_widget = [
            self.trilaterasi_koord_2,
            self.input_jarak_2,
            self.trilaterasi_titik_2,
            self.trilaterasi_koord_3,
            self.input_jarak_3,
            self.trilaterasi_titik_3,
            self.trilaterasi_ok,
        ]

        self.set_disabled(list_of_widget)
        self.dialog_bar.clearWidgets()

        for vm in self.list_vm:
            try:
                self.iface.mapCanvas().scene().removeItem(vm)
            except:  # noqa
                pass
        for rb in self.list_rb:
            try:
                self.iface.mapCanvas().scene().removeItem(rb)
            except Exception:
                pass
