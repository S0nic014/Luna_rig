import pymel.core as pm
import pymel.api as pma
import luna_rig


# Modified from https://gist.github.com/rondreas/1c6d4e5fc6535649780d5b65fc5a9283
def mirror_xform(transforms=[], across="yz", behaviour=True, space="world"):
    """
    :param transforms: Transforms to mirror, defaults to []
    :type transforms: list or str or pm.PyNode, optional
    :param across: Plane to mirror across, options("YZ", "XY", "XZ"), defaults to 'YZ'
    :type across: str, optional
    :param behaviour: If behavior should be mirrored, defaults to True
    :type behaviour: bool, optional
    :param space: Space to mirror across, valid options(transform or "world") , defaults to "world"
    :type space: str, optional
    :raises ValueError: If invalid object passed as transform.
    :raises ValueError: If invalid mirror plane
    """
    if isinstance(transforms, str) or isinstance(transforms, pm.PyNode):
        transforms = [transforms]
    transforms = [pm.PyNode(node) for node in transforms]  # type: list(luna_rig.nt.Transform])
    # Check to see all provided objects is an instance of pymel transform node,
    if not all(map(lambda x: isinstance(x, pm.nt.Transform), transforms)):
        raise ValueError("Passed node which wasn't of type: Transform")

    # Validate plane which to mirror across
    across = across.lower()
    if across not in ('xy', 'yz', 'xz'):
        raise ValueError("Keyword Argument: 'across' not of accepted value ('xy', 'yz', 'xz').")

    stored_matrices = {}
    for transform in transforms:
        # Get the worldspace matrix, as a list of 16 float values
        if space == "world":
            mtx = pm.xform(transform, q=True, ws=True, m=True)
        else:
            mtx = matrix_to_list(relative_world_matrix(transform, space))
        # Invert rotation columns,
        rx = [n * -1 for n in mtx[0:9:4]]
        ry = [n * -1 for n in mtx[1:10:4]]
        rz = [n * -1 for n in mtx[2:11:4]]
        # Invert translation row,
        t = [n * -1 for n in mtx[12:15]]
        # Set matrix based on given plane, and whether to include behaviour or not.
        if across == "xy":
            mtx[14] = t[2]    # set inverse of the Z translation
            # Set inverse of all rotation columns but for the one we've set translate to.
            if behaviour:
                mtx[0:9:4] = rx
                mtx[1:10:4] = ry
        elif across == "yz":
            mtx[12] = t[0]    # set inverse of the X translation
            if behaviour:
                mtx[1:10:4] = ry
                mtx[2:11:4] = rz
        else:
            mtx[13] = t[1]    # set inverse of the Y translation

            if behaviour:
                mtx[0:9:4] = rx
                mtx[2:11:4] = rz
        stored_matrices[transform] = mtx
    for transform in transforms:
        transform.setMatrix(stored_matrices[transform], ws=(space == "world"))


def world_matrix(transform):
    """Get transform world matrix

    :param transform: Transform obj
    :type transform: str or pm.PyNode
    :return: World matrix
    :rtype: MMatrix
    """
    transform = pm.PyNode(transform)
    return pma.MMatrix(transform.getMatrix(ws=True))


def relative_world_matrix(transform, parent_space):
    """Get relative matrix

    :param transform: Transform object
    :type transform: str or pm.PyNode
    :param parent_space: Relative space transform
    :type parent_space: str or pm.PyNode
    :return: Relative matrix
    :rtype: MMatrix
    """
    transform = pm.PyNode(transform)
    parent_space = pm.PyNode(parent_space)
    mtx = world_matrix(transform) * world_matrix(parent_space).inverse()
    return mtx


def matrix_to_list(mtx):
    """Convert MMatrix to python list.

    :param mtx: Matrix to convert.
    :type mtx: pymel.api.MMatrix
    :return: Matrix as list
    :rtype: list
    """
    mtx_list = list(mtx)
    flat_list = [value for array in mtx_list for value in list(array)]
    return flat_list
