import math
import pymel.core as pm
import pymel.api as pma
from pymel.core import nodetypes
from luna import Logger
from luna_rig.functions import nameFn


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
        original_name = nameFn.deconstruct_name(str(old_jnt))
        if replace_name:
            original_name.name = replace_name
        if add_name:
            original_name.name.append(add_name)
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
    assert isinstance(start_joint, nodetypes.Joint), "{0} is not a joint".format(start_joint)
    start_joint = pm.PyNode(start_joint)  # type: nodetypes.Joint
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


def rotToOrient(jnt):
    jnt = pm.PyNode(jnt)  # type: nodetypes.Joint
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


def validate_rotations(joint_chain):
    is_valid = True
    for jnt in joint_chain:
        jnt = pm.PyNode(jnt)  # type: nodetypes.Joint
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
        mid_index = (len(joint_chain) - 1) / 2
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
