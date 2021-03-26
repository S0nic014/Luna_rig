import pymel.core as pm
from luna import Logger
import luna_rig
import luna_rig.functions.curveFn as curveFn
import luna_rig.functions.rivetFn as rivetFn
import luna_rig.functions.attrFn as attrFn
import luna_rig.functions.nameFn as nameFn


class RibbonLipsComponent(luna_rig.AnimComponent):
    @property
    def upper_linear_curve(self):
        crv = self.pynode.upperLinearCurve.get()  # type: luna_rig.nt.Transform
        return crv

    @property
    def lower_linear_curve(self):
        crv = self.pynode.lowerLinearCurve.get()  # type: luna_rig.nt.Transform
        return crv

    @classmethod
    def create(cls,
               meta_parent=None,
               side='c',
               name='lips',
               hook=0,
               character=None,
               tag='face',
               upper_curve=None,
               lower_curve=None,):
        instance = super(RibbonLipsComponent, cls).create(meta_parent=meta_parent, side=side, name=name, hook=hook, character=character, tag=tag)  # type: RibbonLipsComponent
        instance.pynode.addAttr("upperLinearCurve", at="message")
        instance.pynode.addAttr("lowerLinearCurve", at="message")
        if not upper_curve or not lower_curve:
            Logger.error("{0}: Requires upper and lower NURBS curves to build on".format(instance))
            raise ValueError

        # PyNode convert
        if not isinstance(upper_curve, pm.PyNode):
            upper_curve = pm.PyNode(upper_curve)  # type: luna_rig.nt.Transform
        if not isinstance(lower_curve, pm.PyNode):
            lower_curve = pm.PyNode(lower_curve)  # type: luna_rig.nt.Transform
        attrFn.add_meta_attr(upper_curve)
        attrFn.add_meta_attr(lower_curve)
        upper_curve.setParent(instance.group_noscale)
        lower_curve.setParent(instance.group_noscale)

        # Bound curves
        upper_bound_curve = pm.duplicate(upper_curve)[0]  # type: luna_rig.nt.Transform
        upper_bound_curve.rename(nameFn.generate_name([instance.indexed_name, "upper", "bound"], instance.side, "crv"))
        pm.rebuildCurve(upper_bound_curve, d=3, ch=0, kcp=True, kr=0, kt=0, kep=True)
        lower_bound_curve = pm.duplicate(lower_curve)[0]  # type: luna_rig.nt.Transform
        lower_bound_curve.rename(nameFn.generate_name([instance.indexed_name, "lower", "bound"], instance.side, "crv"))
        pm.rebuildCurve(lower_bound_curve, d=3, ch=0, kcp=True, kr=0, kt=0, kep=True)

        # Sticky curves
        upper_sticky_curve = pm.duplicate(upper_bound_curve)[0]  # type: luna_rig.nt.Transform
        upper_sticky_curve.rename(nameFn.generate_name([instance.indexed_name, "upper", "sticky"], instance.side, "crv"))
        lower_sticky_curve = pm.duplicate(lower_bound_curve)[0]  # type: luna_rig.nt.Transform
        lower_sticky_curve.rename(nameFn.generate_name([instance.indexed_name, "lower", "sticky"], instance.side, "crv"))

        # Wire curves
        upper_wire_curve = pm.duplicate(upper_bound_curve)[0]  # type: luna_rig.nt.Transform
        upper_wire_curve.rename(nameFn.generate_name([instance.indexed_name, "upper", "wire"], instance.side, "crv"))
        lower_wire_curve = pm.duplicate(lower_bound_curve)[0]  # type: luna_rig.nt.Transform
        lower_wire_curve.rename(nameFn.generate_name([instance.indexed_name, "lower", "wire"], instance.side, "crv"))

        # Connections
        upper_curve.metaParent.connect(instance.pynode.upperLinearCurve)
        lower_curve.metaParent.connect(instance.pynode.lowerLinearCurve)

        return instance

    def apply_skin_weights(self, source_mesh):
        try:
            mesh_skin = pm.listHistory(source_mesh, type="skinCluster")[0]  # type: luna_rig.nt.SkinCluster
        except IndexError:
            Logger.error("{0}: Failed to get skinCluster from {1}".format(self, source_mesh))
        # Upper
        upper_skin = pm.skinCluster(mesh_skin.getWeightedInfluence(), self.upper_linear_curve)  # type: luna_rig.nt.SkinCluster
        pm.copySkinWeights(sourceSkin=mesh_skin, destinationSkin=upper_skin, sa="closestPoint", ia=["closestJoint", "oneToOne"], noMirror=True)

        # Lower
        lower_skin = pm.skinCluster(mesh_skin.getWeightedInfluence(), self.lower_linear_curve)
        pm.copySkinWeights(sourceSkin=mesh_skin, destinationSkin=lower_skin, sa="closestPoint", ia=["closestJoint", "oneToOne"], noMirror=True)
