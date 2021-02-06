import pymel.core as pm
from luna import Logger
from luna.utils import enumFn
import luna_rig
from luna_rig.functions import jointFn
from luna_rig.functions import attrFn
from luna_rig.functions import nameFn


class IKComponent(luna_rig.AnimComponent):

    class Hooks(enumFn.Enum):
        IK = 0
        PV = 1

    @property
    def ik_control(self):
        transform = self.pynode.ikControl.listConnections(d=1)[0]  # type: luna_rig.nt.Transform
        return luna_rig.Control(transform)

    @property
    def pv_control(self):
        transform = self.pynode.poleVectorControl.listConnections(d=1)  # type: luna_rig.nt.Transform
        return luna_rig.Control(transform[0]) if transform else None

    @classmethod
    def create(cls,
               meta_parent=None,
               hook=0,
               side="c",
               name="ik_component",
               start_joint=None,
               end_joint=None):
        instance = super(IKComponent, cls).create(meta_parent, side, name)  # type: IKComponent
        # Joint chain
        joint_chain = jointFn.joint_chain(start_joint, end_joint)
        jointFn.validate_rotations(joint_chain)

        # Create control chain
        for jnt in joint_chain:
            attrFn.add_meta_attr(jnt)
        ctl_chain = jointFn.duplicate_chain(original_chain=joint_chain, add_name="ctl", new_parent=instance.group_joints)
        for jnt, ctl_jnt in zip(joint_chain, ctl_chain):
            pm.parentConstraint(ctl_jnt, jnt, mo=1)

        # Create ik control
        ik_control = luna_rig.Control.create(side=instance.side,
                                             name="{0}_ik".format(instance.indexed_name),
                                             object_to_match=ctl_chain[-1],
                                             delete_match_object=False,
                                             attributes="tr",
                                             parent=instance.group_ctls,
                                             shape="cube",
                                             tag="ik")
        ik_handle = pm.ikHandle(n=nameFn.generate_name(instance.indexed_name, side=instance.side, suffix="ikh"),
                                sj=ctl_chain[0],
                                ee=ctl_chain[-1],
                                sol="ikRPsolver")[0]
        pm.parent(ik_handle, ik_control.transform)

        # Pole vector
        pole_locator = jointFn.get_pole_vector(ctl_chain)
        pv_control = luna_rig.Control.create(side=instance.side,
                                             name="{0}_pvec".format(instance.indexed_name),
                                             object_to_match=pole_locator,
                                             delete_match_object=True,
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
        # Store indiviual controls
        instance.pynode.addAttr("ikControl", at="message")
        instance.pynode.addAttr("poleVectorControl", at="message")
        ik_control.transform.metaParent.connect(instance.pynode.ikControl)
        pv_control.transform.metaParent.connect(instance.pynode.poleVectorControl)

        # Store attach points
        instance.add_hook(ik_control.transform)
        instance.add_hook(pv_control.transform)
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

    def attach_to_component(self, other_comp, hook=0):
        # Check if should attach at all
        if not other_comp:
            return

        # Get attach point from super method
        attach_obj = super(IKComponent, self).attach_to_component(other_comp, hook)
        if not attach_obj:
            return
        # Component specific attach logic
        pm.parentConstraint(attach_obj, self.group_joints, mo=1)
