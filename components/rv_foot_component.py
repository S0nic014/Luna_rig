import pymel.core as pm
from luna import Logger
import luna_rig
from luna_rig.functions import jointFn
from luna_rig.functions import attrFn
from luna_rig.functions import nameFn


class RVFootComponent(luna_rig.AnimComponent):

    @classmethod
    def create(cls, meta_parent=None, side=None, name='rv_foot'):
        # Validate arguments
        if not (isinstance(meta_parent, luna_rig.components.FKIKComponent) or isinstance(meta_parent, luna_rig.components.IKComponent)):
            Logger.error("{0}: Invalid meta_parent type. Should be FKIKComponent or IKComponent")
            raise TypeError
        side = side if side else meta_parent.side
        # Create instance
        instance = super(RVFootComponent, cls).create(meta_parent=meta_parent, side=side, name=name)  # type: RVFootComponent

        return instance
