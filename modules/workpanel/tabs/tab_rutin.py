import os
import json

from qgis.PyQt import QtWidgets, uic
from qgis.core import QgsProject

from qgis.PyQt.QtCore import pyqtSignal
from qgis.utils import iface

from ...utils import (
    readSetting,
    get_project_crs,
    sdo_to_layer,
    get_layer_config,
)
from ...api import endpoints
from ...memo import app_state
from ...topology import quick_check_topology
from ...desain_persil import DesainPersil
from ...informasi_persil import InformasiPersil

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "../../../ui/workpanel/tab_rutin.ui")
)


STACKWIDGET_LOKASI = 0
STACKWIDGET_RUTIN = 1


class TabRutin(QtWidgets.QWidget, FORM_CLASS):
    """Dialog for Peta Bidang"""

    closingPlugin = pyqtSignal()

    def __init__(self, parent=iface.mainWindow()):
        super(TabRutin, self).__init__(parent)
        self.setupUi(self)
        self.project = QgsProject
        self._set_initial_state()

        self.current_berkas = None
        self.current_layers = []
        self._sistem_koordinat = ""

        self._item_per_page = 20
        self._start_item = 0
        self._num_item = -1

        self.current_settings = self._get_current_settings()

        self._parcel_ready_to_map = []

        self.btn_rutin_cari.clicked.connect(self._handle_cari_berkas_rutin)
        self.btn_rutin_mulai.clicked.connect(self.mulai_berkas_rutin)
        self.btn_rutin_informasi.clicked.connect(self._handle_informasi_berkas_rutin)
        self.btn_rutin_simpan.clicked.connect(self.simpan_berkas_rutin)
        self.btn_rutin_tutup.clicked.connect(self.tutup_berkas_rutin)
        self.btn_rutin_selesai.clicked.connect(self.selesai_berkas_rutin)
        self.btn_first.clicked.connect(self._handle_first_page)
        self.btn_last.clicked.connect(self._handle_last_page)
        self.btn_next.clicked.connect(self._handle_next_page)
        self.btn_prev.clicked.connect(self._handle_prev_page)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        self.stackedWidget.setCurrentIndex(0)
        event.accept()

    def setup_workpanel(self):
        pass

    def _set_initial_state(self):
        self.btn_rutin_cari.setDisabled(False)
        self.btn_rutin_mulai.setDisabled(False)
        self.btn_rutin_simpan.setDisabled(True)
        self.btn_rutin_informasi.setDisabled(True)
        self.btn_rutin_di302.setDisabled(True)
        self.btn_rutin_layout.setDisabled(True)
        self.btn_rutin_tutup.setDisabled(True)
        self.btn_rutin_selesai.setDisabled(True)
        self.input_rutin_no_berkas.setDisabled(False)
        self.input_rutin_th_berkas.setDisabled(False)

    def _get_current_settings(self):
        kantor = readSetting("kantorterpilih")
        # provinsi = readSetting("provinsiterpilih")
        # kabupaten = readSetting("kabupatenterpilih")
        # kecamatan = readSetting("kecamatanterpilih")
        # kelurahan = readSetting("kelurahanterpilih")

        self.current_settings = {
            "kantor": kantor,
            # "provinsi": provinsi,
            # "kabupaten": kabupaten,
            # "kecamatan": kecamatan,
            # "kelurahan": kelurahan,
        }
        return self.current_settings

    def cari_berkas_rutin(self):
        self._get_current_settings()
        if not self.current_settings["kantor"]:
            return

        no_berkas = self.input_rutin_no_berkas.text()
        th_berkas = self.input_rutin_th_berkas.text()

        response = endpoints.get_berkas(
            nomor_berkas=no_berkas,
            tahun_berkas=th_berkas,
            kantor_id=self.current_settings["kantor"]["kantorID"],
            tipe_kantor_id=str(self.current_settings["kantor"]["tipeKantorId"]),
            start=self._start_item,
            count=self._num_item,
            limit=self._item_per_page,
        )
        response_json = json.loads(response.content)
        print("cari", response_json)
        self._setup_pagination(response_json["JUMLAHTOTAL"])
        self.populate_berkas_rutin(response_json["BERKASSPATIAL"])

    def populate_berkas_rutin(self, data):
        self.table_rutin.setRowCount(0)
        for item in data:
            pos = self.table_rutin.rowCount()
            self.table_rutin.insertRow(pos)

            self.table_rutin.setItem(
                pos, 0, QtWidgets.QTableWidgetItem(str(item["NOMOR"]))
            )
            self.table_rutin.setItem(
                pos, 1, QtWidgets.QTableWidgetItem(str(item["TAHUN"]))
            )
            self.table_rutin.setItem(
                pos, 2, QtWidgets.QTableWidgetItem(item["OPERASISPASIAL"])
            )

    def _setup_pagination(self, data):
        if self._num_item == -1:
            self._num_item = data[0]["COUNT(1)"]
        print(self._num_item, self._start_item, self._item_per_page)

        if self._num_item > 0:
            if self._start_item + self._item_per_page >= self._num_item:
                page = (
                    f"{self._start_item + 1} - {self._num_item} dari {self._num_item}"
                )
                self.btn_next.setDisabled(True)
                self.btn_last.setDisabled(True)
            else:
                page = f"{self._start_item + 1} - {self._start_item + self._item_per_page} dari {self._num_item}"
                self.btn_next.setDisabled(False)
                self.btn_last.setDisabled(False)
        else:
            page = "0"
            self.btn_next.setDisabled(True)
            self.btn_prev.setDisabled(True)
            self.btn_first.setDisabled(True)
            self.btn_last.setDisabled(True)

        prev_btn_disabled = self._start_item == 0 or self._num_item == 0
        self.btn_prev.setDisabled(prev_btn_disabled)
        self.btn_first.setDisabled(self._start_item == 0)
        self.input_page.setText(page)

    def _handle_first_page(self):
        self._start_item = 0
        self.cari_berkas_rutin()

    def _handle_next_page(self):
        self._start_item += self._item_per_page
        self.cari_berkas_rutin()

    def _handle_prev_page(self):
        self._start_item -= self._item_per_page
        self.cari_berkas_rutin()

    def _handle_last_page(self):
        self._start_item = (self._num_item // self._item_per_page) * self._item_per_page
        if self._start_item >= self._num_item:
            self._start_item -= self._item_per_page
        self.cari_berkas_rutin()

    def _handle_cari_berkas_rutin(self):
        self._start_item = 0
        self._num_item = -1
        self.cari_berkas_rutin()

    def mulai_berkas_rutin(self):
        # if self.current_berkas is not None:
        #     QtWidgets.QMessageBox.critical(
        #         None,
        #         "Tutup berkas",
        #         "Tutup berkas yang sedang dikerjakan terlebih dahulu",
        #     )
        #     return

        selected_row = self.table_rutin.selectedItems()
        no_berkas = selected_row[0].text()
        th_berkas = selected_row[1].text()
        username = app_state.get("username").value

        response_start_berkas = endpoints.start_berkas_spasial(
            nomor_berkas=no_berkas,
            tahun_berkas=th_berkas,
            kantor_id=self.current_settings["kantor"]["kantorID"],
            tipe_kantor_id=str(self.current_settings["kantor"]["tipeKantorId"]),
            username=username,
        )
        response_start_berkas_json = json.loads(response_start_berkas.content)
        self.current_berkas = response_start_berkas_json
        print(self.current_berkas)

        if self.current_berkas["valid"]:
            lanjut_blanko = True
            is_e_sertifikat = readSetting("isESertifikat")
            if is_e_sertifikat and self.tipe_kantor_id not in ["1", "2"]:
                response_blanko = endpoints.get_blanko_by_berkas_id(
                    berkas_id=self.current_berkas["BERKASID"]
                )
                response_blanko_json = json.loads(response_blanko.content)
                if len(response_blanko_json["BLANKO"]) > 0:
                    lanjut_blanko = True
                else:
                    lanjut_blanko = False

            if (
                self.current_berkas["kodeSpopp"]
                in [
                    "SPOPP-3.46.3",
                    "SPOPP-3.09.9",
                    "SPOPP-3.09.1",
                    "SPOPP-3.09.2",
                    "SPOPP-3.18.1",
                    "SPOPP-3.12.1",
                ]
                or lanjut_blanko
            ):
                if self.current_berkas["newGugusId"] != "":
                    if self.current_berkas["tipeBerkas"] != "DAG":
                        gugus_id = self.current_berkas["newGugusId"]
                        self._load_berkas_spasial([gugus_id], False)
                else:
                    if self.current_berkas["oldGugusIds"]:
                        gugus_ids = [
                            str(id) for id in self.current_berkas["oldGugusIds"]
                        ]
                        self._load_berkas_spasial(gugus_ids, True)
                    else:
                        # TODO: Add new blank layer
                        pass

                self.btn_rutin_cari.setDisabled(True)
                self.btn_rutin_mulai.setDisabled(True)
                self.btn_rutin_informasi.setDisabled(False)
                self.btn_rutin_di302.setDisabled(False)
                self.btn_rutin_simpan.setDisabled(False)
                self.btn_rutin_tutup.setDisabled(False)
                self.btn_rutin_selesai.setDisabled(False)
                self.input_rutin_no_berkas.setDisabled(True)
                self.input_rutin_th_berkas.setDisabled(True)

                if self.current_berkas["tipeBerkas"] == "DAG":
                    # TODO: Add input gambar denah
                    pass
                else:
                    self._sistem_koordinat = "TM3"
            else:
                QtWidgets.QMessageBox.warning(
                    None, "Perhatian", "Lakukan registrasi blanko terlebih dahulu"
                )
        else:
            message = "\n".join(self.current_berkas["errorStack"])
            QtWidgets.QMessageBox.critical(None, "Error", message)

    def _load_berkas_spasial(self, gugus_ids, riwayat=False):
        response_spatial_sdo = endpoints.get_spatial_document_sdo(
            gugus_ids=gugus_ids, include_riwayat=riwayat
        )
        response_spatial_sdo_json = json.loads(response_spatial_sdo.content)
        print(response_spatial_sdo_json)

        if not response_spatial_sdo_json["status"]:
            QtWidgets.QMessageBox.critical(None, "Error", "Proses Unduh Geometri gagal")
            return

        epsg = get_project_crs()
        if response_spatial_sdo_json["geoKkpPolygons"]:
            print(response_spatial_sdo_json["geoKkpPolygons"][0])

            if response_spatial_sdo_json["geoKkpPolygons"]:
                layer_config = get_layer_config(20100)
                layer = sdo_to_layer(
                    response_spatial_sdo_json["geoKkpPolygons"],
                    name=layer_config["Nama Layer"],
                    symbol=layer_config["Style Path"],
                    crs=epsg,
                    coords_field="boundary",
                )
                self.current_layers.append(layer)

    def simpan_berkas_rutin(self):
        if self.current_berkas and self.current_berkas["tipeBerkas"] == "DAG":
            # TODO: Add input gambar denah
            return

        topo_error_message = []
        for layer in self.current_layers:
            valid, num = quick_check_topology(layer)
            print(valid, num)
            if not valid:
                message = f"Ada {num} topology error di layer {layer.name()}"
                topo_error_message.append(message)

        if topo_error_message:
            QtWidgets.QMessageBox.warning(
                None, "Perhatian", "\n".join(topo_error_message)
            )
            return

        self._create_dataset_integration()

        gambar_ukur_id = (
            self.current_berkas["gambarUkurs"]
            if self.current_berkas["gambarUkurs"]
            else ""
        )
        desain_persil = DesainPersil(
            parent=self,
            nomor_berkas=self.current_berkas["nomorBerkas"],
            tahun_berkas=self.current_berkas["tahunBerkas"],
            kantor_id=self.current_settings["kantor"]["kantorID"],
            tipe_kantor_id=str(self.current_settings["kantor"]["tipeKantorId"]),
            tipe_berkas=self.current_berkas["tipeBerkas"],
            gambar_ukur_id=gambar_ukur_id,
            wilayah_id=self.current_berkas["wilayahId"],
            tipe_sistem_koordinat="TM3",
            new_parcel_number=self.current_berkas["newParcelNumber"],
            new_apartment_number=self.current_berkas["newApartmentNumber"],
            new_parcels=self.current_berkas["newParcels"],
            old_parcels=self.current_berkas["oldParcels"],
            new_apartments=self.current_berkas["newApartments"],
            old_apartments=self.current_berkas["oldApartments"],
        )
        desain_persil.show()
        desain_persil.integrasi.connect(self._process_integration)

    def _process_integration(self, payload):
        sdo_to_submit = {}
        # not saving wilayah id

        list_data = []
        print("integrasi", payload)
        for data in payload["ds_parcel"]["PersilBaru"]:
            temp = {
                "OID": data["OID"],
                "Label": data["LABEL"],
                "Area": float(str(data["AREA"]).replace(",", ".")),
                "Boundary": data["BOUNDARY"],
                "Text": data["TEXT"],
                "Keterangan": data["KETERANGAN"],
                "Height": data["HEIGHT"],
                "Orientation": data["ORIENTATION"],
            }
            list_data.append(temp)
        sdo_to_submit["PersilBaru"] = list_data

        list_data = []
        for data in payload["ds_parcel"]["PersilEdit"]:
            temp = {
                "OID": data["OID"],
                "REGID": data["REGID"],
                "NIB": data["NIB"],
                "Luast": float(str(data["LUAST"]).replace(",", ".")),
                "Label": data["LABEL"],
                "Area": float(str(data["AREA"]).replace(",", ".")),
                "Boundary": data["BOUNDARY"],
                "Text": data["TEXT"],
                "Keterangan": data["KETERANGAN"],
                "Height": data["HEIGHT"],
                "Orientation": data["ORIENTATION"],
            }
            list_data.append(temp)
        sdo_to_submit["PersilEdit"] = list_data

        list_data = []
        for data in payload["ds_parcel"]["PersilInduk"]:
            if data["OID"] is None:
                continue

            temp = {
                "OID": data["OID"],
                "REGID": data["REGID"],
                "NIB": data["NIB"],
                "Luast": float(str(data["LUAST"]).replace(",", ".")),
                "Label": data["LABEL"],
                "Area": float(str(data["AREA"]).replace(",", ".")),
                "Boundary": data["BOUNDARY"],
                "Text": data["TEXT"],
                "Keterangan": data["KETERANGAN"],
                "Height": data["HEIGHT"],
                "Orientation": data["ORIENTATION"],
            }
            list_data.append(temp)
        sdo_to_submit["PersilInduk"] = list_data

        if self.current_berkas["tipeBerkas"] in ["SUB", "UNI"]:
            if self.current_berkas["delParcels"]:
                for p in self.current_berkas["delParcels"]:
                    self.dataset_integration["PersilMati"].append([str(p)])

        self._fill_entity_datatable()
        self._fill_text_entity()
        self._fill_point_entity()
        self._fill_dimensi_entity()

        self._run_integration(
            sdo_to_submit, payload["reset_302"], payload["wilayah_id"]
        )

    def _run_integration(self, sdo_to_submit, reset302, wilayah_id):
        current_settings = self._get_current_settings()
        if not current_settings["kantor"]:
            return

        gu_reg_id = ""
        if self.current_berkas["gambarUkurs"]:
            gu_reg_id = str(self.current_berkas["gambarUkurs"][0])

        skb = "NonTM3" if self._sistem_koordinat not in ["TM3", "NonTM3"] else "TM3"
        user = app_state.get("pegawai", {})
        print("user", user)
        user_id = (
            user.value["userId"]
            if user.value and "userId" in user.value.keys() and user.value["userId"]
            else ""
        )
        print(self.current_berkas.keys())
        response = endpoints.submit_sdo(
            nomor_berkas=self.current_berkas["nomorBerkas"],
            tahun_berkas=self.current_berkas["tahunBerkas"],
            kantor_id=current_settings["kantor"]["kantorID"],
            tipe_kantor_id=str(current_settings["kantor"]["tipeKantorId"]),
            wilayah_id=wilayah_id,
            petugas_id=user_id,
            user_id=user_id,
            gugus_ids=self.current_berkas["newGugusId"],
            gu_id=gu_reg_id,
            sistem_koordinat=skb,
            keterangan="",
            reset302=reset302,
            sdo_to_submit=sdo_to_submit,
        )
        response_json = json.loads(response.content)
        print(response_json)
        if not response_json:
            QtWidgets.QMessageBox.critical(
                None,
                "Integrasi",
                "Integrasi gagal!\nCek service berkas spatial di server sudah dijalankan!",
            )

        if response_json["Error"]:
            if response_json["Error"][0]["message"].startswith(
                "Geometri persil dengan ID"
            ) or response_json["Error"][0]["message"].startswith(
                "Geometri apartemen dengan ID"
            ):
                msg = str(response_json["Error"][0]["message"]).split("|")[0]
                QtWidgets.QMessageBox.critical(None, "GeoKKP Web", msg)
            else:
                msg = str(response_json["Error"][0]["message"])
                QtWidgets.QMessageBox.critical(None, "GeoKKP Web", msg)
            return

        self._parcel_ready_to_map = []
        for persil in response_json["PersilBaru"]:
            regid = persil["regid"]
            self._parcel_ready_to_map.append(regid)

            if (
                regid not in self.current_berkas["oldParcels"]
                and regid not in self.current_berkas["delParcels"]
                and regid not in self.current_berkas["oldApartments"]
                and regid not in self.current_berkas["delApartments"]
            ):
                self.current_berkas["newParcels"].append(regid)

            nib = persil["nib"]
            # TODO: Update NIB to new parcels

        self.btn_rutin_selesai.setDisabled(False)
        self.btn_rutin_layout.setDisabled(False)

        QtWidgets.QMessageBox.information(
            None,
            "GeoKKP Web",
            "Data telah disimpan ke dalam database. \nLanjutkan ke pencetakan dan plotting peta",
        )

    def _fill_entity_datatable(self):
        pass

    def _fill_text_entity(self):
        pass

    def _fill_point_entity(self):
        pass

    def _fill_dimensi_entity(self):
        pass

    def _process_ganti_desa(self, payload):
        pass

    def _create_dataset_integration(self):
        self.dataset_integration = {
            "PersilMati": [],  # REGID
            "Poligon": [],  # Key, Type, Label, Height, Orientation, Boundary, Text
            "Garis": [],  # KEY, TYPE, LINE
            "Teks": [],  # Key, Type, Height, Orientation, Label, Position
            "Titik": [],  # Key, Type, PointOrientation, TextOrientation, Scale, height, Label, PointPosition, TextPosition
            "Dimensi": [],  # Key, Type, Line, InitialPoint, Label, Endpoint, Initialorientation, Labelorientation, Endorientation, Height, Label
        }

    def _handle_informasi_berkas_rutin(self):
        current_settings = self._get_current_settings()
        if not current_settings["kantor"]:
            return

        gambar_ukur_id = (
            self.current_berkas["gambarUkurs"][0]
            if self.current_berkas["gambarUkurs"]
            else ""
        )

        informasi_persil = InformasiPersil(
            self.current_berkas["nomorBerkas"],
            self.current_berkas["tahunBerkas"],
            current_settings["kantor"]["kantorID"],
            self.current_berkas["tipeBerkas"],
            self._sistem_koordinat,
            self.current_berkas["newParcelNumber"],
            self.current_berkas["wilayahId"],
            gambar_ukur_id,
            self.current_berkas["newParcels"],
            self.current_berkas["oldParcels"],
        )
        informasi_persil.show()

    def tutup_berkas_rutin(self):
        current_settings = self._get_current_settings()
        if not current_settings["kantor"]:
            return

        response_tutup_berkas = endpoints.stop_berkas(
            nomor_berkas=self.current_berkas["nomorBerkas"],
            tahun_berkas=self.current_berkas["tahunBerkas"],
            kantor_id=current_settings["kantor"]["kantorID"],
        )
        response_tutup_berkas_json = json.loads(response_tutup_berkas.content)
        if response_tutup_berkas_json:
            self.current_berkas = None
            layer_ids = [layer.id() for layer in self.current_layers]
            self.project.instance().removeMapLayers(layer_ids)
            iface.mapCanvas().refresh()
            self.current_layers = []

            self._set_initial_state()

    def selesai_berkas_rutin(self):
        pass
