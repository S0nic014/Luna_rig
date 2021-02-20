import pymel.core as pm
import maya.cmds as mc
from luna import Logger
import luna_rig


class Twist(object):

    def __repr__(self):
        return "Twist ({0})".format(self.node)

    @property
    def handle(self):
        transform = mc.listConnections(self.node + ".matrix", d=1)[0]  # type: luna_rig.nt.Transform
        return transform

    @property
    def start_angle(self):
        value = mc.getAttr(self.node + ".startAngle")  # type: float
        return value

    @start_angle.setter
    def start_angle(self, value):
        try:
            mc.setAttr(self.node + ".startAngle", value)
        except RuntimeError:
            Logger.exception("{0}: Failed to set start angle".format(self))

    @property
    def end_angle(self):
        value = mc.getAttr(self.node + ".endAngle")  # type: float
        return value

    @end_angle.setter
    def end_angle(self, value):
        try:
            mc.setAttr(self.node + ".endAngle", value)
        except RuntimeError:
            Logger.exception("{0}: Failed to set end angle".format(self))

    @property
    def low_bound(self):
        value = mc.getAttr(self.node + ".lowBound")  # type: float
        return value

    @low_bound.setter
    def low_bound(self, value):
        try:
            mc.setAttr(self.node + ".lowBound", value)
        except RuntimeError:
            Logger.exception("{0}: Failed to set low bound".format(self))

    @property
    def high_bound(self):
        value = mc.getAttr(self.node + ".highBound")  # type: float
        return value

    @high_bound.setter
    def high_bound(self, value):
        try:
            mc.setAttr(self.node + ".highBound", value)
        except RuntimeError:
            Logger.exception("{0}: Failed to set high bound".format(self))

    def __init__(self, twist_node):
        self.node = twist_node

    @classmethod
    def create(cls,
               geometry,
               name="twist",
               * args,
               **kwargs):
        deformer = mc.nonLinear(str(geometry), type="twist", n=name, ap=False, *args, **kwargs)[0]
        instance = Twist(deformer)
        return instance


def is_painted(deformer_node):
    if isinstance(deformer_node, str):
        deformer_node = pm.PyNode(deformer_node)
    return deformer_node.weightList.get(size=True) > 0


def get_deformer(node, type):
    def_list = pm.listHistory(node, type=type)
    return def_list[0] if def_list else None


def list_deformers(type, under_group=None):
    deformers_list = []
    if under_group:
        for child_node in pm.listRelatives(under_group, ad=1):
            for deformer_node in child_node.listHistory(type=type):
                if deformer_node not in deformers_list:
                    deformers_list.append(deformer_node)
    else:
        deformers_list = pm.ls(typ=type)
    return deformers_list
