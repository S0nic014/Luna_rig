import pymel.core as pm
from Luna import Logger
from Luna.utils import environFn
from Luna_rig.core import control
from Luna_rig.core.meta import MetaRigNode


def list_controls():
    """Get all controller nodes in the scene as Control instances

    :return: List of controls
    :rtype: list(Control)
    """
    transforms = pm.controller(ac=1, q=1)
    ctls = []
    for each in transforms:
        try:
            instance = control.Control(each)  # type :control.Control
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
    all_characters = MetaRigNode.list_nodes(of_type="Character")
    for char_node in all_characters:
        if char_node.pynode.characterName.get() == current_asset.name:
            return char_node
    Logger.error("Failed to find build character!")
