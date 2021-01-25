import pymel.core as pm
from pymel.core import nodetypes
from Luna import Logger
from Luna.utils import enumFn
from Luna_rig.core import component
from Luna_rig.core import control
from Luna_rig.functions import jointFn
from Luna_rig.functions import nameFn


class FKComponent(component.AnimComponent):

    @classmethod
    def create(cls,
               meta_parent=None,
               attach_point=0,
               side="c",
               name="fk_component",
               chain_start=None,
               chain_end=None,
               end_jnt_ctl=False):  # noqa:F821
        fkcomp = super(FKComponent, cls).create(meta_parent, side, name)  # type: FKComponent
        # Joint chain
        joint_chain = jointFn.joint_chain(chain_start, chain_end)
        jointFn.validate_rotations(joint_chain)
        for jnt in joint_chain:
            jnt.addAttr("metaParent", at="message")
        pm.parent(joint_chain[0], fkcomp.group_joints)
        ctl_chain = jointFn.duplicate_chain(original_chain=joint_chain, add_name="ctl")
        for jnt, ctl_jnt in zip(joint_chain, ctl_chain):
            pm.parentConstraint(ctl_jnt, jnt, mo=1)

        # Create control
        fk_controls = []
        next_parent = fkcomp.group_ctls
        guide_chain = ctl_chain if end_jnt_ctl else ctl_chain[:-1]
        for jnt in guide_chain:
            ctl = control.Control.create(side=fkcomp.side,
                                         name="{0}_fk".format(fkcomp.indexed_name),
                                         object_to_match=jnt,
                                         parent=next_parent,
                                         tag="fk")
            pm.parentConstraint(ctl.transform, jnt, mo=1)
            next_parent = ctl
            fk_controls.append(ctl)

        # # Store joint chains
        fkcomp._store_bind_joints(joint_chain)
        fkcomp._store_ctl_chain(ctl_chain)
        fkcomp._store_controls(fk_controls)
        # # Store attach points
        for each in fk_controls:
            fkcomp.add_attach_point(each.transform)
        # Connect to character, parent
        fkcomp.connect_to_character(parent=meta_parent is None)
        fkcomp.attach_to_component(meta_parent, attach_point)
        # House keeping
        if fkcomp.character:
            pm.parent(joint_chain[0], fkcomp.character.deformation_rig)
            fkcomp.group_parts.visibility.set(0)
            fkcomp.group_joints.visibility.set(0)
        return fkcomp

    def attach_to_component(self, other_comp, attach_point=0):
        # Check if should attach at all
        if not other_comp:
            return

        # Get attach point from super method
        attach_obj = super(FKComponent, self).attach_to_component(other_comp, attach_point=attach_point)
        if not attach_obj:
            return
        # Component specific attach logic
        pm.parent(self.root, attach_obj)
        Logger.debug("Attached: {0} ->> {1}({2})".format(self, other_comp, attach_obj))
