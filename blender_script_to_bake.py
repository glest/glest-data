import bpy

obj = bpy.context.active_object
scene = bpy.context.scene

if obj.type != 'MESH':
    raise Exception("Select a mesh object with an armature modifier")

armature_mod = next((m for m in obj.modifiers if m.type == 'ARMATURE'), None)
if not armature_mod:
    raise Exception("No Armature modifier found on object")

# Duplicate object to preserve original
dup = obj.copy()
dup.data = obj.data.copy()
bpy.context.collection.objects.link(dup)
dup.name = obj.name + "_Baked"

# Ensure no modifiers (baked mesh must not have Armature modifiers)
for m in dup.modifiers:
    dup.modifiers.remove(m)

# Remove any shape keys that might exist
dup.shape_key_clear()

depsgraph = bpy.context.evaluated_depsgraph_get()
frame_start = scene.frame_start
frame_end = scene.frame_end
current_frame = scene.frame_current

print(f"Baking frames {frame_start} to {frame_end-1} for {dup.name} (no Basis, loop ready)...")

for f in range(frame_start, frame_end):  # omit last frame for seamless loop
    scene.frame_set(f)
    bpy.context.view_layer.update()
    key_name = f"Frame_{f}"
    sk = dup.shape_key_add(name=key_name)

    eval_obj = obj.evaluated_get(depsgraph)
    mesh_eval = eval_obj.to_mesh()
    
    if len(mesh_eval.vertices) != len(dup.data.vertices):
        eval_obj.to_mesh_clear()
        raise Exception("Vertex count changed! Animation baking aborted.")
    
    for i, v in enumerate(mesh_eval.vertices):
        sk.data[i].co = v.co
    
    eval_obj.to_mesh_clear()

scene.frame_set(current_frame)

# Confirm no "Basis" exists
if dup.data.shape_keys and "Basis" in dup.data.shape_keys.key_blocks:
    dup.active_shape_key_index = 0
    bpy.ops.object.shape_key_remove(all=False)