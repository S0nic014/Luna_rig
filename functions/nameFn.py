import pymel.core as pm
from luna import Logger


def deconstruct_name(node):
    """Deconstruct node name

    :param node: Node to deconstruct name for.
    :type node: str or PyNode
    :return: Name struct {namespaces, side, name, index, suffix}
    :rtype: nameStruct
    """
    node = pm.PyNode(node)
    full_name = node.name(stripNamespace=True)
    name_parts = full_name.split("_")

    class _nameStruct:
        def __init__(self):
            self.namespaces = node.namespaceList()  # type :list
            self.side = name_parts[0]  # type :str
            self.name = name_parts[1:-2]  # type :list
            self.index = name_parts[-2]  # type: str
            self.suffix = name_parts[-1]  # type: str
    try:
        name_struct = _nameStruct()
    except IndexError:
        Logger.exception("Failed to deconstruct name: {0}".format(full_name))

    return name_struct  # type: _nameStruct


def rename(node, side=None, name=None, index=None, suffix=None):
    """Rename node

    :param node: Node to rename
    :type node: str or PyNode
    :param side: New side prefix, defaults to None
    :type side: str, optional
    :param name: New name, defaults to None
    :type name: str, (str, list), optional
    :param index: New index, defaults to None
    :type index: str or int, optional
    :param suffix: New suffix, defaults to None
    :type suffix: str, optional
    """
    if node is None:
        return

    old_name = str(node)
    name_parts = deconstruct_name(old_name)
    if side is not None:
        name_parts.side = side
    if name is not None:
        name_parts.name = name
    if index is not None:
        name_parts.index = str(index)
    if suffix is not None:
        name_parts.suffix = suffix

    if isinstance(name_parts.name, list):
        name_parts.name = "_".join(name_parts.name)
    new_name = "_".join([name_parts.side, name_parts.name, name_parts.index, name_parts.suffix])
    pm.rename(node, new_name)


def generate_name(name, side="", suffix=""):
    """Generate unique node name using format "side_name_index_suffix".

    :param name: Node name
    :type name: str or (str, list)
    :param side: Side prefix, defaults to ""
    :type side: str, optional
    :param suffix: Name suffix, defaults to ""
    :type suffix: str, optional
    :return: Unique node name
    :rtype: str
    """
    if side:
        side += "_"
    if suffix:
        suffix = "_" + suffix
    if isinstance(name, list):
        name = "_".join(name)

    index = 0
    version = '_{0:02}'.format(index)

    full_name = side + name + version + suffix
    while pm.objExists(full_name):
        index += 1
        version = '_{0:02}'.format(index)
        full_name = side + name + version + suffix

    return full_name


def get_namespace(node):
    """Get node namespace

    :param node: Node to get namepspace for.
    :type node: str or PyNode
    :return: Namespace string
    :rtype: str
    """
    node = pm.PyNode(node)
    namespaces = node.namespaceList()
    if not namespaces:
        return ""
    else:
        return ":".join(namespaces) + ":"
