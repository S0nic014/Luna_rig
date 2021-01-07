import pymel.core as pm
from pymel.core import nodetypes
import os
from Luna.utils import fileFn
from Luna import Logger
from Luna_rig.importexport import manager
from Luna_rig.core.shape_manager import ShapeManager
from Luna_rig.core.control import Control
from Luna_rig.functions import rigFn


class CtlShapeManager(manager.DataManager):

    def __init__(self, data_type="controls", extension="crvs"):
        super(CtlShapeManager, self).__init__(data_type, extension)
        self.base_file_name = "{0}_{1}".format(self.current_asset.name, self.data_type)

    @classmethod
    def save_selection_to_lib(cls):
        selection = pm.ls(sl=1)
        if not selection or not Control.is_control(selection[-1]):
            Logger.warning("No control selected to save")
            return

        selection = selection[-1]
        export_path = pm.fileDialog2(ff='JSON files (*.json)', cap='Save new shape', dir=ShapeManager.SHAPES_LIB)
        if not export_path:
            return

        export_path = export_path[0]
        shape_name = os.path.basename(export_path)
        ShapeManager.save_shape(selection, shape_name)
        Logger.info("Exported shape: {0}".format(export_path))

    @classmethod
    def load_shape_from_lib(cls):
        selection = pm.ls(sl=1)
        if not selection or not Control.is_control(selection[-1]):
            Logger.warning("No control selected to load shape for!")
            return

        shape_file = pm.fileDialog2(ff='JSON files (*.json)', cap='Select shape', dir=ShapeManager.SHAPES_LIB, fm=1)
        if not shape_file:
            return
        shape_name = os.path.basename(shape_file[0]).split(".")[0]
        for node in selection:
            ctl = Control(node)
            ctl.shape = shape_name
        Logger.info("Successfully loaded shape: " + shape_name)

    @classmethod
    def export_asset_shapes(cls):
        manager = CtlShapeManager()
        if not manager.current_asset:
            Logger.error("Asset is not set!")
            return

        data_dict = {}
        all_controls = rigFn.list_controls()
        if not all_controls:
            Logger.warning("No controls to save shapes for")
            return

        for ctl in all_controls:
            data_dict[ctl.transform.name()] = ctl.shape
        export_path = fileFn.get_new_versioned_file(manager.base_file_name, dir_path=manager.current_asset.controls, extension=manager.extension, full_path=True)
        fileFn.write_json(export_path, data=data_dict)
        Logger.info("Exported {0} control shapes: {1}".format(manager.current_asset.name, export_path))

    @classmethod
    def import_asset_shapes(cls):
        manager = CtlShapeManager()
        if not manager.current_asset:
            Logger.error("Asset is not set!")
            return
        latest_file = fileFn.get_latest_file(manager.base_file_name, manager.current_asset.controls, extension=manager.extension, full_path=True)
        if not latest_file:
            return
        data_dict = fileFn.load_json(latest_file)
        success_count = 0
        for transform, shape_data in data_dict.items():
            success = ShapeManager.apply_shape(transform, shape_list=shape_data)
            if success:
                success_count += 1
        Logger.info("Imported {0}/{1} control shapes: {2}".format(success_count, len(data_dict.keys()), latest_file))
