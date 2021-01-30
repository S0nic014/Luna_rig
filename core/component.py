import pymel.core as pm
from pymel.core import nodetypes
from PySide2 import QtCore

from luna import Logger
from luna.utils import enumFn
from luna_rig.functions import nameFn
from luna_rig.functions import outlinerFn
from luna_rig.core.meta import MetaRigNode
from luna_rig.core.control import Control


class _compSignals(QtCore.QObject):
    removed = QtCore.Signal()
    attached = QtCore.Signal(object)


class Component(MetaRigNode):

    def __new__(cls, node=None):
        return object.__new__(cls, node)

    def __init__(self, node):
        super(Component, self).__init__(node)
        self.signals = _compSignals()

    @property
    def settings(self):
        """Component controls attrs to export/import

        :return: Dictionary of {attr: value}
        :rtype: dict
        """
        attr_dict = {}
        for connected_attr in self.pynode.settings.listConnections(d=1, plugs=1):
            attr_dict[str(connected_attr)] = connected_attr.get()
        return attr_dict

    @ classmethod
    def create(cls, meta_parent, side="c", name="component"):
        """Creates instance of component

        :param meta_parent: Other Component to parent to.
        :type meta_parent: Component
        :param side: Component side, defaults to "c"
        :type side: str, optional
        :param name: Component name, defaults to "component"
        :type name: str, optional
        :return: New component instance.
        :rtype: Component
        """
        Logger.info("Building {0}({1}_{2})...".format(cls.as_str(name_only=True), side, name))
        if isinstance(meta_parent, MetaRigNode):
            meta_parent = meta_parent.pynode
        instance = super(Component, cls).create(meta_parent)  # type: Component
        instance.pynode.rename(nameFn.generate_name(name, side, suffix="meta"))
        instance.pynode.addAttr("settings", at="message", multi=1, im=0)
        return instance

    def set_outliner_color(self, color):
        raise NotImplementedError

    def attach_to_component(self, other_comp):
        """Attach to other component

        :param other_comp: Other component
        :type other_comp: Component
        """
        if not isinstance(other_comp, Component):
            other_comp = MetaRigNode(other_comp)
        if other_comp.pynode not in self.pynode.metaParent.listConnections():
            self.set_meta_parent(other_comp)

    def _store_settings(self, attr):
        """Store given attribute as component setting

        :param attr: Node attribute
        :type attr: pymel.core.Attribute
        """
        # if not attr.isConnectedTo(self.pynode.settings, checkLocalArray=True, checkOtherArray=True):
        if attr not in self.pynode.settings.listConnections(d=1, plugs=1):
            attr.connect(self.pynode.settings, na=1)


class AnimComponent(Component):

    @ classmethod
    def create(cls,
               meta_parent=None,
               side="c",
               name="anim_component",
               attach_point=0):  # noqa:F821
        """Create AnimComponent hierarchy in the scene and instance.

        :param meta_parent: Other Rig element to connect to, defaults to None
        :type meta_parent: AnimComponent, optional
        :param side: Component side, used for naming, defaults to "c"
        :type side: str, optional
        :param name: Component name. If list - items will be connected by underscore, defaults to "anim_component"
        :type name: str, list[str], optional
        :param attach_point: Point index on parent component to attach to, defaults to 0
        :type attach_point: int, optional
        :return: New instance of AnimComponent.
        :rtype: AnimComponent
        """

        instance = super(AnimComponent, cls).create(meta_parent, side, name)  # type: AnimComponent
        # Create hierarchy
        root_grp = pm.group(n=nameFn.generate_name(instance.name, instance.side, suffix="comp"), em=1)
        ctls_grp = pm.group(n=nameFn.generate_name(instance.name, instance.side, suffix="ctls"), em=1, p=root_grp)
        joints_grp = pm.group(n=nameFn.generate_name(instance.name, instance.side, suffix="jnts"), em=1, p=root_grp)
        parts_grp = pm.group(n=nameFn.generate_name(instance.name, instance.side, suffix="parts"), em=1, p=root_grp)
        for node in [root_grp, ctls_grp, joints_grp, parts_grp]:
            node.addAttr("metaParent", at="message")

        # Add message attrs
        instance.pynode.addAttr("character", at="message")
        instance.pynode.addAttr("rootGroup", at="message")
        instance.pynode.addAttr("ctlsGroup", at="message")
        instance.pynode.addAttr("jointsGroup", at="message")
        instance.pynode.addAttr("partsGroup", at="message")
        instance.pynode.addAttr("bindJoints", at="message", multi=1, im=0)
        instance.pynode.addAttr("ctlChain", at="message", multi=1, im=0)
        instance.pynode.addAttr("attachPoints", at="message", multi=1, im=0)
        instance.pynode.addAttr("controls", at="message", multi=1, im=0)

        # Connect hierarchy to meta
        root_grp.metaParent.connect(instance.pynode.rootGroup)
        ctls_grp.metaParent.connect(instance.pynode.ctlsGroup)
        joints_grp.metaParent.connect(instance.pynode.jointsGroup)
        parts_grp.metaParent.connect(instance.pynode.partsGroup)
        instance.set_outliner_color(17)

        return instance

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

    def set_outliner_color(self, color):
        outlinerFn.set_color(self.root, color)

    def _store_bind_joints(self, joint_chain):
        for jnt in joint_chain:
            if jnt not in self.pynode.bindJoints.listConnections(d=1):
                jnt.metaParent.connect(self.pynode.bindJoints, na=1)

    def _store_ctl_chain(self, joint_chain):
        for jnt in joint_chain:
            if jnt not in self.pynode.ctlChain.listConnections(d=1):
                jnt.metaParent.connect(self.pynode.ctlChain, na=1)

    def _store_controls(self, ctl_list):
        for ctl in ctl_list:
            if ctl.transform not in self.pynode.controls.listConnections(d=1):
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
        for ctl_jnt, bind_jnt in zip(self.ctl_chain, self.bind_joints):
            pm.parentConstraint(ctl_jnt, bind_jnt)

    def bake_to_skeleton(self):
        """Override: bake animation to skeleton"""
        pass

    def bake_and_detach(self):
        pass

    def bake_to_rig(self):
        """Override: reverse bake to rig"""
        pass

    def to_bind_pose(self):
        """Override: revert all controls to default values"""
        for ctl in self.controls:
            ctl.to_bind_pose()

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
        if not other_comp:
            return
        super(AnimComponent, self).attach_to_component(other_comp)
        # Fetch attach point from component if int
        if isinstance(attach_point, str):
            attach_obj = pm.PyNode(attach_point)
        elif isinstance(attach_point, Control):
            attach_obj = attach_point.transform
        elif isinstance(attach_point, pm.PyNode):
            attach_obj = attach_point
        else:
            attach_obj = other_comp.get_attach_point(index=attach_point)
        if not attach_obj:
            Logger.error("Failed to connect {0} to {1} at point {2}".format(self, other_comp, attach_point))
        self.signals.attached.emit(other_comp)
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

    def scale_controls(self, scale_dict):
        if self.character:
            clamped_size = self.character.clamped_size
        else:
            clamped_size = 1.0

        for ctl, factor in scale_dict.items():
            ctl.scale(clamped_size, factor=factor)
