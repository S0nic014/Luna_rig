import os
import pymel.core as pm
import pymel.api as pma

import luna_rig
from luna import Logger
from luna import static
from luna.utils import fileFn
import luna_rig.functions.apiFn as apiFn
from luna_rig.importexport.manager import AbstractManager
import luna_rig.functions.nameFn as nameFn
import luna_rig.functions.deformerFn as deformerFn
reload(deformerFn)


class SkinManager(AbstractManager):
    """Manager for skinCluster deformer."""

    def __init__(self):
        super(SkinManager, self).__init__("skinCluster", "skin")

    @property
    def path(self):
        return self.asset.weights.skin

    def get_base_name(self, node):
        return str(node)

    def get_new_file(self, node):
        return fileFn.get_new_versioned_file(self.get_base_name(node), dir_path=self.path, extension=self.extension, full_path=True)

    def get_latest_file(self, node):
        return fileFn.get_latest_file(self.get_base_name(node), self.path, extension=self.extension, full_path=True)

    def export_all(self, under_group=static.CharacterMembers.geometry.value):
        """Export all skinCluster weights to skin folder.

        :param under_group: Limit export to nodes that are decendant of this group, defaults to static.CharacterMembers.geometry.value
        :type under_group: str, pm.PyNode, optional
        """
        for deformer_node in deformerFn.list_deformers(self.data_type, under_group=under_group):
            geo_nodes = deformer_node.getGeometry()
            for geo in geo_nodes:
                self.export_single(geo.getTransform())

    def import_all(self):
        """Import asset skin weights.
        """
        Logger.info("Importing skin weights...")
        for geo_name in self.versioned_files.keys():
            if not pm.objExists(geo_name):
                Logger.warning("Object {0} no longer exists, skipping...".format(geo_name))
                continue
            self.import_single(geo_name)

    def export_single(self, node):
        """Export skinCluster for geometry node

        :param node: Shape node with skinCluster attached.
        :type node: str, pm.PyNode
        """
        deformer = deformerFn.get_deformer(node, self.data_type)
        # Do before export checks
        if not deformer:
            Logger.warning("No {0} deformer found in {1} history".format(self.data_type, node))
            return
        if not deformerFn.is_painted(deformer):
            Logger.warning("{0} on {1} has no weights initialized, nothing to export.")
            return
        # Export
        new_file = self.get_new_file(node)
        try:
            skin = SkinCluster(deformer)
            skin.export(new_file)
            Logger.info("Exported {0} skin: {1}".format(node, new_file))
        except Exception:
            Logger.exception("Failed to export {0} skin {1}".format(node, deformer))

    def import_single(self, geo_name):
        """Import skinCluster weights for given shape.

        :param geo_name: Node to import skinCluster for
        :type geo_name: str, pm.PyNode
        """
        latest_file = self.get_latest_file(geo_name)
        if not latest_file:
            Logger.warning("No saved skin weights found found for {0}".format(geo_name))
            return

        skin_data = fileFn.load_json(latest_file)
        deformer = deformerFn.get_deformer(geo_name, self.data_type)
        if not deformer:
            try:
                geo_name_parts = nameFn.deconstruct_name(geo_name)
                cluster_name = "{0}_{1}_skin".format(geo_name_parts.side, geo_name_parts.indexed_name)
            except Exception:
                cluster_name = str(geo_name) + "_skin"

            Logger.debug("skinCluster name: " + cluster_name)
            # pm.skinCluster(skin_data.get("influences"), geo_name, n=cluster_name)
        Logger.info("Imported {0} skin weights: {1}".format(geo_name, latest_file))

    @classmethod
    def export_selected(cls):
        """Export skinCluster weights for selected objects."""
        instance = cls()
        for node in pm.selected():
            instance.export_single(node.stripNamespace())

    @classmethod
    def import_selected(cls):
        """Import skinCluster weights for selected objects."""
        instance = cls()
        for node in pm.selected():
            instance.import_single(node.stripNamespace())


class SkinCluster(object):
    def __init__(self, pynode):
        super(SkinCluster, self).__init__()
        self.pynode = pynode  # type: luna_rig.nt.SkinCluster

    def get_data(self):
        data_dict = {}
        # Get weights
        weight_dict = self.get_influence_weights()
        blend_weights_list = self.get_blend_weights()
        # Store collected data
        data_dict.update(weight_dict)
        data_dict["blendWeights"] = blend_weights_list
        # Store attributes
        for attr_name in ["skinningMethod", "normalizeWeights", "deformUserNormals"]:
            data_dict[attr_name] = self.pynode.attr(attr_name).get()
        return data_dict

    def get_influence_weights(self):
        """Get dictionary of inluence : weight list

        :return: Inluence weights
        :rtype: dict
        """
        weight_dict = {"weights": {}}
        weights = self.pynode.getWeights(self.pynode.getGeometry()[0])
        influence_objects = self.pynode.getInfluence()
        for influence, weight_list in zip(influence_objects, weights):
            weight_dict["weights"][influence.stripNamespace()] = weight_list
        return weight_dict

    def get_blend_weights(self):
        """Get blend weights list for affected geometry

        :return: Blend weights. List of floats.
        :rtype: list
        """
        deformer_set = self.pynode.deformerSet()  # type: luna_rig.nt.ObjectSet
        members = deformer_set.members()
        blend_weights = self.pynode.getBlendWeights(self.pynode.getGeometry()[0], members[0])
        return blend_weights

    def export(self, path, file_type="json"):
        """Export skin data to given file path.

        :param path: Export path
        :type path: str
        :param file_type: Export file type, supported types: "json", "pickle", defaults to "json"
        :type file_type: str, optional
        """
        skin_data = self.get_data()
        if file_type == "json":
            fileFn.write_json(path, skin_data, sort_keys=True)
        elif file_type == "pickle":
            Logger.info("Exporing as pickle...")


if __name__ == "__main__":
    skin_manager = SkinManager()
    skin_manager.export_all()
