import pymel.core as pm
from Luna import Logger
from Luna_rig.core import component


class FKComponent(component.AnimComponent):
    def __init__(self, node):
        super(FKComponent, self).__init__(node)

    @classmethod
    def create(cls, meta_parent=None, version=1, side="c", name="fk_component", attach_point_index=0):  # noqa:F821
        fkcomp = super(FKComponent, cls).create(meta_parent, version, side, name)  # type: FKComponent

        # Store attach points
        fkcomp.add_attach_point(fkcomp.group.ctls)
        # Connect to
        fkcomp.connect_to_character(parent=meta_parent is None)
        if meta_parent:
            fkcomp.attach_to_component(meta_parent, attach_point_index)

        return fkcomp

    def attach_to_component(self, other_comp, attach_point_index=0):
        super(FKComponent, self).attach_to_component(other_comp, attach_point_index=attach_point_index)
        attach_obj = other_comp.get_attach_point(attach_point_index)
        pm.parent(self.group.root, attach_obj)
        Logger.debug("Attached: {0} ->> {1}({2})".format(self, other_comp, attach_obj))
