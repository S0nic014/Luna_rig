import pymel.core as pm
import luna_rig
import luna_rig.functions.nameFn as nameFn
import luna_rig.functions.attrFn as attrFn
from luna import Logger


class WireComponent(luna_rig.AnimComponent):

    @property
    def wire_curve(self):
        crv = self.pynode.wireCurve.get()  # type: luna_rig.nt.Transform
        return crv

    @property
    def geometry(self):
        crv = self.pynode.affectedGeometry.get()  # type: luna_rig.nt.Transform
        return crv

    @property
    def wire_deformer(self):
        dfrm = self.pynode.wireDeformer.get()  # type: luna_rig.nt.Wire
        return dfrm

    @property
    def root_control(self):
        return luna_rig.Control(self.pynode.rootControl.get())

    @property
    def shape_controls(self):
        return [luna_rig.Control(conn) for conn in self.pynode.shapeControls.listConnections(d=1)]

    @classmethod
    def create(cls,
               character=None,
               meta_parent=None,
               side='c',
               name='wire_component',
               hook=None,
               tag='', curve=None,
               geometry=None,
               dropoff_distance=100.0,
               num_controls=4):
        instance = super(WireComponent, cls).create(character=character, meta_parent=meta_parent, side=side, name=name, hook=hook, tag=tag)  # type: WireComponent
        instance.pynode.addAttr("rootControl", at="message")
        instance.pynode.addAttr("shapeControls", at="message", multi=True, im=False)
        instance.pynode.addAttr("wireCurve", at="message")
        instance.pynode.addAttr("wireDeformer", at="message")
        instance.pynode.addAttr("affectedGeometry", at="message")

        if not curve or not geometry:
            Logger.error("{0}: Requires geometry and curve to build on.")
            raise ValueError
        curve = pm.PyNode(curve)  # type: luna_rig.nt.Transform
        curve.setParent(instance.group_noscale)

        # Create deformer
        wire_deformer = pm.wire(geometry, wire=curve, n=nameFn.generate_name(instance.name, instance.side, "wire"))[0]  # type: luna_rig.nt.Wire
        wire_deformer.setWireDropOffDistance(0, dropoff_distance)
        attrFn.add_meta_attr([curve, wire_deformer])

        # Create controls
        shape_controls = []
        ctl_locator = pm.spaceLocator(n="temp_control_loc")
        # Root control
        ctl_locator.translate.set(pm.pointOnCurve(curve, pr=0.0, top=1))
        root_control = luna_rig.Control.create(name=[instance.indexed_name, "root"],
                                               side=instance.side,
                                               guide=ctl_locator,
                                               parent=instance.group_ctls,
                                               delete_guide=False,
                                               attributes="trs")

        # Shape control
        for index in range(0, num_controls + 1):
            u_value = float(index) / float(num_controls)
            ctl_locator.translate.set(pm.pointOnCurve(curve, pr=u_value, top=1))
            ctl = luna_rig.Control.create(name=[instance.indexed_name, "shape"],
                                          side=instance.side,
                                          guide=ctl_locator,
                                          parent=root_control,
                                          delete_guide=False,
                                          attributes="tr",
                                          shape="circle",
                                          orient_axis="y",
                                          joint=True)
            shape_controls.append(ctl)
        pm.delete(ctl_locator)
        pm.skinCluster([each.joint for each in shape_controls], curve, n=nameFn.generate_name([instance.indexed_name, "curve"], instance.side, "skin"))

        # Store objects
        instance._store_controls([root_control])
        instance._store_controls(shape_controls)
        curve.metaParent.connect(instance.pynode.wireCurve)
        wire_deformer.metaParent.connect(instance.pynode.wireDeformer)
        pm.connectAttr(geometry + ".message", instance.pynode.affectedGeometry)
        root_control.transform.metaParent.connect(instance.pynode.rootControl)
        for ctl in shape_controls:
            ctl.transform.metaParent.connect(instance.pynode.shapeControls, na=True)

        # Connections
        instance.attach_to_component(meta_parent, hook_index=hook)
        instance.connect_to_character(character_component=character, parent=True)
        instance.character.root_control.transform.Scale.connect(instance.wire_deformer.scale[0])

        # Scale controls
        scale_dict = {}
        for ctl in shape_controls:
            scale_dict[ctl] = 0.06
        instance.scale_controls(scale_dict)

        # House keeping
        instance.group_parts.visibility.set(False)
        instance.group_joints.visibility.set(False)

        return instance
