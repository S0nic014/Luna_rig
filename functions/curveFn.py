import pymel.core as pm
from Luna import Logger


def get_curve_data(curve):
    curve = pm.PyNode(curve)
    data_dict = {}
    if not isinstance(curve, pm.nodetypes.NurbsCurve):
        Logger.exception("Invalid NurbsCurve {}".format(curve))
        return data_dict

    # Ponts
    points = []
    for i in range(curve.controlPoints.get(s=1)):
        point_xyz = list(curve.controlPoints[i].get())
        points.append(point_xyz)

    data_dict["type"] = curve.nodeType()
    data_dict["points"] = points
    data_dict["knots"] = curve.getKnots()
    data_dict["form"] = curve.form().index
    data_dict["degree"] = curve.degree()
    data_dict["color"] = curve.overrideColor.get()

    return data_dict
