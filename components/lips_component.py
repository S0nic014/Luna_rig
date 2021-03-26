import pymel.core as pm
from luna import Logger
import luna_rig
import luna_rig.functions.curveFn as curveFn
import luna_rig.functions.rivetFn as rivetFn
import luna_rig.functions.attrFn as attrFn
import luna_rig.functions.nameFn as nameFn


class RibbonLipsComponent(luna_rig.AnimComponent):

    @property
    def upper_bound_curve(self):
        crv = self.pynode.upperBoundCurve.get()  # type: luna_rig.nt.Transform
        return crv

    @property
    def lower_bound_curve(self):
        crv = self.pynode.lowerBoundCurve.get()  # type: luna_rig.nt.Transform
        return crv

    @property
    def upper_sticky_curve(self):
        crv = self.pynode.upperStickyCurve.get()  # type: luna_rig.nt.Transform
        return crv

    @property
    def lower_sticky_curve(self):
        crv = self.pynode.lowerStickyCurve.get()  # type: luna_rig.nt.Transform
        return crv

    @property
    def upper_wire_curve(self):
        crv = self.pynode.upperWireCurve.get()  # type: luna_rig.nt.Transform
        return crv

    @property
    def lower_wire_curve(self):
        crv = self.pynode.lowerWireCurve.get()  # type: luna_rig.nt.Transform
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
               lower_curve=None,
               upper_sticky_override=None,
               lower_sticky_override=None):
        instance = super(RibbonLipsComponent, cls).create(meta_parent=meta_parent, side=side, name=name, hook=hook, character=character, tag=tag)  # type: RibbonLipsComponent
        instance.pynode.addAttr("upperBoundCurve", at="message")
        instance.pynode.addAttr("lowerBoundCurve", at="message")
        instance.pynode.addAttr("upperStickyCurve", at="message")
        instance.pynode.addAttr("lowerStickyCurve", at="message")
        instance.pynode.addAttr("upperWireCurve", at="message")
        instance.pynode.addAttr("lowerWireCurve", at="message")
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

        # Insert knots
        curveFn.insert_end_knots(upper_curve)
        curveFn.insert_end_knots(lower_curve)

        # Bound curves
        upper_bound_curve = pm.duplicate(upper_curve)[0]  # type: luna_rig.nt.Transform
        upper_bound_curve.rename(nameFn.generate_name([instance.indexed_name, "upper", "bound"], instance.side, "crv"))
        pm.rebuildCurve(upper_bound_curve, d=3, ch=0, kcp=True, kr=0, kt=0, kep=True)
        lower_bound_curve = pm.duplicate(lower_curve)[0]  # type: luna_rig.nt.Transform
        lower_bound_curve.rename(nameFn.generate_name([instance.indexed_name, "lower", "bound"], instance.side, "crv"))
        pm.rebuildCurve(lower_bound_curve, d=3, ch=0, kcp=True, kr=0, kt=0, kep=True)

        # Sticky curves
        if not upper_sticky_override:
            upper_sticky_curve = pm.duplicate(upper_bound_curve)[0]  # type: luna_rig.nt.Transform
            upper_sticky_curve.rename(nameFn.generate_name([instance.indexed_name, "upper", "sticky"], instance.side, "crv"))
        else:
            upper_sticky_curve = pm.PyNode(upper_sticky_override)
            attrFn.add_meta_attr(upper_sticky_curve)
        if not lower_sticky_override:
            lower_sticky_curve = pm.duplicate(lower_bound_curve)[0]  # type: luna_rig.nt.Transform
            lower_sticky_curve.rename(nameFn.generate_name([instance.indexed_name, "lower", "sticky"], instance.side, "crv"))
        else:
            lower_sticky_curve = pm.PyNode(lower_sticky_override)
            attrFn.add_meta_attr(lower_sticky_curve)

        # Wire curves
        upper_wire_curve = pm.duplicate(upper_bound_curve)[0]  # type: luna_rig.nt.Transform
        upper_wire_curve.rename(nameFn.generate_name([instance.indexed_name, "upper", "wire"], instance.side, "crv"))
        lower_wire_curve = pm.duplicate(lower_bound_curve)[0]  # type: luna_rig.nt.Transform
        lower_wire_curve.rename(nameFn.generate_name([instance.indexed_name, "lower", "wire"], instance.side, "crv"))

        # Connections
        upper_bound_curve.metaParent.connect(instance.pynode.upperBoundCurve)
        lower_bound_curve.metaParent.connect(instance.pynode.lowerBoundCurve)
        upper_sticky_curve.metaParent.connect(instance.pynode.upperStickyCurve)
        lower_sticky_curve.metaParent.connect(instance.pynode.lowerStickyCurve)
        upper_wire_curve.metaParent.connect(instance.pynode.upperWireCurve)
        lower_wire_curve.metaParent.connect(instance.pynode.lowerWireCurve)

        # Cleanup
        pm.delete([upper_curve, lower_curve])

        return instance

    def apply_skin_weights(self, source_mesh):
        try:
            mesh_skin = pm.listHistory(source_mesh, type="skinCluster")[0]  # type: luna_rig.nt.SkinCluster
        except IndexError:
            Logger.error("{0}: Failed to get skinCluster from {1}".format(self, source_mesh))
        # Bound
        upper_bound_skin = pm.skinCluster(mesh_skin.getWeightedInfluence(), self.upper_bound_curve)  # type: luna_rig.nt.SkinCluster
        pm.copySkinWeights(sourceSkin=mesh_skin, destinationSkin=upper_bound_skin, sa="closestPoint", ia=["closestJoint", "oneToOne"], noMirror=True)
        lower_bound_skin = pm.skinCluster(mesh_skin.getWeightedInfluence(), self.lower_bound_curve)  # type: luna_rig.nt.SkinCluster
        pm.copySkinWeights(sourceSkin=mesh_skin, destinationSkin=lower_bound_skin, sa="closestPoint", ia=["closestJoint", "oneToOne"], noMirror=True)

        # Sticky
        upper_sticky_skin = pm.skinCluster(mesh_skin.getWeightedInfluence(), self.upper_sticky_curve)  # type: luna_rig.nt.SkinCluster
        pm.copySkinWeights(sourceSkin=upper_bound_skin, destinationSkin=upper_sticky_skin, sa="closestPoint", ia=["closestJoint", "oneToOne"], noMirror=True)
        lower_sticky_skin = pm.skinCluster(mesh_skin.getWeightedInfluence(), self.lower_sticky_curve)  # type: luna_rig.nt.SkinCluster
        pm.copySkinWeights(sourceSkin=lower_bound_skin, destinationSkin=lower_sticky_skin, sa="closestPoint", ia=["closestJoint", "oneToOne"], noMirror=True)
        # Upper sticky skin percent
        upper_mid_weights = curveFn.get_skin_persent(self.upper_sticky_curve, upper_sticky_skin, 0)
        for cv_index in range(self.upper_sticky_curve.getShape().numCVs()):
            pm.skinPercent(upper_sticky_skin, self.upper_sticky_curve, transformValue=upper_mid_weights)
        # Lower sticky skin percent
        lower_mid_weights = curveFn.get_skin_persent(self.lower_sticky_curve, lower_sticky_skin, 0)
        for cv_index in range(self.lower_sticky_curve.getShape().numCVs()):
            pm.skinPercent(lower_sticky_skin, self.lower_sticky_curve, transformValue=lower_mid_weights)
