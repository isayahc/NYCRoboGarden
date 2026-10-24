"""Export compiled MuJoCo geometry once and lightweight world poses thereafter."""
from __future__ import annotations

import struct
from hashlib import sha256

import mujoco
import numpy as np
import fast_simplification


def quaternion(matrix):
    """Convert MuJoCo's rotation matrix to Three.js xyzw quaternion order."""
    q = np.empty(4)
    mujoco.mju_mat2Quat(q, matrix)
    return [float(q[1]), float(q[2]), float(q[3]), float(q[0])]


class BrowserScene:
    def __init__(self, model, data):
        self.model = model
        self.dynamic = []
        self.meshes = {}
        geometries = []
        types = {int(getattr(mujoco.mjtGeom, 'mjGEOM_'+name.upper())): name
                 for name in ('plane', 'sphere', 'capsule', 'ellipsoid', 'cylinder', 'box', 'mesh')}
        for i in range(model.ngeom):
            kind = types.get(int(model.geom_type[i]))
            if kind is None:
                raise ValueError(f'Unsupported browser geometry: {model.geom_type[i]}')
            body = int(model.geom_bodyid[i])
            dynamic = False
            while body:
                if model.body_dofnum[body] or model.body_mocapid[body] >= 0:
                    dynamic = True
                    break
                body = int(model.body_parentid[body])
            if dynamic:
                self.dynamic.append(i)
            mesh_id = int(model.geom_dataid[i]) if kind == 'mesh' else None
            geometries.append(dict(id=i, kind=kind, mesh=mesh_id, dynamic=dynamic,
                                   size=model.geom_size[i].tolist(), rgba=model.geom_rgba[i].tolist(),
                                   position=data.geom_xpos[i].tolist(), quaternion=quaternion(data.geom_xmat[i])))
            if mesh_id is not None and mesh_id not in self.meshes:
                va, vn = int(model.mesh_vertadr[mesh_id]), int(model.mesh_vertnum[mesh_id])
                fa, fn = int(model.mesh_faceadr[mesh_id]), int(model.mesh_facenum[mesh_id])
                # Faces are mesh-local indices; MuJoCo has already applied STL scaling
                # and principal-axis transforms to vertices and geom poses.
                vertices = np.asarray(model.mesh_vert[va:va+vn], dtype='<f4')
                faces = np.asarray(model.mesh_face[fa:fa+fn], dtype='<u4')
                if faces.size and int(faces.max()) >= vn:
                    raise ValueError('Mesh face index outside vertex buffer')
                # Simplify visualization copies only; physics/IK keep the full model.
                target = min(4000, max(800, int(fn * .12)))
                while fn > target:
                    reduced_vertices, reduced_faces = fast_simplification.simplify(vertices, faces, target_count=target)
                    bounds_error = max(np.abs(reduced_vertices.min(0)-vertices.min(0)).max(),
                                       np.abs(reduced_vertices.max(0)-vertices.max(0)).max())
                    if bounds_error <= .01:
                        vertices = np.asarray(reduced_vertices, dtype='<f4')
                        faces = np.asarray(reduced_faces, dtype='<u4')
                        vn, fn = len(vertices), len(faces)
                        break
                    target *= 2
                self.meshes[mesh_id] = struct.pack('<II', vn, fn) + vertices.tobytes() + faces.tobytes()
        self.document = dict(version=1, up='Z', geometries=geometries,
                             meshes={str(i): f'/assets/mesh/{i}.bin?v={sha256(blob).hexdigest()[:12]}' for i, blob in self.meshes.items()})
        self.mount = model.body('arm_mount').id
        self.tool = model.site('arm_tcp').id

    def poses(self, data):
        return [[i, *data.geom_xpos[i].tolist(), *quaternion(data.geom_xmat[i])] for i in self.dynamic]

    def focus(self, data):
        return ((data.xpos[self.mount] + data.site_xpos[self.tool]) / 2).tolist()
