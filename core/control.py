
import json
import pymel.core as pm
from pymel.core import nodetypes
from Luna import Logger
from Luna.static import colors
from Luna.static import names
from Luna_rig.functions import nameFn
from Luna_rig.functions import attrFn
from Luna_rig.functions import transformFn
from Luna_rig.core.shape_manager import ShapeManager
from Luna_rig.core import meta
reload(transformFn)


class Control(object):
    def __repr__(self):
        return "Control({0})".format(self.transform)

    def __init__(self, node):
        self.transform = pm.PyNode(node)

    @classmethod
    def create(cls,
               name="control_obj",
               side="c",
               object_to_match=None,
               parent=None,
               attributes="tr",
               delete_match_object=False,
               match_pos=True,
               match_orient=True,
               match_pivot=True,
               color=None,
               offset_grp=True,
               joint=False,
               shape="cube",
               tag="",
               scale=1.0):
        """Control creation method

        :param name: Control name, defaults to "control_obj"
        :type name: str, optional
        :param side: Control side, defaults to "c"
        :type side: str, optional
        :param object_to_match: Transform object to match, defaults to None
        :type object_to_match: pm.nodetypes.Transform, optional
        :param parent: Object to parent to, defaults to None
        :type parent: pm.nodetypes.Transform, optional
        :param attributes: Attributes to leave unlocked and visible, defaults to "tr"
        :type attributes: str, optional
        :param delete_match_object: If guide object should be deleted after matched, defaults to False
        :type delete_match_object: bool, optional
        :param match_pos: If Control position should be matched to guide object, defaults to True
        :type match_pos: bool, optional
        :param match_orient: If Control rotation values should be matched to guide object, defaults to True
        :type match_orient: bool, optional
        :param match_pivot: If Control pivot should match guide object, defaults to True
        :type match_pivot: bool, optional
        :param color: Control color, if not set will use color based on side., defaults to None
        :type color: int, enumFn.Enum, optional
        :param offset_grp: If offset group should be created, defaults to True
        :type offset_grp: bool, optional
        :param joint: If control joint should be created, defaults to False
        :type joint: bool, optional
        :param shape: Desired control shape from shape lib, defaults to "cube"
        :type shape: str, optional
        :param tag: Additional tag to set on tag node, defaults to ""
        :type tag: str, optional
        :param scale: Control scale, defaults to 1.0
        :type scale: float, optional
        :return: Control instance
        :rtype: Control
        """
        # TODO: Implement scaling

        # Group
        offset_node = None
        ctl_joint = None
        if isinstance(parent, Control):
            parent = parent.transform
        temp_parent = parent

        group_node = pm.createNode('transform', n=nameFn.generate_name(name, side, suffix="grp"), p=temp_parent)
        temp_parent = group_node
        if object_to_match:
            pm.matchTransform(group_node, object_to_match, pos=match_pos, rot=match_orient, piv=match_pivot)
            if delete_match_object:
                pm.delete(object_to_match)
        # Offset
        if offset_grp:
            offset_node = pm.createNode('transform', n=nameFn.generate_name(name, side, suffix="ofs"), p=temp_parent)
            temp_parent = offset_node

        # Transform
        transform_node = pm.createNode('transform', n=nameFn.generate_name(name, side, suffix="ctl"), p=temp_parent)
        transform_node.addAttr("bindPose", dt="string", keyable=False)
        transform_node.bindPose.set(json.dumps({}))
        transform_node.bindPose.lock()
        temp_parent = transform_node

        # Joint
        if joint:
            ctl_joint = pm.createNode('joint', n=nameFn.generate_name([name], side, suffix="cjnt"), p=temp_parent)
            ctl_joint.visibility.set(0)

        # Tag node
        pm.controller(transform_node)
        tag_node = transform_node.listConnections(t="controller")[0]
        tag_node.addAttr("group", at="message")
        tag_node.addAttr("offset", at="message", multi=1, im=0)
        tag_node.addAttr("joint", at="message")
        tag_node.addAttr("tag", dt="string")
        tag_node.tag.set(tag)

        # Add meta parent attribs
        for node in [group_node, offset_node, transform_node, ctl_joint]:
            if node:
                node.addAttr("metaParent", at="message")

        # Connect to tag node
        group_node.metaParent.connect(tag_node.group)
        if parent:
            parent.message.connect(tag_node.parent)
        if offset_node:
            offset_node.metaParent.connect(tag_node.offset, na=1)
        if ctl_joint:
            ctl_joint.metaParent.connect(tag_node.joint)

        # Create instance
        instance = Control(transform_node)
        instance.shape = shape
        instance.color = color

        # Cleanup
        instance.lock_attrib(exclude_attr=attributes, channel_box=False)

        return instance

    @property
    def name(self):
        """Name part of control's name

        :return: Name
        :rtype: str
        """
        name_parts = nameFn.deconstruct_name(self.transform)
        name = "_".join(name_parts.name)
        return name

    @property
    def side(self):
        """Control side as string.

        :return: Side
        :rtype: str
        """
        return nameFn.deconstruct_name(self.transform).side

    @property
    def index(self):
        """Index value of control as string

        :return: Index
        :rtype: str
        """
        return nameFn.deconstruct_name(self.transform).index

    @property
    def tag(self):
        """Value of tag_node.tag attribute

        :return: Tag text
        :rtype: str
        """
        value = self.tag_node.tag.get()  # type: str
        return value

    @property
    def tag_node(self):
        """Controller node

        :return: Control tag node as instance.
        :rtype: nodetypes.Controller
        """
        node = self.transform.listConnections(t="controller")[0]  # type: nodetypes.Controller
        return node

    @property
    def group(self):
        """Control's root group

        :return: Group
        :rtype: nodetypes.Transform
        """
        node = self.tag_node.group.listConnections()[0]  # type: nodetypes.Transform
        return node

    @property
    def joint(self):
        """Joint parented under Control.transform

        :return: Joint
        :rtype: nodetypes.Joint
        """
        result = None  # type: nodetypes.Joint
        child_joints = self.tag_node.joint.listConnections()
        if child_joints:
            result = child_joints[0]  # type: nodetypes.Joint
        return result

    @property
    def offset(self):
        """Get offset above transform node

        :return: Offset node
        :rtype: nodetypes.Transform
        """
        all_offsets = self.offset_list
        result = None  # type: nodetypes.Transform
        if all_offsets:
            result = all_offsets[-1]  # type: nodetypes.Transform
        else:
            result = None  # type: nodetypes.Transform
        return result

    @property
    def offset_list(self):
        """List of controls offsets. Newly inserted offsets are appended at the end of the list.

        :return: List of transform nodes
        :rtype: list, nodetypes.Transform
        """
        offsets = self.tag_node.offset.listConnections()  # type: list
        return offsets

    @property
    def color(self):
        """Control color as color index

        :return: Control color.
        :rtype: int
        """
        return ShapeManager.get_color(self.transform)

    @color.setter
    def color(self, value):
        """Set control color by passing color index

        :param value: Color index
        :type value: int
        """
        if not value:
            value = colors.SideColor[self.side].value
        ShapeManager.set_color(self.transform, value)

    @property
    def shape(self):
        """Control shape as dictionary

        :return: Control shape.
        :rtype: dict
        """
        return ShapeManager.get_shapes(self.transform)

    @shape.setter
    def shape(self, name):
        """Set control shape by passing shape name.

        :param name: Shape name
        :type name: str
        """
        ShapeManager.set_shape_from_lib(self.transform, name)

    @property
    def bind_pose(self):
        """Control bind pose as dictionary

        :return: Bind pose.
        :rtype: dict
        """
        pose_dict = {}
        if pm.hasAttr(self.transform, "bindPose"):
            pose_dict = json.loads(self.transform.bindPose.get())
        else:
            Logger.warning("{0}: missing bind pose!".format(self))
        return pose_dict

    @property
    def pose(self):
        pose_dict = {}
        attributes = pm.listAttr(self.transform, k=1, u=1) + pm.listAttr(self.transform, cb=1, u=1)
        for attr in attributes:
            if not pm.listConnections("{0}.{1}".format(self.transform, attr), s=1, d=0):
                pose_dict[attr] = pm.getAttr("{0}.{1}".format(self.transform, attr))
        return pose_dict

    @property
    def connected_component(self):
        """Get component this control is connected to via metaParent attribute of Control.transform

        :return: [description]
        :rtype: [type]
        """
        result = None
        connections = self.transform.metaParent.listConnections()
        for node in connections:
            if not meta.MetaRigNode.is_metanode(node):
                Logger.warning("Strange connection on {0}.metaParent: {1}".format(self, node))
                continue
            result = meta.MetaRigNode(node)
        return result

    @property
    def character(self):
        comp = self.connected_component
        if not comp:
            Logger.warning("{0}: Failed to find connected component!".format(self))
            return None
        if "Character" in comp.as_str():
            return comp
        return comp.character

    @classmethod
    def is_control(cls, node):
        """Test if specified node is a controller

        :param node: Node to test
        :type node: str or nodetypes.Transform
        :return: Test result (0 or 1)
        :rtype: int
        """
        result = pm.controller(node, q=1, ic=1)  # type: int
        return result

    def print_debug(self):
        """Print control debug information"""
        Logger.debug("""========Control instance========
                tree:
                -group: {0}
                -offset_list: {1}
                -offset: {2}
                -transform: {3}
                -joint: {4}
                -tag_node: {5}
                -shape: {6}
                -bind pose {7}

                data:
                -side: {8}
                -name: {9}
                        """.format(self.group, self.offset_list, self.offset, self.transform, self.joint, self.tag_node, self.shape, self.bind_pose,
                                   self.side, self.name))

    def set_parent(self, parent):
        """Set control parent

        :param parent: Parent to set, if None - will be parented to world.
        :type parent: pm.PyNode
        """
        if not parent:
            self.tag_node.parent.disconnect()
            pm.parent(self.group, w=1)
            return

        if isinstance(parent, str):
            parent = pm.PyNode(parent)

        if isinstance(parent, Control):
            parent = parent.transform

        pm.parent(self.group, parent)
        parent.message.connect(self.tag_node.parent, f=1)

    def get_parent(self):
        """Get current parent

        :return: Parent node
        :rtype: pm.PyNode
        """
        result = None
        conn = self.tag_node.parent.listConnections()
        if conn:
            result = conn[0]  # type: nodetypes.Transform

        return result

    def lock_attrib(self, exclude_attr, channel_box=False):
        """Lock attributes on transform node

        :param exclude_attr: Attributes to leave unlocked
        :type exclude_attr: list
        :param channel_box: If locked attributes should be present in channel box, defaults to False
        :type channel_box: bool, optional
        """
        to_lock = ['tx', 'ty', 'tz',
                   'rx', 'ry', 'rz',
                   'sx', 'sy', 'sz',
                   'v']
        exclude_attr = list(exclude_attr)

        for attr in exclude_attr:
            if attr in list("trs"):
                for axis in "xyz":
                    to_lock.remove(attr + axis)
            else:
                to_lock.remove(attr)

        attrFn.lock(self.transform, to_lock, channel_box)
        Logger.debug("{0} - locked attributes: {1}".format(self.transform, to_lock))

    def insert_offset(self, extra_name="extra"):
        """Inserts extra ofset node and inbetween transform and last offset node present.

        :param extra_name: name to add to new offset node, defaults to "extra"
        :type extra_name: str, optional
        :return: Created node
        :rtype: pm.PyNode
        """
        Logger.debug("{0} - Inserting offset with extra name: {1}".format(self.transform, extra_name))
        if self.offset_list:
            parent = self.offset_list[-1]
        else:
            parent = self.group
        if extra_name:
            new_name = "_".join([self.name, extra_name])
        new_offset = pm.createNode("transform", n=nameFn.generate_name(new_name, side=self.side, suffix="ofs"), p=parent)  # type: nodetypes.Transform
        pm.parent(self.transform, new_offset)
        new_offset.addAttr("metaParent", at="message")
        new_offset.metaParent.connect(self.tag_node.offset, na=1)
        Logger.debug("Updated {0}".format(self))
        return new_offset

    def mirror_shape(self):
        """Mirrors control's shape
        """
        # TODO: Mirror control shape
        Logger.debug("{0} - mirroing shape...")

    def add_space(self, name, target):
        """Add new space

        :param name: Space name (will be used by enum attribute)
        :type name: str
        :param target: target space
        :type target: str or pm.nodetypes.Transform
        """
        # TODO: Addspace
        Logger.debug("{0} - adding {1} space with named {2}".format(self, target, name))

    def add_world_space(self):
        """Uses add space method to add space to hidden world locator
        """
        # TODO: Add world space
        self.add_space("World", names.Character.world_space.value)

    def add_wire(self, source):
        """Adds staight line curve connecting source object and controls' transform

        :param source: Wire source object
        :type source: str or pm.nodetypes.Transform
        """
        # TODO: Add wire
        Logger.debug("{0} - adding wire line to {1}".format(self, source))

    def rename(self, side=None, name=None, index=None, suffix=None):
        """Rename control member nodes

        :param side: New side, defaults to None
        :type side: str, optional
        :param name: New name, defaults to None
        :type name: str, optional
        :param index: New index, defaults to None
        :type index: int, optional
        :param suffix: New suffix, defaults to None
        :type suffix: str, optional
        """
        old_name = self.name
        for node in [self.group, self.transform, self.joint]:
            nameFn.rename(node, side, name, index, suffix)
        for node in self.offset_list:
            if name:
                name_parts = nameFn.deconstruct_name(node).name
                extra_parts = [substr for substr in name_parts if substr not in old_name.split("_")]
                name = "_".join([name] + extra_parts)
            nameFn.rename(node, side, name, index, suffix)

    def write_bind_pose(self):
        """Writes current control pose to bindPose attribute on Control.transform"""
        if not pm.hasAttr(self.transform, "bindPose"):
            self.transform.addAttr("bindPose", dt="string", keyable=False)
            self.transform.bindPose.set(json.dumps(self.pose))
            self.transform.bindPose.lock()
        else:
            self.transform.bindPose.unlock()
            self.transform.bindPose.set(json.dumps(self.pose))
            self.transform.bindPose.lock()
        Logger.debug("Bind pose written for {0}".format(self))

    def to_bind_pose(self):
        """Reset control to pose stored in bindPose attribute"""
        self.set_pose(self.bind_pose)

    def set_pose(self, attr_dict):
        """Set attributes from dict

        :param attr_dict: Dictionary of pairs attr:value
        :type attr_dict: dict
        """
        for attr, value in attr_dict.items():
            if self.transform.hasAttr(attr):
                pm.setAttr("{0}.{1}".format(self.transform, attr), value)
            else:
                Logger.warning("Missing attribute {0}.{1}".format(self.transform, attr))

    def find_opposite(self):
        if self.side not in ["l", "r"]:
            return None
        opposite_transform = "{0}_{1}_{2}_{3}".format(names.OppositeSide[self.side].value, self.name, self.index, "ctl")
        if pm.objExists(opposite_transform):
            return Control(opposite_transform)
        else:
            Logger.info("{0}: No opposite control found.".format(self))
            return None

    def mirror_pose_from_opposite(self, across="YZ", space=names.Character.world_space.value, behavior=True):
        opposite_ctl = self.find_opposite()
        if not opposite_ctl:
            return
        pm.matchTransform(self.transform, opposite_ctl.transform)
        transformFn.mirror_xform(transforms=self.transform, across=across, behaviour=behavior, space=space)

    def mirror_pose_to_opposite(self, across="YZ", space=names.Character.world_space.value, behavior=True):
        opposite_ctl = self.find_opposite()
        if not opposite_ctl:
            return
        pm.matchTransform(opposite_ctl.transform, self.transform)
        transformFn.mirror_xform(transforms=opposite_ctl.transform, across=across, behaviour=behavior, space=space)
