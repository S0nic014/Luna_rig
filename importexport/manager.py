import abc
import pymel.core as pm
from Luna.utils import environFn


class AbstractManager(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def data_type(self):
        pass

    @abc.abstractproperty
    def extension(self):
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
    def __init__(self):
        super(DeformerManager, self).__init__()
        self.asset = environFn.get_asset_var()
        self.character = environFn.get_character_var()
        if not self.asset:
            Logger.error("Asset is not set")
            raise RuntimeError

    @classmethod
    def is_painted(cls, deformer_node):
        return deformer_node.weightList.get(size=True) > 0

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
        pass

    def import_single(self, node):
        pass

    def export_all(self):
        pass

    def import_all(self):
        pass
