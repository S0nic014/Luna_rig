import pymel.core as pm

from luna import Logger
from luna.utils import enumFn
import luna_rig
import luna_rig.functions.nameFn as nameFn
import luna_rig.functions.attrFn as attrFn
import luna_rig.functions.jointFn as jointFn
import luna_rig.functions.curveFn as curveFn
import luna_rig.functions.surfaceFn as surfaceFn
import luna_rig.functions.rivetFn as rivetFn
import luna_rig.functions.transformFn as transformFn


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
                                             parent=instance.group_noscale)
        pm.rebuildCurve(ik_curve, d=3, kep=1, rpo=1, ch=0, tol=0.01, spans=4)
        # ik_curve.inheritsTransform.set(0)
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
               end_joint=None,
               side_vector=[1, 0, 0],
               joints_aim_vector=[1.0, 0.0, 0.0],
               joints_up_vector=[0.0, 1.0, 0.0]):
        # Create instance and add attrs
        instance = super(FKRibbonSpineComponent, cls).create(meta_parent, side, name)  # type: FKIKSpineComponent
        instance.pynode.addAttr("midControl", at="message")

        # Joint chains
        joint_chain = jointFn.joint_chain(start_joint, end_joint)
        jointFn.validate_rotations(joint_chain)
        for jnt in joint_chain:
            attrFn.add_meta_attr(jnt)
        ctl_chain = jointFn.duplicate_chain(original_chain=joint_chain, add_name="ctl", new_parent=instance.group_joints)
        ctl_spine_chain = ctl_chain[1:]
        ctl_pelvis_joint = ctl_chain[0]

        # Create temp curve for positioning and get joints points
        joint_points = [jnt.getTranslation(space="world") for jnt in ctl_chain]

        # Create spiene surface
        nurbs_width = (joint_points[-1] - joint_points[0]).length() * 0.1
        spine_surface = surfaceFn.loft_from_points(joint_points[1:], side_vector=side_vector, width=nurbs_width)
        surfaceFn.rebuild_1_to_3(spine_surface)
        spine_surface.rename(nameFn.generate_name(instance.name, instance.side, "nurbs"))
        spine_surface.setParent(instance.group_noscale)
        # Create rivets
        rivet_joints = []
        follicles = rivetFn.FollicleRivet.along_surface(spine_surface,
                                                        side=instance.side,
                                                        name=[instance.indexed_name, "rivet"],
                                                        use_span="v",
                                                        parent=instance.group_noscale)
        for index, jnt in enumerate(ctl_spine_chain):
            rvt_jnt = pm.createNode("joint",
                                    n=nameFn.generate_name([instance.indexed_name, "rivet"], instance.side, suffix="jnt"),
                                    parent=follicles[index].follicle_transform)
            pm.matchTransform(rvt_jnt, jnt, rot=1)
            jointFn.rot_to_orient(rvt_jnt)
            rivet_joints.append(rvt_jnt)
        # Contrain rivet joints aim to next
        for index, rvt_jnt in enumerate(rivet_joints[:-1]):
            pm.aimConstraint(rivet_joints[index + 1], rvt_jnt,
                             aim=joints_aim_vector,
                             upVector=joints_up_vector,
                             wut="objectrotation",
                             wuo=rivet_joints[index + 1])

        # Create controls
        temp_curve = curveFn.curve_from_points(name="temp_spine_curve", degree=1, points=joint_points)
        pm.rebuildCurve(temp_curve, d=3, rpo=1, ch=0, spans=4)
        ctl_locator = pm.spaceLocator(n="temp_control_loc")
        ctl_locator.translate.set(pm.pointOnCurve(temp_curve, pr=0.0, top=1))
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
        ctl_locator.translate.set(pm.pointOnCurve(temp_curve, pr=0.5, top=1))
        mid_control = luna_rig.Control.create(side=instance.side,
                                              name="{0}_mid".format(instance.indexed_name),
                                              object_to_match=ctl_locator,
                                              delete_match_object=False,
                                              parent=root_control,
                                              joint=True,
                                              attributes="tr",
                                              shape="circle",
                                              orient_axis="y")
        # Chest
        ctl_locator.translate.set(pm.pointOnCurve(temp_curve, pr=1.0, top=1))
        chest_control = luna_rig.Control.create(side=instance.side,
                                                name="{0}_chest".format(instance.indexed_name),
                                                object_to_match=ctl_locator,
                                                delete_match_object=True,
                                                parent=root_control,
                                                joint=True,
                                                attributes="tr",
                                                shape="chest",
                                                orient_axis="y")
        # Connect rivet joints to control chain
        for ctl_jnt, rvt_jnt in zip(ctl_spine_chain[:-1], rivet_joints):
            pm.pointConstraint(rvt_jnt, ctl_jnt)
            pm.orientConstraint(rvt_jnt, ctl_jnt)
        # Connect chest joint to control
        jointFn.match_orient(chest_control.joint, ctl_spine_chain[-1])
        pm.orientConstraint(chest_control.joint, ctl_spine_chain[-1])
        # Connect pelvis joint to control
        jointFn.match_orient(hips_control.joint, ctl_pelvis_joint)
        pm.pointConstraint(hips_control.joint, ctl_pelvis_joint)
        pm.orientConstraint(hips_control.joint, ctl_pelvis_joint)

        # Create wire curve
        wire_curve = pm.curve(n=nameFn.generate_name([instance.indexed_name, "wire"], instance.side, "crv"),
                              d=2,
                              #   p=[joint_points[1], pm.pointOnCurve(temp_curve, pr=0.5, top=1), joint_points[-1]])
                              p=[joint_points[1], pm.pointOnSurface(spine_surface, u=0.5, v=0.5, top=1), joint_points[-1]])
        hips_cluster = pm.cluster(wire_curve.getShape().controlPoints[0], n=nameFn.generate_name([instance.indexed_name, "hips"], instance.side, "clst"))
        mid_cluster = pm.cluster(wire_curve.getShape().controlPoints[1], n=nameFn.generate_name([instance.indexed_name, "mid"], instance.side, "clst"))
        chest_cluster = pm.cluster(wire_curve.getShape().controlPoints[2], n=nameFn.generate_name([instance.indexed_name, "chest"], instance.side, "clst"))
        pm.parentConstraint(hips_control.transform, hips_cluster, mo=1)
        pm.parentConstraint(mid_control.transform, mid_cluster, mo=1)
        pm.parentConstraint(chest_control.transform, chest_cluster, mo=1)
        pm.group(hips_cluster, mid_cluster, chest_cluster, n=nameFn.generate_name([instance.indexed_name, "clusters"], instance.side, suffix="grp"), p=instance.group_parts)
        wire_deformer = pm.wire(spine_surface,
                                wire=wire_curve,
                                n=nameFn.generate_name([instance.indexed_name, "surface"], instance.side, "wire"),
                                dds=(0, 50))[0]  # type: luna_rig.nt.Wire
        wire_base_curve = wire_deformer.baseWire[0].listConnections(d=1)[0]
        pm.group(wire_curve, wire_base_curve, n=nameFn.generate_name([instance.indexed_name, "wire"], instance.side, "grp"), p=instance.group_noscale)

        # Store default items
        instance._store_bind_joints(joint_chain)
        instance._store_ctl_chain(ctl_chain)
        instance._store_controls([root_control, hips_control, mid_control, chest_control])

        # Store indiviual items
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

        # Scale controls
        scale_dict = {root_control: 0.25,
                      hips_control: 0.25,
                      mid_control: 1.2,
                      chest_control: 0.25}
        instance.scale_controls(scale_dict)

        # # House keeping
        # if instance.character:
        #     instance.group_parts.visibility.set(0)
        #     instance.group_joints.visibility.set(0)

        return instance

    def attach_to_skeleton(self):
        return super(FKRibbonSpineComponent, self).attach_to_skeleton()
