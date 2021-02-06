import pymel.core as pm
from luna import Logger
import luna_rig
import luna_rig.core.component as component
import luna_rig.core.control as control
from luna_rig.functions import jointFn
from luna_rig.functions import attrFn
from luna_rig.functions import nameFn


class RVFootComponent(component.AnimComponent):

    @classmethod
    def create(cls, meta_parent=None, side=None, name='rv_foot'):
        # Validate arguments
        if not (isinstance(meta_parent, luna_rig.components.FKIKComponent) or isinstance(meta_parent, luna_rig.components.IKComponent)):
            Logger.error("{0}: Invalid meta_parent type. Should be FKIKComponent or IKComponent")
            raise TypeError
        if not side:
            side = meta_parent.side
        # Create instance
        instance = super(RVFootComponent, cls).create(meta_parent=meta_parent, side=side, name=name)
