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
    os.path.join(os.path.dirname(__file__), "../ui/layout_gu.ui")
)

qpt_path_a3 = os.path.join(os.path.dirname(__file__), "../template/gu-a3.qpt")


class LayoutGUDialog(QtWidgets.QDialog, FORM_CLASS):
    """Dialog for Zoom to Location"""

    closingPlugin = pyqtSignal()

    def __init__(self, parent=iface.mainWindow()):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        super(LayoutGUDialog, self).__init__(parent)
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
        self.var_set("nomor_gu", self.nomor_gu.text())

        self.var_set("gu_nama_kantah", self.gu_nama_kantah.text())
        self.var_set("gu_nama_kecamatan", self.gu_nama_kecamatan.text())
        self.var_set("gu_nama_desa", self.gu_nama_desa.text())

        self.var_set("gu_no_peta_pendaftaran", self.gu_no_peta_pendaftaran.text())
        self.var_set("gu_no_peta_kerja", self.gu_no_peta_kerja.text())

        self.var_set("gu_pu_nama", self.gu_pu_nama.text())
        self.var_set("gu_pu_status", self.gu_pu_status.text())
        self.var_set("gu_pu_instansi", self.gu_pu_instansi.text())
        self.var_set("gu_pu_nomor", self.gu_pu_nomor.text())
        self.var_set("gu_pu_surat_tugas", self.gu_pu_surat_tugas.text())
        self.var_set("gu_pu_alat", self.gu_pu_alat.text())

    def read_settings(self):
        self.nomor_gu.setText(self.project.readEntry("GeoKKP", "nomor_gu")[0])

        self.gu_nama_kantah.setText(
            self.project.readEntry("GeoKKP", "gu_nama_kantah")[0]
        )
        self.gu_nama_kecamatan.setText(
            self.project.readEntry("GeoKKP", "gu_nama_kecamatan")[0]
        )
        self.gu_nama_desa.setText(self.project.readEntry("GeoKKP", "gu_nama_desa")[0])

        self.gu_no_peta_pendaftaran.setText(
            self.project.readEntry("GeoKKP", "gu_no_peta_pendaftaran")[0]
        )
        self.gu_no_peta_kerja.setText(
            self.project.readEntry("GeoKKP", "gu_no_peta_kerja")[0]
        )

        self.gu_pu_nama.setText(self.project.readEntry("GeoKKP", "gu_pu_nama")[0])
        self.gu_pu_status.setText(self.project.readEntry("GeoKKP", "gu_pu_status")[0])
        self.gu_pu_instansi.setText(
            self.project.readEntry("GeoKKP", "gu_pu_instansi")[0]
        )
        self.gu_pu_nomor.setText(self.project.readEntry("GeoKKP", "gu_pu_nomor")[0])
        self.gu_pu_surat_tugas.setText(
            self.project.readEntry("GeoKKP", "gu_pu_surat_tugas")[0]
        )
        self.gu_pu_alat.setText(self.project.readEntry("GeoKKP", "gu_pu_alat")[0])

    def write_settings(self):
        self.project.writeEntry("GeoKKP", "nomor_gu", self.nomor_gu.text())

        self.project.writeEntry("GeoKKP", "gu_nama_kantah", self.gu_nama_kantah.text())
        self.project.writeEntry(
            "GeoKKP", "gu_nama_kecamatan", self.gu_nama_kecamatan.text()
        )
        self.project.writeEntry("GeoKKP", "gu_nama_desa", self.gu_nama_desa.text())

        self.project.writeEntry(
            "GeoKKP", "gu_no_peta_pendaftaran", self.gu_no_peta_pendaftaran.text()
        )
        self.project.writeEntry(
            "GeoKKP", "gu_no_peta_kerja", self.gu_no_peta_kerja.text()
        )

        self.project.writeEntry("GeoKKP", "gu_pu_nama", self.gu_pu_nama.text())
        self.project.writeEntry("GeoKKP", "gu_pu_status", self.gu_pu_status.text())
        self.project.writeEntry("GeoKKP", "gu_pu_instansi", self.gu_pu_instansi.text())
        self.project.writeEntry("GeoKKP", "gu_pu_nomor", self.gu_pu_nomor.text())
        self.project.writeEntry(
            "GeoKKP", "gu_pu_surat_tugas", self.gu_pu_surat_tugas.text()
        )
        self.project.writeEntry("GeoKKP", "gu_pu_alat", self.gu_pu_alat.text())

    def on_btn_edit_layout_pressed(self):
        gu_template_exists = False
        # check if the same PBT layout already existed
        for existing_layout in self.project.layoutManager().printLayouts():
            if existing_layout.name() == "Gambar Ukur A3":
                gu_template_exists = True
                layout = existing_layout
        if not gu_template_exists:
            project = QgsProject.instance()
            layout = QgsPrintLayout(project)
            with open(qpt_path_a3) as qpt_file_a3:
                qpt_content_a3 = qpt_file_a3.read()
            doc = QtXml.QDomDocument()
            doc.setContent(qpt_content_a3)
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
