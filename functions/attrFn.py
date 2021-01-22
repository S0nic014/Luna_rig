from Luna import Logger
import pymel.core as pm


def lock(node, attributes, channelBox=False, key=False):
    locked_attrs = []
    for attr in attributes:
        pm.setAttr(node + "." + attr, lock=1, cb=channelBox, k=key)
        locked_attrs.append("." + attr)
    return locked_attrs


def get_enums(attribute):
    """Get enums values as sorted list

    :param attribute: Attribute to get enums from.
    :type attribute: pm.Attribute
    :return: List of enums as list of tuples (name, index)
    :rtype: list[(str, int)]
    """
    try:
        enum_list = attribute.getEnums().items()
        enum_list = sorted(enum_list, key=lambda pair: pair[1])
    except TypeError:
        return []
    return enum_list
