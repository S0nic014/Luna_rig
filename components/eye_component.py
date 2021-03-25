import pymel.core as pm
from luna import Logger
import luna_rig
import luna_rig.functions.attrFn as attrFn


class EyeComponent(luna_rig.AnimComponent):

    @property
    def aim_control(self):
        return luna_rig.Control(self.pynode.aimControl.listConnections(d=1)[0])

    @classmethod
    def create(cls,
               aim_locator,
               eye_joint,
               side="c",
               name="eye",
               character=None,
               meta_parent=None,
               hook=0,
               aim_vector=[0, 0, 1],
               up_vector=[0, 1, 0],
               target_wire=False,
               tag="face"):
        instance = super(EyeComponent, cls).create(meta_parent=meta_parent, side=side, name=name, hook=hook, character=character, tag=tag)  # type: EyeComponent
        instance.pynode.addAttr("aimControl", at="message")
        eye_joint = pm.PyNode(eye_joint)
        attrFn.add_meta_attr(eye_joint)
        aim_control = luna_rig.Control.create(name="{0}_aim".format(instance.indexed_name),
                                              side=instance.side,
                                              guide=aim_locator,
                                              parent=instance.group_ctls,
                                              delete_guide=True,
                                              attributes="t",
                                              shape="circle",
                                              orient_axis="z",
                                              tag="face")
        pm.aimConstraint(aim_control.transform, eye_joint, aim=aim_vector, u=up_vector)
        if target_wire:
            aim_control.add_wire(eye_joint)

        instance.connect_to_character(parent=True)
        instance._store_bind_joints([eye_joint])
        instance._store_controls([aim_control])
        aim_control.transform.metaParent.connect(instance.pynode.aimControl)
        instance.attach_to_component(meta_parent, hook)
        return instance

    def attach_to_component(self, other_comp, hook_index=0):
        super(EyeComponent, self).attach_to_component(other_comp, hook_index=hook_index)
        if self.in_hook:
            pm.parentConstraint(self.in_hook.transform, self.root, mo=1)
