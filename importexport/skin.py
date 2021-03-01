# Derived from https://github.com/mgear-dev/mgear/blob/master/scripts/mgear/maya/skin.py

import pymel.core as pm
import maya.OpenMaya as om

import luna_rig
import luna
from luna import Logger
from luna import static
from luna.utils import fileFn
from luna_rig.importexport.manager import AbstractManager
import luna_rig.functions.outlinerFn as outlinerFn
import luna_rig.functions.nameFn as nameFn
import luna_rig.functions.deformerFn as deformerFn


class SkinManager(AbstractManager):
    """Manager for skinCluster deformer."""

    def __init__(self, file_format=None):
        super(SkinManager, self).__init__("skinCluster", "skin")
        if not file_format:
            self.file_format = luna.Config.get(luna.RigVars.skin_export_format, default="pickle")  # type: str
        else:
            self.file_format = file_format
        # Verify format
        if self.file_format not in ["json", "pickle"]:
            Logger.error("{0}: Invalid file format: {1}".format(self, self.file_format))
            raise ValueError

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
        Logger.info("{0}: Importing weights...".format(self))
        for geo_name in self.versioned_files.keys():
            if not pm.objExists(geo_name):
                Logger.warning("{0}: Object {1} no longer exists, skipping...".format(self, geo_name))
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
            Logger.warning("{0}: No {1} deformer found in {2} history".format(self, self.data_type, node))
            return
        if not deformerFn.is_painted(deformer):
            Logger.warning("{0}: {1} on {2} has no weights initialized, nothing to export.".format(self, deformer, node))
            return
        # Export
        new_file = self.get_new_file(node)
        try:
            skin = SkinCluster(deformer)
            skin.export_data(new_file, fmt=self.file_format)
            Logger.info("{0}: Exported {1} skin: {2}".format(self, node, new_file))
        except Exception:
            Logger.exception("{0}: Failed to export {1} skin {2}".format(self, node, deformer))

    def import_single(self, geo_name):
        """Import skinCluster weights for given shape.

        :param geo_name: Node to import skinCluster for
        :type geo_name: str, pm.PyNode
        """
        latest_file = self.get_latest_file(geo_name)
        if not latest_file:
            Logger.warning("{0}: No saved skin weights found found for {1}".format(self, geo_name))
            return
        try:
            SkinCluster.import_data(latest_file, geo_name, fmt=self.file_format)
            Logger.info("{0}: Imported {1} weights: {2}".format(self, geo_name, latest_file))
        except Exception:
            Logger.exception("{0}: Failed to import weights for: {1}".format(self, geo_name))

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
        self.pynode = pynode  # type: luna_rig.nt.SkinCluster
        self.data = {"weights": {},
                     "blendWeights": []}

    def get_geometry_components(self):
        fn_set = om.MFnSet(self.pynode.__apimfn__().deformerSet())
        members = om.MSelectionList()
        fn_set.getMembers(members, False)
        dag_path = om.MDagPath()
        components = om.MObject()
        members.getDagPath(0, dag_path, components)
        return dag_path, components
    # Collection

    def get_current_weights(self):
        dag_path, components = self.get_geometry_components()
        weights = om.MDoubleArray()
        util = om.MScriptUtil()
        util.createFromInt(0)
        uint_ptr = util.asUintPtr()
        self.pynode.__apimfn__().getWeights(dag_path, components, weights, uint_ptr)
        return weights

    def collect_inluence_weights(self):
        weights = self.get_current_weights()
        influence_paths = om.MDagPathArray()
        num_inluences = self.pynode.__apimfn__().influenceObjects(influence_paths)
        num_comps_per_influence = weights.length() / num_inluences
        for ii in range(influence_paths.length()):
            influence_name = influence_paths[ii].partialPathName()
            influence_name_no_ns = pm.PyNode(influence_name).stripNamespace()
            inf_weight = [weights[jj * num_inluences + ii] for jj in range(num_comps_per_influence)]
            self.data["weights"][influence_name_no_ns] = inf_weight

    def collect_blend_weights(self):
        dag_path, components = self.get_geometry_components()
        weights = om.MDoubleArray()
        self.pynode.__apimfn__().getBlendWeights(dag_path, components, weights)
        self.data["blendWeights"] = [weights[i] for i in range(weights.length())]

    def collect_data(self):
        self.collect_inluence_weights()
        self.collect_blend_weights()
        for attr_name in ["skinningMethod", "normalizeWeights"]:
            self.data[attr_name] = self.pynode.attr(attr_name).get()

    def export_data(self, file_path, fmt="json"):
        self.collect_data()
        if fmt == "json":
            fileFn.write_json(file_path, self.data, sort_keys=False)
        elif fmt == "pickle":
            fileFn.write_cpickle(file_path, self.data)

    # Setters
    def set_influence_weights(self, skin_data):
        unused_imports = []
        dag_path, components = self.get_geometry_components()
        weights = self.get_current_weights()
        influence_paths = om.MDagPathArray()
        num_influences = self.pynode.__apimfn__().influenceObjects(influence_paths)
        num_comps_per_influence = weights.length() / num_influences
        for imported_influence, imported_weights in skin_data["weights"].items():
            for ii in range(influence_paths.length()):
                influence_name = influence_paths[ii].partialPathName()
                influence_name_no_ns = pm.PyNode(influence_name).stripNamespace()
                if influence_name_no_ns == imported_influence:
                    for jj in range(num_comps_per_influence):
                        weights.set(imported_weights[jj], jj * num_influences + ii)
                    break
            else:
                unused_imports.append(imported_influence)
        influence_indices = om.MIntArray(num_influences)
        for ii in range(num_influences):
            influence_indices.set(ii, ii)
        self.pynode.__apimfn__().setWeights(dag_path, components, influence_indices, weights, False)

        # Show unsused imports
        if unused_imports:
            unused_grp = pm.createNode("transform", n="unsused_joints")
            outlinerFn.set_color(unused_grp, color=[1.0, 0.3, 0.3])
            for unused_name in unused_imports:
                pm.createNode("joint", n=unused_name, p=unused_grp)

    def set_blend_weights(self, skin_data):
        dag_path, components = self.get_geometry_components()
        blend_weights = om.MDoubleArray(len(skin_data["blendWeights"]))
        for index, weight in enumerate(skin_data["blendWeights"]):
            blend_weights.set(weight, index)
        self.pynode.__apimfn__().setBlendWeights(dag_path, components, blend_weights)

    def set_data(self, skin_data):
        self.set_influence_weights(skin_data)
        self.set_blend_weights(skin_data)
        for attr_name in ["skinningMethod", "normalizeWeights"]:
            self.pynode.attr(attr_name).set(skin_data[attr_name])

    @classmethod
    def import_data(cls, file_path, geometry, fmt="json"):
        if fmt == "json":
            skin_data = fileFn.load_json(file_path)
        elif fmt == "pickle":
            skin_data = fileFn.load_cpickle(file_path)  # type: dict

        # Find or create skin cluster
        deformer = deformerFn.get_deformer(geometry, "skinCluster")
        if not deformer:
            try:
                geo_name_parts = nameFn.deconstruct_name(geometry)
                cluster_name = "{0}_{1}_skin".format(geo_name_parts.side, geo_name_parts.indexed_name)
            except Exception:
                cluster_name = str(geometry) + "_skin"
            deformer = pm.skinCluster(skin_data["weights"].keys(), geometry, tsb=True, nw=2, n=cluster_name)
        skin = SkinCluster(deformer)
        skin.set_data(skin_data)
