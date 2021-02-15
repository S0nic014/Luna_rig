import pymel.core as pm
from luna import Logger
import luna_rig
import luna_rig.functions.nameFn as nameFn


class FollicleRivet(object):
    def __repr__(self):
        return "{0}({1})".format(self.__class__.__name__, self.name)

    def __init__(self,
                 side="c",
                 name="rivet"):
        # Create follicle
        self.name = nameFn.generate_name(name, side, "fol")
        self.follicle_shape = pm.createNode("follicle", n=self.name)  # type: luna_rig.nt.Follicle
        self.follicle_shape.pointLock.set(0)
        self.follicle_shape.simulationMethod.set(0)
        self.follicle_shape.collide.set(0)
        self.follicle_shape.stiffness.set(0)
        self.follicle_shape.clumpWidthMult.set(0)
        self.follicle_shape.densityMult.set(0)
        self.follicle_shape.curlMult.set(0)
        self.follicle_shape.sampleDensity.set(0)
        self.follicle_shape.degree.set(1)
        self.follicle_shape.clumpWidth.set(0)
        self.follicle_shape.getTransform().inheritsTransform.set(0)
        # Connect shape to transform
        self.follicle_shape.outRotate.connect(self.follicle_shape.getTransform().rotate)
        self.follicle_shape.outTranslate.connect(self.follicle_shape.getTransform().translate)

    def set_uv(self, uv_values):
        self.follicle_shape.parameterU.set(uv_values[0])
        self.follicle_shape.parameterV.set(uv_values[1])

    def pin_proximity(self, target_shape, pin_guide, delete_guide=False):
        target_shape = pm.PyNode(target_shape)  # type: luna_rig.nt.Mesh
        pin_guide = pm.PyNode(pin_guide)  # type: luna_rig.nt.Transform
        # Verify parameters
        if not isinstance(target_shape, luna_rig.nt.Shape):
            try:
                target_shape = target_shape.getShape()
            except RuntimeError:
                Logger.exception("Can't get shape of object {0}".format(target_shape))
                raise
        uv_values = []
        if isinstance(target_shape, luna_rig.nt.Mesh):
            closest_point_node = pm.createNode("closestPointOnMesh")
            target_shape.worldMesh.connect(closest_point_node.inMesh)
            target_shape.worldMatrix.connect(closest_point_node.inputMatrix)
        elif isinstance(target_shape, luna_rig.nt.NurbsSurface):
            closest_point_node = pm.createNode("closestPointOnSurface")  # type: luna_rig.nt.ClosestPointOnSurface
            target_shape.local.connect(closest_point_node.inputSurface)
        else:
            Logger.error("{0}: Unsupported shape type for pin - {1}".format(self, pm.nodeType(target_shape)))
            raise TypeError
        pin_guide.translate.connect(closest_point_node.inPosition)
        uv_values.append(closest_point_node.result.parameterU.get())
        uv_values.append(closest_point_node.result.parameterV.get())
        pm.delete(closest_point_node)
        self.set_uv(uv_values)
        # Connect world attributes
        if isinstance(target_shape, luna_rig.nt.Mesh):
            target_shape.worldMesh.connect(self.follicle_shape.inputMesh)
        elif isinstance(target_shape, luna_rig.nt.NurbsSurface):
            target_shape.local.connect(self.follicle_shape.inputSurface)
        target_shape.worldMatrix.connect(self.follicle_shape.inputWorldMatrix)
        # Cleanup
        if delete_guide:
            pm.delete(pin_guide)

    def pin_uv(self, target_shape, uv_values):
        target_shape = pm.PyNode(target_shape)  # type: luna_rig.nt.NurbsSurface
        # Verify parameters
        if not isinstance(target_shape, luna_rig.nt.Shape):
            try:
                target_shape = target_shape.getShape()
            except RuntimeError:
                Logger.exception("Can't get shape of object {0}".format(target_shape))
                raise
        # Set uv
        self.set_uv(uv_values)
        # Connect world attributes
        if isinstance(target_shape, luna_rig.nt.Mesh):
            target_shape.worldMesh.connect(self.follicle_shape.inputMesh)
        elif isinstance(target_shape, luna_rig.nt.NurbsSurface):
            target_shape.local.connect(self.follicle_shape.inputSurface)
        target_shape.worldMatrix.connect(self.follicle_shape.inputWorldMatrix)

    @classmethod
    def along_surface(cls,
                      surface,
                      side="c",
                      name="rivet",
                      use_span="u",
                      secondary_value=0.5,
                      parent=None,
                      amount=0):
        created_rivets = []
        # Get surface shape
        if not isinstance(surface, pm.PyNode):
            surface = pm.PyNode(surface)
        if not isinstance(surface, luna_rig.nt.NurbsSurface):
            surface_shape = surface.getShape()
        else:
            surface_shape = surface  # type: luna_rig.nt.NurbsSurface
        # Get spans
        uv_spans = surface_shape.spansUV.get()  # type: list
        if not amount:
            if use_span.lower() == "u":
                amount = uv_spans[0]
            else:
                amount = uv_spans[1]
        # Create rivets
        for span in range(0, amount):
            primary_value = float(span) / float(amount - 1)
            if use_span == "u":
                pin_values = [primary_value, secondary_value]
            else:
                pin_values = [secondary_value, primary_value]
            rivet = cls.create_and_pin(surface, uv_values=pin_values, side=side, name=name, parent=parent)
            created_rivets.append(rivet)

    @classmethod
    def create_and_pin(cls,
                       target_shape,
                       pin_guide=None,
                       uv_values=[],
                       side="c",
                       name="rivet",
                       parent=None,
                       delete_guide=False):
        rivet = cls(side=side, name=name)
        if pin_guide:
            rivet.pin_proximity(target_shape, pin_guide, delete_guide=delete_guide)
        elif uv_values:
            rivet.pin_uv(target_shape, uv_values)
        else:
            Logger.error("Follicle mesh pin requires guide object or UV values.")
            raise RuntimeError
        if parent:
            pm.parent(rivet.follicle_shape.getTransform(), parent)
        return rivet
