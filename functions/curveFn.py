import pymel.core as pm
import luna_rig
from luna import Logger


def get_curve_data(curve):
    curve = pm.PyNode(curve)
    data_dict = {}
    if not isinstance(curve, luna_rig.nt.NurbsCurve):
        Logger.exception("Invalid NurbsCurve {}".format(curve))
        return data_dict

    # Ponts
    points = []
    for i in range(curve.controlPoints.get(s=1)):
        point_xyz = list(curve.controlPoints[i].get())
        points.append(point_xyz)

    data_dict["points"] = points
    data_dict["knots"] = curve.getKnots()
    data_dict["form"] = curve.form().index
    data_dict["degree"] = curve.degree()
    data_dict["color"] = curve.overrideColor.get()

    return data_dict


def curve_from_points(name, degree=1, points=[], parent=None):
    knot_len = len(points) + degree - 1
    if degree == 1:
        knot_vecs = [v for v in range(knot_len)]

    new_curve = pm.curve(n=name, p=points, d=degree, k=knot_vecs)  # type: luna_rig.nt.NurbsCurve
    if parent:
        pm.parent(new_curve, parent)
    return new_curve


def flip_shape(transform, across="yz"):
    if across not in ["yz", "xy", "xz"]:
        Logger.error("Invalid flip plane: {0}".format(across))
        return
    scale_vec = {"yz": [-1, 1, 1],
                 "xy": [1, 1, -1],
                 "xz": [1, -1, 1]}
    for shape in transform.getShapes():
        pm.scale(shape + ".cv[0:1000]", scale_vec.get(across), os=True)
