import pymel.core as pm
import luna_rig
from luna_rig.importexport.key_pose import KeyPoseManager


class HandComponent(luna_rig.AnimComponent):

    @property
    def fingers(self):
        connections = self.pynode.fingers.listConnections()  # type: list
        finger_comps = [luna_rig.MetaRigNode(node) for node in connections]
        return finger_comps

    @property
    def controls(self):
        finger_controls = []
        for finger in self.fingers:
            finger_controls += finger.controls
        return finger_controls

    @classmethod
    def create(cls,
               meta_parent=None,
               side=None,
               name="hand",
               hook=0):
        instance = super(HandComponent, cls).create(meta_parent=meta_parent, side=side, name=name, hook=hook)  # type: HandComponent
        instance.pynode.addAttr("fingers", at="message", multi=True, im=False)

        instance.connect_to_character(parent=True)
        instance.attach_to_component(meta_parent, hook)

        return instance

    def add_fk_finger(self, start_joint, end_joint=None, name="finger"):
        if "finger" not in name:
            name = name + "_finger"
        fk_component = luna_rig.components.FKComponent.create(meta_parent=self,
                                                              hook=self.group_ctls,
                                                              side=self.side,
                                                              name=name,
                                                              start_joint=start_joint,
                                                              end_joint=end_joint,
                                                              add_end_ctl=False,
                                                              lock_translate=False)
        fk_component.pynode.metaParent.connect(self.pynode.fingers, na=1)
        fk_component.controls[0].shape = "markerDiamond"
        fk_component.controls[0].scale(1.0, 0.5)
        for ctl in fk_component.controls[1:]:
            ctl.shape = "cube"
            ctl.scale(1.0, 2)

        return fk_component

    def attach_to_component(self, other_comp, hook=0):
        attach_obj = super(HandComponent, self).attach_to_component(other_comp, hook=hook)
        pm.matchTransform(self.root, attach_obj)
        pm.parentConstraint(attach_obj, self.group_ctls)

    def import_poses(self, drive_value=10):
        KeyPoseManager().import_component_poses(self, driver_value=drive_value)
