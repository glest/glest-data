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
from bpy.props import StringProperty, BoolProperty, IntProperty
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
        # Clear default nodes
        for n in nodes:
            nodes.remove(n)

        output_node = nodes.new(type="ShaderNodeOutputMaterial")
        output_node.location = (400, 0)

        bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
        bsdf.location = (0, 0)
        links.new(bsdf.outputs['BSDF'], output_node.inputs['Surface'])
        
        def resolve_texture_path(base_path, tex_name):
            """Return PNG path if it exists, otherwise fallback to original."""
            tex_dir = os.path.dirname(base_path)
            tex_name_noext, ext = os.path.splitext(tex_name)
            png_path = os.path.join(tex_dir, tex_name_noext + ".png")
            original_path = os.path.join(tex_dir, tex_name)
            return png_path if os.path.exists(png_path) else original_path

        # Diffuse texture
        if header.diffusetexture:
            tex_diff = nodes.new(type="ShaderNodeTexImage")
            tex_diff.location = (-400, 200)
            tex_path = resolve_texture_path(filename, header.diffusetexture)
            try:
                tex_diff.image = bpy.data.images.load(tex_path)
            except:
                print(f"Warning: Diffuse texture not found: {tex_path}")
            links.new(tex_diff.outputs['Color'], bsdf.inputs['Base Color'])

        # Specular texture
        if header.speculartexture:
            tex_spec = nodes.new(type="ShaderNodeTexImage")
            tex_spec.location = (-400, 0)
            tex_path = resolve_texture_path(filename, header.speculartexture)
            try:
                tex_spec.image = bpy.data.images.load(tex_path)
            except:
                print(f"Warning: Specular texture not found: {tex_path}")
            # Connect to Specular input
            links.new(tex_spec.outputs['Color'], bsdf.inputs['Specular'])

        # Normal map
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


def G3DSaver(filepath, context, toglest, operator):
    print(f"\nExporting: {filepath}")
    depsgraph = context.evaluated_depsgraph_get()

    objs = context.selected_objects
    if len(objs) == 0:
        objs = list(bpy.data.objects)
    mesh_objs = [o for o in objs if o.type == 'MESH']
    if not mesh_objs:
        operator.report({'ERROR'}, "No mesh objects found to export")
        return -1

    try:
        f = open(filepath, "wb")
    except Exception as e:
        operator.report({'ERROR'}, f"Unable to open file for writing: {e}")
        return -1

    f.write(struct.pack("<3cB", b'G', b'3', b'D', 4))
    f.write(struct.pack("<HB", len(mesh_objs), 0))

    for obj in mesh_objs:
        eval_obj = obj.evaluated_get(depsgraph)
        me = eval_obj.to_mesh()
        frameCount = 1
        shapekeys = getattr(me, "shape_keys", None)
        if shapekeys and len(shapekeys.key_blocks) > 1:
            frameCount = len(shapekeys.key_blocks)
            
        base_count = len(me.vertices)
        for key in shapekeys.key_blocks:
            if len(key.data) != base_count:
                operator.report({'ERROR'}, f"Shape key '{key.name}' has mismatched vertex count")
                return -1

        me.calc_loop_triangles()

        diffuseColor = (1.0, 1.0, 1.0)
        specularColor = (0.9, 0.9, 0.9)
        opacity = 1.0
        textures_flag = 0
        texnames = []

        if obj.data.materials:
            mat = obj.data.materials[0]
            img = find_image_in_material(mat)
            if img and hasattr(img, "filepath"):
                textures_flag |= 1
                texnames.append(os.path.basename(bpy.path.abspath(img.filepath)))
                diffuseColor = mat.diffuse_color[:3] if hasattr(mat, "diffuse_color") else diffuseColor
                specularColor = mat.specular_color[:3] if hasattr(mat, "specular_color") else specularColor
                opacity = mat.alpha if hasattr(mat, "alpha") else opacity

                if mat.use_nodes and mat.node_tree:
                    images = []
                    for node in mat.node_tree.nodes:
                        if node.type == 'TEX_IMAGE' and getattr(node, "image", None):
                            images.append(node.image)
                    for im in images[1:3]:
                        texnames.append(os.path.basename(bpy.path.abspath(im.filepath)))
                        textures_flag |= 1 << (len(texnames)-1)
                        
        uv_layer = me.uv_layers.active.data if me.uv_layers.active else None
        
        vmap = {}
        uvlist = []
        indices = []

        next_index = 0
        vertices_all = []
        normals_all = []

        if frameCount == 1:
            for v in me.vertices:
                vertices_all.extend(v.co)
                normals_all.extend(v.normal)
        else:
            keys = [k for k in shapekeys.key_blocks if k.name != "Basis"]
            frameCount = len(keys)
            
            for key in keys:
                for v in key.data:
                    vertices_all.extend(v.co)
                for v in me.vertices:
                    normals_all.extend(v.normal)
                    
        for tri in me.loop_triangles:
            tri_verts = []
            for li in tri.loops:
                v_idx = me.loops[li].vertex_index
                uv_u, uv_v = uv_layer[li].uv if uv_layer else (0.0, 0.0)
                vkey = (v_idx, float(uv_u), float(uv_v))
                if vkey in vmap:
                    new_idx = vmap[vkey]
                else:
                    co = obj.matrix_world @ me.vertices[v_idx].co
                    no = obj.matrix_world.to_3x3() @ me.vertices[v_idx].normal
                    vertices_all.extend([co.x, co.y, co.z])
                    normals_all.extend([no.x, no.y, no.z])
                    uvlist.extend([uv_u, uv_v])
                    new_idx = next_index
                    vmap[vkey] = new_idx
                    next_index += 1
                tri_verts.append(new_idx)
            indices.extend(tri_verts)

        indexCount = len(indices)
        vertexCount = next_index

        properties = 0
        mat_data = obj.data
        if hasattr(mat_data, "g3d_customColor") and mat_data.g3d_customColor:
            properties |= 1
        if hasattr(mat_data, "show_double_sided") and mat_data.show_double_sided:
            properties |= 2
        if hasattr(mat_data, "g3d_noSelect") and mat_data.g3d_noSelect:
            properties |= 4
        if hasattr(mat_data, "g3d_glow") and mat_data.g3d_glow:
            properties |= 8
            
        team_alpha = getattr(mat_data, "teamcolor_alpha", 0)
        properties |= (255 - int(team_alpha)) << 24

        textures = textures_flag

        meshname_bytes = bytes(obj.name[:64], "ascii")

        f.write(struct.pack("<64s3I8f2I",
            meshname_bytes,
            frameCount, vertexCount, indexCount,
            float(diffuseColor[0]), float(diffuseColor[1]), float(diffuseColor[2]),
            float(specularColor[0]), float(specularColor[1]), float(specularColor[2]),
            float(9.999999), float(opacity),
            int(properties), int(textures)
        ))

        if textures:
            for tn in texnames:
                f.write(struct.pack("<64s", bytes(tn[:64], "ascii")))

        vertex_format = "<%if" % int(frameCount * vertexCount * 3)
        normals_format = "<%if" % int(frameCount * vertexCount * 3)
        texturecoords_format = "<%if" % int(vertexCount * 2)
        indices_format = "<%iI" % int(indexCount)

        if vertexCount > 0:
            f.write(struct.pack(vertex_format, *vertices_all))
            f.write(struct.pack(normals_format, *normals_all))
            if textures:
                f.write(struct.pack(texturecoords_format, *uvlist))
            f.write(struct.pack(indices_format, *indices))

        eval_obj.to_mesh_clear()
    f.close()
    operator.report({'INFO'}, f"Exported {len(mesh_objs)} mesh(es) to {os.path.basename(filepath)}")
    return 0

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
        self.layout.prop(context.object.data, "show_double_sided", text="double sided")
        self.layout.prop(context.object.data, "g3d_noSelect")
        self.layout.prop(context.object.data, "g3d_fullyOpaque")
        self.layout.prop(context.object.data, "g3d_glow")
        
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

    objs = context.selected_objects
    if not objs:
        objs = list(bpy.data.objects)

    mesh_objs = [o for o in objs if o.type == 'MESH']
    if not mesh_objs:
        operator.report({'ERROR'}, "No mesh objects found to export")
        return -1

    try:
        f = open(filepath, "wb")
    except Exception as e:
        operator.report({'ERROR'}, f"Cannot open file for writing: {e}")
        return -1

    f.write(struct.pack("<3cB", b'G', b'3', b'D', 4))
    f.write(struct.pack("<HB", len(mesh_objs), 0))

    def find_image_in_material(mat):
        if mat is None:
            return None
        if mat.use_nodes and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and getattr(node, "image", None):
                    return node.image
        return None

    for obj in mesh_objs:
        eval_obj = obj.evaluated_get(depsgraph)
        me = eval_obj.to_mesh()
        me.calc_loop_triangles()
        uv_layer = me.uv_layers.active.data if me.uv_layers.active else None

        shapekeys = getattr(me, "shape_keys", None)
        if shapekeys and len(shapekeys.key_blocks) > 1:
            keys = list(shapekeys.key_blocks)
            if keys[0].name != "Basis":
                keys.sort(key=lambda k: 0 if k.name == "Basis" else 1)
            frameCount = len(keys)
        else:
            keys = [None]
            frameCount = 1

        diffuseColor = (1.0, 1.0, 1.0)
        specularColor = (0.9, 0.9, 0.9)
        opacity = 1.0
        textures_flag = 0
        texnames = []

        if obj.data.materials:
            mat = obj.data.materials[0]
            img = find_image_in_material(mat)
            if img and getattr(img, "filepath", None):
                textures_flag |= 1  # diffuse
                texnames.append(os.path.basename(bpy.path.abspath(img.filepath)))
                diffuseColor = mat.diffuse_color[:3] if hasattr(mat, "diffuse_color") else diffuseColor
                specularColor = mat.specular_color[:3] if hasattr(mat, "specular_color") else specularColor
                opacity = mat.alpha if hasattr(mat, "alpha") else opacity

            if mat.use_nodes and mat.node_tree:
                images = [n.image for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE' and getattr(n, "image", None)]
                for im in images[1:3]:
                    texnames.append(os.path.basename(bpy.path.abspath(im.filepath)))
                    textures_flag |= 1 << (len(texnames)-1)

        vmap = {}
        base_vertices = []
        base_normals = []
        uvlist = []
        indices = []
        next_index = 0

        for tri in me.loop_triangles:
            tri_verts = []
            for li in tri.loops:
                v_idx = me.loops[li].vertex_index
                uv_u, uv_v = uv_layer[li].uv if uv_layer else (0.0, 0.0)
                vkey = (v_idx, float(uv_u), float(uv_v))
                if vkey not in vmap:
                    vmap[vkey] = next_index
                    next_index += 1
                    co = me.vertices[v_idx].co
                    no = me.vertices[v_idx].normal
                    base_vertices.extend([co.x, co.y, co.z])
                    base_normals.extend([no.x, no.y, no.z])
                    uvlist.extend([uv_u, uv_v])
                tri_verts.append(vmap[vkey])
            indices.extend(tri_verts)

        vertexCount = next_index
        indexCount = len(indices)
        specularPower = 9.999999
        properties = 0

        vertices_all = []
        normals_all = []

        if frameCount == 1:
            vertices_all = base_vertices[:]
            normals_all = base_normals[:]
        else:
            for key in keys:
                for vkey, idx in vmap.items():
                    orig_index = vkey[0]
                    co = obj.matrix_world @ key.data[orig_index].co
                    vertices_all.extend([co.x, co.y, co.z])
                normals_all.extend(base_normals)

        rot_forward_x = Matrix((
            (1,  0,  0, 0),
            (0,  0,  1, 0),
            (0, -1,  0, 0),
            (0,  0,  0, 1)
        ))

        rot = rot_forward_x

        rot3 = rot.to_3x3()

        for i in range(0, len(vertices_all), 3):
            v = Vector(vertices_all[i:i+3])
            v_rot = rot3 @ v
            vertices_all[i:i+3] = v_rot

        for i in range(0, len(normals_all), 3):
            n = Vector(normals_all[i:i+3])
            n_rot = rot3 @ n
            normals_all[i:i+3] = n_rot.normalized()

                
        mesh_data = obj.data
        if getattr(mesh_data, "g3d_customColor", False):
            properties |= 1
            properties |= (255 - getattr(mesh_data, "teamcolor_alpha", 0)) << 24
        if getattr(mesh_data, "show_double_sided", False):
            properties |= 2
        if getattr(mesh_data, "g3d_noSelect", False):
            properties |= 4
        if getattr(mesh_data, "g3d_glow", False):
            properties |= 8
        if getattr(mesh_data, "g3d_fullyOpaque", False):
            opacity = 1.0

        meshname_bytes = bytes(obj.name[:64], "ascii")
        f.write(struct.pack("<64s3I8f2I",
            meshname_bytes,
            frameCount, vertexCount, indexCount,
            *diffuseColor,
            *specularColor,
            specularPower, opacity,
            properties, textures_flag
        ))

        for tn in texnames:
            f.write(struct.pack("<64s", bytes(tn[:64], "ascii")))

        f.write(struct.pack("<%if" % (frameCount*vertexCount*3), *vertices_all))
        f.write(struct.pack("<%if" % (frameCount*vertexCount*3), *normals_all))
        if textures_flag:
            f.write(struct.pack("<%if" % (vertexCount*2), *uvlist))
        f.write(struct.pack("<%iI" % indexCount, *indices))

        eval_obj.to_mesh_clear()

    f.close()
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
