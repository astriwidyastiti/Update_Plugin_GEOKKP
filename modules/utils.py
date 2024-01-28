import re
import json
import os
import math
import urllib.parse

from multiprocessing.dummy import Pool as ThreadPool
from functools import partial

from qgis.PyQt.QtCore import QVariant, QFile  # noqa
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QPushButton, QMessageBox
from qgis.core import (
    QgsMessageLog,
    QgsSettings,
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsVectorFileWriter,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsField,
    QgsPointXY,
    QgsRectangle,
    QgsGeometry,
    QgsFeature,
    QgsApplication,
    QgsAuthMethodConfig,
    QgsProcessingFeatureSourceDefinition,
    QgsDxfExport,
)
from qgis.utils import iface
from qgis.gui import QgsMapToolIdentifyFeature
from collections import namedtuple
from qgis import processing

"""
Kumpulan Utilities untuk GeoKKP-QGIS
===========================================

Variabel global dan modul global untuk digunakan di plugin GeoKKP-GIS

TODO: Pindah variabel & konstanta global ke modul terpisah
"""

layer_json_file = os.path.join(os.path.dirname(__file__), "../config/layers.json")

epsg4326 = QgsCoordinateReferenceSystem("EPSG:4326")

CoordinateValidationResult = namedtuple("CoordinateValidationResult", "is_valid errors")
CoordinateValidationErrors = namedtuple(
    "CoordinateValidationErrors", "row, col error_value"
)

DefaultMessageBarButton = QPushButton()
DefaultMessageBarButton.setText("Show Me")
DefaultMessageBarButton.pressed.connect(iface.openMessageLog)

# constants for NLP
x_origin = 32000
y_origin = 282000
grid_10rb = 6000
grid_2500 = 1500
grid_1000 = 500
grid_500 = 250
grid_250 = 125

# constants for NLP_INDEX
NLP_INDEX = ["A", "B", "C", "D", "E", "F"]

# constants for TM-3 Zone
zona_TM3 = {
    "46.2": "EPSG:23830",
    "47.1": "EPSG:23831",
    "47.2": "EPSG:23832",
    "48.1": "EPSG:23833",
    "48.2": "EPSG:23834",
    "49.1": "EPSG:23835",
    "49.2": "EPSG:23836",
    "50.1": "EPSG:23837",
    "50.2": "EPSG:23838",
    "51.1": "EPSG:23839",
    "51.2": "EPSG:23840",
    "52.1": "EPSG:23841",
    "52.2": "EPSG:23842",
    "53.1": "EPSG:23843",
    "53.2": "EPSG:23844",
    "54.1": "EPSG:23845",
}

# constants for SDO Geometries
GPOINT = "Point"
GLINESTRING = "LineString"
GPOLYGON = "Polygon"
SDO_GTYPE_MAP = {
    "00": "Unknown",
    "01": GPOINT,
    "02": GLINESTRING,
    "03": GPOLYGON,
    "04": "Collection",
    "05": "MultiPoint",
    "06": "MultiLine",
    "07": "MultiPolygon",
    "08": "Solid",
    "09": "MultiSolid",
}

SDO_FIELD_EXCLUDE = ["text", "boundary"]


# constants for processing snap parameter (auto-adjust)
SNAP_ALIGNING_NODE_INSERT_WHEN_REQUIRED = 0
SNAP_CLOSEST_NODE_INSERT_WHEN_REQUIRED = 1
SNAP_ALIGNING_NODE_NOT_INSERT = 2
SNAP_CLOSEST_NODE_NOT_INSERT = 3
SNAP_MOVE_END_POINT_ALIGN_NODE = 4
SNAP_MOVE_END_CLOSEST_NODE = 5
SNAP_ENDPOINT_TO_ENDPOINT = 6
SNAP_ANCHOR_NODES = 7


# global settings variable
settings = QgsSettings()


"""
Definisi Fungsi
TODO: buat kelas untuk tiap kategori
"""


def logMessage(message, level=Qgis.Info):
    """
    Logger untuk debugging
    """
    QgsMessageLog.logMessage(message, "GeoKKP-GIS", level=level)


def dialogBox(text, title="Peringatan GeoKKP", type="Information"):
    """
    Kotak peringatan
    """
    message = QMessageBox(parent=iface.mainWindow())

    if type == "Information":
        icon = QMessageBox.Information
    elif type == "Warning":
        icon = QMessageBox.Critical

    message.setIcon(icon)
    message.setText(text)
    message.setWindowTitle(title)
    message.setStandardButtons(QMessageBox.Ok)
    message.exec()


def display_message_bar(
    tag,
    message,
    parent=None,
    level=Qgis.Info,
    action=DefaultMessageBarButton,
    duration=5,
):
    """
    Wrapper untuk menampilkan pesan di message bar
    """
    parent = parent if parent else iface.messageBar()
    widget = parent.createMessage(tag, message)
    if action:
        action.setParent(widget)
        widget.layout().addWidget(action)
    parent.pushWidget(widget, level, duration=duration)


def get_tm3_zone(long):
    """
    Get TM-3 Zone from long
    """
    nom = math.floor((long - 90) / 6) + 46
    if math.floor((long - 93) / 3) % 2 == 0:
        denom = 2
    else:
        denom = 1
    return f"{nom}.{denom}"


def loadXYZ(url, name):
    """
    Memuat layer dalam bentuk XYZ Tile
    """
    encodedUrl = urllib.parse.quote(url)
    urlString = "type=xyz&zmin=0&zmax=21&url=" + encodedUrl
    logMessage("Loaded url: " + urlString)
    rasterLyr = QgsRasterLayer(urlString, name, "wms")
    QgsProject.instance().addMapLayer(rasterLyr)


def add_google_basemap():
    """
    Tambahkan layer basemap default: Google Basemap
    """
    url = "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
    loadXYZ(url, "Google Satellite")


def activate_editing(layer):
    """
    Activate layer editing tools
    TODO: fix conflicts with built-in layer editing in QGIS
    """
    QgsProject.instance().setTopologicalEditing(True)
    layer.startEditing()
    iface.layerTreeView().setCurrentLayer(layer)
    iface.actionAddFeature().trigger()
    # for vertex editing
    # iface.actionVertexTool().trigger()


def storeSetting(key, value):
    """
    Store value to QGIS Settings
    """
    settings.setValue("geokkp/" + str(key), value)
    logMessage("Menyimpan data " + str(key) + " pada memory proyek QGIS")
    settings.sync()


def readSetting(key, default=None):
    """
    Read value from QGIS Settings
    """
    logMessage("Mengambil data " + str(key) + " dari memory proyek QGIS")
    try:
        return settings.value("geokkp/" + str(key), default)
    except Exception:
        logMessage("gagal memuat data")
    settings.sync()


def clear_all_vars():
    """Hapus semua value dari QgsSettings yang digunakan oleh GeoKKP"""
    for key in sorted(settings.allKeys()):
        if key.startswith("geokkp"):
            settings.remove(key)
            # s.setValue(x, "")
    if not settings.contains("geokkp"):
        logMessage("Flushed all GeoKKP vars")
    settings.sync()


def is_layer_exist(project, layername):
    """
    Boolean check if layer exist
    """
    for layer in project.instance().mapLayers().values():
        if layer.name == layername:
            return True
        else:
            return False


def set_symbology(layer, qml):
    """
    Set layer symbology based on QML files in ./styles folder
    """
    uri = os.path.join(os.path.dirname(__file__), "../styles/" + qml)
    layer.loadNamedStyle(uri)


def properify(self, text):
    """
    Filter text for OS's friendly directory format

    Remove all non-word characters (everything except numbers and letters) and
    replace all runs of whitespace with a single dash

    """
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", "_", text)
    return text


def edit_by_identify(mapcanvas, layer):
    layer = iface.activeLayer()
    mc = iface.mapCanvas()
    mapTool = QgsMapToolIdentifyFeature(mc)
    mapTool.setLayer(layer)
    mc.setMapTool(mapTool)
    mapTool.featureIdentified.connect(onFeatureIdentified)


def onFeatureIdentified(feature):
    fid = feature.id()
    return fid


def save_with_description(layer, outputfile):
    options = QgsVectorFileWriter.SaveVectorOptions()

    # If geopackage exists, append layer to it, else create it
    if os.path.exists(outputfile):
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
    else:
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile

    # Use input layer abstract and name in the geopackage
    options.layerOptions = [f"DESCRIPTION={layer.abstract()}"]
    options.layerName = layer.name()
    return QgsVectorFileWriter.writeAsVectorFormat(layer, outputfile, options)


def iconPath(name):
    # logMessage(os.path.join(os.path.dirname(__file__), "images", name))
    return os.path.join(os.path.dirname(__file__), "..", "images", name)


def icon(name):
    return QIcon(iconPath(name))


def validate_raw_coordinates(raw_coords):
    r"""Validate list of coordinate pair with rules below
    1) only number, comma, point, minus, semicolon, whitespace
    2) minus could only be placed in front of number
    3) point could only be placed between number
    4) comma could only be placed between number, whitespace, or tab
    5) simicolon could only be placed after number or whitespace and not in the last position
    6) coordinate number that is allowed are only the number that follow
        this pattern ^\s*(?:-?\d+\.?\d+)\s*$|;\s*(?:-?\d+\.?\d+)\s*;

    Parameters
    ----------
    raw_coords: str
        list of coordinate pair which separated by semicolon for each pair

    Returns
    ----------
    CoordinateValidationResult
        CoordinateValidationResult is a namedtuple contain two attributes, is_valid which indicate whether
        the raw coordinate is valid or not and errors which is tuple that contain CoordinateValidationError.
        CoordinateValidationError is namedtuple contain the row, col and error_value
    """
    pattern = "|".join(
        [
            r"(?:[^-.,;\d\r\n \t])",
            r"(?:(?<!\D)-|-(?=\D))",
            r"(?:(?<=\D)\.|\.(?!\d))",
            r"(?:(?<=[^\d \t]),|,(?=[^\d \t]))",
            r"(?:(?<=[^\d \t]);|;$)",
            r"(?:(?:(?<=^)|(?<=;))\s*(?:-?\d+\.?\d+)\s*(?:(?=;)|(?=$)))",
        ]
    )
    re_pattern = re.compile(pattern)

    errors = []
    row = 0
    cursor_pos = 0
    for match in re_pattern.finditer(raw_coords):
        if match:
            col = match.start() + 1
            row += raw_coords[cursor_pos:col].count("\n")
            cursor_pos = col
            prev_error = len(errors) and errors[-1]
            if prev_error and prev_error.row == row and prev_error.col + 1 == col:
                errors[-1] = CoordinateValidationErrors(
                    row=row, col=col, error_value=prev_error.error_value + match.group()
                )
            else:
                errors.append(
                    CoordinateValidationErrors(
                        row=row, col=col, error_value=match.group()
                    )
                )
    return CoordinateValidationResult(is_valid=not len(errors), errors=tuple(errors))


def parse_raw_coordinate(coordList):
    """sanitasi input koordinat"""
    stripped_coords = coordList.strip()
    splitted_coords = stripped_coords.split(";")
    for coords in splitted_coords:
        coord_components = coords.split(",")
        if len(coord_components) < 2:
            raise ValueError(
                "Coordinate pair must be consist of two number separated by comma"
            )
        point = QgsPointXY(float(coord_components[0]), float(coord_components[1]))
        yield point


def parse_sdo_geometry_type(sdo_gtype):
    sdo_gtype_str = str(sdo_gtype).rjust(4, "0")
    gtype = sdo_gtype_str[2:4]
    dim = max(2, int(sdo_gtype_str[0]))
    return SDO_GTYPE_MAP[gtype], dim


def parse_sdo_fields(sdo):
    fields = {}
    for field in sdo.keys():
        if field not in SDO_FIELD_EXCLUDE:
            fields[field] = "String"
    return fields


def parse_sdo_geometry(elem_info, ordinates):
    start_index = elem_info[0] - 1
    gtype, dim = parse_sdo_geometry_type(elem_info[1])

    result = []
    start = start_index
    while True:
        end = start + min(2, dim)
        result.append(QgsPointXY(*ordinates[start:end]))
        start += dim
        if start >= len(ordinates):
            break

    if gtype == GPOINT:
        return QgsGeometry.fromPointXY(result[0])
    elif gtype == GLINESTRING:
        return QgsGeometry.fromPolyline(result)
    elif gtype == GPOLYGON:
        return QgsGeometry.fromPolygonXY([result])


def sdo_to_feature(sdo, fields, coords_field="boundary"):
    attrs = [sdo[f] for f in fields]
    geometry = parse_sdo_geometry(
        sdo[coords_field]["sdoElemInfo"], sdo[coords_field]["sdoOrdinates"]
    )

    feature = QgsFeature()
    feature.setGeometry(geometry)
    feature.setAttributes(attrs)

    return feature


def sdo_to_layer(sdo, name, crs=None, symbol=None, coords_field="boundary"):
    if not isinstance(sdo, list):
        sdo = [sdo]

    gtype, dim = parse_sdo_geometry_type(sdo[0]["boundary"]["sdoGtype"])
    fields = parse_sdo_fields(sdo[0])
    layer = add_layer(name, gtype, symbol=symbol, fields=fields, crs=crs)
    provider = layer.dataProvider()

    pool = ThreadPool()
    func1 = partial(sdo_to_feature, fields=fields.keys())
    func2 = partial(func1, coords_field=coords_field)
    features = pool.map(func2, sdo)
    pool.close()
    pool.join()
    provider.addFeatures(features)
    layer.commitChanges()

    return layer


def get_layer_config(kode):
    with open(layer_json_file, "r") as f:
        layer_config = json.loads(f.read())
    for layers in layer_config["layers"].values():
        for layer in layers:
            if layer["Kode"] == kode:
                return layer
    return None


def sdo_geokkp_to_layer(sdo, crs):
    layers = []
    if sdo["geoKkpPolygons"]:
        if sdo["geoKkpPolygons"]["boundary"]:
            fields = parse_sdo_fields(sdo["geoKkpPolygons"]["boundary"][0])
            features = sdo_to_feature(fields, sdo["geoKkpPolygons"]["boundary"])
            layer_config = get_layer_config(20100)
            layer = add_layer(
                layer_config["Nama Layer"],
                layer_config["Tipe Layer"],
                layer_config["Style Path"],
                fields,
                crs,
            )
            layers.append(layer)
            provider = layer.dataProvider()
            provider.addFeatures(features)
            layer.commitChanges()

    return layers


def get_epsg_from_tm3_zone(zone, include_epsg_key=True):
    zone = zone.replace(",", ".")
    splitted_zone = zone.split(".")
    major = int(splitted_zone[0])
    minor = int(splitted_zone[1]) if len(splitted_zone) == 2 else 1
    if major < 46 or major > 54:
        return False
    magic = (major * 2 + minor) - 64
    return f"EPSG:238{magic}" if include_epsg_key else f"238{magic}"


def get_saved_credentials():
    auth_mgr = QgsApplication.authManager()
    auth_id = readSetting("authId")
    auth_cfg = QgsAuthMethodConfig()
    if auth_id:
        auth_mgr.loadAuthenticationConfig(auth_id, auth_cfg, True)
    return auth_cfg.configMap()


def save_credentials(username, password):
    auth_mgr = QgsApplication.authManager()
    auth_id = readSetting("authId")
    auth_cfg = QgsAuthMethodConfig()
    if not auth_id:
        auth_id = auth_cfg.id()
        auth_cfg.setName("geokkp")
        auth_cfg.setMethod("Basic")
    else:
        auth_mgr.loadAuthenticationConfig(auth_id, auth_cfg, True)

    auth_cfg.setConfig("username", username)
    auth_cfg.setConfig("password", password)
    assert auth_cfg.isValid()
    auth_mgr.storeAuthenticationConfig(auth_cfg)
    assert auth_cfg.id()
    storeSetting("authId", auth_cfg.id())
    return auth_cfg.id()


def add_layer(layername, type, symbol=None, fields=None, crs=None, parent=None):
    crs = iface.mapCanvas().mapSettings().destinationCrs()

    layer = QgsVectorLayer(
        f"{type}?crs=epsg:" + str(crs.postgisSrid()), layername, "memory"
    )
    layer_dataprovider = layer.dataProvider()
    if not fields:
        field_list = [
            QgsField("ID", QVariant.String),
            QgsField("Keterangan", QVariant.String),
        ]
    else:
        field_list = []
        for key, value in fields.items():
            if value == "String":
                field_type = QVariant.String
            elif value == "Int":
                field_type = QVariant.Int
            elif value == "Double":
                field_type = QVariant.Double
            field = QgsField(key, field_type)
            field_list.append(field)
    if symbol:
        symbolurl = os.path.join(os.path.dirname(__file__), "../styles/" + symbol)
        layer.loadNamedStyle(symbolurl)

    layer_dataprovider.addAttributes(field_list)
    layer.updateFields()
    QgsProject.instance().addMapLayer(layer)
    return layer


def resolve_path(name, basepath=None):
    if not basepath:
        basepath = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(basepath, name)


def set_project_crs_by_epsg(epsg):
    print(epsg)
    try:
        crs = QgsCoordinateReferenceSystem(epsg)
        QgsProject.instance().setCrs(crs)
    except Exception as e:
        print(e)


def get_project_crs(epsg=True):
    crs = QgsProject.instance().crs()
    return crs if not epsg else crs.authid()


def snap_geometries_to_layer(
    layer,
    ref_layer,
    tolerance=1,
    behavior=SNAP_ALIGNING_NODE_NOT_INSERT,
    output="memory:snap",
    only_selected=False,
):
    if isinstance(layer, str):
        layer = get_layer_by_id(layer)
    is_selected = only_selected or bool(layer.selectedFeatureCount())

    parameters = {
        "INPUT": QgsProcessingFeatureSourceDefinition(layer.id(), is_selected),
        "REFERENCE_LAYER": QgsProcessingFeatureSourceDefinition(ref_layer.id(), False),
        "TOLERANCE": tolerance,
        "BEHAVIOR": behavior,
        "OUTPUT": output,
    }

    result = processing.run("qgis:snapgeometries", parameters)

    return result["OUTPUT"]


def explode_polyline(layer, output="memory:explode"):
    if isinstance(layer, str):
        layer = get_layer_by_id(layer)
    is_selected = bool(layer.selectedFeatureCount())

    parameters = {
        "INPUT": QgsProcessingFeatureSourceDefinition(layer.id(), is_selected),
        "OUTPUT": output,
    }
    result = processing.run("native:explodelines", parameters)

    return result["OUTPUT"]


def polygonize(layer, output="memory:polygonize"):
    if isinstance(layer, str):
        layer = get_layer_by_id(layer)
    is_selected = bool(layer.selectedFeatureCount())

    parameters = {
        "INPUT": QgsProcessingFeatureSourceDefinition(layer.id(), is_selected),
        "OUTPUT": output,
    }
    result = processing.run("qgis:polygonize", parameters)

    return result["OUTPUT"]


def dissolve(layer, output="memory:dissolve"):
    if isinstance(layer, str):
        layer = get_layer_by_id(layer)
    is_selected = bool(layer.selectedFeatureCount())

    parameters = {
        "INPUT": QgsProcessingFeatureSourceDefinition(layer.id(), is_selected),
        "OUTPUT": output,
    }
    result = processing.run("native:dissolve", parameters)

    return result["OUTPUT"]


def get_layer_by_id(layer_id):
    return QgsProject.instance().mapLayer(layer_id)


def draw_rect_bound(xMin, yMin, xMax, yMax, epsg, nama="Blok NLP"):
    epsg = str(epsg)
    is_layer_exist
    layer = QgsVectorLayer(f"Polygon?crs={epsg}", nama, "memory")
    QgsProject.instance().addMapLayer(layer)

    rect = QgsRectangle(xMin, yMin, xMax, yMax)
    print(rect)
    polygon = QgsGeometry.fromRect(rect)
    print(polygon)

    feature = QgsFeature()
    feature.setGeometry(polygon)

    layer.dataProvider().addFeatures([feature])
    layer.updateExtents()


def bk_10000(x, y):
    k_10rb = int((x - x_origin) / grid_10rb) + 1
    b_10rb = int((y - y_origin) / grid_10rb) + 1
    return [k_10rb, b_10rb]


def bk_2500(x, y):
    k_10rb, b_10rb = bk_10000(x, y)
    k_2500 = int((x - (x_origin + (k_10rb - 1) * grid_10rb)) / grid_2500) + 1
    b_2500 = int((y - (y_origin + (b_10rb - 1) * grid_10rb)) / grid_2500) + 1
    return [k_2500, b_2500]


def bk_1000(x, y):
    k_10rb, b_10rb = bk_10000(x, y)
    k_2500, b_2500 = bk_2500(x, y)
    k_1000 = (
        int(
            (x - (x_origin + (k_10rb - 1) * grid_10rb + (k_2500 - 1) * grid_2500))
            / grid_1000
        )
        + 1
    )
    b_1000 = (
        int(
            (y - (y_origin + (b_10rb - 1) * grid_10rb + (b_2500 - 1) * grid_2500))
            / grid_1000
        )
        + 1
    )
    return [k_1000, b_1000]


def bk_500(x, y):
    k_10rb, b_10rb = bk_10000(x, y)
    k_2500, b_2500 = bk_2500(x, y)
    k_1000, b_1000 = bk_1000(x, y)
    k_500 = (
        int(
            (
                x
                - (
                    x_origin
                    + (k_10rb - 1) * grid_10rb
                    + ((k_2500 - 1) * grid_2500)
                    + (k_1000 - 1) * grid_1000
                )
            )
            / grid_500
        )
        + 1
    )
    b_500 = (
        int(
            (
                y
                - (
                    y_origin
                    + (b_10rb - 1) * grid_10rb
                    + ((b_2500 - 1) * grid_2500)
                    + (b_1000 - 1) * grid_1000
                )
            )
            / grid_500
        )
        + 1
    )
    return [k_500, b_500]


def bk_250(x, y):
    k_10rb, b_10rb = bk_10000(x, y)
    k_2500, b_2500 = bk_2500(x, y)
    k_1000, b_1000 = bk_1000(x, y)
    k_500, b_500 = bk_500(x, y)
    k_250 = (
        int(
            (
                x
                - (
                    x_origin
                    + (k_10rb - 1) * grid_10rb
                    + ((k_2500 - 1) * grid_2500)  # noqa
                    + ((k_1000 - 1) * grid_1000)
                    + (k_500 - 1) * grid_500
                )
            )
            / grid_250
        )
        + 1
    )
    b_250 = (
        int(
            (
                y
                - (
                    y_origin
                    + (b_10rb - 1) * grid_10rb
                    + ((b_2500 - 1) * grid_2500)  # noqa
                    + ((b_1000 - 1) * grid_1000)
                    + (b_500 - 1) * grid_500
                )
            )
            / grid_250
        )
        + 1
    )
    return [k_250, b_250]


def get_nlp(skala, x, y):
    """
    Cetak Nomor Lembar Peta berdasarkan skala

    argumen:
        skala   : skala peta dalam string
        x       : koordinat x dalam CRS TM-3
        y       : koordinat y dalam CRS TM-3
    output: string NLP
    """
    # hitungan baris dan kolom
    k_10rb, b_10rb = bk_10000(x, y)
    k_2500, b_2500 = bk_2500(x, y)
    k_1000, b_1000 = bk_1000(x, y)
    k_500, b_500 = bk_500(x, y)
    k_250, b_250 = bk_250(x, y)

    # Skala 2500
    nlp_2500 = 4 * (b_2500 - 1) + k_2500

    # Skala 1000
    nlp_1000 = 3 * (b_1000 - 1) + k_1000

    # Skala 500
    nlp_500 = 2 * (b_500 - 1) + k_500

    # Skala 250
    nlp_250 = 2 * (b_250 - 1) + k_250

    if skala == "10000":
        return f"{k_10rb:02d}.{b_10rb:03d}"
    elif skala == "2500":
        return f"{k_10rb:02d}.{b_10rb:03d}-{nlp_2500:02d}"
    elif skala == "1000":
        return f"{k_10rb:02d}.{b_10rb:03d}-{nlp_2500:02d}-{nlp_1000}"
    elif skala == "500":
        return f"{k_10rb:02d}.{b_10rb:03d}-{nlp_2500:02d}-{nlp_1000}-{nlp_500}"
    elif skala == "250":
        return (
            f"{k_10rb:02d}.{b_10rb:03d}-{nlp_2500:02d}-{nlp_1000}-{nlp_500}-{nlp_250}"
        )
    else:
        return "Kesalahan Penentuan skala"


def get_nlp_index(scale, x, y):
    """
    Cetak Nomor Index Sel TM3 Berdasar Skala

    argumen:
        skala   : skala peta dalam string
        x       : koordinat x dalam CRS TM-3
        y       : koordinat y dalam CRS TM-3
    output: string Nomor Index
    """

    min_x = x_origin
    min_y = y_origin
    max_x = x_origin + (56 * 6000)
    max_y = y_origin + (314 * 6000)

    if x < min_x or x > max_x or y < min_y or y > max_y:
        return "-"

    k_10rb, b_10rb = map(lambda x: x - 1, bk_10000(x, y))
    k_2500, b_2500 = map(lambda x: x - 1, bk_2500(x, y))
    k_1000, b_1000 = map(lambda x: x - 1, bk_1000(x, y))
    k_500, b_500 = map(lambda x: x - 1, bk_500(x, y))
    k_250, b_250 = map(lambda x: x - 1, bk_250(x, y))

    if scale == "10000":
        col = math.floor((x - min_x - (k_10rb * grid_10rb)) / 1000)
        row = math.floor((y - min_y - (b_10rb * grid_10rb)) / 1000)
    elif scale == "2500":
        col = math.floor((x - min_x - (k_10rb * grid_10rb + k_2500 * grid_2500)) / 250)
        row = math.floor((y - min_y - (b_10rb * grid_10rb + b_2500 * grid_2500)) / 250)
    elif scale == "1000":
        col = math.floor(
            (x - min_x - (k_10rb * grid_10rb + k_2500 * grid_2500 + k_1000 * grid_1000))
            / 100
        )
        row = math.floor(
            (y - min_y - (b_10rb * grid_10rb + b_2500 * grid_2500 + b_1000 * grid_1000))
            / 100
        )
    elif scale == "500":
        col = math.floor(
            (
                x
                - min_x
                - (
                    k_10rb * grid_10rb
                    + k_2500 * grid_2500
                    + k_1000 * grid_1000
                    + k_500 * grid_500
                )
            )
            / 50
        )
        row = math.floor(
            (
                y
                - min_y
                - (
                    b_10rb * grid_10rb
                    + b_2500 * grid_2500
                    + b_1000 * grid_1000
                    + b_500 * grid_500
                )
            )
            / 50
        )
    elif scale == "250":
        col = math.floor(
            (
                x
                - min_x
                - (
                    k_10rb * grid_10rb
                    + k_2500 * grid_2500
                    + k_1000 * grid_1000
                    + k_500 * grid_500
                    + k_250 * grid_250
                )
            )
            / 25
        )
        row = math.floor(
            (
                y
                - min_y
                - (
                    b_10rb * grid_10rb
                    + b_2500 * grid_2500
                    + b_1000 * grid_1000
                    + b_500 * grid_500
                    + b_250 * grid_250
                )
            )
            / 25
        )

    return f"{NLP_INDEX[int(col)]}{int(row + 1)}"


def export_layer_to_dxf(layers, output_path, encoding=""):
    dxf_export = QgsDxfExport()

    settings = iface.mapCanvas().mapSettings()
    # settings.setLayerStyleOverrides( QgsProject.instance().mapThemeCollection().mapThemeStyleOverrides( _yourmaptheme_ ) )
    dxf_export.setMapSettings(settings)
    dxf_export.addLayers([QgsDxfExport.DxfLayer(layer) for layer in layers])

    dxfFile = QFile(output_path)
    result = dxf_export.writeToFile(dxfFile, encoding)
    return result
