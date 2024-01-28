from qgis.PyQt.QtWidgets import QFileDialog


class ImportGeomFromFile:
    def __init__(self, parent=None, *args, **kwargs):
        self.parent = parent
        self._file = None
        self._setup_file_browser()

    def _setup_file_browser(self):
        filters = "CSV (*.csv)"
        self._file_browser = QFileDialog(filter=filters)

    def _show_using_plotxy(self, file):
        self.parent.plotxy()
        with open(file, "r") as f:
            self.parent.plotxyaction.list_coords.setText(f.read())

    def show(self):
        self._file_browser.show()
        file = self._file_browser.getOpenFileName()
        if len(file) == 2 and file[0]:
            self._show_using_plotxy(file[0])
        self._file_browser.close()
