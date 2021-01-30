import abc
import pymel.core as pm
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


class DeformerManager(AbstractManager):

    @classmethod
    def is_painted(cls, deformer_node):
        return deformer_node.weightList.get(size=True) > 0

    @classmethod
    def get_deformer_data(cls, deformer_node):
        raise NotImplementedError

    def get_deformer(self, node):
        node = pm.PyNode(node)
        def_list = node.listHistory(type=self.data_type)
        return def_list[0] if def_list else None

    def list_deformers(self, under_group=None):
        deformers = []
        for deformer_node in pm.ls(type=self.data_type):
            geo_nodes = deformer_node.getGeometry()
            for geometry in geo_nodes:
                if under_group:
                    if under_group in geometry.longName().split("|"):
                        deformers.append(deformer_node)
                else:
                    deformers.append(deformer_node)
        return deformers

    def export_single(self, node):
        raise NotImplementedError

    def import_single(self, node):
        raise NotImplementedError

    def export_all(self):
        raise NotImplementedError

    def import_all(self):
        raise NotImplementedError
