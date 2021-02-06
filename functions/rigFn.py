import pymel.core as pm
import pymel.api as pma
from luna import Logger
from luna.utils import environFn
import luna_rig


def list_controls():
    """Get all controller nodes in the scene as Control instances

    :return: List of controls
    :rtype: list(Control)
    """
    transforms = pm.controller(ac=1, q=1)
    ctls = []
    for each in transforms:
        try:
            instance = luna_rig.Control(each)  # type :control.Control
        except Exception:
            Logger.exception("Failed to create control instance from {0}".format(each))
            continue
        ctls.append(instance)
    return ctls


def get_build_character():
    """Gets character component of current build.

    :return: Character meta node as Character instance.
    :rtype: Character
    """
    current_asset = environFn.get_asset_var()
    all_characters = luna_rig.MetaRigNode.list_nodes(of_type=luna_rig.components.Character)
    for char_node in all_characters:
        if char_node.pynode.characterName.get() == current_asset.name:
            return char_node
    Logger.error("Failed to find build character!")


def get_param_ctl_locator(side, joint_chain, move_axis="x", align_index=-1):
    current_char = get_build_character()
    if not current_char:
        clamped_size = current_char.clamped_size
    else:
        clamped_size = 1.0

    locator = pm.spaceLocator(n="param_loc")  # type: luna_rig.nt.Transform
    end_jnt_vec = joint_chain[align_index].getTranslation(space="world")  # type:pma.MVector
    side_mult = -1 if side == "r" else 1
    if move_axis == "x":
        end_jnt_vec.x += clamped_size * 20 * side_mult
    elif move_axis == "y":
        end_jnt_vec.y += clamped_size * 20 * side_mult
    elif move_axis == "z":
        end_jnt_vec.z += clamped_size * 20 * side_mult
    locator.translate.set(end_jnt_vec)
    return locator


def delete_all_meta_nodes():
    for node in luna_rig.MetaRigNode.list_nodes():
        if pm.objExists(node.pynode):
            pm.delete(node.pynode)
