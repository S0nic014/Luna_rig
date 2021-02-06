import pymel.core as pm
from luna import Logger
import luna_rig
from luna_rig.functions import jointFn
from luna_rig.functions import attrFn
from luna_rig.functions import nameFn


class FootComponent(luna_rig.AnimComponent):
    ROLL_ATTRS = ["footRoll", "toeRoll", "heelRoll", "bank", "heelTwist", "toeTwist", "toeTap"]

    # @property
    # def ik_chain(self):
    #     return self.pynode.ikChain.listConnections(d=1)

    # @property
    # def fk_chain(self):
    #     return self.pynode.fkChain.listConnections(d=1)

    @classmethod
    def create(cls,
               meta_parent=None,
               side=None,
               name="rv_foot",
               start_joint=None,
               end_joint=None,
               rv_chain=None,
               foot_locators_grp=None,
               roll_axis="ry"):
        # Validate arguments
        if not isinstance(meta_parent, luna_rig.components.FKIKComponent):
            Logger.error("{0}: Invalid meta_parent type. Should be FKIKComponent.")
            raise TypeError
        side = side if side else meta_parent.side
        foot_locators_grp = pm.PyNode(foot_locators_grp)  # type: luna_rig.nt.Transform
        # Create instance and add attrs
        instance = super(FootComponent, cls).create(meta_parent=meta_parent, side=side, name=name)  # type: FootComponent
        instance.pynode.addAttr("fkChain", at="message", multi=1, im=0)
        instance.pynode.addAttr("ikChain", at="message", multi=1, im=0)

        # Chains
        joint_chain = jointFn.joint_chain(start_joint, end_joint)
        for jnt in joint_chain:
            attrFn.add_meta_attr(jnt)
        ctl_chain = jointFn.duplicate_chain(joint_chain, add_name="ctl")
        ik_chain = jointFn.duplicate_chain(joint_chain, add_name="ik")
        fk_chain = jointFn.duplicate_chain(joint_chain, add_name="fk")
        rv_chain = jointFn.joint_chain(rv_chain)
        ctl_chain[0].setParent(meta_parent.ctl_chain[-1])
        ik_chain[0].setParent(meta_parent.ik_chain[-1])
        fk_chain[0].setParent(meta_parent.fk_chain[-1])
        # Fkik blend
        reverse_fkik = meta_parent.param_control.transform.fkik.listConnections(s=1, type="reverse")[0]
        for ctl_jnt, fk_jnt, ik_jnt in zip(ctl_chain, fk_chain, ik_chain):
            parent_constr = pm.parentConstraint(fk_jnt, ik_jnt, ctl_jnt)
            reverse_fkik.outputX.connect(parent_constr.getWeightAliasList()[0])
            meta_parent.param_control.transform.fkik.connect(parent_constr.getWeightAliasList()[1])

        # Foot handles
        ball_handle = pm.ikHandle(n=nameFn.generate_name([instance.indexed_name, "ball"], side=instance.side, suffix="ikh"),
                                  sj=ik_chain[0].getParent(),
                                  ee=ik_chain[0],
                                  sol="ikSCsolver")[0]
        toe_handle = pm.ikHandle(n=nameFn.generate_name([instance.indexed_name, "toe"], side=instance.side, suffix="ikh"),
                                 sj=ik_chain[0],
                                 ee=ik_chain[1],
                                 sol="ikSCsolver")[0]

        # Foot locators
        for child in foot_locators_grp.getChildren():
            if "inner" in child.name():
                inner_locator = child
            elif "outer" in child.name():
                outer_locator = child
            elif "toe" in child.name():
                toe_locator = child
            elif "heel" in child.name():
                heel_locator = child
        # Tap transform
        toe_tap_transform = pm.createNode("transform", n=nameFn.generate_name([instance.indexed_name, "tap"], side=instance.side, suffix="grp"), p=rv_chain[2])
        toe_tap_transform.setParent(rv_chain[1])
        # Parent handles
        pm.parent(meta_parent.handle, rv_chain[-1])
        ball_handle.setParent(rv_chain[2])
        toe_handle.setParent(toe_tap_transform)

        # Parent foot locators
        foot_locators_grp.setParent(meta_parent.ik_control.transform)
        toe_locator.setParent(heel_locator)
        outer_locator.setParent(toe_locator)
        inner_locator.setParent(outer_locator)
        rv_chain[0].setParent(inner_locator)

        # Controls
        meta_parent.param_control.transform.fkik.connect(instance.group_ctls.visibility)
        fk_control = luna_rig.Control.create(side=instance.side,
                                             name="{0}_fk".format(instance.indexed_name),
                                             object_to_match=fk_chain[0],
                                             parent=meta_parent.fk_controls[-1],
                                             delete_match_object=False,
                                             attributes="r",
                                             shape="circleCrossed",
                                             tag="fk")
        pm.orientConstraint(fk_control.transform, fk_chain[0])
        # Roll attributes
        attrFn.add_divider(meta_parent.ik_control.transform, attr_name="FOOT")
        for attr_name in FootComponent.ROLL_ATTRS:
            meta_parent.ik_control.transform.addAttr(attr_name, at="float", k=1, dv=0.0)
        meta_parent.ik_control.transform.footRoll.connect(rv_chain[2].attr(roll_axis))
        meta_parent.ik_control.transform.toeRoll.connect(toe_locator.rotateX)
        meta_parent.ik_control.transform.heelRoll.connect(heel_locator.rotateX)
        meta_parent.ik_control.transform.toeTap.connect(toe_tap_transform.attr(roll_axis))
        meta_parent.ik_control.transform.heelTwist.connect(heel_locator.rotateY)
        meta_parent.ik_control.transform.toeTwist.connect(toe_locator.rotateY)
        # Bank logic
        bank_condition = pm.createNode("condition", n=nameFn.generate_name([instance.indexed_name, "bank"], side=instance.side, suffix="cond"))
        if instance.side == "r":
            bank_condition.operation.set(4)
        else:
            bank_condition.operation.set(2)
        bank_condition.colorIfFalseR.set(0)
        meta_parent.ik_control.transform.bank.connect(bank_condition.firstTerm)
        meta_parent.ik_control.transform.bank.connect(bank_condition.colorIfTrueR)
        meta_parent.ik_control.transform.bank.connect(bank_condition.colorIfFalseG)
        bank_condition.outColorG.connect(outer_locator.rotateZ)
        bank_condition.outColorR.connect(inner_locator.rotateZ)

        # Store objects
        instance._store_bind_joints(joint_chain)
        instance._store_ctl_chain(ctl_chain)
        # Store chains
        for jnt in ik_chain:
            jnt.metaParent.connect(instance.pynode.ikChain, na=1)
        for jnt in fk_chain:
            jnt.metaParent.connect(instance.pynode.fkChain, na=1)

        instance.connect_to_character(parent=True)
        instance.attach_to_component(meta_parent, hook=meta_parent.Hooks.IK)

        # Scale controls
        scale_dict = {fk_control: 0.2}
        instance.scale_controls(scale_dict)
        # Cleanup
        foot_locators_grp.visibility.set(0)

        return instance

    def remove(self):
        pm.delete(self.ctl_chain[0])
        pm.delete(self.ik_chain[0])
        pm.delete(self.fk_chain[0])
        pm.deleteAttr(self.meta_parent.ik_control.transform.FOOT)
        for attr_name in self.ROLL_ATTRS:
            pm.deleteAttr(self.meta_parent.ik_control.transform.attr(attr_name))
        super(FootComponent, self).remove()
