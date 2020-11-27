import pymel.core as pm
from Luna import Logger


def deconstruct_name(full_name):
    if isinstance(full_name, pm.PyNode):
        full_name = full_name.name()
    name_parts = full_name.split("_")

    class _nameStruct:
        def __init__(self):
            self.side = name_parts[0]
            self.name = name_parts[1:-2]
            self.index = name_parts[-2]
            self.suffix = name_parts[-1]
    try:
        name_struct = _nameStruct()
    except IndexError:
        Logger.exception("Failed to deconstruct name: {0}".format(full_name))

    return name_struct


def rename(node, side=None, name=None, index=None, suffix=None):
    if node is None:
        return

    old_name = str(node)
    name_parts = deconstruct_name(old_name)
    if side is not None:
        name_parts.side = side
    if name is not None:
        name_parts.name = name
    if index is not None:
        name_parts.index = index
    if side is not None:
        name_parts.suffix = suffix

    if isinstance(name_parts.name, list):
        name_parts.name = "_".join(name_parts.name)
    new_name = "_".join([name_parts.side, name_parts.name, name_parts.index, name_parts.suffix])
    pm.rename(node, new_name)


def generate_name(name, side="", suffix=""):
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
