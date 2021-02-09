import os
import pymel.core as pm
from luna import Logger
import luna_rig
import luna.utils.fileFn as fileFn
from luna_rig.importexport import manager


class KeyPoseManager(manager.AbstractManager):
    def __init__(self):
        super(KeyPoseManager, self).__init__("pose", "json")

    @property
    def path(self):
        return self.asset.data.poses

    def get_component_dir(self, component_node):
        return os.path.join(self.path, component_node)

    def get_base_name(self, pose_name):
        return pose_name

    def get_new_file(self, node_name, pose_name):
        node_dir = self.get_component_dir(node_name)
        if not os.path.isdir(node_dir):
            os.mkdir(node_dir)
        return fileFn.get_new_versioned_file(self.get_base_name(pose_name), node_dir, extension=self.extension, full_path=True)

    def get_latest_file(self, node_name, pose_name):
        return fileFn.get_latest_file(self.get_base_name(pose_name), self.get_component_dir(node_name), extension=self.extension, full_path=True)

    def export_pose(self, component_node, controls_list, driver_ctl, pose_name):
        pose_dict = {}
        for control in controls_list:
            pose_dict[control.transform.name()] = {}
            for attr_name in ["rotate", "translate"]:
                attr_value = control.transform.attr(attr_name).get()
                if attr_value == pm.dt.Vector(0.0, 0.0, 0.0):
                    continue
                pose_dict[control.transform.name()][attr_name] = list(attr_value)
        pose_dict["driver"] = driver_ctl
        export_path = self.get_new_file(component_node.pynode.name(), pose_name)
        fileFn.write_json(export_path, data=pose_dict)
        Logger.info("Exported {0} key pose: {1}".format(component_node, export_path))

        return pose_dict

    def import_pose(self, component, pose_name, driver_value=10):
        if isinstance(component, luna_rig.AnimComponent):
            component_node = component.pynode.name()
        else:
            component_node = component
        # Import data
        latest_file = self.get_latest_file(component_node, pose_name)
        pose_dict = fileFn.load_json(latest_file)  # type:dict
        driver_ctl = pose_dict.pop("driver")
        if not pm.objExists(driver_ctl):
            Logger.error("Pose {0} driver {1} doesnt exist!".format(pose_name, driver_ctl))
            return
        # Add pose name to driver
        driver_ctl = pm.PyNode(driver_ctl)
        if not driver_ctl.hasAttr(pose_name):
            driver_ctl.addAttr(pose_name, at="float", k=True, dv=0.0, min=0, max=driver_value)

        # Create driven keys
        for transform, attr_dict in pose_dict.items():
            if not pm.objExists(transform):
                continue
            if not attr_dict:
                continue
            control = luna_rig.Control(transform)
            for attr, value_list in attr_dict.items():
                axis_dict = {attr + "X": value_list[0],
                             attr + "Y": value_list[1],
                             attr + "Z": value_list[2]}
                control.add_key_pose(axis_dict, driver_ctl.attr(pose_name), driver_value)
        Logger.info("{0}: Imported key poses: {1}".format(component, latest_file))

    def import_component_poses(self, component_node, driver_value=10):
        if isinstance(component_node, luna_rig.AnimComponent):
            component_node = component_node.pynode.name()
        if not os.path.isdir(self.get_component_dir(component_node)):
            return
        for pose_file in os.listdir(os.path.join(self.path, component_node)):
            pose_name = pose_file.split(".")[0]
            self.import_pose(component_node, pose_name, driver_value)
