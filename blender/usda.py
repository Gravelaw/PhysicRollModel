"""Minimal static USD ASCII mesh export for Blender builds without USD support.

World-space evaluated meshes, PreviewSurface materials, Z-up metres, no textures.
No animation, rigging, instancing, physics schema or lossless Blender round trip.
"""
import json
import re


def identifier(name):
    return re.sub(r'[^A-Za-z0-9_]', '_', name)


def export_meshes(filepath, objects, depsgraph):
    lines = ['#usda 1.0', '(', '    defaultPrim = "Mill"', '    metersPerUnit = 1',
             '    upAxis = "Z"', ')', 'def Xform "Mill" {',
             '    custom string model_status = "GENERIC_SYNTHETIC_UNCALIBRATED"',
             '    custom string coordinate_convention = "X rolling, Y width, Z up"',
             '    def Scope "Materials" {']
    materials = {o.active_material.name: o.active_material for o in objects if o.active_material}
    for name, m in sorted(materials.items()):
        bsdf = m.node_tree.nodes.get('Principled BSDF')
        color = tuple(bsdf.inputs['Base Color'].default_value[:3])
        metal = bsdf.inputs['Metallic'].default_value
        rough = bsdf.inputs['Roughness'].default_value
        key = identifier(name)
        lines.extend([f'        def Material "{key}" {{',
            f'            token outputs:surface.connect = </Mill/Materials/{key}/Shader.outputs:surface>',
            '            def Shader "Shader" {', '                uniform token info:id = "UsdPreviewSurface"',
            f'                color3f inputs:diffuseColor = {color}',
            f'                float inputs:metallic = {metal}', f'                float inputs:roughness = {rough}',
            '                token outputs:surface', '            }', '        }'])
    lines.append('    }')
    for obj in sorted(objects, key=lambda o: o.name):
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        points = [tuple(evaluated.matrix_world @ v.co) for v in mesh.vertices]
        counts = [len(p.vertices) for p in mesh.polygons]
        indices = [i for p in mesh.polygons for i in p.vertices]
        lines.extend([f'    def Mesh "{identifier(obj.name)}" (',
            '        prepend apiSchemas = ["MaterialBindingAPI"]', '    ) {',
            f'        custom string equipment_id = {json.dumps(obj["equipment_id"])}',
            '        custom bool synthetic_geometry = true',
            *([f'        custom string sensor_id = {json.dumps(obj["sensor_id"])}'] if 'sensor_id' in obj else []),
            '        uniform token subdivisionScheme = "none"',
            '        bool doubleSided = false',
            f'        point3f[] points = {points}', f'        int[] faceVertexCounts = {counts}',
            f'        int[] faceVertexIndices = {indices}',
            f'        rel material:binding = </Mill/Materials/{identifier(obj.active_material.name)}>',
            '    }'])
        evaluated.to_mesh_clear()
    lines.append('}')
    filepath.write_text('\n'.join(lines)+'\n')
