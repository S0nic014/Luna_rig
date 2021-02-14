import pymel.core as pm
from luna import Logger
from luna import static
from luna.utils import fileFn
import luna_rig
from luna_rig.importexport import manager
import luna_rig.functions.deformerFn as deformerFn


class BlendShapeManager(manager.AbstractManager):

    def __init__(self):
        super(BlendShapeManager, self).__init__("blendShape", "shape")

    @property
    def path(self):
        return self.asset.data.blendshapes

    def get_base_name(self, geo_name, bs_name):
        return "{0}-{1}".format(geo_name, bs_name)

    def get_latest_file(self, base_name, full_path=False):
        return fileFn.get_latest_file(base_name, self.path, extension=self.extension, full_path=full_path)

    def get_new_file(self, geo_name, bs_name):
        return fileFn.get_new_versioned_file(self.get_base_name(geo_name, bs_name), self.path, extension=self.extension, full_path=True)

    def export_single(self, node):
        node = pm.PyNode(node)  # type:  luna_rig.nt.BlendShape
        if not isinstance(node, luna_rig.nt.BlendShape):
            Logger.error("{0} is not a blendShape node.".format(node))
            return False
        export_path = self.get_new_file(node.getGeometry()[0], node.name())
        try:
            node.export(export_path)
            Logger.info("{0}: Exported blendshape {1}".format(self, export_path))
            return export_path
        except RuntimeError:
            Logger.exception("{0}: Failed to export blendshape {1}".format(self, node))
            return False

    def export_all(self, under_group=static.CharacterMembers.geometry.value):
        export_list = []
        export_list = deformerFn.list_deformers(self.data_type, under_group=under_group)
        for shape in export_list:
            self.export_single(shape)

    def import_single(self, full_name):
        latest_path = self.get_latest_file(full_name, full_path=True)
        if not latest_path:
            Logger.warning("{0}:No saved blendshape found {1}".format(self, full_name))
            return False
        # Find existing geometry
        geometry, shape_name = self.get_latest_file(full_name, full_path=False).split(".")[0].split("-")
        if not pm.objExists(geometry):
            Logger.warning("{0}: Geometry {1} for shape {2} no longer exists, skipping...".format(self, geometry, shape_name))
            return False
        # Check if blendshape already exists and create one if not.
        geometry = pm.PyNode(geometry)  # type: luna_rig.nt.Shape
        if shape_name not in [str(node) for node in geometry.listHistory(type=self.data_type)]:
            shape_node = pm.blendShape(geometry, n=shape_name, foc=1)  # type: luna_rig.nt.BlendShape
        else:
            shape_node = pm.PyNode(shape_name)  # type:  luna_rig.nt.BlendShape
        # Import data
        try:
            pm.blendShape(shape_node, e=1, ip=latest_path)
            Logger.info("{0}: Imported blendshape {1}".format(self, latest_path))
            return True
        except RuntimeError:
            Logger.exception("{0}: Failed to import blendshape {1}".format(self, latest_path))
            return False

    def import_all(self):
        for full_name in self.versioned_files.keys():
            self.import_single(full_name)


if __name__ == "__main__":
    bs_manager = BlendShapeManager()
    bs_manager.export_all()
