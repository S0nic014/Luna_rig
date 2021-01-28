import pymel.core as pm
from pymel.core import nodetypes
from luna import Logger
from luna.utils import enumFn
from luna_rig.core import component
from luna_rig.core import control
from luna_rig.functions import jointFn
from luna_rig.functions import attrFn


class IKComponent(component.AnimComponent):

    class AttachPoints(enumFn.Enum):
        IK = 0
        PV = 1

    @property
    def ik_control(self):
        transform = self.pynode.ikControl.listConnections(d=1)[0]  # type: nodetypes.Transform
        return control.Control(transform)

    @property
    def pv_control(self):
        transform = self.pynode.poleVectorControl.listConnections(d=1)  # type: nodetypes.Transform
        return control.Control(transform[0]) if transform else None

    @classmethod
    def create(cls,
               meta_parent=None,
               attach_point=0,
               side="c",
               name="ik_component",
               start_joint=None,
               end_joint=None):
        ikcomp = super(IKComponent, cls).create(meta_parent, side, name)  # type: IKComponent
        # Joint chain
        joint_chain = jointFn.joint_chain(start_joint, end_joint)
        jointFn.validate_rotations(joint_chain)

        # Create control chain
        for jnt in joint_chain:
            attrFn.add_meta_attr(jnt)
        ctl_chain = jointFn.duplicate_chain(original_chain=joint_chain, add_name="ctl", new_parent=ikcomp.group_joints)
        for jnt, ctl_jnt in zip(joint_chain, ctl_chain):
            pm.parentConstraint(ctl_jnt, jnt, mo=1)

        # Create ik control
        ik_control = control.Control.create(side=ikcomp.side,
                                            name="{0}_ik".format(ikcomp.indexed_name),
                                            object_to_match=ctl_chain[-1],
                                            delete_match_object=False,
                                            attributes="tr",
                                            parent=ikcomp.group_ctls,
                                            shape="cube",
                                            tag="ik")
        ik_handle = pm.ikHandle(n="{0}_ikh".format(ikcomp.indexed_name),
                                sj=ctl_chain[0],
                                ee=ctl_chain[-1],
                                sol="ikRPsolver")[0]
        pm.parent(ik_handle, ik_control.transform)

        # Pole vector
        pole_locator = jointFn.get_pole_vector(ctl_chain)
        pv_control = control.Control.create(side=ikcomp.side,
                                            name="{0}_pvec".format(ikcomp.indexed_name),
                                            object_to_match=pole_locator,
                                            delete_match_object=True,
                                            parent=ikcomp.group_ctls,
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
        ikcomp._store_bind_joints(joint_chain)
        ikcomp._store_ctl_chain(ctl_chain)
        ikcomp._store_controls([ik_control, pv_control])
        # Store indiviual controls
        ikcomp.pynode.addAttr("ikControl", at="message")
        ikcomp.pynode.addAttr("poleVectorControl", at="message")
        ik_control.transform.metaParent.connect(ikcomp.pynode.ikControl)
        pv_control.transform.metaParent.connect(ikcomp.pynode.poleVectorControl)

        # Store attach points
        ikcomp.add_attach_point(ik_control.transform)
        ikcomp.add_attach_point(pv_control.transform)
        # Connect to character, parent
        ikcomp.connect_to_character(parent=True)
        ikcomp.attach_to_component(meta_parent, attach_point)
        # Store settings
        ikcomp._store_settings()
        # Scale controls
        scale_dict = {ik_control: 0.8,
                      pv_control: 0.1}
        ikcomp.scale_controls(scale_dict)

        # House keeping
        ik_handle.visibility.set(0)
        if ikcomp.character:
            ikcomp.group_parts.visibility.set(0)
            ikcomp.group_joints.visibility.set(0)
        return ikcomp

    def attach_to_component(self, other_comp, attach_point=0):
        # Check if should attach at all
        if not other_comp:
            return

        # Get attach point from super method
        attach_obj = super(IKComponent, self).attach_to_component(other_comp, attach_point=attach_point)
        if not attach_obj:
            return
        # Component specific attach logic
        pm.parentConstraint(attach_obj, self.group_joints, mo=1)
        Logger.debug("Attached: {0} ->> {1}({2})".format(self, other_comp, attach_obj))
