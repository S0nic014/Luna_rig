import pymel.core as pm
from pymel.core import nodetypes
from luna import Logger
from luna.utils import enumFn
from luna_rig.core import component
from luna_rig.core import control
from luna_rig.functions import jointFn
from luna_rig.functions import nameFn
from luna_rig.functions import rigFn
from luna_rig.functions import attrFn
from luna_rig.functions import curveFn

from luna_rig.components import fk_component


class FKDynamicsComponent(component.AnimComponent):

    @classmethod
    def create(cls,
               meta_parent,
               name="dynamics_component",
               unique_nsolver=False):
        if not isinstance(meta_parent, fk_component.FKComponent):
            Logger.exception("Dynamics component requires FKComponent instance as meta_parent")
            return

        instance = super(FKDynamicsComponent, cls).create(meta_parent, meta_parent.side, name)
        # Joint chain
        ctl_chain = jointFn.duplicate_chain(original_chain=meta_parent.ctl_chain,
                                            replace_name=name,
                                            new_parent=instance.group_joints)

        # Create input curve:
        joint_points = [pm.xform(jnt, q=1, t=1, ws=1) for jnt in ctl_chain]
        input_curve = curveFn.curve_from_points(nameFn.generate_name([name, "input"], side=instance.side, suffix="crv"),
                                                points=joint_points,
                                                parent=instance.group_parts)
        pm.rebuildCurve(input_curve, d=3, end=1, kep=1, rpo=1, ch=0, tol=0.01)
        input_curve.inheritsTransform.set(0)
        meta_parent.character.root_ctl.transform.scale.connect(input_curve.scale)
        # Create hair system
        input_curve.select(r=1)
        pm.mel.eval('makeCurvesDynamic 2 { "0", "0", "1", "1", "0"};')
        pm.select(cl=1)

        # Gather created nodes
        follicle = input_curve.getParent()  # type: nodetypes.Transform
        hair_system = follicle.getShape().listConnections(type="hairSystem")[0]  # type:  nodetypes.Transform
        nucleus = hair_system.getShape().listConnections(type="nucleus")[0]
        output_curve = follicle.getShape().outCurve.listConnections()[0]  # type: nodetypes.NurbsCurve
        output_grp = output_curve.getParent()  # type:  nodetypes.Transform

        # Assign nucleus
        if not unique_nsolver:
            char_nucleus = meta_parent.character.get_nucleus()
            if char_nucleus:
                pm.select(hair_system, r=1)
                pm.mel.eval("assignNSolver {0}".format(char_nucleus))
                pm.delete(nucleus)
                nucleus = char_nucleus  # type: nodetypes.Nucleus
                pm.select(cl=1)
            else:
                nucleus.rename("{0}_nucl".format(meta_parent.character.name))
        else:
            old_nucleus = nucleus
            nucleus = pm.createNode("nucleus", n="{0}_nucl".format(instance.indexed_name))  # type: nodetypes.Nucleus
            pm.select(hair_system, r=1)
            pm.mel.eval("assignNSolver {0}".format(nucleus))
            pm.select(cl=1)
            if not old_nucleus.inputActive.listConnections():
                pm.delete(old_nucleus)
        pm.parent(nucleus, meta_parent.character.root_ctl.transform)

        # Rename hair system objects
        hair_system.rename(nameFn.generate_name([instance.name, "hair"], side=instance.side, suffix="sys"))
        follicle.rename(nameFn.generate_name([instance.name], side=instance.side, suffix="fol"))
        output_grp.rename(nameFn.generate_name([instance.name, "output"], side=instance.side, suffix="grp"))
        output_curve.rename(nameFn.generate_name([instance.name, "out"], side=instance.side, suffix="crv"))

        # Adjust dynamics
        follicle.getShape().pointLock.set(1)
        hair_system.getShape().bendResistance.set(0.3)

        # Parent hair objects
        hair_system.setParent(instance.group_parts)
        output_grp.setParent(instance.group_parts)

        # Create IK spline setup
        ik_handle = pm.ikHandle(n=nameFn.generate_name([instance.name], side=instance.side, suffix="ikh"),
                                sj=ctl_chain[0],
                                ee=ctl_chain[-1],
                                c=output_curve,
                                sol="ikSplineSolver",
                                roc=1,
                                pcv=0,
                                ccv=0,
                                scv=0)[0]  # type: nodetypes.IkHandle
        ik_handle.setParent(instance.group_parts)
        # for fk_ctl, jnt in zip(meta_parent.controls, ctl_chain):
        #     dynam_offset = fk_ctl.insert_offset("dynamics")
        #     jnt.rotate.connect(dynam_offset.rotate)

        # Create param control
        param_locator = rigFn.get_param_ctl_locator(side=instance.side, joint_chain=ctl_chain, move_axis="x", align_index=0)
        param_control = control.Control.create(side=instance.side,
                                               name="{0}_param".format(instance.indexed_name),
                                               object_to_match=param_locator,
                                               delete_match_object=True,
                                               attributes="",
                                               parent=instance.group_ctls,
                                               match_orient=False,
                                               offset_grp=False,
                                               shape="small_cog")
        # Add dynamics attributes
        attr_dict = attrFn.transfer_attr(hair_system.getShape(), param_control.transform, connect=True)
        for added_attr in attr_dict.values():
            instance._store_settings(added_attr)

        # Store joint chains
        instance._store_controls([param_control])
        instance._store_ctl_chain(ctl_chain)
        # Connect to character, parent
        instance.connect_to_character(parent=True)
        instance.attach_to_component(meta_parent)

        # Scale controls
        if not instance.character:
            clamped_size = 1.0
        else:
            clamped_size = instance.character.clamped_size
        param_control.scale(clamped_size, factor=0.2)

        # # House keeping
        if instance.character:
            instance.group_parts.visibility.set(0)
            instance.group_joints.visibility.set(0)
        return instance

    def attach_to_component(self, other_comp, attach_point=0):
        # Check if should attach at all
        if not other_comp:
            return
        # Create meta parent connections
        super(FKDynamicsComponent, self).attach_to_component(other_comp, attach_point=attach_point)
        # Component specific attach logic
        for fk_ctl, jnt in zip(self.meta_parent.controls, self.ctl_chain):
            dynam_offset = fk_ctl.insert_offset("dynamics")
            jnt.rotate.connect(dynam_offset.rotate)
        Logger.debug("Attached: {0} ->> {1}".format(self, other_comp))

    def attach_to_skeleton(self):
        pass
