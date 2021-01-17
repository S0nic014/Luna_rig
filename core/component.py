import pymel.core as pm
from pymel.core import nodetypes
from PySide2 import QtCore

from Luna import Logger
from Luna.utils import enumFn
from Luna_rig.functions import nameFn
from Luna_rig.core.meta import MetaRigNode
from Luna_rig.core.control import Control


class _compSignals(QtCore.QObject):
    created = QtCore.Signal()
    removed = QtCore.Signal()


class Component(MetaRigNode):

    def __repr__(self):
        return "{0}({1})".format(self.as_str(name_only=True), self.pynode.name())

    def __new__(cls, node=None):
        return object.__new__(cls, node)

    def __init__(self, node):
        super(Component, self).__init__(node)
        self.signals = _compSignals()

    def __eq__(self, other):
        return self.pynode == other.pynode

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
        obj_instance.pynode.rename(nameFn.generate_name(name, side, suffix="meta"))

        return obj_instance

    def attach_to_component(self, other_comp):
        if not isinstance(other_comp, Component):
            other_comp = MetaRigNode(other_comp)
        if other_comp.pynode not in self.pynode.metaParent.listConnections():
            self.set_meta_parent(other_comp)


class AnimComponent(Component):

    @ classmethod
    def create(cls,
               meta_parent=None,
               version=1,
               side="c",
               name="anim_component",
               attach_point=0):  # noqa:F821
        """Create AnimComponent hierarchy in the scene and instance.

        :param meta_parent: Other Rig element to connect to, defaults to None
        :type meta_parent: AnimComponent, optional
        :param version: Component version, defaults to 1
        :type version: int, optional
        :param side: Component side, used for naming, defaults to "c"
        :type side: str, optional
        :param name: Component name. If list - items will be connected by underscore, defaults to "anim_component"
        :type name: str, list[str], optional
        :param attach_point: Point index on parent component to attach to, defaults to 0
        :type attach_point: int, optional
        :return: New instance of AnimComponent.
        :rtype: AnimComponent
        """

        obj_instance = super(AnimComponent, cls).create(meta_parent, version, side, name)  # type: AnimComponent
        # Create hierarchy
        root_grp = pm.group(n=nameFn.generate_name(obj_instance.name, obj_instance.side, suffix="comp"), em=1)
        ctls_grp = pm.group(n=nameFn.generate_name(obj_instance.name, obj_instance.side, suffix="ctls"), em=1, p=root_grp)
        joints_grp = pm.group(n=nameFn.generate_name(obj_instance.name, obj_instance.side, suffix="jnts"), em=1, p=root_grp)
        parts_grp = pm.group(n=nameFn.generate_name(obj_instance.name, obj_instance.side, suffix="parts"), em=1, p=root_grp)
        for node in [root_grp, ctls_grp, joints_grp, parts_grp]:
            node.addAttr("metaParent", at="message")

        # Add message attrs
        obj_instance.pynode.addAttr("character", at="message")
        obj_instance.pynode.addAttr("rootGroup", at="message")
        obj_instance.pynode.addAttr("ctlsGroup", at="message")
        obj_instance.pynode.addAttr("jointsGroup", at="message")
        obj_instance.pynode.addAttr("partsGroup", at="message")
        obj_instance.pynode.addAttr("bindJoints", at="message", multi=1, im=0)
        obj_instance.pynode.addAttr("ctlChain", at="message", multi=1, im=0)
        obj_instance.pynode.addAttr("attachPoints", at="message", multi=1, im=0)
        obj_instance.pynode.addAttr("controls", at="message", multi=1, im=0)

        # Connect hierarchy to meta
        root_grp.metaParent.connect(obj_instance.pynode.rootGroup)
        ctls_grp.metaParent.connect(obj_instance.pynode.ctlsGroup)
        joints_grp.metaParent.connect(obj_instance.pynode.jointsGroup)
        parts_grp.metaParent.connect(obj_instance.pynode.partsGroup)

        return obj_instance

    @property
    def root(self):
        node = self.pynode.rootGroup.listConnections()[0]  # type: nodetypes.Transform
        return node

    @property
    def group_ctls(self):
        node = self.pynode.ctlsGroup.listConnections()[0]  # type: nodetypes.Transform
        return node

    @property
    def group_joints(self):
        node = self.pynode.jointsGroup.listConnections()[0]  # type: nodetypes.Transform
        return node

    @property
    def group_parts(self):
        node = self.pynode.partsGroup.listConnections()[0]  # type: nodetypes.Transform
        return node

    @property
    def controls(self):
        connected_nodes = self.pynode.controls.listConnections()
        all_ctls = [Control(node) for node in connected_nodes]
        return all_ctls

    @property
    def bind_joints(self):
        joint_list = self.pynode.bindJoints.listConnections()  # type: list[nodetypes.Joint]
        return joint_list

    @property
    def ctl_chain(self):
        ctl_chain = self.pynode.ctlChain.listConnections()  # type: list[nodetypes.Joint]
        return ctl_chain

    @property
    def character(self):
        connections = self.pynode.character.listConnections()
        if connections:
            return MetaRigNode(connections[0])
        else:
            return None

    def _store_bind_joints(self, joint_chain):
        for jnt in joint_chain:
            jnt.metaParent.connect(self.pynode.bindJoints, na=1)

    def _store_ctl_chain(self, joint_chain):
        for jnt in joint_chain:
            jnt.metaParent.connect(self.pynode.ctlChain, na=1)

    def _store_controls(self, ctl_list):
        for ctl in ctl_list:
            ctl.transform.metaParent.connect(self.pynode.controls, na=1)

    def list_controls(self, tag=None):
        """Get list of component controls. Extra attr for tag sorting.

        :return: List of all component controls.
        :rtype: list[Control]
        """
        connected_nodes = self.pynode.controls.listConnections()
        all_ctls = [Control(node) for node in connected_nodes]
        if tag:
            taged_list = [ctl for ctl in all_ctls if ctl.tag == tag]
            return taged_list
        return all_ctls

    def select_controls(self):
        """Select all component controls"""
        for ctl in self.controls:
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

    def remove(self):
        """Delete component from scene"""
        pm.delete(self.root)
        self.signals.removed.emit()

    def add_attach_point(self, node):
        """Set given node as attach point

        :param node: Dag node
        :type node: str or pm.PyNode
        """
        node = pm.PyNode(node)
        node.message.connect(self.pynode.attachPoints, na=1)

    def get_attach_point(self, index=0):
        """Get component attach point from index

        :param index: Index for attach point, defaults to 0
        :type index: int or enumFn.Enum, optional
        :return: Attach point object.
        :rtype: pm.PyNode
        """
        if isinstance(index, enumFn.Enum):
            index = index.value

        connected_points = self.pynode.attachPoints.listConnections()
        try:
            point = connected_points[index]
        except IndexError:
            Logger.error("{0}: No attach point at index {1}".format(self, index))
            point = None
        return point

    def attach_to_component(self, other_comp, attach_point=0):
        """Attach to other AnimComponent

        :param other_comp: Component to attach to.
        :type other_comp: AnimComponent
        :param attach_point: Attach point index, defaults to 0
        :type attach_point: int, enumFn.Enum, optional
        :return: Attach object to use in derived method.
        :rtype: pm.PyNode
        """
        super(AnimComponent, self).attach_to_component(other_comp)
        attach_obj = other_comp.get_attach_point(index=attach_point)
        if not attach_obj:
            Logger.error("Failed to connect {0} to {1} at point {2}".format(self, other_comp, attach_point))

        return attach_obj

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

        self.pynode.character.connect(character.pynode.metaChildren, na=1)
        if parent:
            pm.parent(self.root, character.control_rig)
