import pymel.core as pm
from luna import Logger
import luna_rig
import luna_rig.functions.curveFn as curveFn
import luna_rig.functions.rivetFn as rivetFn
import luna_rig.functions.nodeFn as nodeFn
import luna_rig.functions.attrFn as attrFn
import luna_rig.functions.nameFn as nameFn


class RibbonLipsComponent(luna_rig.AnimComponent):

    LEFT_STICKY_ATTR_NAME = "l_sticky_lips"
    RIGHT_STICKY_ATTR_NAME = "r_sticky_lips"

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

    @property
    def attrib_control(self):
        ctl = luna_rig.Control(self.pynode.attribControl.get())
        return ctl

    @property
    def upper_wire_blendshape(self):
        bsp = self.pynode.upperWireBlendshape.get()  # type: luna_rig.nt.BlendShape
        return bsp

    @property
    def lower_wire_blendshape(self):
        bsp = self.pynode.lowerWireBlendshape.get()  # type: luna_rig.nt.BlendShape
        return bsp

    @property
    def left_sticky_attr(self):
        attr = self.attrib_control.transform.attr(self.LEFT_STICKY_ATTR_NAME)  # type: pm.Attribute
        return attr

    @property
    def right_sticky_attr(self):
        attr = self.attrib_control.transform.attr(self.RIGHT_STICKY_ATTR_NAME)  # type: pm.Attribute
        return attr

    @classmethod
    def create(cls,
               meta_parent=None,
               side='c',
               name='lips',
               hook=0,
               character=None,
               tag='face',
               create_end_knots=True,
               sticky_attrs_control=None,
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
        instance.pynode.addAttr("upperWireBlendshape", at="message")
        instance.pynode.addAttr("lowerWireBlendshape", at="message")
        instance.pynode.addAttr("attribControl", at="message")
        if not upper_curve or not lower_curve:
            Logger.error("{0}: Requires upper and lower NURBS curves to build on".format(instance))
            raise ValueError
        if not sticky_attrs_control:
            Logger.error("{0}: Requires a control to store sticky attributes to".format(instance))
            raise ValueError
        elif not isinstance(sticky_attrs_control, luna_rig.Control):
            try:
                sticky_attrs_control = luna_rig.Control(sticky_attrs_control)
            except Exception:
                Logger.exception("{0}: Failed to create Control instance from {1}".format(instance, sticky_attrs_control))
                raise

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
        if create_end_knots:
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
            upper_sticky_curve.setParent(instance.group_noscale)
            attrFn.add_meta_attr(upper_sticky_curve)
        if not lower_sticky_override:
            lower_sticky_curve = pm.duplicate(lower_bound_curve)[0]  # type: luna_rig.nt.Transform
            lower_sticky_curve.rename(nameFn.generate_name([instance.indexed_name, "lower", "sticky"], instance.side, "crv"))
        else:
            lower_sticky_curve = pm.PyNode(lower_sticky_override)
            lower_sticky_curve.setParent(instance.group_noscale)
            attrFn.add_meta_attr(lower_sticky_curve)

        # Wire curves
        upper_wire_curve = pm.duplicate(upper_bound_curve)[0]  # type: luna_rig.nt.Transform
        upper_wire_curve.rename(nameFn.generate_name([instance.indexed_name, "upper", "wire"], instance.side, "crv"))
        lower_wire_curve = pm.duplicate(lower_bound_curve)[0]  # type: luna_rig.nt.Transform
        lower_wire_curve.rename(nameFn.generate_name([instance.indexed_name, "lower", "wire"], instance.side, "crv"))

        # Wire blendshapes
        upper_wire_blendshape = pm.blendShape(upper_bound_curve,
                                              upper_sticky_curve,
                                              upper_wire_curve,
                                              n=nameFn.generate_name([instance.indexed_name, "upper", "wire"], instance.side, "bsp"))[0]
        lower_wire_blendshape = pm.blendShape(lower_bound_curve,
                                              lower_sticky_curve,
                                              lower_wire_curve,
                                              n=nameFn.generate_name([instance.indexed_name, "lower", "wire"], instance.side, "bsp"))[0]
        attrFn.add_meta_attr(upper_wire_blendshape)
        attrFn.add_meta_attr(lower_wire_blendshape)

        # Add attributes
        attrFn.add_divider(sticky_attrs_control.transform, attr_name="LIPS")
        sticky_attrs_control.transform.addAttr(cls.LEFT_STICKY_ATTR_NAME, nn="Left sticky lips", at="float", min=0.0, max=10.0, dv=0.0, k=True)
        sticky_attrs_control.transform.addAttr(cls.RIGHT_STICKY_ATTR_NAME, nn="Right sticky lips", at="float", min=0.0, max=10.0, dv=0.0, k=True)

        # Connections
        upper_bound_curve.metaParent.connect(instance.pynode.upperBoundCurve)
        lower_bound_curve.metaParent.connect(instance.pynode.lowerBoundCurve)
        upper_sticky_curve.metaParent.connect(instance.pynode.upperStickyCurve)
        lower_sticky_curve.metaParent.connect(instance.pynode.lowerStickyCurve)
        upper_wire_curve.metaParent.connect(instance.pynode.upperWireCurve)
        lower_wire_curve.metaParent.connect(instance.pynode.lowerWireCurve)
        upper_wire_blendshape.metaParent.connect(instance.pynode.upperWireBlendshape)
        lower_wire_blendshape.metaParent.connect(instance.pynode.lowerWireBlendshape)
        sticky_attrs_control.transform.message.connect(instance.pynode.attribControl)

        # Blend
        instance._setup_sticky_blend()

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

    def _setup_sticky_blend(self):
        lip_val_list = [self.upper_wire_curve.getShape().numCVs(), self.lower_wire_curve.getShape().numCVs()]
        lip_names = ["upper", "lower"]
        blendshapes = [self.upper_wire_blendshape, self.lower_wire_blendshape]

        for num_cvs, lip_name, wire_blendshape in zip(lip_val_list, lip_names, blendshapes):
            # Left side
            half_val = (num_cvs / 2) + 1
            div_val = 10.0 / half_val
            counter = 0
            while(counter < half_val):
                # Normal range
                lip_range_node = nodeFn.create("setRange", [self.indexed_name, lip_name], self.side, "range")
                lip_range_node.oldMaxX.set(div_val * (counter + 1))
                lip_range_node.oldMinX.set(div_val * counter)
                lip_range_node.maxX.set(0)
                lip_range_node.minX.set(1)
                if counter == half_val - 1:
                    lip_range_node.minX.set(0.5)
                self.left_sticky_attr.connect(lip_range_node.valueX, f=True)

                # Flip range
                lip_flip_range_node = nodeFn.create("setRange", [self.indexed_name, lip_name, "flip"], self.side, "range")
                lip_flip_range_node.oldMaxX.set(1)
                if counter == half_val - 1:
                    lip_flip_range_node.oldMaxX.set(0.5)
                lip_flip_range_node.oldMinX.set(0)
                lip_flip_range_node.maxX.set(0)
                lip_flip_range_node.minX.set(1)
                if counter == half_val - 1:
                    lip_flip_range_node.minX.set(0.5)
                lip_range_node.outValueX.connect(lip_flip_range_node.valueX, f=True)

                # Blendshape connection
                if counter == half_val - 1:
                    mid_pma = nodeFn.create("plusMinusAverage", [self.indexed_name, lip_name], self.side, "range")
                    lip_range_node.outValueX.connect(mid_pma.input2D[0].input2Dx, f=True)
                    lip_flip_range_node.outValueX.connect(mid_pma.input2D[0].input2Dy, f=True)
                else:
                    lip_range_node.outValueX.connect(wire_blendshape.inputTarget[0].inputTargetGroup[0].targetWeights[counter], f=True)
                    lip_flip_range_node.outValueX.connect(wire_blendshape.inputTarget[0].inputTargetGroup[1].targetWeights[counter], f=True)

                counter += 1

            # Right side
            counter = half_val - 1
            rev_counter = half_val
            while(counter < num_cvs):
                # Normal range
                lip_range_node = nodeFn.create("setRange", [self.indexed_name, lip_name], self.side, "range")
                lip_range_node.oldMaxX.set(div_val * rev_counter)
                lip_range_node.oldMinX.set(div_val * (rev_counter - 1))
                lip_range_node.maxX.set(0)
                lip_range_node.minX.set(1)
                if counter == (half_val - 1):
                    lip_range_node.minX.set(0.5)
                self.right_sticky_attr.connect(lip_range_node.valueX, f=True)

                # Flip range
                lip_flip_range_node = nodeFn.create("setRange", [self.indexed_name, lip_name, "flip"], self.side, "range")
                lip_flip_range_node.oldMaxX.set(1)
                if counter == half_val - 1:
                    lip_flip_range_node.oldMaxX.set(0.5)
                lip_flip_range_node.oldMinX.set(0)
                lip_flip_range_node.maxX.set(0)
                lip_flip_range_node.minX.set(1)
                if counter == half_val - 1:
                    lip_flip_range_node.minX.set(0.5)
                lip_range_node.outValueX.connect(lip_flip_range_node.valueX, f=True)

                # Blendshape connection
                if counter == half_val - 1:
                    lip_range_node.outValueX.connect(mid_pma.input2D[1].input2Dx, f=True)
                    lip_flip_range_node.outValueX.connect(mid_pma.input2D[1].input2Dy, f=True)
                    mid_pma.output2Dx.connect(wire_blendshape.inputTarget[0].inputTargetGroup[0].targetWeights[counter], f=True)
                    mid_pma.output2Dy.connect(wire_blendshape.inputTarget[0].inputTargetGroup[1].targetWeights[counter], f=True)
                else:
                    lip_range_node.outValueX.connect(wire_blendshape.inputTarget[0].inputTargetGroup[0].targetWeights[counter], f=True)
                    lip_flip_range_node.outValueX.connect(wire_blendshape.inputTarget[0].inputTargetGroup[1].targetWeights[counter], f=True)

                counter += 1
                rev_counter -= 1
