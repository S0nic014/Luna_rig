import pymel.core as pm
from pymel.core import nodetypes
from Luna import Logger
from Luna.static import names
from Luna_rig.core import component
from Luna_rig.core import control
from Luna_rig.functions import attrFn
from Luna_rig.functions import outlinerFn
from Luna_rig.functions import rigFn


class Character(component.Component):
    def __repr__(self):
        return "Character component: ({0})".format(self.pynode.characterName.get())

    def __init__(self, node):
        """Character constructor.
        Can be used to instansiate Character object from meta network node.

        :param node: Node to instansiate from.
        :type node: str, PyNode
        """
        super(Character, self).__init__(node)
        # Signals
        self.signals.created.emit()

    @classmethod
    def create(cls, meta_parent=None, name="character"):
        """Creation method.

        :param meta_parent: Not used, defaults to None
        :type meta_parent: Component, optional
        :param name: Character name, defaults to "character"
        :type name: str, optional
        :return: New character instance.
        :rtype: Character
        """
        obj_instance = super(Character, cls).create(meta_parent, name=name, side="char")  # type: Character
        # Create main members
        root_ctl = control.Control.create(name="character_node",
                                          side="c",
                                          offset_grp=False,
                                          attributes="trs",
                                          shape="character_node",
                                          tag="root")
        root_ctl.rename(index="")
        control_rig = pm.createNode('transform', n=names.Character.control_rig.value, p=root_ctl.transform)  # type: nodetypes.Transform
        deformation_rig = pm.createNode('transform', n=names.Character.deformation_rig.value, p=root_ctl.transform)  # type: nodetypes.Transform
        locators_grp = pm.createNode('transform', n=names.Character.locators.value, p=root_ctl.transform)  # type: nodetypes.Transform
        world_locator = pm.spaceLocator(n=names.Character.world_space.value)  # type: nodetypes.Locator
        pm.parent(world_locator, locators_grp)

        # Handle geometry group
        if not pm.objExists(names.Character.geometry.value):
            geometry_grp = pm.createNode('transform', n=names.Character.geometry.value, p=root_ctl.transform)
        else:
            geometry_grp = pm.PyNode(names.Character.geometry.value)
            pm.parent(geometry_grp, root_ctl.transform)

        # Add message attrs to meta node
        obj_instance.pynode.addAttr("characterName", dt="string")
        obj_instance.pynode.addAttr("rootCtl", at="message")
        obj_instance.pynode.addAttr("controlRig", at="message")
        obj_instance.pynode.addAttr("deformationRig", at="message")
        obj_instance.pynode.addAttr("geometryGroup", at="message")
        obj_instance.pynode.addAttr("locatorsGroup", at="message")
        obj_instance.pynode.addAttr("worldLocator", at="message")

        # Add meta parent attrs to nodes
        for node in [control_rig, deformation_rig, geometry_grp, locators_grp, world_locator]:
            node.addAttr("metaParent", at="message")

        # Connect to meta node
        obj_instance.pynode.characterName.set(name)
        root_ctl.transform.metaParent.connect(obj_instance.pynode.rootCtl)
        control_rig.metaParent.connect(obj_instance.pynode.controlRig)
        deformation_rig.metaParent.connect(obj_instance.pynode.deformationRig)
        geometry_grp.metaParent.connect(obj_instance.pynode.geometryGroup)
        locators_grp.metaParent.connect(obj_instance.pynode.locatorsGroup)
        world_locator.metaParent.connect(obj_instance.pynode.worldLocator)

        # Edit attributes
        # Merge scale to make uniform
        root_ctl.transform.addAttr("Scale", defaultValue=1.0, shortName="us", at="float", keyable=1)
        root_ctl.transform.Scale.connect(root_ctl.transform.scaleX)
        root_ctl.transform.Scale.connect(root_ctl.transform.scaleY)
        root_ctl.transform.Scale.connect(root_ctl.transform.scaleZ)

        # Fit root control size
        scaleF = 0.8
        clamped_size = max(obj_instance.get_size(axis="y") * 0.1, obj_instance.get_size(axis="x"))
        for shape in obj_instance.root_ctl.transform.getShapes():
            pm.scale(shape + ".cv[0:1000]", [scaleF * clamped_size, scaleF * clamped_size, scaleF * clamped_size])

        # Visibility
        locators_grp.visibility.set(0)
        # Lock
        attrFn.lock(root_ctl.transform, ["sx", "sy", "sz"])
        # Colors
        outlinerFn.set_color(root_ctl.group, rgb=[0.6, 0.8, 0.9])
        return obj_instance

    @ property
    def root_ctl(self):
        return control.Control(self.pynode.rootCtl.listConnections()[0])

    @ property
    def control_rig(self):
        node = self.pynode.controlRig.listConnections()[0]  # type: nodetypes.Transform
        return node

    @ property
    def deformation_rig(self):
        node = self.pynode.deformationRig.listConnections()[0]  # type: nodetypes.Transform
        return node

    @ property
    def geometry_grp(self):
        node = self.pynode.geometryGroup.listConnections()[0]  # type: nodetypes.Transform
        return node

    @ property
    def locators_grp(self):
        node = self.pynode.locatorsGroup.listConnections()[0]  # type: nodetypes.Transform
        return node

    @ property
    def world_locator(self):
        node = self.pynode.worldLocator.listConnections()[0]  # type:nodetypes.Locator
        return node

    def list_geometry(self):
        """List geometry nodes under geometry group.

        :return: List of nodes.
        :rtype: list[PyNode]
        """
        result = []
        for child in self.geometry_grp.listRelatives(ad=1):
            if isinstance(child, pm.nodetypes.Mesh):
                result.append(child)

        return result

    def list_controls(self, tag=None):
        ctls = []
        comp_list = self.get_meta_children()
        for comp in comp_list:
            if isinstance(comp, component.AnimComponent):
                ctls += comp.list_controls(tag)
        return ctls

    def list_bind_joints(self):
        joint_list = []
        comp_list = self.get_meta_children()
        for comp in comp_list:
            if isinstance(comp, component.AnimComponent):
                joint_list += comp.bind_joints
        return joint_list

    def get_size(self, axis="y"):
        bounding_box = pm.exactWorldBoundingBox(self.geometry_grp, ii=True)
        if axis == "z":
            return bounding_box[3] - bounding_box[0]
        elif axis == "y":
            return bounding_box[4] - bounding_box[1]
        elif axis == "z":
            return bounding_box[5] - bounding_box[2]

    def save_bind_pose(self):
        Logger.info("Writing controls bind poses...")
        counter = 0
        ctls = rigFn.list_controls()
        for each in ctls:
            each.write_bind_pose()
            counter += 1
        Logger.info("Written {0} bind poses.".format(counter))

    def to_bind_pose(self):
        for ctl in self.list_controls():
            ctl.to_bind_pose()

    def create_controls_set(self, name="controls_set", tag=None):
        result = pm.sets([ctl.transform for ctl in self.list_controls(tag)], n=name)  # type: nodetypes.ObjectSet
        return result

    def create_joints_set(self, name="bind_joints_set"):
        result = pm.sets(self.list_bind_joints(), n=name)  # type: nodetypes.ObjectSet
        return result

    @ classmethod
    def find(cls, name):
        result = []
        for character_node in cls.list_nodes(of_type=cls):
            if character_node.pynode.characterName.get() == name:
                result.append(character_node)
        if len(result) == 1:
            return result[0]
        return result
