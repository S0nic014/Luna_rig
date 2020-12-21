import pymel.core as pm
import os
from Luna import Logger
from Luna.utils import environFn
from PySide2 import QtWidgets


def clear_all_references(*args):
    references = pm.listReferences()
    for r in references:
        r.remove()


def browse_model():
    current_asset = environFn.get_asset_var()
    file_filters = "Maya (*.ma *mb);;Maya ASCII (*.ma);;Maya Binary(*.mb);;All Files (*.*)"
    selected_filter = "Maya (*.ma *mb)"
    model_path = QtWidgets.QFileDialog.getOpenFileName(None, "Select model file", current_asset.path, file_filters, selected_filter)[0]
    if not model_path:
        return ""

    return model_path


def import_model():
    current_asset = environFn.get_asset_var()
    model_path = current_asset.model_path
    if not os.path.isfile(model_path):
        model_path = browse_model()
    try:
        pm.importFile(model_path)
        current_asset.meta_data = ("model", model_path)
    except RuntimeError as e:
        Logger.exception("Failed to load model file: {0}".format(model_path))
        raise e
    Logger.info("Imported model: {0}".format(model_path))
    return model_path


def import_guides():
    current_asset = environFn.get_asset_var()
    latest_guides_path = current_asset.latest_guides_path
    pm.importFile(latest_guides_path, loadReferenceDepth="none", dns=1)
    Logger.info("Imported guides: {0}".format(latest_guides_path))
    return latest_guides_path


def reference_model(*args):
    current_asset = environFn.get_asset_var()
    if current_asset:
        pm.createReference(current_asset.model_path)
    else:
        pm.warning("Asset is not set!")
