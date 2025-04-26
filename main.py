import sys
import time
from functools import wraps
from pathlib import Path
import json
import numpy as np
from stl import mesh
from collections import defaultdict

ANGLE_THRESHOLD = 1e-2  # Cosine similarity tolerance for coplanar check
pairs = []

def timing(func):
    @wraps(func)
    def wrap(*args, **kw):
        ts = time.time()
        result = func(*args, **kw)
        te = time.time()
        print('\n>>  Finished %r took: %2.4f sec' % (func.__name__, te - ts))
        return result
    return wrap

class Converted:
    # Unique vertex index mapping
    file = None
    file_dir = ""
    vertex_map = {}
    vertices = []
    neighbors = defaultdict(set)
    # Group triangles into surfaces using DFS
    visited = set()
    surface_groups = []
    result = {}
    triangles = None
    normals = None

    def __str__(self):
        return f"---[Convertable]---\nFile: {self.file}\nDir: {self.file_dir}\nVertx: {len(self.vertices)}\nResult: {len(self.result['vertices'])}/{len(self.result['lines'])}\n------"

    def __init__(self, abspath : str):
        if Path.exists(Path(abspath)):
            file = Path(abspath)
            self.fname = file.name.replace('.stl', '')
            self.file = file
            self.file_dir = file.parent
            mesh_data = mesh.Mesh.from_file(str(file.absolute()))
            self.triangles = mesh_data.vectors
            self.normals = mesh_data.normals
            self.result = {}
        else:
            print(f'<!> Model file cant be imported.')
            print(f'<!> - Path: {abspath}')
        return

    @timing
    def convert(self):
        # Build triangle index list
        tri_data = []
        for tri, normal in zip(self.triangles, self.normals):
            indices = [self.get_vertex_idx(v) for v in tri]
            tri_data.append({
                'indices': indices,
                'normal': normal / np.linalg.norm(normal)
            })

        # Build edge -> triangle map
        edge_to_tris = defaultdict(list)
        for i, tri in enumerate(tri_data):
            v_ids = tri['indices']
            for a, b in [(0, 1), (1, 2), (2, 0)]:
                edge = tuple(sorted((v_ids[a], v_ids[b])))
                edge_to_tris[edge].append(i)

        # Build adjacency graph

        for edge, tris in edge_to_tris.items():
            if len(tris) == 2:
                i, j = tris
                n1 = tri_data[i]['normal']
                n2 = tri_data[j]['normal']
                if np.dot(n1, n2) > 1 - ANGLE_THRESHOLD:
                    self.neighbors[i].add(j)
                    self.neighbors[j].add(i)

        # Group triangles into surfaces using DFS
        surface_groups = []
        for i in range(len(tri_data)):
            if i not in self.visited:
                group = []
                self.dfs(i, group)
                surface_groups.append(group)

        all_boundary_edges = set()  # Collect all boundary edges from all surfaces

        for group in surface_groups:
            edge_count = defaultdict(int)
            for tri_id in group:
                v_ids = tri_data[tri_id]['indices']
                for a, b in [(0, 1), (1, 2), (2, 0)]:
                    edge = tuple(sorted((v_ids[a], v_ids[b])))
                    edge_count[edge] += 1
            # Only keep edges used once (on the boundary of the group)
            for edge, count in edge_count.items():
                if count == 1:
                    all_boundary_edges.add(edge)

        # Output result
        self.result = {
            'vertices': [list(map(float, v)) for v in self.vertices],
            'lines': sorted(list(all_boundary_edges))
        }
        return self.result

    def get_vertex_idx(self, v):
        key = tuple(np.round(v, 6))
        if key not in self.vertex_map:
            self.vertex_map[key] = len(self.vertices)
            self.vertices.append(key)
        return self.vertex_map[key]

    def dfs(self, tr_id, listed):
        self.visited.add(tr_id)
        listed.append(tr_id)
        for n in self.neighbors[tr_id]:
            if n not in self.visited:
                self.dfs(n, listed)

    # noinspection PyTypeChecker
    def export(self):
        """
        Exports the data into .json file
        If not the "models" folder (i.e.: sys.args) - saves output near the model file
        """
        print(self)
        output_file = f'{self.file.parent}\\{self.fname}.json'
        if Path(self.file_dir).name == "models":
            export_path = str(self.file.parent.parent) + "\\exports"
            output_file = f'{export_path}\\{self.fname}.json'
            Path(export_path).mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w+', encoding='utf-8') as out_f:
            json.dump(self.result, out_f)

if __name__ == '__main__':
    convertables = [str(m.absolute()) for m in Path('models').rglob('*.stl')]
    if len(sys.argv) > 1:
        convertables = sys.argv
        convertables.pop(0)
        print(f'args: {sys.argv}')
    print(f'convertables: {convertables}')
    outputs = [m.absolute().replace('.json','') for m in Path('exports').rglob('*.json')]
    for stl_file in convertables:
        fp = Path(stl_file)
        fname = fp.name.replace('.stl','')
        if fname in outputs: continue
        print(f'{fname} - converting...')
        cnvrt = Converted(stl_file)
        data = cnvrt.convert()
        cnvrt.export()
    print('Finished.')