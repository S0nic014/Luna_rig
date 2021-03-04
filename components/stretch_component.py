from luna import Logger
import luna_rig
import luna_rig.functions.nodeFn as nodeFn


class IKSplineStretch(luna_rig.Component):

    @property
    def ik_curve(self):
        try:
            curve_transform = self.meta_parent.pynode.ikCurve.get()  # type: luna_rig.nt.Transform
        except AttributeError:
            Logger.exception("{0}: Parent component with IKCurve attribute not found. No override curve provided.")
            raise
        return curve_transform

    @classmethod
    def create(cls, meta_parent,
               side=None,
               name='stretch',
               switch_control=None,
               default_state=False,
               switch_attr="stretch",
               joint_attr="scaleX"):
        if not isinstance(meta_parent, luna_rig.AnimComponent):
            Logger.error("{0}: Must have AnimComponent instance as meta_parent".format(cls))
            raise TypeError

        if switch_control and not isinstance(switch_control, luna_rig.Control):
            switch_control = luna_rig.Control(switch_control)

        if not side:
            side = meta_parent.side

        # Full name based on parent component
        full_name = "_".join([meta_parent.indexed_name, name])
        instance = super(IKSplineStretch, cls).create(meta_parent, side=side, name=full_name)  # type: IKSplineStretch

        # Apply stretch
        curve_info = nodeFn.create("curveInfo", [instance.name, "curve"], instance.side, suffix="info")
        instance.ik_curve.getShape().worldSpace.connect(curve_info.inputCurve)
        # Divide initial length by current
        final_scale_mdv = nodeFn.create("multiplyDivide", [instance.name, "pure"], instance.side, suffix="mdv")
        final_scale_mdv.operation.set(2)
        curve_info.arcLength.connect(final_scale_mdv.input1X)

        # Counter scale
        counter_scale_mdv = nodeFn.create("multiplyDivide", [instance.name, "unscale"], instance.side, suffix="mdv")
        meta_parent.character.root_control.transform.Scale.connect(counter_scale_mdv.input1X)
        counter_scale_mdv.input2X.set(curve_info.arcLength.get())
        counter_scale_mdv.outputX.connect(final_scale_mdv.input2X)

        if switch_control:
            switch_control.transform.addAttr(switch_attr, at="bool", k=1, dv=default_state)
            switch_choice = nodeFn.create("choice", [instance.name, "switch"], instance.side, suffix="mdl")
            switch_control.transform.attr(switch_attr).connect(switch_choice.selector)
            switch_choice.input[0].set(1.0)
            final_scale_mdv.outputX.connect(switch_choice.input[1])
            for jnt in meta_parent.ctl_chain:
                switch_choice.output.connect(jnt.attr(joint_attr))
        else:
            Logger.warning("{0}: No control was used for state control")
