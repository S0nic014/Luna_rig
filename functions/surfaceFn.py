import pymel.core as pm
import pymel.api as pma
from luna import Logger
from luna.static import colors
from luna_rig.functions import apiFn


class Surface:

    @classmethod
    def get_surface_data(cls, surface_node):
        """Get surface data

        :param surface_node: Surface to get data from.
        :type surface_node: str or pm.nodetypes.NurbsSurface
        :return: Surface data as dict
        :rtype: dict
        """
        surface_node = pm.PyNode(surface_node)
        if isinstance(surface_node, pm.nodetypes.Transform):
            surface_node = surface_node.getShape()
        if not isinstance(surface_node, pm.nodetypes.NurbsSurface):
            Logger.exception("Invalid shape node type, expected NurbsSurface, got {0}".format(surface_node))
            raise RuntimeError("Faield to get surface data")

        # MObject
        mobj = apiFn.get_MObject(surface_node)
        mfn_surface = pma.MFnNurbsSurface(mobj)
        # Cvs
        cv_array = pma.MPointArray()
        mfn_surface.getCVs(cv_array)
        points = []
        for i in range(cv_array.length()):
            points.append((cv_array[i].x, cv_array[i].y, cv_array[i].z))
        # Knots
        knots_u_array = pma.MDoubleArray()
        knots_v_array = pma.MDoubleArray()
        mfn_surface.getKnotsInU(knots_u_array)
        mfn_surface.getKnotsInV(knots_v_array)
        knots_u = []
        knots_v = []
        for i in range(knots_u_array.length()):
            knots_u.append(knots_u_array[i])
        for i in range(knots_v_array.length()):
            knots_v.append(knots_v_array[i])
        # Degree
        degree_u = mfn_surface.degreeU()
        degree_v = mfn_surface.degreeV()
        # Form
        form_u = mfn_surface.formInU()
        form_v = mfn_surface.formInV()

        # Store data
        data_dict = {"points": points,
                     "knots_u": knots_u,
                     "knots_v": knots_v,
                     "degree_u": degree_u,
                     "degree_v": degree_v,
                     "form_u": form_u,
                     "form_v": form_v}

        return data_dict

    @classmethod
    def create(cls, data_dict, transform=None):
        """Create Nurbs surfac from given data

        :param data: Surface data
        :type data: _surfaceDataStruct
        :param transform: Transform to connect shape node to, defaults to None
        :type transform: pm.nodetypes.Transform, optional
        :return: Packed struct(mobj, partial_path, full_path)
        :rtype: _returnStruct
        """
        # legacy_compatibility
        legacy_keys = {"knotsU": "knots_u",
                       "knotsV": "knots_v",
                       "degreeU": "degree_u",
                       "degreeV": "degree_v",
                       "formU": "form_u",
                       "formV": "form_v"}
        for key in data_dict:
            if key not in legacy_keys.keys():
                continue
            Logger.debug("Legacy key '{0}' found in NurbsSurface dict, converting...".format(key))
            data_dict[legacy_keys[key]] = data_dict.pop(key)

        # Pack dict with API types
        data_dict = cls.pack_surface_data(data_dict)

        mfn_surface = pma.MFnNurbsSurface()
        if transform:
            parent_mobj = apiFn.get_MObject(transform)
        else:
            parent_mobj = pma.MObject()

        instance = mfn_surface.create(data_dict.get("points"),
                                      data_dict.get("knots_u"),
                                      data_dict.get("knots_v"),
                                      data_dict.get("degree_u"),
                                      data_dict.get("degree_v"),
                                      data_dict.get("form_u"),
                                      data_dict.get("form_v"),
                                      True,
                                      parent_mobj)
        # Dag path
        dag_path = pma.MDagPath()
        dag_path = dag_path.getAPathTo(instance)

        # Pack and return
        class _returnStruct:
            mobj = instance
            partial_path = dag_path.partialPathName()
            full_path = dag_path.fullPathName()

        return _returnStruct

    @classmethod
    def get_surface_shader_data(cls, surface):
        surface = pm.PyNode(surface)
        try:
            shading_engine = surface.listConnections(surface, type="shadingEngine")[0]
        except IndexError:
            return None

        material = shading_engine.surfaceShader.listConnections(s=1)[0] or []
        out_color = material.outColor.get()
        data_dict = {"engine": shading_engine,
                     "material": material,
                     "out_color": out_color,
                     "out_color_index": colors.ColorIndex.rgb_to_index(out_color),
                     "out_transparency": material.outTransparency.get()}
        return data_dict

    @classmethod
    def get_shader_data(cls, shader_name):
        shader = pm.PyNode(shader_name)
        out_color = shader.outColor.get()  # RGB
        data_dict = {"out_color": out_color,
                     "out_transparency": shader.outTransparency.get(),
                     "out_color_index": colors.ColorIndex.rgb_to_index(out_color)}
        return data_dict

    @classmethod
    def get_shader_name(cls, index=0):
        """Get shader name from index

        :param index: Color index, defaults to 0
        :type index: int, optional
        """
        color_name = colors.ColorIndex(index).name
        shader_name = "ctl_{0}_shd".format(color_name)
        return shader_name

    @classmethod
    def set_shader(cls, surface, color_index, transparency=0.0):
        surface = pm.PyNode(surface)
        old_shader_data = cls.get_surface_shader_data(surface)
        rgb_color = colors.ColorIndex.index_to_rgb(color_index)
        shader_name = cls.get_shader_name(color_index)
        if not pm.objExists(shader_name):
            shader, engine = pm.createSurfaceShader("surfaceShader", name=shader_name)
        else:
            shader = pm.PyNode(shader_name)
            engine = shader.outColor.listConnections(d=1)[0]
        if isinstance(transparency, float):
            transparency = [transparency, transparency, transparency]
        Logger.debug(transparency)

        shader.outColor.set(rgb_color)
        shader.outTransparency.set(transparency)
        pm.select(surface, r=1)
        pm.sets(engine, fe=1)
        pm.select(cl=1)
        # Delete old shader if unused
        if old_shader_data:
            cls.delete_unused_shader(old_shader_data)

    @classmethod
    def delete_unused_shader(cls, shader_data=None):
        engine = shader_data.get("engine")
        dag_set_members = engine.dagSetMembers.listConnections(d=1)
        if not dag_set_members:
            pm.delete(engine)
            pm.delete(shader_data.get("material"))
            Logger.debug("Deleted unsused control material {0}".format(shader_data.get("material")))

    @classmethod
    def pack_surface_data(cls, data_dict):
        # Cvs
        points = pma.MPointArray()
        for each in data_dict.get("points"):
            newPoint = pma.MPoint(each[0], each[1], each[2])
            points.append(newPoint)

        # Knots
        knots_u = pma.MDoubleArray()
        knots_v = pma.MDoubleArray()
        for val in data_dict.get("knots_u"):
            knots_u.append(val)
        for val in data_dict.get("knots_v"):
            knots_v.append(val)

        data_dict["points"] = points
        data_dict["knots_u"] = knots_u
        data_dict["knots_v"] = knots_v

        return data_dict
