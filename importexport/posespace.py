import pymel.core as pm
import luna_rig
from luna import Logger
import luna.utils.fileFn as fileFn
from luna_rig.importexport import manager as manager_base
from luna_rig.importexport import BlendShapeManager


class PsdManager(manager_base.AbstractManager):
    def __init__(self):
        super(PsdManager, self).__init__("psd", "pose")

    @property
    def path(self):
        return self.asset.data.psd

    def get_base_name(self):
        return self.asset.name

    def get_latest_file(self):
        return fileFn.get_latest_file(self.get_base_name(), self.path, extension=self.extension, full_path=True)

    def get_new_file(self):
        return fileFn.get_new_versioned_file(self.get_base_name(), self.path, extension=self.extension, full_path=True)

    def export_all(self):
        interpolators = pm.ls(typ="poseInterpolator")
        if not interpolators:
            Logger.warning("No pose interpolators found in the scene.")
            return False
        # Export pose blendshapes
        pose_blendshapes = []
        for pose_node in interpolators:
            connected_bs_nodes = pose_node.output.listConnections(s=1, type="blendShape")
            for bs_node in connected_bs_nodes:
                if bs_node not in pose_blendshapes:
                    pose_blendshapes.append()
        bs_manager = BlendShapeManager()
        for bs_node in pose_blendshapes:
            if not bs_node.name().endswith("_pose"):
                bs_node.rename(bs_node.name() + "_pose")
            bs_manager.export_single(bs_node)
        # Export interpolators
        export_path = self.get_new_file()
        pm.poseInterpolator(interpolators, e=1, ex=export_path)
        Logger.info("Exported pose interpolators: {0}".format(export_path))
        return export_path

    def import_all(self):
        interpolator_file = self.get_latest_file()
        pm.poseInterpolator(im=interpolator_file)
        for interpolator_shape in pm.ls(typ="poseInterpolator"):
            driver = interpolator_shape.getTransform().driver.listConnections()[0]
            driver_parent_component = luna_rig.MetaRigNode.get_connected_metanode(driver)
            if driver_parent_component:
                pm.parent(interpolator_shape.getTransform(), driver_parent_component.character.util_grp)
        Logger.info("Imported PSD interpolator: {0}".format(interpolator_file))
