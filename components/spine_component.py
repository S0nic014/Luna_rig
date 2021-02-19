import pymel.core as pm

from luna import Logger
from luna.utils import enumFn
import luna_rig
from luna_rig.functions import jointFn
from luna_rig.functions import attrFn
from luna_rig.functions import curveFn
from luna_rig.functions import nameFn


class SpineComponent(luna_rig.AnimComponent):

    @property
    def root_control(self):
        return luna_rig.Control(self.pynode.rootControl.listConnections()[0])

    @property
    def hips_control(self):
        return luna_rig.Control(self.pynode.hipsControl.listConnections()[0])

    @property
    def chest_control(self):
        return luna_rig.Control(self.pynode.chestControl.listConnections()[0])

    @classmethod
    def create(cls,
               meta_parent=None,
               side='c',
               name='spine'):
        # Create instance and add attrs
        instance = super(SpineComponent, cls).create(meta_parent, side, name)  # type: FKIKSpineComponent
        instance.pynode.addAttr("rootControl", at="message")
        instance.pynode.addAttr("hipsControl", at="message")
        instance.pynode.addAttr("chestControl", at="message")
        return instance

    def add_stretch(self, default_value=False):
        pass

    def add_free_pivot(self):
        pass


class FKIKSpineComponent(SpineComponent):

    class Hooks(enumFn.Enum):
        ROOT = 0
        HIPS = 1
        MID = 2
        CHEST = 3

    @property
    def mid_control(self):
        return luna_rig.Control(self.pynode.midControl.listConnections()[0])

    @property
    def fk1_control(self):
        return luna_rig.Control(self.pynode.fkControls.listConnections()[0])

    @property
    def fk2_control(self):
        return luna_rig.Control(self.pynode.fkControls.listConnections()[1])

    @property
    def pivot_control(self):
        if not self.pynode.hasAttr("pivotControl"):
            return None
        else:
            return luna_rig.Control(self.pynode.pivotControl.listConnections()[0])

    @classmethod
    def create(cls,
               meta_parent=None,
               hook=0,
               side='c',
               name='spine',
               start_joint=None,
               end_joint=None):
        # Create instance and add attrs
        instance = super(FKIKSpineComponent, cls).create(meta_parent, side, name)  # type: FKIKSpineComponent
        instance.pynode.addAttr("fkControls", at="message", multi=1, im=0)
        instance.pynode.addAttr("midControl", at="message")

        # Joint chains
        joint_chain = jointFn.joint_chain(start_joint, end_joint)
        jointFn.validate_rotations(joint_chain)
        for jnt in joint_chain:
            attrFn.add_meta_attr(jnt)
        ctl_chain = jointFn.duplicate_chain(original_chain=joint_chain, add_name="ctl", new_parent=instance.group_joints)

        # Create IK curve and handle
        ik_curve_points = [jnt.getTranslation(space="world") for jnt in joint_chain]
        ik_curve = curveFn.curve_from_points(name=nameFn.generate_name([instance.indexed_name, "ik"], side=instance.side, suffix="crv"),
                                             points=ik_curve_points,
                                             parent=instance.group_parts)
        pm.rebuildCurve(ik_curve, d=3, kep=1, rpo=1, ch=0, tol=0.01, spans=4)
        ik_curve.inheritsTransform.set(0)
        ik_handle = pm.ikHandle(n=nameFn.generate_name([instance.name], side=instance.side, suffix="ikh"),
                                sj=ctl_chain[0],
                                ee=ctl_chain[-1],
                                c=ik_curve,
                                sol="ikSplineSolver",
                                roc=1,
                                pcv=0,
                                ccv=0,
                                scv=0)[0]
        pm.parent(ik_handle, instance.group_parts)

        # Create IK controls
        ctl_locator = pm.spaceLocator(n="temp_control_loc")
        ctl_locator.translate.set(pm.pointOnCurve(ik_curve, pr=0.0, top=1))
        # Root
        root_control = luna_rig.Control.create(side=instance.side,
                                               name="{0}_root".format(instance.indexed_name),
                                               object_to_match=ctl_locator,
                                               delete_match_object=False,
                                               parent=instance.group_ctls,
                                               joint=False,
                                               attributes="tr",
                                               color="red",
                                               shape="root",
                                               orient_axis="y")
        # Hips
        hips_control = luna_rig.Control.create(side=instance.side,
                                               name="{0}_hips".format(instance.indexed_name),
                                               object_to_match=ctl_locator,
                                               delete_match_object=False,
                                               parent=root_control,
                                               joint=True,
                                               attributes="tr",
                                               shape="hips",
                                               orient_axis="y")
        # Mid
        ctl_locator.translate.set(pm.pointOnCurve(ik_curve, pr=0.5, top=1))
        mid_control = luna_rig.Control.create(side=instance.side,
                                              name="{0}_mid".format(instance.indexed_name),
                                              object_to_match=ctl_locator,
                                              delete_match_object=False,
                                              parent=root_control,
                                              joint=True,
                                              attributes="tr",
                                              shape="circle",
                                              orient_axis="y")
        mid_control.transform.addAttr("followChest", at="float", dv=0.5, k=1)
        mid_control.transform.addAttr("followHips", at="float", dv=0.5, k=1)
        # Chest
        ctl_locator.translate.set(pm.pointOnCurve(ik_curve, pr=1.0, top=1))
        chest_control = luna_rig.Control.create(side=instance.side,
                                                name="{0}_chest".format(instance.indexed_name),
                                                object_to_match=ctl_locator,
                                                delete_match_object=False,
                                                parent=root_control,
                                                joint=True,
                                                attributes="tr",
                                                shape="chest",
                                                orient_axis="y")
        # Connect IK controls
        mid_ctl_constr = pm.parentConstraint(hips_control.transform, chest_control.transform, mid_control.group, mo=1)  # type: luna_rig.nt.ParentConstraint
        mid_control.transform.followChest.connect(mid_ctl_constr.getWeightAliasList()[0])
        mid_control.transform.followHips.connect(mid_ctl_constr.getWeightAliasList()[1])
        # Skin to curve
        pm.skinCluster([hips_control.joint, mid_control.joint, chest_control.joint],
                       ik_curve,
                       n=nameFn.generate_name(instance.name, instance.side, suffix="skin"))

        # Add twist
        ik_handle.dTwistControlEnable.set(1)
        ik_handle.dWorldUpType.set(4)
        hips_control.transform.worldMatrix.connect(ik_handle.dWorldUpMatrix)
        chest_control.transform.worldMatrix.connect(ik_handle.dWorldUpMatrixEnd)
        ik_handle.dWorldUpVectorZ.set(1)
        ik_handle.dWorldUpVectorY.set(0)
        ik_handle.dWorldUpVectorEndZ.set(1)
        ik_handle.dWorldUpVectorEndY.set(0)

        # Create FK controls
        ctl_locator.translate.set(pm.pointOnCurve(ik_curve, pr=0.25, top=1))
        fk1_control = luna_rig.Control.create(side=instance.side,
                                              name="{0}_fk".format(instance.indexed_name),
                                              object_to_match=ctl_locator,
                                              delete_match_object=False,
                                              parent=root_control,
                                              joint=True,
                                              attributes="r",
                                              shape="circleCrossed",
                                              orient_axis="y")
        ctl_locator.translate.set(pm.pointOnCurve(ik_curve, pr=0.75, top=1))
        fk2_control = luna_rig.Control.create(side=instance.side,
                                              name="{0}_fk".format(instance.indexed_name),
                                              object_to_match=ctl_locator,
                                              delete_match_object=True,
                                              parent=fk1_control,
                                              joint=True,
                                              attributes="r",
                                              shape="circleCrossed",
                                              orient_axis="y")
        pm.matchTransform(fk2_control.joint, ctl_chain[-1])
        jointFn.rot_to_orient(fk2_control.joint)
        pm.parentConstraint(fk2_control.joint, chest_control.group, mo=1)

        # Store default items
        instance._store_bind_joints(joint_chain)
        instance._store_ctl_chain(ctl_chain)
        instance._store_controls([root_control, hips_control, mid_control, chest_control, fk1_control, fk2_control])

        # Store indiviual items
        fk1_control.transform.metaParent.connect(instance.pynode.fkControls, na=1)
        fk2_control.transform.metaParent.connect(instance.pynode.fkControls, na=1)
        root_control.transform.metaParent.connect(instance.pynode.rootControl)
        hips_control.transform.metaParent.connect(instance.pynode.hipsControl)
        mid_control.transform.metaParent.connect(instance.pynode.midControl)
        chest_control.transform.metaParent.connect(instance.pynode.chestControl)

        # Store attach points
        instance.add_hook(root_control.transform)
        instance.add_hook(hips_control.transform)
        instance.add_hook(mid_control.transform)
        instance.add_hook(chest_control.transform)

        # Connect to character, metaparent
        instance.connect_to_character(parent=True)
        instance.attach_to_component(meta_parent, hook)

        # Store settings
        instance._store_settings(mid_control.transform.followChest)
        instance._store_settings(mid_control.transform.followHips)

        # Scale controls
        scale_dict = {root_control: 0.25,
                      hips_control: 0.25,
                      mid_control: 1.2,
                      chest_control: 0.25,
                      fk1_control: 0.4,
                      fk2_control: 0.4}
        instance.scale_controls(scale_dict)

        # House keeping
        ik_handle.visibility.set(0)
        if instance.character:
            instance.group_parts.visibility.set(0)
            instance.group_joints.visibility.set(0)

        return instance


class FKRibbonSpineComponent(SpineComponent):
    class Hooks(enumFn.Enum):
        ROOT = 0
        HIPS = 1
        MID = 2
        CHEST = 3

    @property
    def mid_control(self):
        return luna_rig.Control(self.pynode.midControl.listConnections()[0])

    @classmethod
    def create(cls,
               meta_parent=None,
               hook=0,
               side='c',
               name='spine',
               start_joint=None,
               end_joint=None):
        # Create instance and add attrs
        instance = super(FKRibbonSpineComponent, cls).create(meta_parent, side, name)  # type: FKIKSpineComponent
        instance.pynode.addAttr("midControl", at="message")

        # Joint chains
        joint_chain = jointFn.joint_chain(start_joint, end_joint)
        jointFn.validate_rotations(joint_chain)
        for jnt in joint_chain:
            attrFn.add_meta_attr(jnt)
        ctl_chain = jointFn.duplicate_chain(original_chain=joint_chain, add_name="ctl", new_parent=instance.group_joints)
