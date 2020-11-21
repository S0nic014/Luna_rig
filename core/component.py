import pymel.core as pm
from Luna import Logger
from Luna_rig.functions import nameFn
from Luna_rig.core.meta import MetaRigNode
from Luna_rig.core.control import Control


class _dataStruct:
    def __init__(self):
        self.side = None  # type: str
        self.name = None  # type: str
        self.fullname = None  # type: str


class _groupStruct:
    def __init__(self):
        self.root = None
        self.ctls = None
        self.joints = None
        self.parts = None


class Component(MetaRigNode):
    def __new__(cls, node=None):
        return object.__new__(cls, node)

    def __init__(self, node):
        super(Component, self).__init__(node)
        self.data = _dataStruct()

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

    @ staticmethod
    def create(meta_parent, meta_type, version, side="c", name="component"):
        """Creates instance of component

        :param meta_parent: Other Component to parent to.
        :type meta_parent: Component
        :param meta_type: Component class.
        :type meta_type: Class
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

        obj_instance = super(Component, Component).create(meta_parent, meta_type, version)  # type: Component
        obj_instance.__create__(side, name)

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
            connections = self.pynode.listConnections()
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
            self.pynode.metaParent.connect(other_comp.pynode.metaChildren, na=1)

    def connect_to_character(self, character):
        pass


class AnimComponent(Component):

    def __init__(self, node):
        super(AnimComponent, self).__init__(node)
        self.group = _groupStruct()

        if pm.hasAttr(self.pynode, "rootGroup"):
            self.group.root = self.pynode.rootGroup.listConnections()[0]
            self.group.ctls = self.pynode.ctlsGroup.listConnections()[0]
            self.group.joints = self.pynode.jointsGroup.listConnections()[0]
            self.group.parts = self.pynode.partsGroup.listConnections()[0]

    def __create__(self, side, name):
        """Override
        Base creation method. Called after object instance is created in "create" method.

        :param side: Component side.
        :type side: str
        :param name: Component name
        :type name: str
        """
        super(AnimComponent, self).__create__(side, name)

        # Create hierarchy
        self.group.root = pm.group(n=nameFn.generate_name(self.data.name, self.data.side, suffix="grp"), em=1)
        self.group.ctls = pm.group(n=nameFn.generate_name(self.data.name, self.data.side, suffix="ctls"), em=1, p=self.group.root)
        self.group.joints = pm.group(n=nameFn.generate_name(self.data.name, self.data.side, suffix="jnts"), em=1, p=self.group.root)
        self.group.parts = pm.group(n=nameFn.generate_name(self.data.name, self.data.side, suffix="parts"), em=1, p=self.group.root)
        for node in [self.group.root, self.group.ctls, self.group.joints, self.group.parts]:
            node.addAttr("metaParent", at="message")

        # Add message attrs
        self.pynode.addAttr("rootGroup", at="message")
        self.pynode.addAttr("ctlsGroup", at="message")
        self.pynode.addAttr("jointsGroup", at="message")
        self.pynode.addAttr("partsGroup", at="message")
        self.pynode.addAttr("bindJoints", at="message", multi=1, im=0)
        self.pynode.addAttr("controls", at="message", multi=1, im=0)

        # Connect hierarchy to meta
        self.group.root.metaParent.connect(self.pynode.rootGroup)
        self.group.ctls.metaParent.connect(self.pynode.ctlsGroup)
        self.group.joints.metaParent.connect(self.pynode.jointsGroup)
        self.group.parts.metaParent.connect(self.pynode.partsGroup)

    @staticmethod
    def create(meta_parent=None,
               meta_type=None,
               version=1,
               side="c",
               name="anim_component"):  # noqa:F821
        """Create AnimComponent hierarchy in the scene and instance.

        :param meta_parent: Other Rig element to connect to, defaults to None
        :type meta_parent: AnimComponent, optional
        :param meta_type: Component class if None will use generic AnimComponent, defaults to None
        :type meta_type: class, optional
        :param version: Component version, defaults to 1
        :type version: int, optional
        :param side: Component side, used for naming, defaults to "c"
        :type side: str, optional
        :param name: Component name. If list - items will be connected by underscore, defaults to "anim_component"
        :type name: str, list[str], optional
        :return: New instance of AnimComponent.
        :rtype: AnimComponent
        """

        if not meta_type:
            meta_type = AnimComponent
        obj_instance = super(AnimComponent, AnimComponent).create(meta_parent, meta_type, version, side, name)  # type: AnimComponent

        return obj_instance

    def remove(self):
        """Delete component from scene"""
        pm.delete(self.group.root)

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

    def attach_to_component(self, other_comp):
        """Attach to other component.

        :param other_comp: Component to attach to.
        :type other_comp: Component
        """
        super(AnimComponent, self).attach_to_component(other_comp)
        # TODO: add parenting/constraining?

    def connect_to_character(self, character_name=""):
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
        pm.parent(self.group.root, character.hierarchy.control_rig)
