import re
import pymel.core as pm
import luna
from luna import Logger


def deconstruct_name(node):
    template = get_current_template()
    node = pm.PyNode(node)
    full_name = node.stripNamespace()
    name_parts = full_name.split("_")
    # Find last index
    re_index = re.compile(r"\d+|^$")
    all_indexes = list(filter(re_index.match, name_parts))
    index_index = len(name_parts) - name_parts[::-1].index(all_indexes[-1]) - 1
    index = name_parts[index_index]  # type: str
    # Find name
    name_start_index = template.split("_").index("{name}")
    name = "_".join(name_parts[name_start_index:index_index])
    indexed_name = "_".join(name_parts[name_start_index:index_index + 1])
    # Find suffix and side
    temp_name = full_name.replace(indexed_name, "name")
    side_index = template.split("_").index("{side}")
    suffix_index = template.split("_").index("{suffix}")
    side = temp_name.split("_")[side_index]  # type: str
    suffix = temp_name.split("_")[suffix_index]  # type: str

    class _nameStruct:
        def __init__(self):
            self.namespaces = node.namespaceList()  # type: list
            self.side = side
            self.name = name
            self.indexed_name = indexed_name
            self.index = index
            self.suffix = suffix

    return _nameStruct()  # type: _nameStruct


def generate_name(name, side, suffix, override_index=None):
    template = get_current_template()
    naming_profile = luna.Config.get(luna.LunaVars.naming_profile, stored=True, default={})  # type: dict

    if isinstance(name, list):
        name = "_".join(name)
    # Prepare for name generation
    timeout = 300
    index = naming_profile.get("start_index", 0)
    zfill = naming_profile.get("index_padding", 2)
    # Construct base name
    index_str = str(index).zfill(zfill) if override_index is None else override_index
    indexed_name = name + "_" + index_str
    full_name = template.format(side=side, name=indexed_name, suffix=suffix)
    while pm.objExists(full_name):
        index += 1
        index_str = str(index).zfill(zfill) if override_index is None else override_index
        indexed_name = name + "_" + index_str
        full_name = template.format(side=side, name=indexed_name, suffix=suffix)
        if index == timeout:
            Logger.warning("Reached max iterations of {0}".format(timeout))
            break
    return full_name


def get_current_template():
    naming_profile = luna.Config.get(luna.LunaVars.naming_profile, stored=True, default={})  # type: dict
    all_templates = luna.Config.get(luna.LunaVars.naming_templates, stored=True, default={})  # type: dict
    template = all_templates.get(naming_profile.get("template", "default"), "{side}_{name}_{suffix}")  # type: str
    return template


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

    name_parts = deconstruct_name(node)
    if side is not None:
        name_parts.side = side
    if name is not None:
        name_parts.name = name
    if suffix is not None:
        name_parts.suffix = suffix
    if index is not None:
        name_parts.index = index

    new_name = generate_name(name_parts.name, name_parts.side, name_parts.suffix, override_index=name_parts.index)
    pm.rename(node, new_name)


def add_namespaces(name, namespaces):
    # Handle name input
    if isinstance(name, pm.PyNode):
        name = name.name()
    # Handle namespaces input
    if not namespaces:
        return name

    if isinstance(namespaces, str):
        namespaced_name = ":".join([namespaces] + [name])
    elif isinstance(namespaces, list):
        namespaced_name = ":".join([namespaces] + name)
    else:
        Logger.error("Invalid type for namespaces arg: {0}".format(type(namespaces)))
        raise TypeError
    return namespaced_name


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
