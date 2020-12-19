
import pymel.core as pm
from Luna import Logger
from Luna.static import colors
from Luna_rig.functions import nameFn
from Luna_rig.functions import attrFn


class _dataStruct:
    def __init__(self):
        self.name = None  # type: str
        self.side = None  # type: str


class Control():
    def __repr__(self):
        return "Control({0}), Offsets: {1}".format(self.transform, self.offset_list)

    def __init__(self, node):
        self.data = _dataStruct()

        self.transform = pm.PyNode(node)
        self.group = pm.PyNode(self.transform.name().replace("ctl", "grp"))
        self.tag_node = self.transform.listConnections(t="controller")[0] or None
        self.joint = None
        self.offset = None
        self.offset_list = []

        # Find joint
        child_joints = self.tag_node.joint.listConnections()
        if child_joints:
            self.joint = child_joints[0]

        # Find offsets
        self.offset_list = self.tag_node.offset.listConnections()
        if self.offset_list:
            self.offset = self.offset_list[0]

        # Populate data struct
        name_parts = nameFn.deconstruct_name(self.transform)
        self.data.name = "_".join(name_parts.name)
        self.data.side = name_parts.side

        Logger.debug("""========Control instance========
                tree:
                -group: {0}
                -offset_list: {1}
                -offset: {2}
                -transform: {3}
                -joint: {4}
                -tag_node: {5}

                data:
                -side: {6}
                -name: {7}
                        """.format(self.group, self.offset_list, self.offset, self.transform, self.joint, self.tag_node,
                                   self.data.side, self.data.name))

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
        instance.data.name = name
        instance.data.side = side
        instance.set_shape(shape)
        instance.set_color(color)

        # Cleanup
        instance.lock_attrib(exclude_attr=attributes, channel_box=False)

        return instance

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
            result = conn[0]  # type: pm.PyNode

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
        Logger.debug("TODO: {0} - inserting offset with extra name: {1}".format(self.transform, extra_name))
        if self.offset_list:
            parent = self.offset_list[-1]
        else:
            parent = self.group
        Logger.debug(parent)
        new_offset = pm.createNode("transform", n=nameFn.generate_name([self.data.name, extra_name], side=self.data.side, suffix="ofs"), p=parent)
        pm.parent(self.transform, new_offset)
        self.offset_list.append(new_offset)
        new_offset.addAttr("metaParent", at="message")
        new_offset.metaParent.connect(self.tag_node.offset, na=1)
        return new_offset

    def set_shape(self, name):
        """Set control's shape

        :param name: Shape name
        :type name: str
        """
        Logger.debug("TODO: {0} - setting shape to {1}".format(self.transform, name))

    def set_color(self, color):
        """Set control color

        :param color: New color
        :type color: int or enumFn.Enum
        """
        if not color:
            color = colors.SideColor[self.data.side].value
        self.data.color = color
        Logger.debug("TODO: {0} - setting color to {1}".format(self.transform, color))

    def add_space(self, name, target):
        """Add new space

        :param name: Space name (will be used by enum attribute)
        :type name: str
        :param target: target space
        :type target: str or pm.nodetypes.Transform
        """
        Logger.debug("TODO: {0} - adding {1} space with named {2}".format(self.transform, target, name))

    def add_world_space(self):
        """Uses add space method to add space to hidden world locator
        """
        Logger.debug("TODO: {0} - adding world space".format(self.transform))
        self.add_space("World", "world_loc")

    def mirror_shape(self):
        """Mirrors control's shape
        """
        Logger.debug("TODO: {0} - mirroing shape...")

    def add_wire(self, source):
        """Adds staight line curve connecting source object and controls' transform

        :param source: Wire source object
        :type source: str or pm.nodetypes.Transform
        """
        Logger.debug("TODO: {0} - adding wire...")

    def get_color(self):
        """Get current control color"""
        Logger.debug("TODO: {0} - getting ctl color...")

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
        for node in [self.group, self.transform, self.joint] + self.offset_list:
            nameFn.rename(node, side, name, index, suffix)


if __name__ == "__main__":
    pm.newFile(f=1)
    new_ctl1 = Control.create(name="leg_fk", side="r", tag="fk", joint=True)
    new_ctl2 = Control.create(name="leg_fk", side="r", tag="fk", parent=new_ctl1)
