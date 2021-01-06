import os
from abc import ABC, abstractmethod, abstractproperty
from Luna.utils import environFn


class AbstractManager(ABC):
    def __init__(self, data_type, extension):
        self.current_asset = environFn.get_asset_var()


class DeformerManager(AbstractManager):
    def __init__(self, data_type, extension):
        super(DeformerManager, self).__init__(data_type, extension)


class DataManager(AbstractManager):
    def __init__(self, data_type, extension):
        super(DataManager, self).__init__(data_type, extension)
