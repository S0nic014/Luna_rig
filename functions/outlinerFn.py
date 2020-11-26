import pymel.core as pm


def hide(node, visibility=False):
    if pm.objExists(node):
        pm.setAttr(node + '.v', visibility)
        pm.setAttr(node + '.hiddenInOutliner', True)


def fade(node):
    pm.setAttr(node + '.useOutlinerColor', True)
    pm.setAttr(node + '.outlinerColor', 0.5, 0.5, 0.5)


def set_color(node, rgb=[]):
    if isinstance(rgb, list) or isinstance(rgb, tuple):
        while len(rgb) < 3:
            rgb.append(0.0)

        # Apply colors
        pm.setAttr(node + '.useOutlinerColor', True)
        pm.setAttr(node + '.outlinerColor', rgb[0], rgb[1], rgb[2])
