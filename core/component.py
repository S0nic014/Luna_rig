import pymel.core as pm
from PySide2 import QtCore

import luna_rig
from luna import Logger
import luna.utils.enumFn as enumFn
import luna_rig.functions.nameFn as nameFn
import luna_rig.functions.outlinerFn as outlinerFn
import luna_rig.functions.animFn as animFn


class _compSignals(QtCore.QObject):
    removed = QtCore.Signal()
    attached = QtCore.Signal(object)


class Component(luna_rig.MetaRigNode):

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

    @property
    def util_nodes(self):
        nodes = self.pynode.utilNodes.listConnections(d=1)  # type: list
        return nodes

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
        if isinstance(meta_parent, luna_rig.MetaRigNode):
            meta_parent = meta_parent.pynode
        instance = super(Component, cls).create(meta_parent)  # type: Component
        instance.pynode.rename(nameFn.generate_name(name, side, suffix="meta"))
        instance.pynode.addAttr("settings", at="message", multi=1, im=0)
        instance.pynode.addAttr("utilNodes", at="message", multi=1, im=0)
        return instance

    def set_outliner_color(self, color):
        raise NotImplementedError

    def attach_to_component(self, other_comp):
        """Attach to other component

        :param other_comp: Other component
        :type other_comp: Component
        """
        if not isinstance(other_comp, Component):
            other_comp = luna_rig.MetaRigNode(other_comp)
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

    def _store_util_nodes(self, nodes):
        if not isinstance(nodes, list):
            nodes = [nodes]
        for each in nodes:
            if each not in self.util_nodes:
                each.message.connect(self.pynode.utilNodes, na=1)

    def delete_util_nodes(self):
        for util_node in self.util_nodes:
            if isinstance(util_node, luna_rig.nt.DagNode):
                if util_node.numChildren():
                    try:
                        util_node.childAtIndex(0).setParent(util_node.getParent())
                    except RuntimeError:
                        Logger.warning("Failed to parent {0} children ({1}) to {2}".format(util_node, util_node.getChildren(), util_node.getParent()))
            pm.delete(util_node)
            Logger.debug("{0}: Deleted util node {1}".format(self, util_node))


class AnimComponent(Component):

    @ classmethod
    def create(cls,
               meta_parent=None,
               side="c",
               name="anim_component",
               hook=0):  # noqa:F821
        """Create AnimComponent hierarchy in the scene and instance.

        :param meta_parent: Other Rig element to connect to, defaults to None
        :type meta_parent: AnimComponent, optional
        :param side: Component side, used for naming, defaults to "c"
        :type side: str, optional
        :param name: Component name. If list - items will be connected by underscore, defaults to "anim_component"
        :type name: str, list[str], optional
        :param hook: Point index on parent component to attach to, defaults to 0
        :type hook: int, optional
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
        instance.pynode.addAttr("controls", at="message", multi=1, im=0)
        instance.pynode.addAttr("hooks", at="message", multi=1, im=0)
        instance.pynode.addAttr("attachObject", at="message")

        # Connect hierarchy to meta
        root_grp.metaParent.connect(instance.pynode.rootGroup)
        ctls_grp.metaParent.connect(instance.pynode.ctlsGroup)
        joints_grp.metaParent.connect(instance.pynode.jointsGroup)
        parts_grp.metaParent.connect(instance.pynode.partsGroup)
        instance.set_outliner_color(17)

        return instance

    @property
    def root(self):
        node = self.pynode.rootGroup.listConnections()[0]  # type: luna_rig.nt.Transform
        return node

    @property
    def group_ctls(self):
        node = self.pynode.ctlsGroup.listConnections()[0]  # type: luna_rig.nt.Transform
        return node

    @property
    def group_joints(self):
        node = self.pynode.jointsGroup.listConnections()[0]  # type: luna_rig.nt.Transform
        return node

    @property
    def group_parts(self):
        node = self.pynode.partsGroup.listConnections()[0]  # type: luna_rig.nt.Transform
        return node

    @property
    def controls(self):
        connected_nodes = self.pynode.controls.listConnections()  # type: list[luna_rig.nt.Transform]
        all_ctls = [luna_rig.Control(node) for node in connected_nodes]
        return all_ctls

    @property
    def bind_joints(self):
        joint_list = self.pynode.bindJoints.listConnections()  # type: list[luna_rig.nt.Joint]
        return joint_list

    @property
    def ctl_chain(self):
        ctl_chain = self.pynode.ctlChain.listConnections()  # type: list[luna_rig.nt.Joint]
        return ctl_chain

    @property
    def character(self):
        connections = self.pynode.character.listConnections()
        result = luna_rig.MetaRigNode(connections[0]) if connections else None  # type: luna_rig.components.Character
        return result

    @property
    def attach_object(self):
        connections = self.pynode.attachObject.listConnections()
        result = connections[0] if connections else None  # type: luna_rig.nt.Transform
        return result

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
        :rtype: list[luna_rig.Control]
        """
        connected_nodes = self.pynode.controls.listConnections()
        all_ctls = [luna_rig.Control(node) for node in connected_nodes]
        if tag:
            taged_list = [ctl for ctl in all_ctls if ctl.tag == tag]
            return taged_list
        return all_ctls

    def select_controls(self, tag=None):
        """Select all component controls"""
        for ctl in self.list_controls(tag):
            ctl.transform.select(add=1)

    def key_controls(self, tag=None):
        """Override: key all componets controls"""
        ctls = self.list_controls(tag)
        for each in ctls:
            pm.setKeyframe(each.transform)

    def attach_to_skeleton(self):
        """Override: attach to skeleton"""
        Logger.info("{0}: Attaching to skeleton...".format(self))
        for ctl_jnt, bind_jnt in zip(self.ctl_chain, self.bind_joints):
            if bind_jnt.listConnections(type="parentConstraint"):
                Logger.info("Replacing {0} attachment to {1}".format(bind_jnt, ctl_jnt))
                pm.delete(bind_jnt.listConnections(type="parentConstraint"))
            pm.parentConstraint(ctl_jnt, bind_jnt, mo=1)

    def bake_to_skeleton(self, time_range=None, *args, **kwargs):
        """Override: bake animation to skeleton"""
        if not self.bind_joints:
            return
        if not time_range:
            time_range = animFn.get_playback_range()
        pm.bakeResults(self.bind_joints, t=time_range, simulation=True, *args, **kwargs)
        Logger.info("{0}: Baked to skeleton.".format(self))

    def bake_and_detach(self, time_range=None, *args, **kwargs):
        self.bake_to_skeleton(time_range, *args, **kwargs)
        for skel_jnt in self.bind_joints:
            pconstr = skel_jnt.listConnections(type="parentConstraint")
            pm.delete(pconstr)
        Logger.info("{0}: Detached from skeleton.".format(self))

    def bake_to_rig(self):
        """Override: reverse bake to rig"""
        pass

    def to_bind_pose(self):
        """Override: revert all controls to default values"""
        for ctl in self.controls:
            ctl.to_bind_pose()

    def remove(self):
        """Delete component from scene"""
        for child in self.meta_children:
            child.remove()
        pm.delete(self.root)
        self.delete_util_nodes()
        pm.delete(self.pynode)
        Logger.info("Removed {0}".format(self))
        self.signals.removed.emit()

    def add_hook(self, node):
        """Set given node as attach point

        :param node: Dag node
        :type node: str or pm.PyNode
        """
        node = pm.PyNode(node)
        node.message.connect(self.pynode.hooks, na=1)

    def get_hook(self, index=0):
        """Get component attach point from index

        :param index: Index for attach point, defaults to 0
        :type index: int or enumFn.Enum, optional
        :return: Attach point object.
        :rtype: pm.PyNode
        """
        if isinstance(index, enumFn.Enum):
            index = index.value

        connected_points = self.pynode.hooks.listConnections()
        try:
            point = connected_points[index]
        except IndexError:
            Logger.error("{0}: No attach point at index {1}".format(self, index))
            point = None
        return point

    def attach_to_component(self, other_comp, hook=0):
        """Attach to other AnimComponent

        :param other_comp: Component to attach to.
        :type other_comp: AnimComponent
        :param hook: Attach point index, defaults to 0
        :type hook: int, enumFn.Enum, optional
        :return: Attach object to use in derived method.
        :rtype: pm.PyNode
        """
        if not other_comp:
            return
        super(AnimComponent, self).attach_to_component(other_comp)
        # Fetch attach point from component if int
        if hook is None:
            attach_obj = None
        if isinstance(hook, str):
            attach_obj = pm.PyNode(hook)
        elif isinstance(hook, luna_rig.Control):
            attach_obj = hook.transform
        elif isinstance(hook, pm.PyNode):
            attach_obj = hook
        else:
            attach_obj = other_comp.get_hook(index=hook)
            if not attach_obj:
                Logger.error("Failed to connect {0} to {1} at point {2}".format(self, other_comp, hook))
        if attach_obj:
            attach_obj.message.connect(self.pynode.attachObject)
        Logger.info("Attached: {0} ->> {1}".format(self, other_comp))
        self.signals.attached.emit(other_comp)
        return attach_obj

    def connect_to_character(self, character_name="", parent=False):
        """Connect component to character

        :param character_name: Specific character to connect to, defaults to ""
        :type character_name: str, optional
        """
        character = None
        all_characters = luna_rig.MetaRigNode.list_nodes(luna_rig.components.Character)
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
            character = all_characters[0]  # type: luna_rig.components.Character

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
