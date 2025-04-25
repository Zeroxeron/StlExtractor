import json
from collections import defaultdict

import numpy
import numpy as np
import stl
from stl import mesh

ANGLE_THRESHOLD = 1e-2  # Cosine similarity tolerance for coplanarity
pairs = []


import json
import numpy as np
from stl import mesh
from collections import defaultdict

ANGLE_THRESHOLD = 1e-2  # max angle diff for coplanar triangles

def parse_stl(stl_file):
    mesh_data = mesh.Mesh.from_file(stl_file)
    triangles = mesh_data.vectors
    normals = mesh_data.normals

    # Unique vertex index mapping
    vertex_map = {}
    vertices = []

    def get_vertex_idx(v):
        key = tuple(np.round(v, 6))
        if key not in vertex_map:
            vertex_map[key] = len(vertices)
            vertices.append(key)
        return vertex_map[key]

    # Build triangle index list
    tri_data = []
    for tri, normal in zip(triangles, normals):
        indices = [get_vertex_idx(v) for v in tri]
        tri_data.append({
            'indices': indices,
            'normal': normal / np.linalg.norm(normal)
        })

    # Build edge -> triangle map
    edge_to_tris = defaultdict(list)
    for i, tri in enumerate(tri_data):
        inds = tri['indices']
        for a, b in [(0,1), (1,2), (2,0)]:
            edge = tuple(sorted((inds[a], inds[b])))
            edge_to_tris[edge].append(i)

    # Build adjacency graph
    neighbors = defaultdict(set)
    for edge, tris in edge_to_tris.items():
        if len(tris) == 2:
            i, j = tris
            n1 = tri_data[i]['normal']
            n2 = tri_data[j]['normal']
            if np.dot(n1, n2) > 1 - ANGLE_THRESHOLD:
                neighbors[i].add(j)
                neighbors[j].add(i)

    # Group triangles into surfaces using DFS
    visited = set()
    surface_groups = []

    def dfs(tri_id, group):
        visited.add(tri_id)
        group.append(tri_id)
        for n in neighbors[tri_id]:
            if n not in visited:
                dfs(n, group)

    for i in range(len(tri_data)):
        if i not in visited:
            group = []
            dfs(i, group)
            surface_groups.append(group)

    all_boundary_edges = set() # Collect all boundary edges from all surfaces

    for group in surface_groups:
        edge_count = defaultdict(int)
        for tri_id in group:
            inds = tri_data[tri_id]['indices']
            for a, b in [(0,1), (1,2), (2,0)]:
                edge = tuple(sorted((inds[a], inds[b])))
                edge_count[edge] += 1
        # Only keep edges used once (on the boundary of the group)
        for edge, count in edge_count.items():
            if count == 1:
                all_boundary_edges.add(edge)

    # Output result
    result = {
        'vertices': [list(map(float, v)) for v in vertices],
        'lines': sorted(list(all_boundary_edges))
    }

    return result

# Optional save to file
def save_to_json(data, output_file):
    with open(output_file, "w", encoding='utf-8') as f:
        json.dump(data, f)#, indent=2)

if __name__ == '__main__':
    data = parse_stl("test.stl")
    save_to_json(data, "out.json")