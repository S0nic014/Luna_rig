import abc
from luna import Logger
from luna.utils import environFn
from luna.utils import fileFn


class AbstractManager(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, data_type, extension):
        self.data_type = data_type  # type :str
        self.extension = extension  # type: str
        self.asset = environFn.get_asset_var()
        self.character = environFn.get_character_var()
        if not self.asset:
            Logger.error("Asset is not set")
            raise RuntimeError
        self.versioned_files = fileFn.get_versioned_files(self.path, extension=self.extension)

    @abc.abstractproperty
    def path(self):
        pass

    @abc.abstractmethod
    def get_base_name(self):
        pass

    @abc.abstractmethod
    def get_new_file(self):
        pass

    @abc.abstractmethod
    def get_latest_file(self):
        pass
