import pymel.core as pm
import timeit
from PySide2 import QtCore

from Luna import Logger
from Luna import Config
from Luna import BuildVars
from Luna.utils import environFn
from Luna.workspace import project
from Luna.workspace import asset
from Luna_rig.functions import asset_files
from Luna_rig import components
reload(asset_files)


class _buildSignals(QtCore.QObject):
    started = QtCore.Signal()
    done = QtCore.Signal()


class PyBuild(object):
    def __init__(self, asset_type, asset_name, version=1):
        self.signals = _buildSignals()

        # Get project instance
        self.project = project.Project.get()  # type: project.Project
        if not self.project:
            pm.warning("Project is not set!")
            return

        # Start build
        self.signals.started.emit()
        pm.newFile(f=1)
        self.start_time = timeit.default_timer()
        Logger.info("Initiating new build...")

        self.asset = asset.Asset(asset_name, asset_type)
        Logger.info(self.asset)
        # Import model and componets files
        asset_files.import_model()
        asset_files.import_guides()
        # Setup character
        Logger.info("Setting up character...")
        self.character = components.Character.create(version=version, name=asset_name)
        Logger.info(self.character)
        environFn.set_character_var(self.character)

        # Override methods
        Logger.info("Building rig...")
        self.run()
        self.character.save_bind_pose()
        Logger.info("Running post build tasks...")
        self.post()

        self.signals.done.emit()
        Logger.info("Build finished in {0:.2f}s".format(timeit.default_timer() - self.start_time))

    def run(self):
        pass

    def post(self):
        pass
