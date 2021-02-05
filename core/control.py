
import json
import pymel.core as pm
from pymel.core import nodetypes
from luna import Logger
from luna import static
from luna_rig.functions import nameFn
from luna_rig.functions import attrFn
from luna_rig.functions import curveFn
from luna_rig.functions import transformFn
from luna_rig.functions import outlinerFn
from luna_rig.core.shape_manager import ShapeManager
from luna_rig.core import meta


class Control(object):

    def __repr__(self):
        return "Control({0})".format(self.transform)

    def __init__(self, node):
        node = pm.PyNode(node)
        if isinstance(node, nodetypes.Controller):
            self.transform = node.controllerObject.listConnections()[0]  # type: nodetypes.Transform
        elif isinstance(node, nodetypes.Transform):
            self.transform = pm.PyNode(node)  # type: nodetypes.Transform
        elif isinstance(node, nodetypes.Shape):
            self.transform = node.getTransform()  # type: nodetypes.Transform
        else:
            raise TypeError("Control requires node with transform to initialize.")
        if not self.transform.hasAttr("metaParent"):
            raise AttributeError("{0} metaParent attribute not found.".format(self))

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
               component=None,
               orient_axis="x",
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
        :param color: Control color, if not set will use color based on side, defaults to None
        :type color: int, enumFn.Enum, optional
        :param offset_grp: If offset group should be created, defaults to True
        :type offset_grp: bool, optional
        :param joint: If control joint should be created, defaults to False
        :type joint: bool, optional
        :param shape: Desired control shape from shape lib, defaults to "cube"
        :type shape: str, optional
        :param tag: Additional tag to set on tag node, defaults to ""
        :type tag: str, optional
        :param component: Connect to component.pynode.controls on creation, defaults to None
        :type component: AnimComponent
        :param: orient_axis: Control orientation. Valid values: ("x", "y", "z"), defaults to "x"
        :type orient_axis: str
        :param scale: Control scale, defaults to 1.0
        :type scale: float, optional
        :return: Control instance
        :rtype: Control
        """
        # Group
        offset_node = None
        ctl_joint = None
        if isinstance(parent, Control):
            temp_parent = parent.transform
        else:
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
        if offset_node:
            offset_node.metaParent.connect(tag_node.offset, na=1)
        if ctl_joint:
            ctl_joint.metaParent.connect(tag_node.joint)
        if isinstance(parent, Control):
            child_index = len(parent.tag_node.children.listConnections())
            tag_node.parent.connect(parent.tag_node.children[child_index])

        # Create instance
        instance = Control(transform_node)
        instance.shape = shape
        instance.color = color
        instance.set_outliner_color(27)
        # Attributes
        instance.lock_attrib(exclude_attr=attributes, channel_box=False)

        # Adjust shape
        instance.scale(scale, factor=0.8)
        instance.orient_shape(direction=orient_axis)
        # Connect to component
        if component:
            component._store_controls((instance))

        return instance

    @property
    def namespace_list(self):
        name_parts = nameFn.deconstruct_name(self.transform)
        return name_parts.namespaces

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
    def unsuffixed_name(self):
        name_parts = nameFn.deconstruct_name(self.transform)
        name = "_".join(name_parts.name)
        return "_".join([name_parts.side, name, name_parts.index])

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
            value = static.SideColor[self.side].value
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
    def spaces(self):
        result = []
        if self.transform.hasAttr("space"):
            result = attrFn.get_enums(self.transform.space)
        return result

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

    def set_outliner_color(self, color):
        outlinerFn.set_color(self.transform, color)

    def scale(self, scale, factor=0.8):
        if scale == 1.0 and factor == 1.0:
            return
        for each in self.transform.getShapes():
            pm.scale(each + ".cv[0:1000]", [factor * scale, factor * scale, factor * scale])

    def set_parent(self, parent):
        """Set control parent

        :param parent: Parent to set, if None - will be parented to world.
        :type parent: pm.PyNode
        """
        if isinstance(parent, Control):
            pm.parent(self.group, parent.transform)
            connect_index = len(parent.tag_node.children.listConnections(d=1))
            self.tag_node.parent.connect(parent.tag_node.children[connect_index])
        else:
            parent.message.connect(self.tag_node.parent, f=1)

    def get_parent(self, generations=1):
        """Get current parent

        :return: Parent node
        :rtype: pm.PyNode
        """
        return self.group.getParent(generations=generations)

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

    def insert_offset(self, extra_name="extra"):
        """Inserts extra ofset node and inbetween transform and last offset node present.

        :param extra_name: name to add to new offset node, defaults to "extra"
        :type extra_name: str, optional
        :return: Created node
        :rtype: pm.PyNode
        """
        Logger.debug("{0} - Inserting offset with extra name: {1}".format(self, extra_name))
        if self.offset_list:
            parent = self.offset
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

    def find_offset(self, extra_name):
        result = None
        for offset_node in self.offset_list:
            if extra_name in nameFn.deconstruct_name(offset_node).name:
                result = offset_node  # type: nodetypes.Transform
                break
        return result

    def mirror_shape(self, across="yz", behaviour=True, flip=False, flip_across="yz"):
        """Mirrors control's shape
        """
        # Create temp transform, parent shapes to it and mirror
        temp_transform = pm.createNode("transform", n="mirror_shape_grp", p=self.transform)
        for shape in self.transform.getShapes():
            shape.setParent(temp_transform, r=1)
        transformFn.mirror_xform(temp_transform, across=across, behaviour=behaviour, space=self.transform)
        # Flip shape
        if flip:
            curveFn.flip_shape(temp_transform, across=flip_across)
        pm.makeIdentity(temp_transform, apply=1)
        # Parent back to control
        for shape in temp_transform.getShapes():
            shape.setParent(self.transform, r=1)
        pm.delete(temp_transform)
        pm.select(cl=1)

    def mirror_shape_to_opposite(self, behaviour=True, across="yz", flip=False, flip_across="yz"):
        opposite_ctl = self.find_opposite()
        if not opposite_ctl:
            Logger.warning("{0}: No opposite control was found.")
            return
        old_color = opposite_ctl.color
        ShapeManager.apply_shape(opposite_ctl.transform, self.shape)
        opposite_ctl.mirror_shape(across=across, behaviour=behaviour, flip=flip, flip_across=flip_across)
        opposite_ctl.color = old_color

    def add_space(self, target, name, method="matrix"):
        # Process inputs
        if method not in ["constr", "matrix"]:
            raise ValueError("Invalid space method, should be constraint or matrix")

        if pm.about(api=1) < 20200100 and method == "matrix":
            Logger.warning("Matrix space method requires Maya 2020+. Using constraint method instead.")
            method = "constr"

        # Add divider if matrix
        if method == "matrix" and not self.transform.hasAttr("SPACE_SWITCHING"):
            attrFn.add_divider(self.transform, "SPACE_SWITCHING")

        if isinstance(target, Control):
            target = target.transform
        else:
            target = pm.PyNode(target)
        if not isinstance(target, nodetypes.Transform):
            Logger.error("{0}: Can't add space to not transform {1}".format(self, target))
            raise ValueError

        # Add space attribute
        if not self.transform.hasAttr("space"):
            self.transform.addAttr("space", at="enum", keyable=True, en=["NONE"])

        # Check if enum name already exists
        existing_enums = attrFn.get_enums(self.transform.space)
        enum_names = [enum[0] for enum in existing_enums]
        if name in enum_names:
            Logger.exception("{0}: space with name {1} already exists.".format(self, name))
            return
        if "NONE" in enum_names:
            enum_names.remove("NONE")

        # Add enum value
        enum_names.append(name)
        pm.setEnums(self.transform.attr("space"), enum_names)

        # Create switch logic
        if method == "matrix":
            self.__add_matrix_space(target, name)
        elif method == "constr":
            self.__add_constr_space(target, name)
        # Store as component setting
        if self.connected_component:
            self.connected_component._store_settings(self.transform.space)
            if method == "matrix":
                self.connected_component._store_settings(self.transform.spaceUseTranslate)
                self.connected_component._store_settings(self.transform.spaceUseRotate)
                self.connected_component._store_settings(self.transform.spaceUseScale)
        Logger.info("{0}: added space {1}".format(self, target))

    def __add_matrix_space(self, target, name):
        """Add space using matrix method\n
        Based on https://www.chadvernon.com/blog/space-switching-offset-parent-matrix/
        :param target: target space
        :type target: PyNode
        :param name: Space name
        :type name: str
        """
        # Add ctl attrs
        if not self.transform.hasAttr("spaceUseTranslate"):
            self.transform.addAttr("spaceUseTranslate", at="bool", dv=True, k=1)
        if not self.transform.hasAttr("spaceUseRotate"):
            self.transform.addAttr("spaceUseRotate", at="bool", dv=True, k=1)
        if not self.transform.hasAttr("spaceUseScale"):
            self.transform.addAttr("spaceUseScale", at="bool", dv=True, k=1)

        # Get offset matrix
        mult_mtx = pm.createNode("multMatrix", n="{0}_{1}_mmtx".format(self.unsuffixed_name, name.lower()))
        offset_mtx = transformFn.matrix_to_list(self.transform.worldMatrix.get() * self.transform.matrix.get().inverse() * target.worldInverseMatrix.get())
        mult_mtx.matrixIn[0].set(offset_mtx)
        target.worldMatrix.connect(mult_mtx.matrixIn[1])
        self.transform.getParent().worldInverseMatrix.connect(mult_mtx.matrixIn[2])
        index = len(self.spaces) - 1
        # Condition
        condition = pm.createNode("condition", n="{0}_{1}_cond".format(self.unsuffixed_name, name.lower()))
        condition.secondTerm.set(index)
        condition.colorIfTrueR.set(1)
        condition.colorIfFalseR.set(0)
        self.transform.space.connect(condition.firstTerm)
        # Blend matrix
        blend_name = "{0}_space_blend".format(self.unsuffixed_name)
        if not pm.objExists(blend_name):
            blend_mtx = pm.createNode("blendMatrix", n=blend_name)
        else:
            blend_mtx = pm.PyNode(blend_name)

        condition.outColorR.connect(blend_mtx.target[index].weight)
        mult_mtx.matrixSum.connect(blend_mtx.target[index].targetMatrix)
        if not self.transform.offsetParentMatrix.isConnected():
            blend_mtx.outputMatrix.connect(self.transform.offsetParentMatrix)
        self.transform.spaceUseTranslate.connect(blend_mtx.target[index].useTranslate)
        self.transform.spaceUseRotate.connect(blend_mtx.target[index].useRotate)
        self.transform.spaceUseScale.connect(blend_mtx.target[index].useScale)

    def __add_constr_space(self, target, name):
        # Space offset
        space_offset = self.find_offset("space")
        if not space_offset:
            space_offset = self.insert_offset(extra_name="space")
        # Create space transforms
        space_node = pm.createNode("transform", n="{0}_{1}_space".format(self.unsuffixed_name, name.lower()), p=self.transform)
        pm.parent(space_node, world=True)
        parent_constr = pm.parentConstraint(space_node, space_offset)
        # Condition node
        condition = pm.createNode("condition", n="{0}_{1}_cond".format(self.unsuffixed_name, name.lower()))
        self.transform.space.connect(condition.firstTerm)
        condition.secondTerm.set(len(parent_constr.getTargetList()) - 1)
        condition.colorIfTrueR.set(1)
        condition.colorIfFalseR.set(0)
        condition.outColorR.connect(parent_constr.getWeightAliasList()[-1])
        pm.parent(space_node, target)

    def add_world_space(self, method="matrix"):
        """Uses add space method to add space to hidden world locator
        """
        self.add_space(self.character.world_locator, "World", method)

    def switch_space(self, index, matching=True):
        if not self.transform.hasAttr("space"):
            return
        if index > len(self.spaces) - 1:
            Logger.warning("{0} - Space index {1} out of bounds.".format(self, index))
            return
        mtx = self.transform.getMatrix(worldSpace=True)
        self.transform.space.set(index)
        if matching:
            self.transform.setMatrix(mtx, worldSpace=True)

    def add_wire(self, source):
        """Adds staight line curve connecting source object and controls' transform

        :param source: Wire source object
        :type source: str or pm.nodetypes.Transform
        """
        # Curve
        curve_points = [source.getTranslation(space="world"), self.transform.getTranslation(space="world")]
        wire_curve = curveFn.curve_from_points(name="{0}_wire_crv".format(self.unsuffixed_name), degree=1, points=curve_points)
        wire_curve.inheritsTransform.set(0)
        # Clusters
        src_cluster = pm.cluster(wire_curve.getShape().controlPoints[0], n="{0}_wire_src_clst".format(self.unsuffixed_name))
        dest_cluster = pm.cluster(wire_curve.getShape().controlPoints[1], n="{0}_wire_dest_clst".format(self.unsuffixed_name))
        pm.pointConstraint(source, src_cluster, n="{0}_wire_src_pconstr".format(self.unsuffixed_name))
        pm.pointConstraint(self.transform, dest_cluster, n="{0}_wire_dest_pconstr".format(self.unsuffixed_name))
        # Grouping
        wire_grp = pm.group(src_cluster, dest_cluster, n="{0}_wire_grp".format(self.unsuffixed_name))
        pm.parent(wire_curve, wire_grp)
        pm.parent(wire_grp, self.group)
        # Housekeeping
        src_cluster[1].visibility.set(0)
        dest_cluster[1].visibility.set(0)
        wire_curve.getShape().overrideEnabled.set(1)
        wire_curve.getShape().overrideDisplayType.set(2)

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
        """Finds opposite control in the scene

        :return: [description]
        :rtype: [type]
        """
        if self.side not in ["l", "r"]:
            return None
        opposite_transform = "{0}_{1}_{2}_{3}".format(static.OppositeSide[self.side].value, self.name, self.index, "ctl")
        # Handle namespaces
        opposite_transform = ":".join(self.transform.namespaceList() + [opposite_transform])
        if pm.objExists(opposite_transform):
            return Control(opposite_transform)
        else:
            Logger.info("{0}: No opposite control found.".format(self))
            return None

    def mirror_pose_from_opposite(self, across="yz", space="character", behavior=True):
        """Mirror control attributes from opposite control.

        :param across: Mirror plan. Valid values: "YZ", "XY", "XZ", , defaults to "YZ"
        :type across: str, optional
        :param space: Mirror space, takes any transform or str values: "world", "character", defaults to "character"
        :type space: str, optional
        :param behavior: If behaviour should be mirrored, defaults to True
        :type behavior: bool, optional
        """
        if space == "character":
            space = self.character.world_locator
        opposite_ctl = self.find_opposite()
        if not opposite_ctl:
            return
        pm.matchTransform(self.transform, opposite_ctl.transform)
        transformFn.mirror_xform(transforms=self.transform, across=across, behaviour=behavior, space=space)

    def mirror_pose_to_opposite(self, across="yz", space="character", behavior=True):
        """Mirror control attributes to control on opposite side.

        :param across: Mirror plan. Valid values: "YZ", "XY", "XZ", , defaults to "YZ"
        :type across: str, optional
        :param space: Mirror space, takes any transform or str values: "world", "character", defaults to "character"
        :type space: str, optional
        :param behavior: If behaviour should be mirrored, defaults to True
        :type behavior: bool, optional
        """
        if space == "character":
            space = self.character.world_locator
        opposite_ctl = self.find_opposite()
        if not opposite_ctl:
            return
        pm.matchTransform(opposite_ctl.transform, self.transform)
        transformFn.mirror_xform(transforms=opposite_ctl.transform, across=across, behaviour=behavior, space=space)

    def orient_shape(self, direction="x"):
        if direction.lower() not in "xyz" and direction.lower() not in ["-x", "-y", "-z"]:
            Logger.exception("Invalid orient direction: {0}".format(direction))
            return
        if direction == "y":
            return

        # Create temp transform and parent shapes to it
        temp_transform = pm.createNode("transform", n="temp_transform", p=self.transform)  # type: nodetypes.Transform
        for each in self.transform.getShapes():
            pm.parent(each, temp_transform, s=1, r=1)

        # Apply rotation
        if direction == "x":
            temp_transform.rotateX.set(-90)
            temp_transform.rotateY.set(-90)
        elif direction == "-x":
            temp_transform.rotateX.set(90)
            temp_transform.rotateY.set(-90)
        elif direction == "-y":
            temp_transform.rotateZ.set(180)
        elif direction == "z":
            temp_transform.rotateX.set(90)
        elif direction == "-z":
            temp_transform.rotateX.set(-90)

        # Reparent shapes and delete temp transform
        pm.makeIdentity(temp_transform, rotate=True, apply=True)
        for each in temp_transform.getShapes():
            pm.parent(each, self.transform, s=1, r=1)
        pm.delete(temp_transform)
