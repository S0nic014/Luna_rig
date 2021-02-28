import pymel.core as pm
import luna_rig
from luna import Logger
from luna_rig.functions import jointFn
from luna_rig.functions import nameFn
from luna_rig.functions import attrFn


class EmptyComponent(luna_rig.AnimComponent):

    @classmethod
    def create(cls,
               meta_parent=None,
               hook=None,
               character=None,
               side="c",
               name="empty_component"):
        instance = super(EmptyComponent, cls).create(meta_parent=meta_parent, side=side, name=name, character=character)  # type: EmptyComponent
        instance.connect_to_character(character, parent=True)
        instance.attach_to_component(meta_parent, hook_index=hook)
        return instance

    def add_control(self, guide_object, name, as_hook=False, add_bind_joint=False, *args, **kwargs):
        new_control = luna_rig.Control.create(name=[self.indexed_name, name],
                                              parent=self.group_ctls,
                                              guide=guide_object,
                                              joint=add_bind_joint,
                                              *args,
                                              **kwargs)
        self._store_controls([new_control])
        # Connect to hook
        if self.in_hook:
            pm.parentConstraint(self.in_hook.transform, new_control.group, mo=1)
        # Store hook
        if as_hook:
            self.add_hook(new_control.transform, new_control.name)
        # Add bind joint
        if add_bind_joint:
            self._store_bind_joints([new_control.joint])
        return new_control

    def attach_to_skeleton(self):
        pass
