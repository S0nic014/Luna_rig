import os
from itertools import izip
import pymel.core as pm
from pymel.core import nodetypes
import pymel.api as pma

from luna import Logger
from luna.static import names
from luna.utils import fileFn
from luna_rig.importexport import manager
from luna_rig.functions import nameFn
reload(manager)


class SkinClusterManager(manager.DeformerManager):
    def __init__(self):
        super(SkinClusterManager, self).__init__("skinCluster", "skin")
        self.versioned_files = fileFn.get_versioned_files(self.path, extension=self.extension)

    @property
    def path(self):
        return self.asset.weights.skin_cluster

    def get_base_name(self, node):
        return str(node)

    def get_new_file(self, node):
        return fileFn.get_new_versioned_file(self.get_base_name(node), dir_path=self.path, extension=self.extension, full_path=True)

    def get_latest_file(self, node):
        return fileFn.get_latest_file(self.get_base_name(node), self.path, extension=self.extension, full_path=True)

    @classmethod
    def get_deformer_data(cls, node):
        skin_data = {
            "name": str(node),
            "weights": node.getWeights(node.getGeometry()[0]),
            # "blendWeights": node.getBlendWeights(node.getGeometry()[0]), #TODO: Add blend weights
            "skinMethod": node.getSkinMethod(),
            "normalizeWeights": node.getNormalizeWeights(),
            "influenceObjects": [str(obj) for obj in node.influenceObjects()]
        }
        return skin_data

    def export_all(self, under_group=names.Character.geometry.value):
        for deformer_node in self.list_deformers(under_group):
            geo_nodes = deformer_node.getGeometry()
            for geo in geo_nodes:
                self.export_single(geo.getTransform())

    def import_all(self):
        Logger.info("Importing skinCluster weights...")
        count = 0
        for geo_name in self.versioned_files.keys():
            if not pm.objExists(geo_name):
                Logger.warning("Object {0} no longer exists, skipping...".format(geo_name))
                continue
            self.import_single(geo_name)
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
        # Write json
        skin_data = self.get_deformer_data(deformer)
        weight_list = [row for row in skin_data.get("weights")]
        skin_data["weights"] = weight_list
        print skin_data.get("influenceObjects")
        fileFn.write_json(new_file, skin_data)
        Logger.info("Exported {0} weights: {1}".format(deformer, new_file))

    def import_single(self, geo_name):
        latest_file = self.get_latest_file(geo_name)
        if not latest_file:
            Logger.warning("No saved skinCluster weights found found for {0}".format(geo_name))
            return

        skin_data = fileFn.load_json(latest_file)
        # TODO: Handle not existing influences
        deformer = self.get_deformer(geo_name)
        if not deformer:
            deformer = pm.skinCluster(skin_data.get("influenceObjects"), geo_name, n=geo_name + "_skin")  # type: nodetypes.SkinCluster
        weights = deformer.getWeights(deformer.getGeometry()[0])
        deformer.setWeights(geo_name, [pm.PyNode(name) for name in skin_data.get("influenceObjects")], weights, skin_data.get("normalizeWeights"))
        Logger.info("Imported {0} skinCluster weights: {1}".format(geo_name, latest_file))

    @classmethod
    def export_selected(cls):
        instance = cls()
        for node in pm.selected():
            instance.export_single(node)

    @classmethod
    def import_selected(cls):
        instance = cls()
        for node in pm.selected():
            instance.import_single(node.stripNamespace())


if __name__ == "__main__":
    skin_manager = SkinClusterManager()
    skin_manager.import_all()
