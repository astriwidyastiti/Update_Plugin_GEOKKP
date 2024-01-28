import os

from qgis.PyQt import QtWidgets, uic, QtXml
from qgis.core import (
    QgsProject,
    QgsPrintLayout,
    QgsReadWriteContext,
    QgsExpressionContextUtils,
)

from qgis.PyQt.QtCore import pyqtSignal
from qgis.utils import iface

# using utils
from .utils import icon

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../ui/layout_pbt.ui")
)

qpt_path = os.path.join(os.path.dirname(__file__), "../template/pbt.qpt")


class LayoutPetaDialog(QtWidgets.QDialog, FORM_CLASS):
    """Dialog for Peta Bidang"""

    closingPlugin = pyqtSignal()

    def __init__(self, parent=iface.mainWindow()):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        super(LayoutPetaDialog, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(icon("icon.png"))

        self.project = QgsProject.instance()
        self.read_settings()

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def var_set(self, var_name, var_value):
        """[summary]

        Args:
            var_name ([type]): [description]
            var_value ([type]): [description]
        """
        QgsExpressionContextUtils.setProjectVariable(self.project, var_name, var_value)

    def set_variable(self):
        self.var_set("nama_provinsi", self.nama_provinsi.text())
        self.var_set("nama_kabupaten", self.nama_kabupaten.text())
        self.var_set("nama_kecamatan", self.nama_kecamatan.text())
        self.var_set("nama_desa", self.nama_desa.text())
        self.var_set("nama_blok", self.nama_blok.text())
        self.var_set("nama_kantah", self.nama_kantah.text())
        self.var_set("nama_pejabat", self.nama_pejabat.text())
        self.var_set("nip_pejabat", self.nip_pejabat.text())
        self.var_set("no_pbt", self.no_pbt.text())
        self.var_set("tgl_pbt", self.tgl_pbt.text())
        self.var_set("nama_ask", self.nama_ask.text())
        self.var_set("lisensi_ask", self.lisensi_ask.text())
        self.var_set("nama_skb", self.nama_skb.text())
        self.var_set("lisensi_skb", self.lisensi_skb.text())

    def read_settings(self):
        self.nama_provinsi.setText(self.project.readEntry("GeoKKP", "nama_provinsi")[0])
        self.nama_kabupaten.setText(
            self.project.readEntry("GeoKKP", "nama_kabupaten")[0]
        )
        self.nama_kecamatan.setText(
            self.project.readEntry("GeoKKP", "nama_kecamatan")[0]
        )
        self.nama_desa.setText(self.project.readEntry("GeoKKP", "nama_desa")[0])
        self.nama_blok.setText(self.project.readEntry("GeoKKP", "nama_blok")[0])
        self.nama_kantah.setText(self.project.readEntry("GeoKKP", "nama_kantah")[0])
        self.nama_pejabat.setText(self.project.readEntry("GeoKKP", "nama_pejabat")[0])
        self.nip_pejabat.setText(self.project.readEntry("GeoKKP", "nip_pejabat")[0])
        self.no_pbt.setText(self.project.readEntry("GeoKKP", "no_pbt")[0])
        self.tgl_pbt.setText(self.project.readEntry("GeoKKP", "tgl_pbt")[0])
        self.nama_ask.setText(self.project.readEntry("GeoKKP", "nama_ask")[0])
        self.lisensi_ask.setText(self.project.readEntry("GeoKKP", "lisensi_ask")[0])
        self.nama_skb.setText(self.project.readEntry("GeoKKP", "nama_skb")[0])
        self.lisensi_skb.setText(self.project.readEntry("GeoKKP", "lisensi_skb")[0])

    def write_settings(self):
        self.project.writeEntry("GeoKKP", "nama_provinsi", self.nama_provinsi.text())
        self.project.writeEntry("GeoKKP", "nama_kabupaten", self.nama_kabupaten.text())
        self.project.writeEntry("GeoKKP", "nama_kecamatan", self.nama_kecamatan.text())
        self.project.writeEntry("GeoKKP", "nama_desa", self.nama_desa.text())
        self.project.writeEntry("GeoKKP", "nama_blok", self.nama_blok.text())
        self.project.writeEntry("GeoKKP", "nama_kantah", self.nama_kantah.text())
        self.project.writeEntry("GeoKKP", "nama_pejabat", self.nama_pejabat.text())
        self.project.writeEntry("GeoKKP", "nip_pejabat", self.nip_pejabat.text())
        self.project.writeEntry("GeoKKP", "no_pbt", self.no_pbt.text())
        self.project.writeEntry("GeoKKP", "tgl_pbt", self.tgl_pbt.text())
        self.project.writeEntry("GeoKKP", "nama_ask", self.nama_ask.text())
        self.project.writeEntry("GeoKKP", "lisensi_ask", self.lisensi_ask.text())
        self.project.writeEntry("GeoKKP", "nama_skb", self.nama_skb.text())
        self.project.writeEntry("GeoKKP", "lisensi_skb", self.lisensi_skb.text())

    def on_btn_edit_layout_pressed(self):
        _pbt_template_exists = False
        # check if the same PBT layout already existed
        for existing_layout in self.project.layoutManager().printLayouts():
            if existing_layout.name() == "PBT":
                _pbt_template_exists = True
                layout = existing_layout
        if not _pbt_template_exists:
            project = QgsProject.instance()
            layout = QgsPrintLayout(project)
            with open(qpt_path) as qpt_file:
                qpt_content = qpt_file.read()
            doc = QtXml.QDomDocument()
            doc.setContent(qpt_content)
            layout_items, _ = layout.loadFromTemplate(doc, QgsReadWriteContext())
            self.project.layoutManager().addLayout(layout)
        # set variable and set settings
        self.set_variable()
        self.write_settings()
        # show the composer and hide dialog
        self.iface.openLayoutDesigner(layout)
        self.close()

    def on_btn_print_pdf_pressed(self):
        """Export Peta Bidang to PDF."""
        pass

    def on_btn_cancel_pressed(self):
        self.close()
