import pymel.core as pm
from pymel.core import nodetypes
from Luna import Logger
from Luna.utils import enumFn
from Luna_rig.core import component
from Luna_rig.core import control
from Luna_rig.functions import jointFn
from Luna_rig.functions import attrFn
from Luna_rig.functions import rigFn
from Luna_rig.functions import nameFn


class FKIKComponent(component.AnimComponent):

    class AttachPoints(enumFn.Enum):
        HIP_JNT = 0
        ANKLE_JNT = 1

    @property
    def ik_control(self):
        transform = self.pynode.ikControl.listConnections(d=1)[0]  # type: nodetypes.Transform
        return control.Control(transform)

    @property
    def pv_control(self):
        transform = self.pynode.poleVectorControl.listConnections(d=1)[0]  # type: nodetypes.Transform
        return control.Control(transform)

    @property
    def fk_controls(self):
        return [control.Control(node) for node in self.pynode.fkControls.listConnections(d=1)]

    @property
    def ik_chain(self):
        return self.pynode.ikChain.listConnections(d=1)

    @property
    def fk_chain(self):
        return self.pynode.fkChain.listConnections(d=1)

    @property
    def param_control(self):
        transform = self.pynode.paramControl.listConnections(d=1)[0]
        return control.Control(transform)

    @property
    def fkik_state(self):
        state = self.param_control.transform.fkik.get()  # type: float
        return state

    @fkik_state.setter
    def fkik_state(self, value):
        self.param_control.transform.fkik.set(value)

    @classmethod
    def create(cls,
               meta_parent=None,
               attach_point=0,
               side="c",
               name="fkik_component",
               chain_start=None,
               chain_end=None,
               default_state=1,
               param_locator=None):
        instance = super(FKIKComponent, cls).create(meta_parent, side, name)  # type: FKIKComponent
        character = rigFn.get_build_character()
        # Joint chain
        joint_chain = jointFn.joint_chain(chain_start, chain_end)
        jointFn.validate_rotations(joint_chain)

        # Create control chain
        for jnt in joint_chain:
            attrFn.add_meta_attr(jnt)
        ctl_chain = jointFn.duplicate_chain(original_chain=joint_chain, add_name="ctl", new_parent=instance.group_joints)
        # Create FK, Ik chains
        fk_chain = jointFn.duplicate_chain(original_chain=joint_chain, add_name="fk", new_parent=instance.group_joints)
        ik_chain = jointFn.duplicate_chain(original_chain=joint_chain, add_name="ik", new_parent=instance.group_joints)

        # Create FK setup
        fk_controls = []
        next_parent = instance.group_ctls
        for jnt in fk_chain:
            ctl = control.Control.create(side=instance.side,
                                         name="{0}_fk".format(instance.indexed_name),
                                         object_to_match=jnt,
                                         attributes="r",
                                         parent=next_parent,
                                         shape="circleCrossed",
                                         tag="fk")
            pm.parentConstraint(ctl.transform, jnt, mo=1)
            next_parent = ctl
            fk_controls.append(ctl)

        # Create IK setup
        ik_control = control.Control.create(side=instance.side,
                                            name="{0}_ik".format(instance.indexed_name),
                                            object_to_match=ik_chain[-1],
                                            delete_match_object=False,
                                            attributes="tr",
                                            parent=instance.group_ctls,
                                            shape="cube",
                                            tag="ik")
        ik_handle = pm.ikHandle(n="{0}_ikh".format(instance.indexed_name),
                                sj=ik_chain[0],
                                ee=ik_chain[-1],
                                sol="ikRPsolver")[0]
        pm.parent(ik_handle, ik_control.transform)
        # Pole vector
        pole_locator = jointFn.get_pole_vector(ik_chain)
        pv_control = control.Control.create(side=instance.side,
                                            name="{0}_pvec".format(instance.indexed_name),
                                            object_to_match=pole_locator,
                                            delete_match_object=True,
                                            parent=instance.group_ctls,
                                            attributes="tr",
                                            shape="poleVector")
        pm.poleVectorConstraint(pv_control.transform, ik_handle)
        # Add wire
        if len(ik_chain) % 2:
            wire_source = ik_chain[(len(ik_chain) - 1) / 2]
        else:
            wire_source = ik_chain[len(ik_chain) / 2]
        pv_control.add_wire(wire_source)

        # Params control
        if not param_locator:
            param_locator = rigFn.get_param_ctl_locator(instance.side, joint_chain, move_axis="x")
        param_control = control.Control.create(side=instance.side,
                                               name="{0}_param".format(instance.indexed_name),
                                               object_to_match=param_locator,
                                               delete_match_object=True,
                                               attributes="",
                                               parent=instance.group_ctls,
                                               match_orient=False,
                                               offset_grp=False,
                                               shape="small_cog")
        pm.pointConstraint(joint_chain[-1], param_control.group, mo=1)

        # Create blend
        param_control.transform.addAttr("fkik", nn="IK/FK", at="float", min=0.0, max=1.0, dv=default_state, k=True)
        revese_fkik = pm.createNode("reverse", n=nameFn.generate_name([instance.indexed_name, "fkik"], side=instance.side, suffix="rev"))
        param_control.transform.fkik.connect(revese_fkik.inputX)
        param_control.transform.fkik.connect(ik_control.group.visibility)
        param_control.transform.fkik.connect(pv_control.group.visibility)
        revese_fkik.outputX.connect(fk_controls[0].group.visibility)
        for ctl_jnt, fk_jnt, ik_jnt in zip(ctl_chain, fk_chain, ik_chain):
            parent_constr = pm.parentConstraint(fk_jnt, ik_jnt, ctl_jnt)
            revese_fkik.outputX.connect(parent_constr.getWeightAliasList()[0])
            param_control.transform.fkik.connect(parent_constr.getWeightAliasList()[1])

        # Scale controls
        if not character:
            clamped_size = 1.0
        else:
            clamped_size = character.clamped_size
        for ctl in fk_controls:
            ctl.scale(clamped_size, factor=0.2)
        param_control.scale(clamped_size, factor=0.2)
        ik_control.scale(clamped_size, factor=0.8)
        pv_control.scale(clamped_size, factor=0.1)

        # Store default items
        instance._store_bind_joints(joint_chain)
        instance._store_ctl_chain(ctl_chain)
        instance._store_controls(fk_controls)
        instance._store_controls([ik_control, pv_control])
        # Store indiviual items
        instance.pynode.addAttr("fkChain", at="message", multi=1, im=0)
        instance.pynode.addAttr("ikChain", at="message", multi=1, im=0)
        instance.pynode.addAttr("fkControls", at="message", multi=1, im=0)
        instance.pynode.addAttr("ikControl", at="message")
        instance.pynode.addAttr("poleVectorControl", at="message")
        instance.pynode.addAttr("paramControl", at="message")
        for fk_jnt in fk_chain:
            fk_jnt.metaParent.connect(instance.pynode.fkChain, na=1)
        for ik_jnt in ik_chain:
            ik_jnt.metaParent.connect(instance.pynode.ikChain, na=1)
        for fk_ctl in fk_controls:
            fk_ctl.transform.metaParent.connect(instance.pynode.fkControls, na=1)
        ik_control.transform.metaParent.connect(instance.pynode.ikControl)
        pv_control.transform.metaParent.connect(instance.pynode.poleVectorControl)
        param_control.transform.metaParent.connect(instance.pynode.paramControl)

        # Store attach points
        instance.add_attach_point(ctl_chain[0])
        instance.add_attach_point(ctl_chain[-1])
        # Connect to character, parent
        instance.connect_to_character(parent=True)
        instance.attach_to_component(meta_parent, attach_point)
        # House keeping
        ik_handle.visibility.set(0)
        if instance.character:
            instance.group_parts.visibility.set(0)
            instance.group_joints.visibility.set(0)
        return instance

    def attach_to_component(self, other_comp, attach_point=0):
        # Check if should attach at all
        if not other_comp:
            return

        # Get attach point from super method
        attach_obj = super(FKIKComponent, self).attach_to_component(other_comp, attach_point=attach_point)
        if not attach_obj:
            return
        # Component specific attach logic
        pm.parentConstraint(attach_obj, self.ik_chain[0], mo=1)
        pm.parentConstraint(attach_obj, self.fk_controls[0].group, mo=1)
        Logger.debug("Attached: {0} ->> {1}({2})".format(self, other_comp, attach_obj))

    def switch_fkik(self, matching=True):
        # If in FK -> match IK to FK and switch to IK
        if not self.fkik_state:
            self.fkik_state = 1
            pm.matchTransform(self.ik_control.transform, self.fk_chain[-1])
            # Pole vector
            pole_locator = jointFn.get_pole_vector(self.fk_chain)
            pm.matchTransform(self.pv_control.transform, pole_locator)
            pm.delete(pole_locator)
            pm.select(self.ik_control.transform, r=1)
        else:
            # If in IK -> match FK to IK and switch to FK
            self.fkik_state = 0
            for ik_jnt, fk_ctl in zip(self.ik_chain, self.fk_controls):
                pm.matchTransform(fk_ctl.transform, ik_jnt, rot=1)
            pm.select(self.fk_controls[-1].transform, r=1)

    def add_twist(self, upper=True, lower=True):
        # TODO: Add twist
        pass

    def add_mtx_twist(self, upper=True, lower=True):
        # TODO: Add mtx twist
        pass
