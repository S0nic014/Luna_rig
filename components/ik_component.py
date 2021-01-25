import pymel.core as pm
from pymel.core import nodetypes
from Luna import Logger
from Luna.utils import enumFn
from Luna_rig.core import component
from Luna_rig.core import control
from Luna_rig.functions import jointFn


class IKComponent(component.AnimComponent):

    class AttachPoints(enumFn.Enum):
        IK = 0
        PV = 1

    @property
    def ik_control(self):
        transform = self.pynode.ikControl.listConnections(d=1)[0]  # type: nodetypes.Transform
        return transform

    @property
    def pv_control(self):
        transform = self.pynode.poleVectorControl.listConnections(d=1)  # type: nodetypes.Transform
        return transform[0] if transform else None

    @classmethod
    def create(cls,
               meta_parent=None,
               attach_point=0,
               side="c",
               name="ik_component",
               chain_start=None,
               chain_end=None,
               add_pv_control=True):
        ikcomp = super(IKComponent, cls).create(meta_parent, side, name)  # type: IKComponent
        # Joint chain
        joint_chain = jointFn.joint_chain(chain_start, chain_end)
        jointFn.validate_rotations(joint_chain)

        # Create control chain
        for jnt in joint_chain:
            jnt.addAttr("metaParent", at="message")
        pm.parent(joint_chain[0], ikcomp.group_joints)
        ctl_chain = jointFn.duplicate_chain(original_chain=joint_chain, add_name="ctl")
        for jnt, ctl_jnt in zip(joint_chain, ctl_chain):
            pm.parentConstraint(ctl_jnt, jnt, mo=1)

        # Create ik control
        ik_control = control.Control.create(side=ikcomp.side,
                                            name="{0}_ik".format(ikcomp.indexed_name),
                                            object_to_match=joint_chain[-1],
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
        if add_pv_control:
            pole_locator = jointFn.get_pole_vector(joint_chain)
            pv_control = control.Control.create(side=ikcomp.side,
                                                name="{0}_pvec".format(ikcomp.indexed_name),
                                                object_to_match=pole_locator,
                                                delete_match_object=True,
                                                parent=ikcomp.group_ctls,
                                                attributes="tr",
                                                shape="poleVector")
            pm.poleVectorConstraint(pv_control.transform, ik_handle)

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
            # House keeping
            ik_handle.visibility.set(0)
            if ikcomp.character:
                pm.parent(joint_chain[0], ikcomp.character.deformation_rig)
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