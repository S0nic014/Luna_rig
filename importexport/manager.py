import abc
import luna
from luna import Logger
from luna.utils import fileFn
import luna_rig.functions.rigFn as rigFn


class AbstractManager(object):
    """Base for importing/exporting asset data
    Following members must be implemented:
    - property: path
    - method: get_base_name
    - method: get_new_file
    - method: get_latest_file
    """
    __metaclass__ = abc.ABCMeta

    def __repr__(self):
        return self.__class__.__name__

    def __init__(self, data_type, extension):
        """
        :param data_type: Deformer type. Must match Maya's nodetype.
        :type data_type: str
        :param extension: Export file extension without dot.
        :type extension: str
        :raises RuntimeError: If luna asset is not set
        """
        self.data_type = data_type  # type :str
        self.extension = extension  # type: str
        self.asset = luna.workspace.Asset.get()
        self.character = rigFn.get_build_character()
        if not self.asset:
            Logger.error("Asset is not set")
            raise RuntimeError
        self.versioned_files = fileFn.get_versioned_files(self.path, extension=self.extension)

    @abc.abstractproperty
    def path(self):
        """Path to asset sub directory. Example: self.asset.weights.skin """
        pass

    @abc.abstractmethod
    def get_base_name(self):
        """Name for versioned dictionary key"""
        pass

    @abc.abstractmethod
    def get_new_file(self):
        """Returns path to new file version"""
        pass

    @abc.abstractmethod
    def get_latest_file(self):
        """Returns path to latest versioned file"""
        pass
