from PyQt5.QtCore import pyqtSignal, QObject


class Item(QObject):
    changed = pyqtSignal(object)

    def __init__(self, value=None):
        super(Item, self).__init__()
        self.__value__ = value

    def update(self, value):
        if self.__value__ != value:
            self.__value__ = value
            self.changed.emit(value)

    @property
    def value(self):
        return self.__value__

    def __del__(self):
        self.changed.disconnect()

    def __repr__(self):
        return str(self.__value__)


class Memo:
    __store__ = {}

    def _create_item(self, value):
        return Item(value)

    def set(self, key, value):
        if key not in self.__store__.keys():
            self.__store__[key] = self._create_item(value)
        else:
            self.__store__[key].update(value)

        return self.__store__[key]

    def get(self, key, default=None):
        item = (
            self.__store__[key]
            if key in self.__store__.keys()
            else self.set(key, default)
        )
        return item

    def keys(self):
        return self.__store__.keys()

    def values(self):
        return self.__store__.values()


app_state = Memo()
