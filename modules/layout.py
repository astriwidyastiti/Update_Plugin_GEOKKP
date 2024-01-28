import os

from qgis.PyQt import QtWidgets, uic, QtXml
from qgis.core import QgsProject, QgsPrintLayout, QgsReadWriteContext, Qgis

from qgis.PyQt.QtCore import pyqtSignal
from qgis.utils import iface
from qgis.gui import QgsMessageBar

# using utils
from .utils import icon, readSetting

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/layout_all.ui")
)


class LayoutDialog(QtWidgets.QDialog, FORM_CLASS):
    """Dialog for Layouting"""

    closingPlugin = pyqtSignal()

    def __init__(self, parent=iface.mainWindow()):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        super(LayoutDialog, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(icon("icon.png"))

        self.dialog_bar = QgsMessageBar()
        self.dialog_bar.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed
        )
        self.layout().insertWidget(0, self.dialog_bar)

        self.project = QgsProject.instance()
        # self.read_settings()

        self.layout_data = readSetting("layout")

        self.cb_layout_type.currentIndexChanged.connect(self.pick_size)
        self.cb_layout_size.currentIndexChanged.connect(self.pick_layout)

        self.tipe_layout()
        # self.pick_size()
        self.pick_layout()

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def tipe_layout(self):
        self.cb_layout_type.clear()
        tipe_layout = []
        for key, values in self.layout_data.items():
            tipe_layout.append(key)
        self.cb_layout_type.addItems(tipe_layout)

    def pick_size(self):
        self.cb_layout_size.clear()
        choosen_layout = self.cb_layout_type.currentText()
        ukuran_layout = []
        for key, value in self.layout_data.items():
            if key == choosen_layout:
                for layout_size in value:
                    ukuran_layout.append(layout_size["Ukuran"])
        self.cb_layout_size.addItems(ukuran_layout)

    def pick_layout(self):
        choosen_layout = self.cb_layout_type.currentText()
        choosen_size = self.cb_layout_size.currentText()
        for key, value in self.layout_data.items():
            if key == choosen_layout:
                for item in value:
                    if item["Ukuran"] == choosen_size:
                        self.layout_name = item["Lokasi"]
        self.layout_path_default = os.path.join(
            os.path.dirname(__file__), "../template/", self.layout_name
        )
        layout, layout_exist = self.read_layout(self.layout_path_default)

    def read_layout(self, layout_path):
        layout_exist = False
        layout = None
        self.dialog_bar.clearWidgets()
        project = QgsProject.instance()
        if os.path.exists(layout_path):
            layout = QgsPrintLayout(project)
            with open(layout_path) as qpt_file:
                qpt_content = qpt_file.read()
            doc = QtXml.QDomDocument()
            doc.setContent(qpt_content)

            layout_items, _ = layout.loadFromTemplate(doc, QgsReadWriteContext())
            # check if there is any layout with the same name
            for existing_layout in self.project.layoutManager().printLayouts():
                if existing_layout.name() == layout.name():
                    layout_exist = True
                    self.dialog_bar.pushMessage(
                        "Info",
                        "Opening existing layout in Layout Manager.",
                        duration=0,
                        level=Qgis.Info,
                    )
                    layout = existing_layout
        else:
            self.dialog_bar.pushMessage(
                "Warning", "Unable to locate default template.", level=Qgis.Warning
            )

        return layout, layout_exist

    def on_btn_load_qpt_pressed(self):
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Single File", "C:'", "*.qpt"
        )
        self.lineEdit_qpt_path.setText(fileName)
        if os.path.exists(fileName):
            self.custom_qpt_template = fileName

    def on_btn_open_layout_pressed(self):
        if self.rb_open_default.isChecked():
            qpt_path = self.layout_path_default
            layout, layout_exist = self.read_layout(qpt_path)
        elif self.rb_load_qpt.isChecked():
            qpt_path = self.custom_qpt_template
            layout, layout_exist = self.read_layout(qpt_path)
        elif self.rb_create_new.isChecked():
            layout_name = self.lineEdit_new_name.text()
            layout_exist = False
            new_layout = QgsPrintLayout(self.project)
            new_layout.initializeDefaults()
            new_layout.setName(layout_name)

            for layout in self.project.layoutManager().printLayouts():
                if layout.name() == layout_name:
                    layout_exist = True

            layout = new_layout

        if layout:
            if not layout_exist:
                self.project.layoutManager().addLayout(layout)
            self.iface.openLayoutDesigner(layout)
            self.close()

    def on_btn_cancel_pressed(self):
        self.close()
