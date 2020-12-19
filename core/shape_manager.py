import os
import pymel.core as pm
import pymel.api as pma

from Luna.utils import fileFn
from Luna.static import directories
from Luna_rig.functions import surfaceFn


class ShapeManager:
    SHAPES_LIB = directories.SHAPES_LIB_PATH

    @classmethod
    def get_shapes(cls, node):
        node = pm.PyNode(node)
        shape_nodes = []

    @classmethod
    def set_shape(cls, transform, shape_name, surface_transparency=0.0):
        pass

    @classmethod
    def load_shape_data(cls, shape_name):
        path = os.path.join(cls.SHAPES_LIB, shape_name + ".json")
        data = fileFn.load_json(path)
        return data

    @classmethod
    def save_shape(cls, transform, name):
        transform = pm.PyNode(transform)
        shape_list = cls.get_shapes()
        save_path = os.path.join(cls.SHAPES_LIB, name + ".json")
        for data_dict in shape_list:
            data_dict.pop("color", None)
            data_dict.pop("transparency", [0.0, 0.0, 0.0])
        fileFn.write_json(save_path, shape_list)

    @classmethod
    def set_color(cls, node, color):
        node = pm.PyNode(node)
        if isinstance(node, pm.nodetypes.Transform):
            shape_nodes = node.getShapes()
        elif isinstance(node, pm.nodetypes.Shape):
            shape_nodes = [node]

        for shape in shape_nodes:
            pass
