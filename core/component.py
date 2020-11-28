import pymel.core as pm
from PySide2 import QtCore

from Luna import Logger
from Luna_rig.functions import nameFn
from Luna_rig.core.meta import MetaRigNode
from Luna_rig.core.control import Control


class _dataStruct:
    def __init__(self):
        self.side = None  # type: str
        self.name = None  # type: str
        self.index = None  # type: str


class _groupStruct:
    def __init__(self):
        self.root = None
        self.ctls = None
        self.joints = None
        self.parts = None


class _compSignals(QtCore.QObject):
    created = QtCore.Signal()
    removed = QtCore.Signal()


class Component(MetaRigNode):

    def __repr__(self):
        return "{0}: {1}".format(self.as_str(name_only=True), self.pynode.name())

    def __new__(cls, node=None):
        return object.__new__(cls, node)

    def __init__(self, node):
        super(Component, self).__init__(node)
        self.data = _dataStruct()
        self.signals = _compSignals()

    def __eq__(self, other):
        return self.pynode == other.pynode

    def __create__(self, side, name):
        """Override
        Base creation method. Called after object instance is created in "create" method.

        :param side: Component side.
        :type side: str
        :param name: Component name
        :type name: str
        """

        # Store data in a struct
        self.data.side = side
        self.data.name = name

        self.pynode.rename(nameFn.generate_name(name, side, suffix="meta"))

    @ classmethod
    def create(cls, meta_parent, version, side="c", name="component"):
        """Creates instance of component

        :param meta_parent: Other Component to parent to.
        :type meta_parent: Component
        :param version: Component version.
        :type version: int
        :param side: Component side, defaults to "c"
        :type side: str, optional
        :param name: Component name, defaults to "component"
        :type name: str, optional
        :return: New component instance.
        :rtype: Component
        """
        if isinstance(meta_parent, MetaRigNode):
            meta_parent = meta_parent.pynode

        obj_instance = super(Component, cls).create(meta_parent, version)  # type: Component

        # Store data in a struct
        obj_instance.pynode.rename(nameFn.generate_name(name, side, suffix="meta"))
        obj_instance.data.side = side
        obj_instance.data.name = name

        return obj_instance

    def get_name(self):
        """Get component name parts

        :return: Name struct with members: {side, name, index, suffix}
        :rtype: nameStruct
        """
        return nameFn.deconstruct_name(self.pynode)

    def get_meta_children(self, of_type=None):
        """Get list of connected meta children

        :param of_type: Only list children of specific type, defaults to None
        :type of_type: class, optional
        :return: List of meta children instances
        :rtype: list[MetaRigNode]
        """
        result = []
        if self.pynode.hasAttr("metaChildren"):
            connections = self.pynode.metaChildren.listConnections()
            if connections:
                children = [MetaRigNode(connection_node) for connection_node in connections if pm.hasAttr(connection_node, "metaRigType")]
                if not of_type:
                    result = children
                else:
                    if isinstance(of_type, str):
                        result = [child for child in children if of_type in child.as_str()]
                    else:
                        result = [child for child in children if isinstance(child, of_type)]

        return result

    def get_meta_parent(self):
        """Get instance of meta parent

        :return: Meta parent Component instance.
        :rtype: Component
        """
        result = None
        connections = self.pynode.metaParent.listConnections()
        if connections:
            result = MetaRigNode(connections[0])
        return result

    def attach_to_component(self, other_comp):
        if not isinstance(other_comp, Component):
            other_comp = MetaRigNode(other_comp)
        if other_comp.pynode not in self.pynode.metaParent.listConnections():
            self.set_meta_parent(other_comp)

    def connect_to_character(self, character_name):
        pass


class AnimComponent(Component):

    def __init__(self, node):
        super(AnimComponent, self).__init__(node)
        self.group = _groupStruct()

        # Having rootGroup means node is properly initialized
        if pm.hasAttr(self.pynode, "rootGroup"):
            # Recover data
            # Group struct
            self.group.root = self.pynode.rootGroup.listConnections()[0]
            self.group.ctls = self.pynode.ctlsGroup.listConnections()[0]
            self.group.joints = self.pynode.jointsGroup.listConnections()[0]
            self.group.parts = self.pynode.partsGroup.listConnections()[0]
            # Data struct
            name_parts = nameFn.deconstruct_name(self.pynode.name())
            self.data.name = "_".join(name_parts.name)
            self.data.side = name_parts.side
            self.data.index = name_parts.index

    @ classmethod
    def create(cls,
               meta_parent=None,
               version=1,
               side="c",
               name="anim_component",
               attach_point_index=0):  # noqa:F821
        """Create AnimComponent hierarchy in the scene and instance.

        :param meta_parent: Other Rig element to connect to, defaults to None
        :type meta_parent: AnimComponent, optional
        :param version: Component version, defaults to 1
        :type version: int, optional
        :param side: Component side, used for naming, defaults to "c"
        :type side: str, optional
        :param name: Component name. If list - items will be connected by underscore, defaults to "anim_component"
        :type name: str, list[str], optional
        :return: New instance of AnimComponent.
        :rtype: AnimComponent
        """

        obj_instance = super(AnimComponent, cls).create(meta_parent, version, side, name)  # type: AnimComponent
        # Create hierarchy
        obj_instance.group.root = pm.group(n=nameFn.generate_name(obj_instance.data.name, obj_instance.data.side, suffix="comp"), em=1)
        obj_instance.group.ctls = pm.group(n=nameFn.generate_name(obj_instance.data.name, obj_instance.data.side, suffix="ctls"), em=1, p=obj_instance.group.root)
        obj_instance.group.joints = pm.group(n=nameFn.generate_name(obj_instance.data.name, obj_instance.data.side, suffix="jnts"), em=1, p=obj_instance.group.root)
        obj_instance.group.parts = pm.group(n=nameFn.generate_name(obj_instance.data.name, obj_instance.data.side, suffix="parts"), em=1, p=obj_instance.group.root)
        for node in [obj_instance.group.root, obj_instance.group.ctls, obj_instance.group.joints, obj_instance.group.parts]:
            node.addAttr("metaParent", at="message")

        # Add message attrs
        obj_instance.pynode.addAttr("rootGroup", at="message")
        obj_instance.pynode.addAttr("ctlsGroup", at="message")
        obj_instance.pynode.addAttr("jointsGroup", at="message")
        obj_instance.pynode.addAttr("partsGroup", at="message")
        obj_instance.pynode.addAttr("bindJoints", at="message", multi=1, im=0)
        obj_instance.pynode.addAttr("attachPoints", at="message", multi=1, im=0)
        obj_instance.pynode.addAttr("controls", at="message", multi=1, im=0)

        # Connect hierarchy to meta
        obj_instance.group.root.metaParent.connect(obj_instance.pynode.rootGroup)
        obj_instance.group.ctls.metaParent.connect(obj_instance.pynode.ctlsGroup)
        obj_instance.group.joints.metaParent.connect(obj_instance.pynode.jointsGroup)
        obj_instance.group.parts.metaParent.connect(obj_instance.pynode.partsGroup)

        return obj_instance

    def remove(self):
        """Delete component from scene"""
        pm.delete(self.group.root)
        self.signals.removed.emit()

    def get_controls(self):
        """Get list of component controls.

        :return: List of all component controls.
        :rtype: list[Control]
        """
        connected_nodes = self.pynode.controls.listConnections()
        return [Control(node) for node in connected_nodes]

    def get_bind_joints(self):
        """Get list of component bind joints.

        :return: List of component bind joints.
        :rtype: list[PyNode]
        """
        return self.pynode.bindJoints.listConnections()

    def select_controls(self):
        """Select all component controls"""
        controls = self.get_controls()
        for ctl in controls:
            ctl.transform.select(add=1)

    def key_controls(self):
        """Override: key all componets controls"""
        pass

    def attach_to_skeleton(self):
        """Override: attach to skeleton"""
        pass

    def bake_to_skeleton(self):
        """Override: bake animation to skeleton"""
        pass

    def bake_and_detach(self):
        pass

    def bake_to_rig(self):
        """Override: reverse bake to rig"""
        pass

    def to_default_pose(self):
        """Override: revert all controls to default values"""
        pass

    def add_attach_point(self, node):
        node = pm.PyNode(node)
        node.message.connect(self.pynode.attachPoints, na=1)

    def get_attach_point(self, index=0):
        connected_points = self.pynode.attachPoints.listConnections()
        try:
            point = connected_points[index]
        except IndexError:
            Logger.error("{0}: No attach point at index {1}".format(self, index))
            point = 0
        return point

    def attach_to_component(self, other_comp, attach_point_index=0):
        """Attach to other component.

        :param other_comp: Component to attach to.
        :type other_comp: Component
        """
        super(AnimComponent, self).attach_to_component(other_comp)
        # TODO: add parenting/constraining?

    def connect_to_character(self, character_name="", parent=False):
        """Connect component to character

        :param character_name: Specific character to connect to, defaults to ""
        :type character_name: str, optional
        """
        character = None
        all_characters = MetaRigNode.list_nodes("Character")
        if not all_characters:
            Logger.error("No characters found in the scene!")
            return

        if character_name:
            for char_node in all_characters:
                if char_node.pynode.characterName.get() == character_name:
                    character = char_node
                    break
            if character is None:
                Logger.error("No character: {0} found!".format(character_name))
                return
        else:
            character = all_characters[0]

        self.pynode.message.connect(character.pynode.metaChildren, na=1)
        if parent:
            pm.parent(self.group.root, character.hierarchy.control_rig)
