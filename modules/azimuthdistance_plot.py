import csv
import os
import math

from qgis.PyQt import uic, QtGui  # , QtCore
from qgis.PyQt.QtWidgets import QFileDialog, QDialog, QTableWidgetItem, QSizePolicy
from PyQt5.QtCore import Qt, QDir
from qgis.utils import iface

from qgis.core import (
    Qgis,
    QgsPointXY,
    QgsGeometry,
    QgsFeature,
    QgsVectorLayer,
    QgsProject,
)

from qgis.gui import QgsVertexMarker, QgsMessageBar, QgsRubberBand

from .maptools import MapTool

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/az_distance.ui")
)

"""
list_of_dicts = [
    {
        'nama' : 'P0',
        'X' : 000000,
        'Y' : 000000,
        'Z' : 000000,
        'x_terkoreksi' : 00000,
        'y_terkoreksi' : 00000,
        'z_terkoreksi' : 00000
    },
    {
        'nama' : 'P1',
        'jarak' : 123.12,
        'sudut' : 12 34 56.789,
        'tinggi' : 12.34,
        'x' : 000000,
        'y' : 000000,
        'z' : 000000,
        'x_terkoreksi' : 00000,
        'y_terkoreksi' : 00000,
        'z_terkoreksi' : 00000
    }
]
"""


class AzDistanceDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=iface.mainWindow()):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        super(AzDistanceDialog, self).__init__(parent)
        self.setupUi(self)

        self.label_last_point.setVisible(False)
        self.last_point.setVisible(False)

        self.initiate_first_row()

        self.dialog_bar = QgsMessageBar()
        self.dialog_bar.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.layout().insertWidget(0, self.dialog_bar)
        self.tableWidget.cellChanged.connect(self.current_item_changed)

        self.list_vm = []
        self.vm_start = None
        self.calculation_status = None
        self.coord_calculated = False
        self.bowditch_calculated = False
        # self.tableWidget.currentCellChanged.connect(self.current_cell_changed)

    def current_item_changed(self):
        current_column = self.tableWidget.currentColumn()
        # check az
        if current_column == 1 or current_column == 3:
            if self.tableWidget.currentItem().text() != "":
                try:
                    _ = float(self.tableWidget.currentItem().text())
                    self.dialog_bar.clearWidgets()
                except ValueError:
                    message = """Format angka tidak sesuai."""
                    self.dialog_bar.pushMessage("Warning", message, level=Qgis.Warning)
        elif current_column == 2:
            if self.tableWidget.currentItem().text() != "":
                az_str = str(self.tableWidget.currentItem().text())
                validated_az = self.validate_az(az_str)  # noqa

    def on_btn_pilihKoord_pressed(self):
        self.vm_start = self.create_vertex_marker("CROSS", "RED")
        self.point_tool = MapTool(self.canvas, self.vm_start)
        self.iface.mapCanvas().setMapTool(self.point_tool)
        self.point_tool.map_clicked.connect(self.update_titik_awal)

    def update_titik_awal(self, x, y):
        self.x_titik_awal.setText(str(round(x, 3)))
        self.y_titik_awal.setText(str(round(y, 3)))
        # self.tableWidget.setItem(0, 4, QTableWidgetItem(str(round(x,3))))
        # self.tableWidget.setItem(0, 5, QTableWidgetItem(str(round(y,3))))
        self.iface.mapCanvas().unsetMapTool(self.point_tool)
        # self.iface.mapCanvas().scene().removeItem(self.vm_start)
        self.list_vm.append(self.vm_start)

    def on_btn_tambahTitik_pressed(self):
        current_row = self.tableWidget.rowCount()
        self.tableWidget.setRowCount(current_row + 1)
        for row in range(current_row, current_row + 1):
            for col in range(7):
                self.tableWidget.setItem(row, col, QTableWidgetItem(""))

    # def disable_cell(self, cell_item):
    # cell_item.setFlags(Qt.ItemIsSelectable)
    # cell_item.setBackground(QtGui.QColor(128,128,128,180))

    def initiate_first_row(self):
        self.tableWidget.setRowCount(1)
        self.tableWidget.setColumnCount(4)
        for i in range(4):
            self.tableWidget.setItem(0, i, QTableWidgetItem(""))

        # disable 2nd to 4th cells
        # for i in range(1,5):
        # self.disable_cell(self.tableWidget.item(0,i))

    def on_btn_hapusTable_pressed(self):
        self.tableWidget.setRowCount(0)
        self.tableWidget.setRowCount(4)
        self.initiate_first_row()

    def on_btn_hapusTitik_pressed(self):
        selected_rows = self.tableWidget.selectionModel().selectedRows()
        for item in reversed(sorted(selected_rows)):
            self.tableWidget.removeRow(item.row())

    def on_btn_bowditch_pressed(self):
        self.calculation_status = "bowditch"
        list_titik_bowditch = self.read_table()
        sum_deltax = 0
        sum_deltay = 0
        sum_distance = 0
        for titik in list_titik_bowditch[:-1]:
            sum_deltax += round(float(titik["Delta X"]), 3)
            sum_deltay += round(float(titik["Delta Y"]), 3)
            sum_distance += round(float(titik["Jarak"]), 3)

        delta_distance = math.sqrt(sum_deltax ** 2 + sum_deltay ** 2)  # noqa

        for id, titik in enumerate(list_titik_bowditch):
            if id < len(list_titik_bowditch) - 1:
                jarak = round(float(titik["Jarak"]), 3)
                deltax = round(float(titik["Delta X"]), 3)
                deltay = round(float(titik["Delta Y"]), 3)

                dx = round((jarak / sum_distance) * sum_deltax, 3)
                dy = round((jarak / sum_distance) * sum_deltay, 3)

                deltax_koreksi = round(deltax - dx, 3)
                deltay_koreksi = round(deltay - dy, 3)
                if id == 0:
                    x_koreksi = round(float(titik["X"]), 3)
                    y_koreksi = round(float(titik["Y"]), 3)
                else:
                    prev_titik = list_titik_bowditch[id - 1]
                    prev_deltax = round(prev_titik["Delta X`"], 3)
                    prev_deltay = round(prev_titik["Delta Y`"], 3)
                    x_koreksi = round(float(prev_titik["X`"]) + prev_deltax, 3)
                    y_koreksi = round(float(prev_titik["Y`"]) + prev_deltay, 3)

            else:
                prev_titik = list_titik_bowditch[id - 1]
                prev_deltax = round(prev_titik["Delta X`"], 3)
                prev_deltay = round(prev_titik["Delta Y`"], 3)
                x_koreksi = round(float(prev_titik["X`"]) + prev_deltax, 3)
                y_koreksi = round(float(prev_titik["Y`"]) + prev_deltay, 3)
                dx = "-"
                dy = "-"
                deltax_koreksi = "-"
                deltay_koreksi = "-"

            titik["dx"] = dx
            titik["dy"] = dy
            titik["X`"] = x_koreksi
            titik["Y`"] = y_koreksi
            titik["Delta X`"] = deltax_koreksi
            titik["Delta Y`"] = deltay_koreksi

        self.table_from_list(list_titik_bowditch)
        self.draw_calculation_result()

    def on_btn_hitungKoord_pressed(self):
        self.calculation_status = "coordinate"

        if self.radio_pTertutup.isChecked():
            self.polygon_tertutup = True
        else:
            self.polygon_tertutup = False

        self.tableWidget.setColumnCount(4)
        # num = 0

        # existing column
        columns = []
        for i in range(self.tableWidget.columnCount()):
            columns.append(self.tableWidget.horizontalHeaderItem(i).text())

        list_titik = self.read_table()

        # set utk titik awal
        x = float(self.x_titik_awal.text())
        y = float(self.y_titik_awal.text())
        z = float(self.z_titik_awal.text())

        list_titik[0]["X"] = x
        list_titik[0]["Y"] = y
        list_titik[0]["Z"] = z

        # insert column
        new_columns = [
            "Nama Titik",
            "X",
            "Y",
            "Z",
            "Jarak",
            "Azimuth",
            "Beda Tinggi",
            "Delta X",
            "Delta Y",
        ]
        # self.tableWidget.setColumnCount(self.tableWidget.columnCount() + 5)
        self.tableWidget.setColumnCount(len(new_columns))
        self.tableWidget.setHorizontalHeaderLabels(new_columns)

        # deltax_idx = new_columns.index("Delta X")
        # deltay_idx = new_columns.index("Delta Y")
        # dz_idx = new_columns.index('Dz')
        # x_idx = new_columns.index("X")
        # y_idx = new_columns.index("Y")
        # z_idx = new_columns.index("Z")

        for id, titik in enumerate(list_titik):
            dist = float(titik["Jarak"])
            az = self.validate_az(titik["Azimuth"])
            deltax = round(dist * math.sin(math.radians(az)), 3)
            deltay = round(dist * math.cos(math.radians(az)), 3)
            deltaz = round(float(titik["Beda Tinggi"]), 3)
            # store in dictionary
            titik["Delta X"] = deltax
            titik["Delta Y"] = deltay

            if id > 0:
                prev_titik = list_titik[id - 1]
                x = prev_titik["X"] + prev_titik["Delta X"]
                y = prev_titik["Y"] + prev_titik["Delta Y"]
                z = prev_titik["Z"] + deltaz
                titik["X"] = round(x, 3)
                titik["Y"] = round(y, 3)
                titik["Z"] = round(z, 3)

        # Last Point
        self.tableWidget.setRowCount(self.tableWidget.rowCount() + 1)
        titik_akhir = {}
        prev_titik = list_titik[-1]
        if self.polygon_tertutup:
            nama_titik_akhir = list_titik[0]["Nama Titik"] + "`"
        else:
            nama_titik_akhir = self.last_point.text()
        deltax = float(prev_titik["Delta X"])
        deltay = float(prev_titik["Delta Y"])
        deltaz = float(prev_titik["Beda Tinggi"])
        titik_akhir["no_titik"] = prev_titik["no_titik"] + 1
        titik_akhir["Nama Titik"] = nama_titik_akhir
        titik_akhir["X"] = round(prev_titik["X"] + deltax, 3)
        titik_akhir["Y"] = round(prev_titik["Y"] + deltay, 3)
        titik_akhir["Z"] = round(prev_titik["Z"] + deltaz, 3)
        list_titik.append(titik_akhir)

        list_titik_hitung = []
        for titik in list_titik:
            titik_hitung = {}
            for col in ["no_titik"] + new_columns:
                try:
                    titik_hitung[col] = titik[col]
                except KeyError:
                    titik_hitung[col] = "-"
            list_titik_hitung.append(titik_hitung)

        self.table_from_list(list_titik_hitung)
        self.draw_calculation_result()

        # print("LIST TITIK", list_titik)
        # print("LIST TITIK HITUNG", list_titik_hitung)

    def read_table(self):
        row_count = self.tableWidget.rowCount()
        col_count = self.tableWidget.columnCount()
        # existing column
        col_name = []
        for i in range(col_count):
            col_name.append(self.tableWidget.horizontalHeaderItem(i).text())

        list_titik_read = []
        for row in range(row_count):
            titik = {}
            titik["no_titik"] = row
            for col in range(col_count):
                current_key = col_name[col]
                current_value = self.tableWidget.item(row, col).text()
                titik[current_key] = current_value
            list_titik_read.append(titik)
        return list_titik_read

    def on_btn_plotTitik_pressed(self):
        # read table and set geometry from coordinate
        if self.calculation_status == "coordinate":
            x_key = "X"
            y_key = "Y"
        elif self.calculation_status == "bowditch":
            x_key = "X`"
            y_key = "Y`"
        else:
            return

        ptxy_list = []
        list_titik = self.read_table()
        for titik in list_titik:
            titik_ptxy = QgsPointXY(float(titik[x_key]), float(titik[y_key]))
            ptxy_list.append(titik_ptxy)
        result_geom = QgsGeometry().fromPolylineXY(ptxy_list)
        result_feat = QgsFeature()
        result_feat.setGeometry(result_geom)

        # create a memory vector
        project_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        project_epsg = project_crs.authid()
        vl = QgsVectorLayer(
            "Linestring?crs=" + project_epsg, "Garis Penggambaran", "memory"
        )
        vl_prov = vl.dataProvider()
        vl.startEditing()
        vl_prov.addFeatures([result_feat])
        vl.commitChanges()
        QgsProject.instance().addMapLayer(vl)

    def draw_calculation_result(self):
        list_titik = self.read_table()

        if self.calculation_status == "coordinate":
            x_key = "X"
            y_key = "Y"
            color = "RED"
        elif self.calculation_status == "bowditch":
            x_key = "X`"
            y_key = "Y`"
            color = "ORANGE"
        else:
            return

        # draw vertex marker
        for id_titik, titik in enumerate(list_titik):
            vm = self.create_vertex_marker("CIRCLE", color)
            xtitik = float(titik[x_key])
            ytitik = float(titik[y_key])
            titik_point = QgsPointXY(xtitik, ytitik)
            if id_titik > 0:
                line_rb = self.create_rubberband(self.canvas, "SOLID_LINE", color)
                prev_titik = list_titik[id_titik - 1]
                prev_titik_x = float(prev_titik[x_key])
                prev_titik_y = float(prev_titik[y_key])
                prev_titik_pt = QgsPointXY(prev_titik_x, prev_titik_y)
                line_geom = QgsGeometry.fromPolylineXY([titik_point, prev_titik_pt])
                line_rb.setToGeometry(line_geom)
                self.list_vm.append(line_rb)

            vm.setCenter(titik_point)
            self.list_vm.append(vm)

    def on_btn_resetHitung_pressed(self):
        # self.tableWidget.setColumnCount(4)
        if self.calculation_status == "bowditch":
            col_removed = [14, 13, 12, 11, 10, 9, 8, 7, 3, 2, 1]
            row_count = self.tableWidget.rowCount()
            self.tableWidget.setRowCount(row_count - 1)
        elif self.calculation_status == "coordinate":
            col_removed = [8, 7, 3, 2, 1]
            row_count = self.tableWidget.rowCount()
            self.tableWidget.setRowCount(row_count - 1)
        else:
            col_removed = []

        self.calculation_status = None

        for col in col_removed:
            self.tableWidget.removeColumn(col)

        for item in self.list_vm:
            self.iface.mapCanvas().scene().removeItem(item)

    def on_btn_importTitik_pressed(self):
        input_csv, _ = QFileDialog.getOpenFileName(
            self, "Browse CSV file", QDir.rootPath(), "*.csv"
        )

        import_list = []

        with open(input_csv, mode="r") as infile:
            reader = csv.reader(infile)
            for row in reader:
                import_list.append(row)

        # df_titik = {} # to be removed
        list_titik_import = []
        titik_key = import_list[0]

        for id, row in enumerate(import_list):
            titik = {}
            for key_id, key in enumerate(titik_key):
                titik[key] = row[key_id]
            # df_titik[id] = titik
            list_titik_import.append(titik)
        # print(list_titik_import)
        # print(f'list titik import: {list_titik_import}')
        self.table_from_list(list_titik_import[1:])

    def table_from_list(self, list_of_titik):
        self.initiate_first_row()
        column = [key for key, value in list_of_titik[0].items()][1:]
        row_count = len(list_of_titik)
        col_count = len(column)

        self.tableWidget.setColumnCount(col_count)
        self.tableWidget.setHorizontalHeaderLabels(column)
        self.tableWidget.setRowCount(row_count)

        if "X" in column:
            x = round(float(list_of_titik[0]["X"]), 3)
            y = round(float(list_of_titik[0]["Y"]), 3)
            z = round(float(list_of_titik[0]["Z"]), 3)

            self.x_titik_awal.setText(str(x))
            self.y_titik_awal.setText(str(y))
            self.z_titik_awal.setText(str(z))
        else:
            self.x_titik_awal.setText("")
            self.y_titik_awal.setText("")
            self.z_titik_awal.setText("")

        for row, titik in enumerate(list_of_titik):
            for key, value in titik.items():
                try:
                    col = column.index(key)
                    cell_val = str(value)
                    # print(f'setting row {row} and col {key} with {value}')
                    self.tableWidget.setItem(row, col, QTableWidgetItem(cell_val))
                except ValueError:
                    pass
                    # print(f'{key} is not in the list of column')

    def on_btn_exportTitik_pressed(self):
        list_titik = self.read_table()

        csv_columns = [key for key, value in list_titik[0].items()]
        csv_file, _ = QFileDialog.getSaveFileName(
            self, "Save File", QDir.rootPath(), "*.csv"
        )

        try:
            with open(csv_file, "w", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
                writer.writeheader()
                # for key,value in self.df_titik.items():
                # writer.writerow(value)
                for titik in list_titik:
                    writer.writerow(titik)
        except IOError:
            print("I/O Error occured")

    def validate_az(self, az_str):
        message = """
                        Format tidak dikenali. Gunakan spasi sebagai pemisah.
                        ('DD.dd' atau 'D M S.ss')
                        """
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
                self.dialog_bar.pushMessage("Warning", message, level=Qgis.Warning)
                return False
            return d + (m / 60) + (s / 3600)

        elif len(az_split) == 1:
            self.dialog_bar.clearWidgets()
            try:
                return float(az_str)
            except ValueError:
                self.dialog_bar.pushMessage("Warning", message, level=Qgis.Warning)
                return False
        else:
            self.dialog_bar.pushMessage("Warning", message, level=Qgis.Warning)
            return False

    def create_vertex_marker(self, type="BOX", color="RED"):
        vm = QgsVertexMarker(self.canvas)

        if type == "BOX":
            icon_type = QgsVertexMarker.ICON_BOX
        elif type == "CIRCLE":
            icon_type = QgsVertexMarker.ICON_CIRCLE
        elif type == "CROSS":
            icon_type = QgsVertexMarker.ICON_CROSS
        else:
            icon_type = QgsVertexMarker.ICON_X

        if color == "RED":
            color = QtGui.QColor(255, 0, 0, 255)  # red
        elif color == "ORANGE":
            color = QtGui.QColor(255, 69, 0, 255)  # orange
        else:
            color = QtGui.QColor(0, 0, 255, 255)  # blue

        vm.setColor(color)
        vm.setIconType(icon_type)
        vm.setPenWidth(3)
        vm.setIconSize(7)
        return vm

    def create_rubberband(self, canvas, line_style="SOLID_LINE", color="RED"):
        rb = QgsRubberBand(canvas, False)

        if line_style == "DASH_LINE":
            rb.setLineStyle(Qt.DashLine)
        elif line_style == "SOLID_LINE":
            rb.setLineStyle(Qt.SolidLine)
        elif line_style == "DOT_LINE":
            rb.setLineStyle(Qt.DotLine)

        if color == "RED":
            color = QtGui.QColor(255, 0, 0, 255)  # red
        elif color == "ORANGE":
            color = QtGui.QColor(255, 69, 0, 255)  # orange
        else:
            color = QtGui.QColor(0, 0, 255, 255)  # blue

        rb.setStrokeColor(color)  # red
        rb.setFillColor(QtGui.QColor(0, 0, 0, 0))
        rb.setWidth(1)
        return rb
