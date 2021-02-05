import pymel.core as pm
from pymel.core import nodetypes
from luna import Logger
from luna_rig.core import component
from luna_rig.core import control
from luna_rig.functions import jointFn
from luna_rig.functions import nameFn
from luna_rig.functions import attrFn


class FKComponent(component.AnimComponent):

    @classmethod
    def create(cls,
               meta_parent=None,
               attach_point=0,
               side="c",
               name="fk_component",
               start_joint=None,
               end_joint=None,
               add_end_ctl=True,
               lock_translate=True):
        instance = super(FKComponent, cls).create(meta_parent, side, name)  # type: FKComponent
        # Joint chain
        joint_chain = jointFn.joint_chain(start_joint, end_joint)
        jointFn.validate_rotations(joint_chain)
        for jnt in joint_chain:
            attrFn.add_meta_attr(jnt)
        ctl_chain = jointFn.duplicate_chain(original_chain=joint_chain, add_name="ctl", new_parent=instance.group_joints)

        # Create control
        fk_controls = []
        next_parent = instance.group_ctls
        skel_chain = ctl_chain if add_end_ctl else ctl_chain[:-1]
        free_attrs = "r" if lock_translate else "tr"
        for jnt in skel_chain:
            ctl = control.Control.create(side=instance.side,
                                         name="{0}_fk".format(instance.indexed_name),
                                         object_to_match=jnt,
                                         parent=next_parent,
                                         attributes=free_attrs,
                                         shape="circleCrossed",
                                         tag="fk")
            pm.parentConstraint(ctl.transform, jnt, mo=1)
            next_parent = ctl
            fk_controls.append(ctl)

        # Store joint chains
        instance._store_bind_joints(joint_chain)
        instance._store_ctl_chain(ctl_chain)
        instance._store_controls(fk_controls)

        # Store attach points
        for each in fk_controls:
            instance.add_attach_point(each.transform)

        # Connect to character, parent
        instance.connect_to_character(parent=True)
        instance.attach_to_component(meta_parent, attach_point)

        # Scale controls
        scale_dict = {}
        for ctl in fk_controls:
            scale_dict[ctl] = 0.2
        instance.scale_controls(scale_dict)

        # House keeping
        if instance.character:
            instance.group_parts.visibility.set(0)
            instance.group_joints.visibility.set(0)
        return instance

    def attach_to_component(self, other_comp, attach_point=0):
        # Check if should attach at all
        if not other_comp:
            return

        # Get attach point from super method
        attach_obj = super(FKComponent, self).attach_to_component(other_comp, attach_point=attach_point)
        if not attach_obj:
            return
        # Component specific attach logic
        pm.parentConstraint(attach_obj, self.root, mo=1)
        Logger.debug("Attached: {0} ->> {1}({2})".format(self, other_comp, attach_obj))

    def add_auto_aim(self, follow_control, mirrored_chain=False):
        if not isinstance(follow_control, control.Control):
            raise ValueError("{0}: {1} is not a Control instance".format(self, follow_control))
        # Create aim transforms
        aim_grp = pm.createNode("transform", n=nameFn.generate_name([self.indexed_name, "aim"], side=self.side,
                                                                    suffix="grp"), p=self.controls[0].group)  # type: nodetypes.Transform
        no_aim_grp = pm.createNode("transform", n=nameFn.generate_name([self.indexed_name, "noaim"],
                                                                       side=self.side, suffix="grp"), p=self.controls[0].group)  # type: nodetypes.Transform
        constr_grp = pm.createNode("transform", n=nameFn.generate_name([self.indexed_name, "aim_constr"],
                                                                       side=self.side, suffix="grp"), p=self.controls[0].group)  # type: nodetypes.Transform
        target_grp = pm.createNode("transform", n=nameFn.generate_name([self.indexed_name, "target"],
                                                                       side=self.side, suffix="grp"), p=follow_control.transform)  # type: nodetypes.Transform

        # Set aim vector to X or -X
        if mirrored_chain:
            aim_vector = [-1, 0, 0]
        else:
            aim_vector = [1, 0, 0]

        # Create aim setup
        pm.aimConstraint(target_grp, aim_grp, wut="object", wuo=self.controls[0].group, aim=aim_vector)
        pm.delete(pm.aimConstraint(target_grp, no_aim_grp, wut="object", wuo=self.controls[0].group, aim=aim_vector))
        orient_constr = pm.orientConstraint(aim_grp, no_aim_grp, constr_grp)  # type: nodetypes.OrientConstraint
        pm.parent(self.controls[0].offset_list[0], constr_grp)
        # Add attr to control
        self.controls[0].transform.addAttr("autoAim", at="float", dv=3.0, min=0.0, max=10.0, k=1)
        mdl_node = pm.createNode("multDoubleLinear", n=nameFn.generate_name([self.indexed_name, "auto_aim"], side=self.side, suffix="mdl"))
        rev_node = pm.createNode("reverse", n=nameFn.generate_name([self.indexed_name, "auto_aim"], side=self.side, suffix="rev"))
        mdl_node.input2.set(0.1)
        # Attr connections
        self.controls[0].transform.autoAim.connect(mdl_node.input1)
        mdl_node.output.connect(rev_node.inputX)
        mdl_node.output.connect(orient_constr.getWeightAliasList()[0])
        rev_node.outputX.connect(orient_constr.getWeightAliasList()[1])
        # Store settings
        self._store_settings(self.controls[0].transform.autoAim)
