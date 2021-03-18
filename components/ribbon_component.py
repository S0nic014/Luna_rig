import pymel.core as pm
from luna import Logger
import luna_rig
import luna_rig.functions.jointFn as jointFn
import luna_rig.functions.nodeFn as nodeFn
import luna_rig.functions.attrFn as attrFn
import luna_rig.functions.nameFn as nameFn

# Curve based


class CurveRibbonComponent(luna_rig.AnimComponent):

    @property
    def shape_controls(self):
        connected_nodes = self.pynode.shapeControls.listConnections()  # type: list[luna_rig.nt.Transform]
        all_ctls = [luna_rig.Control(node) for node in connected_nodes]
        return all_ctls

    @classmethod
    def create(cls,
               meta_parent=None,
               side='c',
               name='curve_ribbon',
               hook=0,
               character=None,
               curve=None,
               num_joints=5,
               skel_joint_parent=None,
               forward_axis="x",
               fk_hierarchy=False,
               up_axis="y"):

        instance = super(CurveRibbonComponent, cls).create(meta_parent=meta_parent, side=side, name=name, hook=hook, character=character)  # type: CurveRibbonComponent
        instance.pynode.addAttr("curve", at="message")
        instance.pynode.addAttr("shapeControls", at="message", multi=True, im=False)

        if not curve:
            Logger.exception("{0}: component requires either curve or ribbon joints for creation.".format(instance))
            raise ValueError
        if not skel_joint_parent:
            skel_joint_parent = instance.group_joints

        if not isinstance(curve, pm.PyNode):
            curve = pm.PyNode(curve)  # type: luna_rig.nt.Transform
        if not isinstance(curve.getShape(), luna_rig.nt.NurbsCurve):
            Logger.exception("{0}: object {1} is not a NURBS curve".format(instance, curve))
            raise TypeError
        ctl_chain = jointFn.along_curve(curve,
                                        num_joints,
                                        joint_name=[instance.name, "ctl"],
                                        joint_side=instance.side,
                                        joint_suffix="jnt",
                                        delete_curve=False)
        ctl_jnt_groups = [jointFn.group_joint(jnt, parent=instance.group_joints) for jnt in ctl_chain]

        # Add meta attributes
        attrFn.add_meta_attr(curve)

        # Set curve attrs, parent
        curve.inheritsTransform.set(False)
        curve.setParent(instance.group_parts)

        # Attach to motion paths
        for index, ctl_group in enumerate(ctl_jnt_groups):
            u_value = float(index) / float(num_joints - 1.0)
            motion_path = pm.pathAnimation(ctl_group.group,
                                           c=curve,
                                           n=nameFn.generate_name([instance.indexed_name, "ctl"], instance.side, "mpath"),
                                           wut="objectrotation",
                                           wuo=instance.group_ctls,
                                           fa=forward_axis,
                                           ua=up_axis)
            pm.cutKey(motion_path)
            pm.setAttr(motion_path + ".uValue", u_value)

        # Create controls
        shape_controls = []
        for ctl_struct in ctl_jnt_groups:
            shape_ctl = luna_rig.Control.create(name=[instance.indexed_name, "shape"],
                                                side=instance.side,
                                                guide=ctl_struct.joint,
                                                attributes="trs",
                                                delete_guide=False,
                                                joint=True,
                                                shape="circle",
                                                parent=instance.group_ctls)
            shape_ctl.transform.scale.connect(ctl_struct.joint.scale)
            shape_controls.append(shape_ctl)
        pm.skinCluster([ctl.joint for ctl in shape_controls], curve, n=nameFn.generate_name([instance.indexed_name, "crv"], instance.side, "skin"))
        if fk_hierarchy:
            for ctl_index in range(len(shape_controls) - 1):
                shape_controls[ctl_index + 1].set_parent(shape_controls[ctl_index])

        # Output joints
        bind_joints = []
        for ctl_jnt in ctl_chain:
            bind_jnt = nodeFn.create("joint", instance.name, instance.side, suffix="jnt")
            pm.matchTransform(bind_jnt, ctl_jnt)
            bind_jnt.setParent(skel_joint_parent)
            bind_joints.append(bind_jnt)

        # Store objects
        curve.metaParent.connect(instance.pynode.curve)
        for shape_ctl in shape_controls:
            shape_ctl.transform.metaParent.connect(instance.pynode.shapeControls, na=True)
        instance._store_bind_joints(bind_joints)
        instance._store_ctl_chain(ctl_chain)
        instance._store_controls(shape_controls)

        # Attach
        instance.attach_to_component(meta_parent, hook_index=hook)
        instance.connect_to_character(character_component=character, parent=True)

        # Scale controls
        scale_dict = {}
        for ctl in shape_controls:
            scale_dict[ctl] = 0.06
        instance.scale_controls(scale_dict)

        # Housekeeping
        instance.group_joints.visibility.set(False)
        instance.group_parts.visibility.set(False)
        return instance

    def attach_to_skeleton(self):
        super(CurveRibbonComponent, self).attach_to_skeleton()
        for ctl_jnt, bind_jnt in zip(self.ctl_chain, self.bind_joints):
            pm.scaleConstraint(ctl_jnt, bind_jnt)

    def attach_to_component(self, other_comp, hook_index=None):
        super(CurveRibbonComponent, self).attach_to_component(other_comp, hook_index=hook_index)
        if self.in_hook:
            pm.parentConstraint(self.in_hook.transform, self.group_ctls, mo=1)


class CurveRibbonBrow(CurveRibbonComponent):
    @property
    def main_control(self):
        transform = self.pynode.mainControl.get()
        if not transform:
            return None
        else:
            return luna_rig.Control(transform)

    @classmethod
    def create(cls,
               meta_parent=None,
               side='c',
               name='brow',
               hook=0,
               character=None,
               curve=None,
               num_joints=5,
               skel_joint_parent=None,
               forward_axis='x',
               main_ctl_guide=None,
               up_axis='y'):
        instance = super(CurveRibbonBrow, cls).create(meta_parent=meta_parent, side=side, name=name, hook=hook, character=character,
                                                      curve=curve, num_joints=num_joints, fk_hierarchy=False, skel_joint_parent=skel_joint_parent, forward_axis=forward_axis, up_axis=up_axis)  # type: CurveRibbonBrow
        instance.pynode.addAttr("mainControl", at="message")

        # Create main control
        main_ctl = luna_rig.Control.create(name=[instance.indexed_name, "main"],
                                           side=instance.side,
                                           guide=main_ctl_guide,
                                           delete_guide=True,
                                           attributes="trs",
                                           shape="circle",
                                           orient_axis="z",
                                           parent=instance.group_ctls)
        for shp_ctl in instance.shape_controls:
            shp_ctl.group.setParent(main_ctl.transform)

        instance._store_controls([main_ctl])

        # Scale control
        scale_dict = {main_ctl: 0.06}
        instance.scale_controls(scale_dict)

        return instance
