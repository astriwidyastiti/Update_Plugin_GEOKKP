from qgis.core import QgsProject, QgsWkbTypes
from qgis.utils import iface
from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtWidgets import QMessageBox, QAction, QLabel, QWidget, QCheckBox

SCOPE = "Topol"
KEY_LAYER_1 = "layer1"
KEY_LAYER_2 = "layer2"
KEY_TEST_COUNT = "testCount"
KEY_TEST_NAME = "testname"

PLUGIN_NOT_FOUND_ERROR_MESSAGE = "Plugin Topology Checker belum diinstal / diaktifkan"

COVERAGE_ALL = "all"
COVERAGE_EXTENT = "extent"

# POINT
RULES_MUST_BE_COVERED_BY = "must be covered by"
MUST_BE_COVERED_BY_ENDPOINTS_OF = "must be covered by endpoints of"
RULES_MUST_BE_INSIDE = "must be inside"

# LINE
RULES_ENDPOINTS_MUST_BE_COVERED_BY = "endpoints must be covered by"
RULES_MUST_NOT_HAVE_DANGLES = "must not have dangles"
RULES_MUST_NOT_HAVE_PSEUDOS = "must not have pseudos"

# POLYGON
RULES_MUST_CONTAIN = "must contain"
RULES_MUST_NOT_HAVE_GAPS = "must not have gaps"
RULES_MUST_NOT_OVERLAPS = "must not overlap"
RULES_MUST_NOT_OVERLAP_WITH = "must not overlap with"

# COMMON
RULES_MUST_NOT_HAVE_DUPLICATES = "must not have duplicates"
RULES_MUST_NOT_HAVE_INVALID_GEOMETRIES = "must not have invalid geometries"
RULES_MUST_NOT_HAVE_MULTIPART_GEOMETRIES = "must not have multi-part geometries"


class Topology:
    def __init__(self):
        self._app = iface.mainWindow()
        self._project = QgsProject.instance()
        self._action_topo_plugin = None
        self._action_topo_validate_all = None
        self._action_topo_validate_extent = None

        self._ready = False

        self._setup()

    def _setup(self):
        topo_plugin = self._app.findChild(QObject, "qgis_plugin_topolplugin")

        if not topo_plugin:
            QMessageBox.critical(None, "Error", PLUGIN_NOT_FOUND_ERROR_MESSAGE)
            return

        topo_action = topo_plugin.findChild(QAction, "mQActionPointer")
        if not topo_action:
            return
        topo_action.trigger()
        topo_panel = self._app.findChild(QWidget, "checkDock")
        if not topo_panel:
            return
        self._action_topo_validate_all = topo_panel.findChild(
            QAction, "actionValidateAll"
        )
        self._action_topo_validate_extent = topo_panel.findChild(
            QAction, "actionValidateExtent"
        )
        self._check_topo_show_error = topo_panel.findChild(
            QCheckBox, "mToggleRubberband"
        )
        self._label_topo_status = topo_panel.findChild(QLabel, "mComment")

        self._ready = True

    def get_test_count(self):
        test_count, exists = self._project.readEntry(SCOPE, KEY_TEST_COUNT)
        return 0 if not exists else int(test_count)

    def _write_rule(self, id_layer1, test_name, id_layer2="No layer"):
        test_count = self.get_test_count()

        key_layer1 = self._build_key(KEY_LAYER_1, test_count)
        key_layer2 = self._build_key(KEY_LAYER_2, test_count)
        key_test_name = self._build_key(KEY_TEST_NAME, test_count)

        self._project.writeEntry(SCOPE, KEY_TEST_COUNT, test_count + 1)
        self._project.writeEntry(SCOPE, key_layer1, id_layer1)
        self._project.writeEntry(SCOPE, key_layer2, id_layer2)
        self._project.writeEntry(SCOPE, key_test_name, test_name)
        iface.projectRead.emit()

    def _build_key(self, name, index):
        return f"{name}_{index}"

    def add_rules(self, layer1, test_name, layer2=None):
        id_layer1 = layer1.id()
        id_layer2 = layer2.id() if layer2 else "No layer"
        self._write_rule(id_layer1=id_layer1, id_layer2=id_layer2, test_name=test_name)

    def reset_rules(self):
        test_count = self.get_test_count()
        for i in range(0, test_count):
            key_layer1 = self._build_key(KEY_LAYER_1, test_count)
            key_layer2 = self._build_key(KEY_LAYER_2, test_count)
            key_test_name = self._build_key(KEY_TEST_NAME, test_count)

            self._project.removeEntry(SCOPE, key_layer1)
            self._project.removeEntry(SCOPE, key_layer2)
            self._project.removeEntry(SCOPE, key_test_name)
            self._project.removeEntry(SCOPE, KEY_TEST_COUNT)

    def _execute(self, action_name):
        if not self._ready:
            self._setup()
        action = getattr(self, action_name)
        if action:
            action.trigger()

    def show_panel(self):
        self._execute("_action_topo_plugin")

    def validate(self, coverage=COVERAGE_ALL):
        if coverage == COVERAGE_EXTENT:
            self._execute("_action_topo_validate_extent")
        else:
            self._execute("_action_topo_validate_all")

    def is_topology_correct(self):
        if not self._ready:
            self._setup()
        if not self._label_topo_status:
            return False, 0

        try:
            status = self._label_topo_status.text()
            num_error = int(status.split(" ")[0])
            return num_error == 0, num_error
        except ValueError:
            return False, 0


_topology = Topology()


def quick_check_topology(layer):
    _topology.reset_rules()

    geometry_type = QgsWkbTypes.displayString(layer.wkbType()).lower()

    _topology.add_rules(layer, RULES_MUST_NOT_HAVE_DUPLICATES)
    _topology.add_rules(layer, RULES_MUST_NOT_HAVE_INVALID_GEOMETRIES)

    if "polygon" in geometry_type:
        _topology.add_rules(layer, RULES_MUST_NOT_HAVE_GAPS)
        _topology.add_rules(layer, RULES_MUST_NOT_OVERLAPS)
    elif "line" in geometry_type:
        _topology.add_rules(layer, RULES_MUST_NOT_HAVE_DANGLES)
        _topology.add_rules(layer, RULES_MUST_NOT_HAVE_PSEUDOS)

    print(_topology._ready)
    _topology.validate()
    print(_topology._ready)
    is_topo_correct = _topology.is_topology_correct()
    return is_topo_correct
