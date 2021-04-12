import pymel.core as pm
from luna import Logger
from luna.utils import enumFn
import luna_rig
import luna_rig.functions.jointFn as jointFn
import luna_rig.functions.attrFn as attrFn
import luna_rig.functions.nameFn as nameFn
import luna_rig.functions.nodeFn as nodeFn


class IKComponent(luna_rig.AnimComponent):

    class Hooks(enumFn.Enum):
        START_JNT = 0
        END_JNT = 1

    @property
    def ik_control(self):
        transform = self.pynode.ikControl.listConnections(d=1)[0]  # type: luna_rig.nt.Transform
        return luna_rig.Control(transform)

    @property
    def pv_control(self):
        transform = self.pynode.poleVectorControl.listConnections(d=1)  # type: luna_rig.nt.Transform
        return luna_rig.Control(transform[0]) if transform else None

    @property
    def handle(self):
        node = self.pynode.ikHandle.listConnections(d=1)[0]  # type:luna_rig.nt.IkHandle
        return node

    @property
    def group_joints_offset(self):
        transform = self.pynode.jointOffsetGrp.get()  # type: luna_rig.nt.Transform
        return transform

    @classmethod
    def create(cls,
               meta_parent=None,
               hook=0,
               character=None,
               side="c",
               name="ik_component",
               start_joint=None,
               end_joint=None,
               tag=""):
        # Create instance and add attrs
        instance = super(IKComponent, cls).create(meta_parent=meta_parent, side=side, name=name, character=character, tag=tag)  # type: IKComponent
        instance.pynode.addAttr("ikControl", at="message")
        instance.pynode.addAttr("poleVectorControl", at="message")
        instance.pynode.addAttr("ikHandle", at="message")
        instance.pynode.addAttr("jointOffsetGrp", at="message")
        # Joint chain
        joint_chain = jointFn.joint_chain(start_joint, end_joint)
        jointFn.validate_rotations(joint_chain)

        # Create control chain
        for jnt in joint_chain:
            attrFn.add_meta_attr(jnt)
        ctl_chain = jointFn.duplicate_chain(original_chain=joint_chain, add_name="ctl", new_parent=instance.group_joints)
        jnt_offset_grp = nodeFn.create("transform", [instance.indexed_name, "constr"], instance.side, suffix="grp", p=instance.group_joints)
        attrFn.add_meta_attr(jnt_offset_grp)
        pm.matchTransform(jnt_offset_grp, ctl_chain[0])
        ctl_chain[0].setParent(jnt_offset_grp)

        # Create ik control
        ik_control = luna_rig.Control.create(side=instance.side,
                                             name="{0}_ik".format(instance.indexed_name),
                                             guide=ctl_chain[-1],
                                             delete_guide=False,
                                             attributes="tr",
                                             parent=instance.group_ctls,
                                             shape="cube",
                                             tag="ik")
        ik_handle = pm.ikHandle(n=nameFn.generate_name(instance.name, side=instance.side, suffix="ikh"),
                                sj=ctl_chain[0],
                                ee=ctl_chain[-1],
                                sol="ikRPsolver")[0]
        attrFn.add_meta_attr(ik_handle)
        pm.parent(ik_handle, ik_control.transform)

        # Pole vector
        pole_locator = jointFn.get_pole_vector(ctl_chain)
        pv_control = luna_rig.Control.create(side=instance.side,
                                             name="{0}_pvec".format(instance.indexed_name),
                                             guide=pole_locator,
                                             delete_guide=True,
                                             parent=instance.group_ctls,
                                             attributes="tr",
                                             shape="poleVector")
        pm.poleVectorConstraint(pv_control.transform, ik_handle)
        # Add wire
        if len(ctl_chain) % 2:
            wire_source = ctl_chain[(len(ctl_chain) - 1) / 2]
        else:
            wire_source = ctl_chain[len(ctl_chain) / 2]
        pv_control.add_wire(wire_source)

        # Store default items
        instance._store_bind_joints(joint_chain)
        instance._store_ctl_chain(ctl_chain)
        instance._store_controls([ik_control, pv_control])
        # Store component items
        ik_control.transform.metaParent.connect(instance.pynode.ikControl)
        pv_control.transform.metaParent.connect(instance.pynode.poleVectorControl)
        ik_handle.metaParent.connect(instance.pynode.ikHandle)
        jnt_offset_grp.metaParent.connect(instance.pynode.jointOffsetGrp)

        # Store attach points
        instance.add_hook(ctl_chain[0], "start_jnt")
        instance.add_hook(ctl_chain[-1], "end_jnt")
        # Connect to character, parent
        instance.connect_to_character(parent=True)
        instance.attach_to_component(meta_parent, hook)
        # Store settings
        instance._store_settings()
        # Scale controls
        scale_dict = {ik_control: 0.8,
                      pv_control: 0.1}
        instance.scale_controls(scale_dict)

        # House keeping
        ik_handle.visibility.set(0)
        if instance.character:
            instance.group_parts.visibility.set(0)
            instance.group_joints.visibility.set(0)
        return instance

    def attach_to_component(self, other_comp, hook_index=0):
        super(IKComponent, self).attach_to_component(other_comp, hook_index)
        if self.in_hook:
            pm.parentConstraint(self.in_hook.transform, self.group_joints_offset, mo=1)

    def attach_to_skeleton(self):
        """Override: attach to skeleton"""
        for ctl_jnt, bind_jnt in zip(self.ctl_chain[:-1], self.bind_joints[:-1]):
            pm.parentConstraint(ctl_jnt, bind_jnt, mo=1)
