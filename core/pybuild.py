import pymel.core as pm
import timeit
from PySide2 import QtCore

from luna import Logger
from luna import Config
from luna import BuildVars
from luna.utils import environFn
from luna.utils import maya_utils
from luna.workspace import project
from luna.workspace import asset
from luna_rig.functions import asset_files
from luna_rig import components


class _buildSignals(QtCore.QObject):
    started = QtCore.Signal()
    done = QtCore.Signal()


class PyBuild(object):
    def __init__(self, asset_type, asset_name):
        self.signals = _buildSignals()

        # Get project instance
        self.project = project.Project.get()  # type: project.Project
        if not self.project:
            pm.warning("Project is not set!")
            return

        # Start build
        pm.scriptEditorInfo(e=1, sr=1)
        self.signals.started.emit()
        pm.newFile(f=1)
        self.start_time = timeit.default_timer()
        Logger.info("Initiating new build...")

        self.asset = asset.Asset(asset_name, asset_type)
        # Import model and componets files
        asset_files.import_model()
        asset_files.import_guides()
        # Setup character
        self.character = components.Character.create(name=asset_name)
        environFn.set_character_var(self.character)

        # Override methods
        self.run()
        self.character.save_bind_pose()
        Logger.info("Running post build tasks...")
        self.post()

        # Adjust viewport
        pm.select(cl=1)
        maya_utils.switch_xray_joints()
        pm.viewFit(self.character.root_ctl.group)
        if Config.get(BuildVars.geometry_override, default=True):
            self.character.geometry_grp.overrideEnabled.set(1)
            self.character.geometry_grp.overrideColor.set(1)

        # Report completion
        self.signals.done.emit()
        Logger.info("Build finished in {0:.2f}s".format(timeit.default_timer() - self.start_time))
        pm.scriptEditorInfo(e=1, sr=0)

    def run(self):
        pass

    def post(self):
        pass
