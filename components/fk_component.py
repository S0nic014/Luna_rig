import pymel.core as pm
from Luna import Logger
from Luna_rig.core import component
from Luna.utils import enumFn


class FKComponent(component.AnimComponent):

    def __init__(self, node):
        super(FKComponent, self).__init__(node)

    @classmethod
    def create(cls, meta_parent=None, version=1, side="c", name="fk_component", attach_point=0):  # noqa:F821
        fkcomp = super(FKComponent, cls).create(meta_parent, version, side, name)  # type: FKComponent

        # Store attach points
        fkcomp.add_attach_point(fkcomp.group.ctls)
        # Connect to
        fkcomp.connect_to_character(parent=meta_parent is None)
        fkcomp.attach_to_component(meta_parent, attach_point)

        return fkcomp

    def attach_to_component(self, other_comp, attach_point=0):
        # Check if should attach at all
        if not other_comp:
            return

        # Get attach point from super method
        attach_obj = super(FKComponent, self).attach_to_component(other_comp, attach_point=attach_point)
        if not attach_obj:
            return
        # Component specific attach logic
        pm.parent(self.group.root, attach_obj)
        Logger.debug("Attached: {0} ->> {1}({2})".format(self, other_comp, attach_obj))
