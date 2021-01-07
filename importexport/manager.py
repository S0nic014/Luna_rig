import os
import abc
from Luna.utils import environFn


class AbstractManager(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, data_type, extension):
        self.current_asset = environFn.get_asset_var()
        self.current_character = environFn.get_character_var()
        self.data_type = data_type
        self.extension = extension


class DeformerManager(AbstractManager):
    def __init__(self, data_type, extension):
        super(DeformerManager, self).__init__(data_type, extension)


class DataManager(AbstractManager):
    def __init__(self, data_type, extension):
        super(DataManager, self).__init__(data_type, extension)
