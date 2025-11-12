bl_info = {
    "name": "G3D Mesh Import/Export",
    "description": "Import/Export .g3d file (Glest 3D)",
    "author": "various, updated for Blender 5.x by Keith",
    "version": (0, 12, 2),
    "blender": (5, 1, 0),
    "location": "File > Import/Export > Glest 3D (.g3d)",
    "category": "Import-Export",
}

import bpy
from bpy.props import StringProperty, BoolProperty, IntProperty, FloatVectorProperty
from bpy_extras.io_utils import ImportHelper, ExportHelper
import struct, os, traceback, bmesh, subprocess
from mathutils import Matrix
from math import radians
from mathutils import Vector

###########################################################################
# --- Helpers & Data Structures ---
###########################################################################
def unpack_list(list_of_tuples):
    l = []
    for t in list_of_tuples:
        l.extend(t)
    return l


class G3DHeader:
    binary_format = "<3cB"
    def __init__(self, fileID):
        temp = fileID.read(struct.calcsize(self.binary_format))
        data = struct.unpack(self.binary_format, temp)
        self.id = (data[0] + data[1] + data[2]).decode("utf-8")
        self.version = data[3]


class G3DModelHeaderv4:
    binary_format = "<HB"
    def __init__(self, fileID):
        temp = fileID.read(struct.calcsize(self.binary_format))
        data = struct.unpack(self.binary_format, temp)
        self.meshcount = data[0]
        self.mtype = data[1]


class G3DMeshHeaderv4:
    binary_format = "<64c3I8f2I"
    texname_format = "<64c"

    def _readtexname(self, fileID):
        temp = fileID.read(struct.calcsize(self.texname_format))
        data = struct.unpack(self.texname_format, temp)
        # decode and strip nulls
        return "".join([c.decode("ascii") for c in data if c != b'\x00'])

    def __init__(self, fileID):
        temp = fileID.read(struct.calcsize(self.binary_format))
        data = struct.unpack(self.binary_format, temp)
        self.meshname = "".join([c.decode("ascii") for c in data[:64] if c != b'\x00'])
        self.framecount = data[64]
        self.vertexcount = data[65]
        self.indexcount = data[66]
        self.diffusecolor = data[67:70]
        self.specularcolor = data[70:73]
        self.specularpower = data[73]
        self.opacity = data[74]
        self.properties = data[75]
        self.textures = data[76]

        self.customalpha = bool(self.properties & 1)
        self.istwosided = bool(self.properties & 2)
        self.noselect = bool(self.properties & 4)
        self.glow = bool(self.properties & 8)
        self.teamcoloralpha = 255 - (self.properties >> 24)

        self.hastexture = False
        self.diffusetexture = None
        self.speculartexture = None
        self.normaltexture = None

        if self.textures:
            if self.textures & 1:
                self.diffusetexture = self._readtexname(fileID)
            if self.textures & 2:
                self.speculartexture = self._readtexname(fileID)
            if self.textures & 4:
                self.normaltexture = self._readtexname(fileID)
            self.hastexture = True


class G3DMeshdataV4:
    def __init__(self, fileID, header):
        vertex_format = "<%if" % int(header.framecount * header.vertexcount * 3)
        normals_format = "<%if" % int(header.framecount * header.vertexcount * 3)
        texturecoords_format = "<%if" % int(header.vertexcount * 2)
        indices_format = "<%iI" % int(header.indexcount)

        self.vertices = struct.unpack(vertex_format, fileID.read(struct.calcsize(vertex_format)))
        self.normals = struct.unpack(normals_format, fileID.read(struct.calcsize(normals_format)))
        if header.hastexture:
            self.texturecoords = struct.unpack(texturecoords_format, fileID.read(struct.calcsize(texturecoords_format)))
        else:
            self.texturecoords = ()
        self.indices = struct.unpack(indices_format, fileID.read(struct.calcsize(indices_format)))

###########################################################################
# --- Import Implementation ---
###########################################################################
def createMesh_import(filename, header, data, toblender, operator):
    mesh = bpy.data.meshes.new(header.meshname)
    meshobj = bpy.data.objects.new(header.meshname + "_Object", mesh)
    bpy.context.collection.objects.link(meshobj)
    bpy.context.view_layer.update()

    # Build vertex list (first frame)
    vertsCO = [(data.vertices[i], data.vertices[i+1], data.vertices[i+2])
               for i in range(0, header.vertexcount * 3, 3)]
    faces = [(data.indices[i], data.indices[i+1], data.indices[i+2])
             for i in range(0, len(data.indices), 3)]
    mesh.from_pydata(vertsCO, [], faces)
    mesh.update()

    if header.hastexture and data.texturecoords:
        uv_layer = mesh.uv_layers.new(name="UVMap")
        for f_idx, face in enumerate(mesh.polygons):
            for loop_idx in face.loop_indices:
                vert_idx = mesh.loops[loop_idx].vertex_index
                u = data.texturecoords[vert_idx * 2]
                v = data.texturecoords[vert_idx * 2 + 1]
                uv_layer.data[loop_idx].uv = (u, v)
    
    # Bake shape keys if animation exists
    if header.framecount > 1:
        if meshobj.data.shape_keys is None:
            meshobj.shape_key_add(name="Basis", from_mix=False)
        for f in range(1, header.framecount):
            sk = meshobj.shape_key_add(name=f"Frame_{f}", from_mix=False)
            for i in range(header.vertexcount):
                idx = (f * header.vertexcount + i) * 3
                sk.data[i].co = (
                    data.vertices[idx],
                    data.vertices[idx + 1],
                    data.vertices[idx + 2]
                )

        # --- Auto-keyframe shape keys for timeline playback ---
        print(f"Baking {len(meshobj.data.shape_keys.key_blocks) - 1} shape keys into timeline keyframes...")

        shape_keys = [k for k in meshobj.data.shape_keys.key_blocks if k.name != "Basis"]
        start_frame = 1
        frame_step = 1

        # Ensure we're in object mode
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        # Reset all values
        for key in shape_keys:
            key.value = 0.0
            key.keyframe_insert(data_path="value", frame=start_frame)

        # Insert keyframes one per shape key
        frame = start_frame
        for key in shape_keys:
            for k in shape_keys:
                k.value = 0.0
                k.keyframe_insert(data_path="value", frame=frame)
            key.value = 1.0
            key.keyframe_insert(data_path="value", frame=frame)
            key.value = 0.0
            frame += frame_step

    if toblender:
        meshobj.rotation_euler = (radians(90), 0, 0)
        
    meshobj["is_g3d"] = True

    # Material setup with textures
    if header.hastexture:
        mat = bpy.data.materials.new(name=header.meshname + "_Mat")
        mat.use_nodes = True
        tree = mat.node_tree
        nodes = tree.nodes
        links = tree.links
        nodes.clear()

        output_node = nodes.new(type="ShaderNodeOutputMaterial")
        output_node.location = (400, 0)

        bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
        bsdf.location = (0, 0)
        links.new(bsdf.outputs['BSDF'], output_node.inputs['Surface'])

        def resolve_texture_path(base_path, tex_name):
            tex_dir = os.path.dirname(base_path)
            tex_name_noext, ext = os.path.splitext(tex_name)
            png_path = os.path.join(tex_dir, tex_name_noext + ".png")
            original_path = os.path.join(tex_dir, tex_name)
            return png_path if os.path.exists(png_path) else original_path

        # --- Diffuse texture (with team color + diffuse multiplier support) ---
        color_input = None
        if header.diffusetexture:
            tex_diff = nodes.new(type="ShaderNodeTexImage")
            tex_diff.location = (-600, 200)
            tex_path = resolve_texture_path(filename, header.diffusetexture)
            try:
                tex_diff.image = bpy.data.images.load(tex_path)
            except:
                print(f"Warning: Diffuse texture not found: {tex_path}")
            color_input = tex_diff.outputs['Color']

            # If model uses custom alpha (team color regions)
        if header.customalpha or getattr(meshobj.data, "g3d_customColor", False):
            team_color_node = nodes.new(type="ShaderNodeRGB")
            team_color_node.location = (-600, 0)
            team_color_node.outputs[0].default_value = (0.1, 0.4, 1.0, 1.0)

            mix_team = nodes.new(type="ShaderNodeMixRGB")
            mix_team.blend_type = 'MIX'
            mix_team.location = (-400, 100)
            mix_team.inputs['Fac'].default_value = header.teamcoloralpha / 255.0
            links.new(tex_diff.outputs['Alpha'], mix_team.inputs['Fac'])
            links.new(team_color_node.outputs['Color'], mix_team.inputs['Color2'])
            links.new(tex_diff.outputs['Color'], mix_team.inputs['Color1'])
            color_input = mix_team.outputs['Color']

            # enable transparency on the material
            mat.blend_method = 'BLEND'
            if hasattr(mat, "shadow_method"):
                mat.shadow_method = 'HASHED'

            # Apply diffuse color multiplier if needed
            if header.diffusecolor != (1.0, 1.0, 1.0):
                mult_node = nodes.new(type="ShaderNodeMixRGB")
                mult_node.location = (-150, 100)
                mult_node.blend_type = 'MULTIPLY'
                mult_node.inputs['Fac'].default_value = 1.0
                mult_node.inputs['Color2'].default_value = (
                    header.diffusecolor[0],
                    header.diffusecolor[1],
                    header.diffusecolor[2],
                    1.0
                )
                links.new(color_input, mult_node.inputs['Color1'])
                color_input = mult_node.outputs['Color']

            # Final link to shader
            links.new(color_input, bsdf.inputs['Base Color'])

        # --- Specular texture ---
        if header.speculartexture:
            tex_spec = nodes.new(type="ShaderNodeTexImage")
            tex_spec.location = (-400, 0)
            tex_path = resolve_texture_path(filename, header.speculartexture)
            try:
                tex_spec.image = bpy.data.images.load(tex_path)
            except:
                print(f"Warning: Specular texture not found: {tex_path}")
            links.new(tex_spec.outputs['Color'], bsdf.inputs['Specular'])

        # --- Normal map ---
        if header.normaltexture:
            tex_norm = nodes.new(type="ShaderNodeTexImage")
            tex_norm.location = (-400, -200)
            tex_path = resolve_texture_path(filename, header.normaltexture)
            try:
                tex_norm.image = bpy.data.images.load(tex_path)
            except:
                print(f"Warning: Normal map not found: {tex_path}")
            tex_norm.image.colorspace_settings.name = 'Non-Color'
            norm_node = nodes.new(type="ShaderNodeNormalMap")
            norm_node.location = (-200, -200)
            links.new(tex_norm.outputs['Color'], norm_node.inputs['Color'])
            links.new(norm_node.outputs['Normal'], bsdf.inputs['Normal'])

        meshobj.data.materials.append(mat)

    mesh.update()
    mesh.validate(clean_customdata=True)
    return meshobj


def G3DLoader(filepath, toblender, operator):
    print(f"\nImporting: {filepath}")
    try:
        fileID = open(filepath, "rb")
    except Exception as e:
        operator.report({'ERROR'}, f"Could not open file: {e}")
        return {'CANCELLED'}

    header = G3DHeader(fileID)

    if header.id != "G3D" or header.version not in (4,):
        operator.report({'ERROR'}, "Unsupported or invalid G3D file (only v4 supported by this importer)")
        fileID.close()
        return {'CANCELLED'}

    modelheader = G3DModelHeaderv4(fileID)
    created = []
    for _ in range(modelheader.meshcount):
        meshheader = G3DMeshHeaderv4(fileID)
        meshdata = G3DMeshdataV4(fileID, meshheader)
        obj = createMesh_import(filepath, meshheader, meshdata, toblender, operator)
        created.append(obj)

    fileID.close()
    operator.report({'INFO'}, f"Imported {len(created)} mesh(es)")
    return {'FINISHED'}

###########################################################################
# --- Export Implementation (full exporter) ---
###########################################################################
def find_image_in_material(material):
    if material is None:
        return None
    if material.use_nodes:
        tree = material.node_tree
        if tree:
            # look for first Image Texture node with an image
            for node in tree.nodes:
                if node.type == 'TEX_IMAGE' and getattr(node, "image", None):
                    return node.image
    else:
        for slot in material.texture_paint_images:
            if slot:
                return slot
        if hasattr(material, "texture_slots"):
            for slot in material.texture_slots:
                if slot and slot.texture and slot.texture.type == 'IMAGE' and slot.texture.image:
                    return slot.texture.image
    return None

###########################################################################
# --- Blender UI / Operators / Panel ---
###########################################################################
class G3DPanel(bpy.types.Panel):
    bl_label = "G3D properties"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        return (context.object is not None and context.object.type == 'MESH')

    def draw(self, context):
        self.layout.prop(context.object.data, "g3d_customColor")
        col = self.layout.column()
        col.prop(context.object.data, "teamcolor_alpha")
        col.enabled = context.object.data.g3d_customColor
        self.layout.prop(context.object.data, "g3d_double_sided", text="double sided")
        self.layout.prop(context.object.data, "g3d_noSelect")
        self.layout.prop(context.object.data, "g3d_fullyOpaque")
        self.layout.prop(context.object.data, "g3d_glow")
        self.layout.prop(context.object.data, "g3d_ignore_lighting", text="Ignore Scene Lights")
        if context.object.data.g3d_ignore_lighting:
            row = self.layout.row()
            row.prop(context.object.data, "g3d_ignore_lighting_normal", text="Uniform Normal", slider=False)   
            
class G3DPlayShapeKeys(bpy.types.Operator):
    bl_idname = "object.play_g3d_shapes"
    bl_label = "Play G3D Animation"

    _timer = None
    frame = 0

    def modal(self, context, event):
        if event.type == 'TIMER':
            obj = context.object
            if obj.data.shape_keys and len(obj.data.shape_keys.key_blocks) > 1:
                keys = obj.data.shape_keys.key_blocks
                for k in keys:
                    k.value = 0.0
                keys[self.frame % len(keys)].value = 1.0
                self.frame += 1
        elif event.type in {'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}

    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.2, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)


class ImportG3D(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.g3d"
    bl_label = "Import G3D"
    filename_ext = ".g3d"
    filter_glob: StringProperty(default="*.g3d", options={'HIDDEN'})
    toblender: BoolProperty(name="rotate to Blender orientation", default=True)

    def execute(self, context):
        try:
            return G3DLoader(self.filepath, self.toblender, self)
        except Exception as e:
            traceback.print_exc()
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}


class ExportG3D(bpy.types.Operator, ExportHelper):
    bl_idname = "export_scene.g3d"
    bl_label = "Export G3D"
    filename_ext = ".g3d"
    filter_glob: StringProperty(default="*.g3d", options={'HIDDEN'})

    showg3d: BoolProperty(
        name="show G3D afterwards",
        description=("Run g3dviewer to show G3D after export. "
                     "g3dviewer needs to be in the scripts directory, "
                     "otherwise the associated program of .g3d is run."),
        default=False)

    toglest: BoolProperty(
        name="rotate to glest orientation",
        description="Rotate meshes from Blender to Glest orientation",
        default=True)

    def execute(self, context):
        try:
            res = G3DSaver(self.filepath, context, self.toglest, self)
            if res == 0 and self.showg3d:
                scriptsdir = bpy.utils.script_path_user()
                dname = os.path.dirname(self.filepath)
                found = False
                if scriptsdir:
                    for f in os.listdir(scriptsdir):
                        if "g3dviewer" in f:
                            fpath = os.path.join(scriptsdir, f)
                            if os.path.isfile(fpath) and os.access(fpath, os.X_OK):
                                subprocess.Popen([fpath, self.filepath], cwd=dname)
                                found = True
                                break
                if not found:
                    if os.name == 'posix':
                        subprocess.Popen(['xdg-open', self.filepath], cwd=dname)
                    elif os.name == 'mac':
                        subprocess.Popen(['open', self.filepath], cwd=dname)
                    elif os.name == 'nt':
                        subprocess.Popen(['cmd', '/C', 'start', self.filepath], cwd=dname)
        except Exception as e:
            traceback.print_exc()
            return {'CANCELLED'}
        return {'FINISHED'}


def menu_func_import(self, context):
    self.layout.operator(ImportG3D.bl_idname, text="Glest 3D Model (.g3d)")


def menu_func_export(self, context):
    self.layout.operator(ExportG3D.bl_idname, text="Glest 3D File (.g3d)")


classes = (
    G3DPanel,
    ImportG3D,
    ExportG3D,
)

def G3DSaver(filepath, context, toglest, operator):
    print(f"\nExporting: {filepath}")
    depsgraph = context.evaluated_depsgraph_get()
    scene = bpy.context.scene

    objs = context.selected_objects or list(bpy.data.objects)
    mesh_objs = [o for o in objs if o.type == 'MESH']

    if not mesh_objs:
        operator.report({'ERROR'}, "No mesh objects found to export")
        return -1

    try:
        f = open(filepath, "wb")
    except Exception as e:
        operator.report({'ERROR'}, f"Cannot open file for writing: {e}")
        return -1

    # --- File header ---
    f.write(struct.pack("<3cB", b'G', b'3', b'D', 4))
    f.write(struct.pack("<HB", len(mesh_objs), 0))

    # --- Export each object ---
    for obj in mesh_objs:
        print(f"Processing object: {obj.name}")

        # Determine animation range
        frame_start = scene.frame_start
        frame_end = scene.frame_end
        current_frame = scene.frame_current

        # Determine if animated
        animated = False
        if getattr(obj, "animation_data", None) and obj.animation_data.action:
            animated = True
        sk = getattr(obj.data, "shape_keys", None)
        if sk and getattr(sk, "animation_data", None) and sk.animation_data.action:
            animated = True
        if any(m.type == 'ARMATURE' for m in obj.modifiers):
            animated = True

        if animated:
            frames = list(range(frame_start, frame_end + 1))
        else:
            frames = [current_frame]
        frameCount = len(frames)

        # --- Gather material info ---
        diffuseColor = (1.0, 1.0, 1.0)
        specularColor = (0.9, 0.9, 0.9)
        opacity = 1.0
        textures_flag = 0
        texnames = []

        if obj.data.materials:
            mat = obj.data.materials[0]
            img = find_image_in_material(mat)
            if img and getattr(img, "filepath", None):
                textures_flag |= 1
                texnames.append(os.path.basename(bpy.path.abspath(img.filepath)))
                diffuseColor = getattr(mat, "diffuse_color", diffuseColor)[:3]
                specularColor = getattr(mat, "specular_color", specularColor)[:3]
                opacity = getattr(mat, "alpha", opacity)

            if mat.use_nodes and mat.node_tree:
                images = [n.image for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE' and getattr(n, "image", None)]
                for im in images[1:3]:
                    texnames.append(os.path.basename(bpy.path.abspath(im.filepath)))
                    textures_flag |= 1 << (len(texnames)-1)

        # --- Base mesh from first frame ---
        scene.frame_set(frames[0])
        bpy.context.view_layer.update()
        eval_obj0 = obj.evaluated_get(depsgraph)
        me0 = eval_obj0.to_mesh()
        me0.calc_loop_triangles()
        uv_layer0 = me0.uv_layers.active.data if me0.uv_layers.active else None

        vmap = {}
        next_index = 0
        base_vertices = []
        base_normals = []
        uvlist = []
        indices = []

        for tri in me0.loop_triangles:
            tri_verts = []
            for li in tri.loops:
                v_idx = me0.loops[li].vertex_index
                uv_u, uv_v = uv_layer0[li].uv if uv_layer0 else (0.0, 0.0)
                vkey = (v_idx, float(uv_u), float(uv_v))
                if vkey not in vmap:
                    vmap[vkey] = next_index
                    next_index += 1
                    co_local = me0.vertices[v_idx].co.copy()
                    no_local = me0.vertices[v_idx].normal.copy()
                    base_vertices.extend([co_local.x, co_local.y, co_local.z])
                    base_normals.extend([no_local.x, no_local.y, no_local.z])
                    uvlist.extend([uv_u, uv_v])
                tri_verts.append(vmap[vkey])
            indices.extend(tri_verts)

        vertexCount = next_index
        indexCount = len(indices)
        eval_obj0.to_mesh_clear()

        # --- Gather vertices/normals across all frames ---
        vertices_all = []
        normals_all = []

        for f_idx, fnum in enumerate(frames):
            scene.frame_set(fnum)
            bpy.context.view_layer.update()
            eval_obj = obj.evaluated_get(depsgraph)
            me = eval_obj.to_mesh()
            mat_world = eval_obj.matrix_world
            mat_world3 = mat_world.to_3x3()

            # vertices
            for vkey, idx in sorted(vmap.items(), key=lambda i: i[1]):
                orig_index = vkey[0]
                v = me.vertices[orig_index].co
                v_world = mat_world @ v
                vertices_all.extend([v_world.x, v_world.y, v_world.z])

            # normals
            for v in me.vertices:
                n = mat_world3 @ v.normal
                normals_all.extend([n.x, n.y, n.z])

            eval_obj.to_mesh_clear()

        # --- Coordinate conversion if needed ---
        if toglest:
            rot_forward_x = Matrix((
                (1, 0, 0, 0),
                (0, 0, 1, 0),
                (0, -1, 0, 0),
                (0, 0, 0, 1)
            ))
            rot3 = rot_forward_x.to_3x3()
            for i in range(0, len(vertices_all), 3):
                v = Vector(vertices_all[i:i+3])
                v = rot3 @ v
                vertices_all[i:i+3] = v
            for i in range(0, len(normals_all), 3):
                n = Vector(normals_all[i:i+3])
                n = (rot3 @ n).normalized()
                normals_all[i:i+3] = n

        # --- Mesh properties ---
        mesh_data = obj.data
        properties = 0
        if getattr(mesh_data, "g3d_customColor", False):
            properties |= 1
            properties |= (255 - getattr(mesh_data, "teamcolor_alpha", 0)) << 24
        if getattr(mesh_data, "g3d_double_sided", False):
            properties |= 2
        if getattr(mesh_data, "g3d_noSelect", False):
            properties |= 4
        if getattr(mesh_data, "g3d_glow", False):
            properties |= 8
        if getattr(mesh_data, "g3d_fullyOpaque", False):
            opacity = 1.0

        # --- Write mesh header ---
        meshname_bytes = bytes(obj.name[:64], "ascii")
        specularPower = 9.999999
        f.write(struct.pack("<64s3I8f2I",
            meshname_bytes,
            frameCount, vertexCount, indexCount,
            *diffuseColor,
            *specularColor,
            specularPower, opacity,
            properties, textures_flag
        ))

        # --- Texture names ---
        for tn in texnames:
            f.write(struct.pack("<64s", bytes(tn[:64], "ascii")))

        # --- Vertex/normals/uvs/indices ---
        f.write(struct.pack("<%if" % (frameCount * vertexCount * 3), *vertices_all))
        f.write(struct.pack("<%if" % (frameCount * vertexCount * 3), *normals_all))
        if textures_flag:
            f.write(struct.pack("<%if" % (vertexCount * 2), *uvlist))
        f.write(struct.pack("<%iI" % indexCount, *indices))

    f.close()
    scene.frame_set(scene.frame_current)
    operator.report({'INFO'}, f"Exported {len(mesh_objs)} mesh(es) to {os.path.basename(filepath)}")
    return 0



def register():
    bpy.types.Mesh.g3d_customColor = BoolProperty(
        name="team color",
        description="replace alpha channel of texture with team color",
        default=False)
    bpy.types.Mesh.g3d_noSelect = BoolProperty(
        name="non-selectable",
        description="click on mesh doesn't select unit",
        default=False)
    bpy.types.Mesh.g3d_fullyOpaque = BoolProperty(
        name="fully opaque",
        description="sets opacity to 1.0, ignoring what's set in materials",
        default=False)
    bpy.types.Mesh.g3d_glow = BoolProperty(
        name="glow",
        description="let objects glow like particles",
        default=False)
    bpy.types.Mesh.teamcolor_alpha = IntProperty(
        name="team color alpha",
        description="set the transparency of the teamcolor part of the texture only",
        default=0, min=0, max=2**8 - 1)
    bpy.types.Mesh.g3d_ignore_lighting = BoolProperty(
        name="ignore lighting",
        description="set a custom lighting normal",
        default=True)
    bpy.types.Mesh.g3d_ignore_lighting_normal = FloatVectorProperty(
        name="Uniform Normal",
        description="Vector used for exporting normals when ignoring scene lighting",
        default=(0.0, -1.0, -4.0),
        size=3,
        precision=1
    )
    bpy.types.Mesh.g3d_double_sided = BoolProperty(
        name="double sided",
        description="Render mesh as double sided",
        default=True
    )

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    for p in ("g3d_customColor", "g3d_noSelect", "g3d_fullyOpaque", "g3d_glow", "teamcolor_alpha"):
        if hasattr(bpy.types.Mesh, p):
            try:
                delattr(bpy.types.Mesh, p)
            except Exception:
                pass


if __name__ == "__main__":
    register()
