import pymel.core as pm
from Luna import Logger
from Luna.static import names
from Luna_rig.core import component
from Luna_rig.core import control
from Luna_rig.functions import attrFn
from Luna_rig.functions import outlinerFn
from Luna_rig.functions import nameFn


class _hierachyStruct:
    def __init__(self):
        self.root_ctl = None  # type: control.Control
        self.control_rig = None  # type: pm.PyNode
        self.geometry_grp = None  # type: pm.PyNode
        self.deformation_rig = None  # type: pm.PyNode
        self.locators_grp = None  # type: pm.PyNode
        self.world_loc = None  # type: pm.PyNode


class Character(component.Component):
    def __repr__(self):
        return "Character component: ({0}, version: {1})".format(self.pynode.characterName.get(), self.pynode.version.get())

    def __init__(self, node):
        """Character constructor.
        Can be used to instansiate Character object from meta network node.

        :param node: Node to instansiate from.
        :type node: str, PyNode
        """
        super(Character, self).__init__(node)
        self.hierarchy = _hierachyStruct()

        # Populate struct when pynode is properly initialized
        if pm.hasAttr(self.pynode, "rootCtl"):
            # Data struct
            name_parts = nameFn.deconstruct_name(self.pynode.name())
            self.data.name = "_".join(name_parts.name)
            self.data.side = name_parts.side
            self.data.index = name_parts.index
            # Hierachy struct
            self.hierarchy.root_ctl = control.Control(self.pynode.rootCtl.listConnections()[0])
            self.hierarchy.control_rig = self.pynode.controlRig.listConnections()[0]
            self.hierarchy.deformation_rig = self.pynode.deformationRig.listConnections()[0]
            self.hierarchy.geometry_grp = self.pynode.geometryGroup.listConnections()[0]
            self.hierarchy.locators_grp = self.pynode.locatorsGroup.listConnections()[0]
            self.hierarchy.world_loc = self.pynode.worldLocator.listConnections()[0]

        # Signals
        self.signals.created.emit()

    def __create__(self, side, name):
        """Create new character instance and hierarchy of nodes.

        :param side: Character side. Not used, will be defaulted to "char"
        :type side: str
        :param name: Character name
        :type name: str
        """
        super(Character, self).__create__(side, name)

        # Create hierarchy nodes
        self.hierarchy.root_ctl = control.Control.create(name="character_node", side="c", offset_grp=False, attributes="trs")
        self.hierarchy.root_ctl.rename(index="")
        self.hierarchy.control_rig = pm.createNode('transform', n=names.Character.control_rig.value, p=self.hierarchy.root_ctl.transform)
        self.hierarchy.deformation_rig = pm.createNode('transform', n=names.Character.deformation_rig.value, p=self.hierarchy.root_ctl.transform)
        self.hierarchy.locators_grp = pm.createNode('transform', n=names.Character.locators.value, p=self.hierarchy.root_ctl.transform)
        self.hierarchy.world_loc = pm.spaceLocator(n=names.Character.world_space.value)
        pm.parent(self.hierarchy.world_loc, self.hierarchy.locators_grp)

        # Handle geometry group
        if not pm.objExists(names.Character.geometry.value):
            self.hierarchy.geometry_grp = pm.createNode('transform', n=names.Character.geometry.value, p=self.hierarchy.root_ctl.transform)
        else:
            self.hierarchy.geometry_grp = pm.PyNode(names.Character.geometry.value)
            pm.parent(self.hierarchy.geometry_grp, self.hierarchy.root_ctl.transform)

        # Add message attrs to meta node
        self.pynode.addAttr("characterName", dt="string")
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
        self.pynode.characterName.set(name)
        self.hierarchy.root_ctl.transform.metaParent.connect(self.pynode.rootCtl)
        self.hierarchy.control_rig.metaParent.connect(self.pynode.controlRig)
        self.hierarchy.deformation_rig.metaParent.connect(self.pynode.deformationRig)
        self.hierarchy.geometry_grp.metaParent.connect(self.pynode.geometryGroup)
        self.hierarchy.locators_grp.metaParent.connect(self.pynode.locatorsGroup)
        self.hierarchy.world_loc.metaParent.connect(self.pynode.worldLocator)

        # Edit attributes
        # Merge scale to make uniform
        self.hierarchy.root_ctl.transform.addAttr("Scale", defaultValue=1.0, shortName="us", at="float", keyable=1)
        self.hierarchy.root_ctl.transform.Scale.connect(self.hierarchy.root_ctl.transform.scaleX)
        self.hierarchy.root_ctl.transform.Scale.connect(self.hierarchy.root_ctl.transform.scaleY)
        self.hierarchy.root_ctl.transform.Scale.connect(self.hierarchy.root_ctl.transform.scaleZ)

        # Visibility
        self.hierarchy.locators_grp.visibility.set(0)
        # Lock
        attrFn.lock(self.hierarchy.root_ctl.transform, ["sx", "sy", "sz"])
        # Colors
        outlinerFn.set_color(self.hierarchy.root_ctl.group, rgb=[0.6, 0.8, 0.9])

    @classmethod
    def create(cls, meta_parent=None, version=1, name="character"):
        """Creation method, will call base AnimComponent.create and then __create__.

        :param meta_parent: Not used, defaults to None
        :type meta_parent: Component, optional
        :param version: Character version, defaults to 1
        :type version: int, optional
        :param name: Character name, defaults to "character"
        :type name: str, optional
        :return: New character instance.
        :rtype: Character
        """
        obj_instance = super(Character, cls).create(meta_parent, version, name=name, side="char")  # type: Character
        return obj_instance

    def list_geometry(self):
        """List geometry nodes under geometry group.

        :return: List of nodes.
        :rtype: list[PyNode]
        """
        result = []
        for child in self.hierarchy.geometry_grp.listRelatives(ad=1):
            if isinstance(child, pm.nodetypes.Mesh):
                result.append(child)

        return result

    @classmethod
    def find(cls, name):
        result = []
        for character_node in cls.list_nodes(of_type=cls):
            if character_node.pynode.characterName.get() == name:
                result.append(character_node)
        if len(result) == 1:
            return result[0]
        return result
