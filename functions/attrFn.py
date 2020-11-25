import pymel.core as pm


def lock(node, attributes, channelBox=False, key=False):
    locked_attrs = []
    for attr in attributes:
        pm.setAttr(node + "." + attr, lock=1, cb=channelBox, k=key)
        locked_attrs.append("." + attr)
    return locked_attrs
