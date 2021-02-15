from __future__ import division
import pymel.core as pm
import pymel.api as pma
from luna import Logger
import luna_rig
import luna.static as static
import luna_rig.functions.nameFn as nameFn


def duplicate_chain(original_chain=[],
                    start_joint=None,
                    end_joint=None,
                    add_name="",
                    replace_name="",
                    replace_side="",
                    replace_suffix="",
                    new_parent=None):

    if not original_chain:
        original_chain = joint_chain(start_joint, end_joint)

    new_chain = pm.duplicate(original_chain, po=1, rc=1)  # type :list
    for old_jnt, new_jnt in zip(original_chain, new_chain):
        original_name = nameFn.deconstruct_name(old_jnt)
        if replace_name:
            original_name.name = replace_name
        if add_name:
            original_name.name = "_".join([original_name.name, add_name])
        if replace_side:
            original_name.side = replace_side
        if replace_suffix:
            original_name.suffix = replace_suffix

        new_name = nameFn.generate_name(original_name.name, original_name.side, original_name.suffix)
        new_jnt.rename(new_name)

    if new_parent:
        if new_parent == "world":
            pm.parent(new_chain[0], w=1)
        else:
            pm.parent(new_chain[0], new_parent)

    return new_chain


def joint_chain(start_joint, end_joint=None):
    """Get joint chain from start joint. Optionally slice the chain at end joint.

    :param start_joint: First joint in the chain
    :type start_joint: str,PyNode
    :param end_joint: Last joint in the chain, defaults to None
    :type end_joint: str, PyNode, optional
    :return: Joint chain as a list
    :rtype: list
    """
    start_joint = pm.PyNode(start_joint)
    assert isinstance(start_joint, luna_rig.nt.Joint), "{0} is not a joint".format(start_joint)
    start_joint = pm.PyNode(start_joint)  # type: luna_rig.nt.Joint
    chain = start_joint.getChildren(type="joint", ad=1) + [start_joint]
    chain.reverse()
    if not end_joint:
        return chain

    # Handle end joint
    assert pm.nodeType(end_joint) == 'joint', "{0} is not a joint".format(end_joint)
    end_joint = pm.PyNode(end_joint)
    cut_chain = []
    for jnt in chain:
        if str(jnt) in end_joint.fullPath().split("|"):
            cut_chain.append(jnt)
    return cut_chain


def create_chain(joint_list=[], reverse=False):
    if reverse:
        joint_list.reverse()
    for index in range(1, len(joint_list)):
        joint_list[index].setParent(joint_list[index - 1])

    return joint_list


def reverse_chain(joint_list=[]):
    for jnt in joint_list:
        jnt.setParent()
    joint_list.reverse()
    create_chain(joint_list)


def mirror_chain(chains=[]):
    if not chains:
        chains = pm.selected()
    valid_chains = [obj for obj in chains if isinstance(obj, luna_rig.nt.Joint)]
    for joint in valid_chains:
        side = joint.name().split("_")[0]
        if side in ["l", "r"]:
            pm.mirrorJoint(joint, mb=1, myz=1, sr=(side + "_", static.OppositeSide[side].value + "_"))
        else:
            pm.mirrorJoint(joint, mb=1, myz=1)


def along_curve(curve, amount, joint_name="joint", joint_side="c", joint_suffix="jnt", delete_curve=False):
    joints = []
    for index in range(amount):
        param = float(index) / float(amount - 1)
        point = pm.pointOnCurve(curve, pr=param, top=1)
        jnt = pm.createNode("joint", n=nameFn.generate_name(joint_name, joint_side, joint_suffix))  # type: luna_rig.nt.Joint
        jnt.setTranslation(point, space="world")
        joints.append(jnt)
    if delete_curve:
        pm.delete(curve)
    return joints


def rot_to_orient(jnt):
    jnt = pm.PyNode(jnt)  # type: luna_rig.nt.Joint
    newOrient = []
    for rot, orient in zip(jnt.rotate.get(), jnt.jointOrient.get()):
        newOrient.append(orient + rot)
    jnt.jointOrientX.set(newOrient[0])
    jnt.jointOrientY.set(newOrient[1])
    jnt.jointOrientZ.set(newOrient[2])
    jnt.rotateX.set(0)
    jnt.rotateY.set(0)
    jnt.rotateZ.set(0)
    return newOrient


def copy_orient(source, destination):
    if not isinstance(destination, list):
        destination = [destination]
    source = pm.PyNode(source)  # type: luna_rig.nt.Joint
    for dest_joint in destination:
        dest_joint.jointOrient.set(source.jointOrient.get())


def validate_rotations(joint_chain):
    is_valid = True
    for jnt in joint_chain:
        jnt = pm.PyNode(jnt)  # type: luna_rig.nt.Joint
        if jnt.rotateX.get() > 0:
            Logger.warning("Non zero rotationX on joint {0}".format(jnt))
            is_valid = False
        if jnt.rotateY.get() > 0:
            Logger.warning("Non zero rotationX on joint {0}".format(jnt))
            is_valid = False
        if jnt.rotateZ.get() > 0:
            Logger.warning("Non zero rotationX on joint {0}".format(jnt))
            is_valid = False
    return is_valid


def get_pole_vector(joint_chain):
    root_jnt_vec = joint_chain[0].getTranslation(space="world")  # type:pma.MVector
    end_jnt_vec = joint_chain[-1].getTranslation(space="world")  # type:pma.MVector

    if len(joint_chain) % 2:
        mid_index = (len(joint_chain) - 1) // 2
        mid_jnt_vec = joint_chain[mid_index].getTranslation(space="world")  # type:pma.MVector
    else:
        prev_jnt_index = len(joint_chain) // 2
        next_jnt_index = prev_jnt_index + 1
        prev_jnt_vec = joint_chain[prev_jnt_index].getTranslation(space="world")  # type:pma.MVector
        next_jnt_vec = joint_chain[next_jnt_index].getTranslation(space="world")  # type:pma.MVector
        mid_jnt_vec = (next_jnt_vec + prev_jnt_vec) * 0.5  # Find mid point between joints with close to mid

    # Get projection vector
    line = (end_jnt_vec - root_jnt_vec)
    point = (mid_jnt_vec - root_jnt_vec)
    scale_value = (line * point) / (line * line)
    project_vec = line * scale_value + root_jnt_vec

    # Get chain length
    rootToMidLen = (mid_jnt_vec - root_jnt_vec).length()
    midToEndLen = (end_jnt_vec - mid_jnt_vec).length()
    totalLen = rootToMidLen + midToEndLen

    pol_vec_pos = (mid_jnt_vec - project_vec).normal() * totalLen + mid_jnt_vec
    pole_locator = pm.spaceLocator(n="polevector_loc")
    pole_locator.translate.set(pol_vec_pos)
    return pole_locator
