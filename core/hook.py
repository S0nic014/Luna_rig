import pymel.core as pm
from luna import Logger
import luna_rig
import luna_rig.functions.nodeFn as nodeFn
import luna_rig.functions.attrFn as attrFn


class Hook(object):

    def __repr__(self):
        return "Hook ({0})".format(self.transform)

    def __eq__(self, other):
        if not isinstance(other, Hook):
            raise TypeError("Can't compare Hook and {0}".format(type(other)))
        return self.transform == other.transform

    def __init__(self, node):
        self.transform = node  # type: luna_rig.nt.Transform

    def add_output(self, anim_component):
        self.transform.children.connect(anim_component.pynode.inHook)
        Logger.info("{0} connection: {0} ->> {1}".format(self, anim_component))

    @classmethod
    def create(cls, anim_component, object_node, name):
        hook_transform = nodeFn.create("transform",
                                       [anim_component.indexed_name, name],
                                       anim_component.side,
                                       suffix="hook",
                                       p=anim_component.group_out)
        if not isinstance(object_node, pm.PyNode):
            object_node = pm.PyNode(object_node)

        pm.pointConstraint(object_node, hook_transform)
        pm.orientConstraint(object_node, hook_transform)

        # Attributes
        attrFn.add_meta_attr(hook_transform)
        hook_transform.addAttr("object", at="message")
        hook_transform.addAttr("children", at="message")
        object_node.message.connect(hook_transform.object)
        hook_transform.metaParent.connect(anim_component.pynode.hooks, na=1)
        instance = cls(hook_transform)
        return instance

    @property
    def as_object(self):
        node = self.transform.object.listConnections(d=1)[0]  # type: luna_rig.nt.DependNode
        return node

    @property
    def component(self):
        comp_node = luna_rig.MetaNode(self.transform.metaParent.listConnections(s=1)[0])  # type: luna_rig.AnimComponent
        return comp_node

    @property
    def children(self):
        connections = self.transform.outputs.listConnections(s=1)
        return [luna_rig.MetaNode(conn) for conn in connections]

    @property
    def index(self):
        return self.component.hooks.index(self)
