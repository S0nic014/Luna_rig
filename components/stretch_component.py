import luna_rig
from luna import Logger


class IKSplineStretch(luna_rig.Component):

    @classmethod
    def create(cls, meta_parent, side='c', name='stretch', ik_curve=None, joint_chain=None):
        if not isinstance(meta_parent, luna_rig.AnimComponent):
            Logger.error("{0}: Must have AnimComponent instance as meta_parent".format(cls))
            raise TypeError

        instance = super(IKSplineStretch, cls).create(meta_parent, side=side, name=name)
        instance.pynode.addAttr("ikCurve", at="message")

        # Get curve
        if not ik_curve:
            try:
                ik_curve = meta_parent.pynode.ikCurve.get()
            except AttributeError:
                Logger.exception("{0}: Parent component with IKCurve attribute not found. No override curve provided.")
                raise
