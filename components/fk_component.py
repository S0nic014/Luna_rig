import pymel.core as pm
from Luna import Logger
from Luna_rig.core import component


class FKComponent(component.AnimComponent):
    def __init__(self, node):
        super(FKComponent, self).__init__(node)

    def __create__(self, side, name):
        super(FKComponent, self).__create__(side, name)

    @classmethod
    def create(cls, meta_parent=None, version=1, side="c", name="fk_component"):  # noqa:F821
        obj_instance = super(FKComponent, cls).create(meta_parent, version, side, name)  # type: FKComponent

        return obj_instance
