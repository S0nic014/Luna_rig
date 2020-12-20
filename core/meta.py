"""Based on 2015 GDC talk by David Hunt & Forrest Sderlind https://www.youtube.com/watch?v=U_4u0kbf-JE"""

import pymel.core as pm
from pymel.core import nodetypes
from Luna import Logger
from Luna_rig.functions import nameFn


class MetaRigNode(object):

    @classmethod
    def as_str(cls, name_only=False):
        """Get a string representation of class path.

        :return: Class string
        :rtype: str
        """
        meta_module = cls.__module__
        meta_name = cls.__name__
        if name_only:
            return meta_name
        meta_type_str = ".".join([meta_module, meta_name])
        return meta_type_str

    def __new__(cls, node=None):
        """Initialize class stored in metaRigType attribute and return a intance of it.

        :param node: Network node, defaults to None
        :type node: str or PyNode, optional
        :return: Evaluated meta class
        :rtype: Meta rig node class instance
        """
        import Luna_rig  # noqa: F401
        result = None
        if node:
            node = pm.PyNode(node)
            class_string = node.metaRigType.get()
            eval_class = eval(class_string, globals(), locals())
            result = eval_class.__new__(eval_class, node)
        else:
            result = super(MetaRigNode, cls)

        return result

    def __init__(self, node):
        """Stores created network node as instance field

        :param node: Network node
        :type node: str or PyNode
        :raises TypeError: If node has no metaRigType attribute
        """
        node = pm.PyNode(node)
        if not node.hasAttr("metaRigType"):
            raise TypeError("{0} is not a valid meta rig node".format(str(node)))
        self.pynode = node  # type: nodetypes.Network

    @property
    def name(self):
        name_parts = nameFn.deconstruct_name(self.pynode.name())
        name = "_".join(name_parts.name)
        return name

    @property
    def side(self):
        return nameFn.deconstruct_name(self.pynode.name()).side

    @property
    def index(self):
        return nameFn.deconstruct_name(self.pynode.name()).index

    @property
    def suffix(self):
        return nameFn.deconstruct_name(self.pynode.name()).suffix

    @classmethod
    def create(cls, meta_parent, version):
        """Creates meta node and calls constructor for MetaRigNode using meta_type.

        :param meta_parent: Meta parent node to connect to
        :type meta_parent: str or PyNode
        :param version: meta version
        :type version: int
        :return: Instance of meta_type class
        :rtype: MetaRigNode
        """
        if meta_parent:
            meta_parent = MetaRigNode(meta_parent)

        # Create node
        node = pm.createNode("network")

        # Add attributes
        node.addAttr("version", at="long")
        node.addAttr("metaRigType", dt="string")
        node.addAttr("metaChildren", at="message", multi=1, im=0)
        node.addAttr("metaParent", at="message")
        node.version.set(version)
        node.metaRigType.set(cls.as_str())
        meta_node = MetaRigNode(node)
        if meta_parent:
            meta_node.set_meta_parent(meta_parent)
        return meta_node

    def set_meta_parent(self, parent):
        self.pynode.metaParent.connect(parent.pynode.metaChildren, na=1)

    @staticmethod
    def list_nodes(of_type=None):
        """List Metarig nodes

        :param of_type: List only specific type, defaults to None
        :type of_type: str, class, optional
        :return: List of MetaRigNode instances.
        :rtype: list[MetaRigNode]
        """
        result = []
        all_nodes = [MetaRigNode(node) for node in pm.ls(typ="network") if node.hasAttr("metaRigType")]
        if of_type:
            if isinstance(of_type, str):
                result = [node for node in all_nodes if of_type in node.as_str()]
            else:
                result = [node for node in all_nodes if isinstance(node, of_type)]
        else:
            result = all_nodes

        return result
