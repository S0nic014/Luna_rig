import pymel.core as pm
from Luna import Logger


def add_meta_attr(node):
    """Add metaParent attribute to node.

    :param node: Node to add attribute to
    :type node: str or PyNode
    :return: Added attribute
    :rtype: pm.Attribute
    """
    node = pm.PyNode(node)
    if not node.hasAttr("metaParent"):
        node.addAttr("metaParent", at="message")
    return node.metaParent  # type: pm.Attribute


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


def add_divider(node, attr_name="divider"):
    node = pm.PyNode(node)
    node.addAttr(attr_name, at="enum", en=["--------------"])
    node.attr(attr_name).set(channelBox=True)
    node.attr(attr_name).lock()
