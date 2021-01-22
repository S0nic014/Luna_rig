import pymel.core as pm


def hide(node, visibility=False):
    """Hide node

    :param node: Node to hide
    :type node: str or PyNode
    :param visibility: Node visibility attr, defaults to False
    :type visibility: bool, optional
    """
    if pm.objExists(node):
        pm.setAttr(node + '.v', visibility)
        pm.setAttr(node + '.hiddenInOutliner', True)


def fade(node):
    """Fade node in outliner

    :param node: Node to fade
    :type node: str or PyNode
    """
    pm.setAttr(node + '.useOutlinerColor', True)
    pm.setAttr(node + '.outlinerColor', 0.5, 0.5, 0.5)


def set_color(node, rgb=[0, 0, 0]):
    """Set color in outliner.

    :param node: Node to set color for.
    :type node: str or Pynode
    :param rgb: RGB values, defaults to []
    :type rgb: list, optional
    """
    if isinstance(rgb, list) or isinstance(rgb, tuple):
        while len(rgb) < 3:
            rgb.append(0.0)

        # Apply colors
        pm.setAttr(node + '.useOutlinerColor', True)
        pm.setAttr(node + '.outlinerColor', rgb[0], rgb[1], rgb[2])
