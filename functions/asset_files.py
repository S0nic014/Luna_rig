import pymel.core as pm
import os
from Luna import Logger
from Luna.utils import environFn


def clearAllReferences(*args):
    references = pm.listReferences()
    for r in references:
        r.remove()


def import_model():
    current_asset = environFn.get_asset_var()
    model_path = current_asset.get_model_path()  # type:str
    if not os.path.isfile(model_path):
        model_path = current_asset.find_model()
    try:
        pm.importFile(model_path)
    except RuntimeError as e:
        Logger.exception("Failed to load model file: {0}".format(model_path))
        raise e
    Logger.info("Imported model: {0}".format(model_path))
    return model_path


def import_guides():
    current_asset = environFn.get_asset_var()
    latest_guides_path = current_asset.get_latest_guides_path()
    pm.importFile(latest_guides_path, loadReferenceDepth="none", dns=1)
    Logger.info("Imported guides: {0}".format(latest_guides_path))
    return latest_guides_path


def referenceLatestModel(*args):
    current_asset = environFn.get_asset_var()
    if current_asset:
        pm.createReference(current_asset.get_model_path())
    else:
        pm.warning("Asset is not set!")
