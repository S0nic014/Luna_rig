import pymel.core as pm
import luna
import luna_rig.functions.nameFn as nameFn


def create_locator(at_object=None):
    # TODO: Implement tool dialog and change to stored
    locator = pm.spaceLocator(n=nameFn.generate_name("space", "temp", "loc"))
    match_object = pm.selected()[-1] if pm.selected() else at_object
    if match_object:
        match_rot = luna.Config.get(luna.ToolVars.locator_match_orient, default=False, stored=False)
        match_pos = luna.Config.get(luna.ToolVars.locator_match_position, default=False, stored=False)
        pm.matchTransform(locator, match_object, pos=match_pos, rot=match_rot)
