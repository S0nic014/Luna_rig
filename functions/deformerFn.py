import pymel.core as pm


def is_painted(cls, deformer_node):
    return deformer_node.weightList.get(size=True) > 0


def get_deformer(node, type):
    node = pm.PyNode(node)
    def_list = node.listHistory(type=type)
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
