import os
from abc import ABC, abstractmethod, abstractproperty
from Luna.utils import environFn


class AbstractManager(ABC):
    def __init__(self, data_type, extension):
        current_asset = environFn.get_asset_var()
