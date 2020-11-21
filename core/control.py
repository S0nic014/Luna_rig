
import pymel.core as pm
from Luna.static import colors
from Luna_rig.functions import nameFn
from Luna import Logger


class _dataStruct:
    def __init__(self):
        self.name = None  # type: str
        self.side = None  # type: str


class Control():
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

    @staticmethod
    def create(name="control_obj",
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
               scale=1.0):

        # Group
        offset_node = None
        ctl_joint = None
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
            ctl_joint = pm.createNode('joint', n=nameFn.generate_name([name, "ctl"], side, suffix="jnt"), p=temp_parent)
            ctl_joint.visibility.set(0)

        # Tag node
        pm.controller(transform_node)
        tag_node = transform_node.listConnections(t="controller")[0]
        Logger.debug(tag_node)
        tag_node.addAttr("group", at="message")
        tag_node.addAttr("offset", at="message", multi=1, im=0)
        tag_node.addAttr("joint", at="message")

        # Create instance
        instance = Control(transform_node)
        instance.data.name = name
        instance.data.side = side
        instance.set_shape(shape)
        instance.set_color(color)

        # Cleanup
        instance.lock_attrib(exclude_attr=attributes, channel_box=False)

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

        return instance

    def set_parent(self, parent):
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
        result = None
        conn = self.tag_node.parent.listConnections()
        if conn:
            result = conn[0]  # type: pm.PyNode

        return result

    def lock_attrib(self, exclude_attr, channel_box=False):
        Logger.debug("TODO: {0} - locking attributes. Excluding: {1}".format(self.transform, exclude_attr))

    def insert_offset(self, extra_name="extra"):
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
        Logger.debug("TODO: {0} - setting shape to {1}".format(self.transform, name))

    def set_color(self, color):
        Logger.debug("TODO: {0} - setting color to {1}".format(self.transform, color))
        if not color:
            color = colors.SideColor[self.data.side].value
        self.data.color = color

    def add_space(self, name, target):
        Logger.debug("TODO: {0} - adding {1} space with named {2}".format(self.transform, target, name))

    def add_world_space(self):
        Logger.debug("TODO: {0} - adding world space".format(self.transform))
        self.add_space("World", "world_loc")

    def mirror_shape(self):
        Logger.debug("TODO: {0} - mirroing shape...")

    def add_wire(self, source):
        Logger.debug("TODO: {0} - adding wire...")

    def get_color(self):
        Logger.debug("TODO: {0} - getting ctl color...")
