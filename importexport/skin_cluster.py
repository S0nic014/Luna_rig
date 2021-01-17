import pymel.core as pm
from Luna import Logger
from Luna.static import names
from Luna.utils import fileFn
from Luna_rig.importexport import manager
reload(manager)


class SkinClusterManager(manager.DeformerManager):
    def __init__(self):
        super(SkinClusterManager, self).__init__()
        self.path = self.asset.weights.skin_cluster
        self.versioned_files = fileFn.get_versioned_files(self.path, extension=self.extension)

    @property
    def data_type(self):
        return "skinCluster"

    @property
    def extension(self):
        return "skin"

    def get_base_name(self, node):
        return str(node)

    def get_new_file(self, node):
        return fileFn.get_new_versioned_file(self.get_base_name(node), dir_path=self.path, extension=self.extension, full_path=True)

    def get_latest_file(self, node):
        return fileFn.get_latest_file(self.get_base_name(node), self.path, extension=self.extension, full_path=True)

    def export_all(self, under_group=names.Character.geometry.value):
        for deformer_node in self.list_deformers(under_group):
            geo_nodes = deformer_node.getGeometry()
            for geo in geo_nodes:
                self.export_single(geo.getTransform())

    def import_all(self):
        Logger.info("Importing skinCluster weights...")
        count = 0
        for geo in self.versioned_files.keys():
            if not pm.objExists(geo):
                Logger.warning("Object {0} no longer exists, skipping...")
                continue
            self.import_single(geo)
            count += 1
        Logger.info("Imported {0} skinClusters.".format(count))

    def export_single(self, node):
        deformer = self.get_deformer(node)
        if not deformer:
            Logger.error("No {0} deformer found in {1} history".format(self.data_type, node))
            return
        if not self.is_painted(deformer):
            Logger.warning("{0} on {1} has no weights initialized, nothing to export.")
            return
        new_file = self.get_new_file(node)
        # pm.deformerWeights()
        Logger.info("Exported {0} weights: {1}".format(deformer, new_file))

    def import_single(self, node):
        latest_file = self.get_latest_file(node)
        if not latest_file:
            Logger.warning("No saved skinCluster weights found found for {0}".format(node))
            return
        # TODO: parse saved json
        deformer = self.get_deformer(node)
        if not deformer:
            pass  # TODO: Create skinCluster and bind to joints
        Logger.info("Imported {0} skinCluster weights from: {1}".format(node, latest_file))


if __name__ == "__main__":
    skin_manager = SkinClusterManager()
    skin_manager.import_all()
