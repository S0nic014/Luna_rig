import pymel.core as pm
from Luna import Logger
from Luna_rig.core import component
from Luna_rig.core import control
from Luna.static import names


class _hierachyStruct:
    def __init__(self):
        self.root_ctl = None  # type: control.Control
        self.control_rig = None  # type: pm.PyNode
        self.geometry_grp = None  # type: pm.PyNode
        self.deformation_rig = None  # type: pm.PyNode
        self.locators_grp = None  # type: pm.PyNode
        self.world_loc = None  # type: pm.PyNode


class Character(component.Component):
    def __init__(self, node):
        super(Character, self).__init__(node)
        Logger.debug(pm.listAttr(self.pynode))
        self.hierarchy = _hierachyStruct()

        if pm.hasAttr(self.pynode, "rootCtl"):
            self.hierarchy.root_ctl = control.Control(self.pynode.rootCtl.listConnections()[0])
            self.hierarchy.control_rig = self.pynode.controlRig.listConnections()[0]
            self.hierarchy.deformation_rig = self.pynode.deformationRig.listConnections()[0]
            self.hierarchy.geometry_grp = self.pynode.geometryGroup.listConnections()[0]
            self.hierarchy.locators_grp = self.pynode.locatorsGroup.listConnections()[0]
            self.hierarchy.world_loc = self.pynode.worldLocator.listConnections()[0]

    def __create__(self, side, name):
        super(Character, self).__create__(side, name)

        Logger.debug("CREATE CALL")

        # Create hierarchy nodes
        self.hierarchy.root_ctl = control.Control.create(name="character_node", side="c", offset_grp=False)
        self.hierarchy.control_rig = pm.createNode('transform', n=names.Character.control_rig.value, p=self.hierarchy.root_ctl.transform)
        self.hierarchy.deformation_rig = pm.createNode('transform', n=names.Character.deformation_rig.value, p=self.hierarchy.root_ctl.transform)
        self.hierarchy.geometry_grp = pm.createNode('transform', n=names.Character.geometry.value, p=self.hierarchy.root_ctl.transform)
        self.hierarchy.locators_grp = pm.createNode('transform', n=names.Character.locators.value, p=self.hierarchy.root_ctl.transform)
        self.hierarchy.world_loc = pm.spaceLocator(n=names.Character.world_space.value)
        pm.parent(self.hierarchy.world_loc, self.hierarchy.locators_grp)

        # Add message attrs to meta node
        self.pynode.addAttr("rootCtl", at="message")
        self.pynode.addAttr("controlRig", at="message")
        self.pynode.addAttr("deformationRig", at="message")
        self.pynode.addAttr("geometryGroup", at="message")
        self.pynode.addAttr("locatorsGroup", at="message")
        self.pynode.addAttr("worldLocator", at="message")

        # Add meta parent attrs to hierarchy nodes
        for node in [self.hierarchy.control_rig, self.hierarchy.deformation_rig, self.hierarchy.geometry_grp, self.hierarchy.locators_grp, self.hierarchy.world_loc]:
            node.addAttr("metaParent", at="message")

        # Connect to meta node
        self.hierarchy.root_ctl.transform.metaParent.connect(self.pynode.rootCtl)
        self.hierarchy.control_rig.metaParent.connect(self.pynode.controlRig)
        self.hierarchy.deformation_rig.metaParent.connect(self.pynode.deformationRig)
        self.hierarchy.geometry_grp.metaParent.connect(self.pynode.geometryGroup)
        self.hierarchy.locators_grp.metaParent.connect(self.pynode.locatorsGroup)
        self.hierarchy.world_loc.metaParent.connect(self.pynode.worldLocator)

    @staticmethod
    def create(meta_parent=None, version=1, name="character"):
        obj_instance = super(Character, Character).create(meta_parent, Character, version, name=name)  # type: Character
        return obj_instance
