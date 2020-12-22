import os
import pymel.core as pm
from pymel.core import nodetypes

from Luna import Logger
from Luna.utils import fileFn
from Luna.utils import enumFn
from Luna.static import directories
from Luna_rig.functions import surfaceFn
from Luna_rig.functions import curveFn


class ShapeManager:
    # TODO: Write tests
    SHAPES_LIB = directories.SHAPES_LIB_PATH

    @classmethod
    def get_shapes(cls, node):
        node = pm.PyNode(node)
        shapes_list = []
        if isinstance(node, pm.nodetypes.Transform):
            child_shapes = node.getShapes()
        elif isinstance(node, pm.nodetypes.Shape):
            child_shapes = node.getTransform().getShapes()
        if not child_shapes:
            Logger.warning("No child shapes found for {0}".format(node))
            return []

        if isinstance(child_shapes[0], pm.nodetypes.NurbsSurface):
            for shape_node in child_shapes:
                shader_data = surfaceFn.Surface.get_surface_shader_data(shape_node)
                shape_data = surfaceFn.Surface.get_surface_data(shape_node)
                shape_data["color"] = shader_data.get("out_color", 0)
                shape_data["transparency"] = shader_data.get("out_transparency", 0.0)
                shape_data["type"] = "nurbsSurface"
                shapes_list.append(shape_data)

        elif isinstance(child_shapes[0], pm.nodetypes.NurbsCurve):
            for shape_node in child_shapes:
                shape_data = curveFn.get_curve_data(shape_node)
                shapes_list.append(shape_data)

        return shapes_list

    @classmethod
    def set_shape_from_lib(cls, node, shape_name, surface_transparency=0.0):
        node = pm.PyNode(node)
        # Store default values
        default_color = 0
        old_color = default_color
        old_transparency = surface_transparency

        # Get child shapes
        if isinstance(node, pm.nodetypes.Transform):
            child_shapes = node.getShapes()
        elif isinstance(node, pm.nodetypes.Shape):
            node = node.getTransform()
            child_shapes = node.getShapes()

        # Get old shapes color and transparency data
        if child_shapes:
            if isinstance(child_shapes[0], pm.nodetypes.NurbsCurve):
                old_color = child_shapes[0].overrideColor.get()
                matching_shader = surfaceFn.Surface.get_shader_name(old_color)
                if pm.objExists(matching_shader):
                    old_transparency = surfaceFn.Surface.get_shader_data(matching_shader)
            elif isinstance(child_shapes, pm.nodetypes.NurbsSurface):
                shader_data = surfaceFn.Surface.get_surface_shader_data(child_shapes[0])
                old_color = shader_data.get("out_color_index")
                old_transparency = shader_data.get("out_transparency")

        # Iterate over loaded shape
        loaded_shape_list = cls.load_shape_from_lib(shape_name)
        cls.apply_shape(node, loaded_shape_list, default_color=old_color, default_transparency=old_transparency)
        pm.select(node, r=1)

    @classmethod
    def apply_shape(cls, node, shape_list, default_color=0, default_transparency=0.0):
        node = pm.PyNode(node)  # type: nodetypes.Transform
        pm.delete(node.getShapes())
        for index, shape_dict in enumerate(shape_list):
            if shape_dict.get("type") == "nurbsCurve":
                # Create temporary curve
                tmp_curve = pm.curve(p=shape_dict.get("points"), k=shape_dict.get("knots"), d=shape_dict.get("degree"))
                new_shape_node = tmp_curve.getShape()
                # Parent new shape node to transform
                pm.parent(new_shape_node, node, r=1, s=1)
                pm.delete(tmp_curve)
                # Rename newly creted shape node
                new_shape_node = pm.rename(new_shape_node, str(node) + "Shape" + str(index + 1).zfill(2))
                new_shape_node.overrideEnabled.set(1)
                # Set color for new shape
                if "color" in shape_dict.keys():
                    cls.set_color(new_shape_node, shape_dict.get("color"))
                else:
                    cls.set_color(new_shape_node, default_color)

            elif shape_dict.get("type") == "nurbsSurface":
                new_surface = surfaceFn.Surface.create(shape_dict, transform=node)
                new_surface = pm.rename(new_surface.partial_path, str(node) + "Shape" + str(index + 1).zfill(2))
                # Set color values
                if "color" in shape_dict.keys():
                    new_color = shape_dict.get("color")
                else:
                    new_color = default_color
                if "transparency" in shape_dict.keys():
                    transparency = shape_dict.get("transparency", 0.0)
                else:
                    transparency = default_transparency

                # Set shader
                surfaceFn.Surface.set_shader(new_surface, color_index=new_color, transparency=transparency)

    @classmethod
    def load_shape_from_lib(cls, shape_name):
        path = os.path.join(cls.SHAPES_LIB, shape_name + ".json")
        if not os.path.isfile(path):
            Logger.exception("Shape file doesn't exist {0}".format(path))
            path = os.path.join(cls.SHAPES_LIB, "cube.json")
        data = fileFn.load_json(path)  # type: dict
        return data

    @classmethod
    def save_shape(cls, transform, name, path=None):
        if not path:
            path = cls.SHAPES_LIB
        transform = pm.PyNode(transform)
        shape_list = cls.get_shapes(transform)
        save_path = os.path.join(path, name + ".json")
        for data_dict in shape_list:
            data_dict.pop("color", None)
            data_dict.pop("transparency", [0.0, 0.0, 0.0])
        fileFn.write_json(save_path, shape_list)

    @classmethod
    def set_color(cls, node, color):
        node = pm.PyNode(node)
        if isinstance(color, enumFn.Enum):
            color = color.value
        if isinstance(node, pm.nodetypes.Transform):
            shape_nodes = node.getShapes()
        elif isinstance(node, pm.nodetypes.Shape):
            shape_nodes = [node]

        for shape in shape_nodes:
            if isinstance(shape, pm.nodetypes.NurbsCurve):
                shape.overrideColor.set(color)
            elif isinstance(shape, pm.nodetypes.NurbsSurface):
                old_transparency = surfaceFn.Surface.get_surface_shader_data(shape).get("out_transparency")
                surfaceFn.Surface.set_shader(shape, color, old_transparency)

    @classmethod
    def get_color(cls, node):
        node = pm.PyNode(node)
        color = 0
        if isinstance(node, pm.nodetypes.Transform):
            shapes = node.getShapes()
            if not shapes:
                Logger.warning("No shapes found for {0}".format(node))
                return color
            child_shape = shapes[0]
            if isinstance(child_shape, pm.nodetypes.NurbsCurve):
                color = child_shape.overrideColor.get()
            elif isinstance(child_shape, pm.nodetypes.NurbsSurface):
                color = surfaceFn.Surface.get_surface_shader_data(child_shape).get("out_color_index")
        else:
            Logger.error("Invalid transform {0}, cant't get color!".format(node))

        return color
