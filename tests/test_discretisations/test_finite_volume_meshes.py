#
# Test for the Finite Volume Mesh class
#
import pybamm

import numpy as np
import unittest


class TestFiniteVolumeMesh(unittest.TestCase):
    def test_mesh_creation(self):
        param = pybamm.Parameters()
        mesh = pybamm.FiniteVolumeMacroMesh(param, 50)
        self.assertEqual(mesh["whole cell"].edges[-1], 1)
        self.assertEqual(
            len(mesh["whole cell"].edges), len(mesh["whole cell"].nodes) + 1
        )
        self.assertAlmostEqual(
            np.linalg.norm(
                mesh["whole cell"].nodes
                - np.concatenate(
                    [
                        mesh["negative electrode"].nodes,
                        mesh["separator"].nodes,
                        mesh["positive electrode"].nodes,
                    ]
                )
            ),
            0,
        )

    def test_mesh_sizes(self):
        param = pybamm.Parameters()
        mesh = pybamm.FiniteVolumeMacroMesh(param, 50)
        self.assertEqual(
            mesh.neg_mesh_points + (mesh.sep_mesh_points - 2) + mesh.pos_mesh_points,
            mesh.total_mesh_points,
        )
        self.assertEqual(mesh["negative electrode"].npts, mesh.neg_mesh_points - 1)
        self.assertEqual(mesh["separator"].npts, mesh.sep_mesh_points - 1)
        self.assertEqual(mesh["positive electrode"].npts, mesh.pos_mesh_points - 1)
        self.assertEqual(mesh["whole cell"].npts, mesh.total_mesh_points - 1)

        self.assertEqual(len(mesh["negative electrode"].edges), mesh.neg_mesh_points)
        self.assertEqual(len(mesh["separator"].edges), mesh.sep_mesh_points)
        self.assertEqual(len(mesh["positive electrode"].edges), mesh.pos_mesh_points)
        self.assertEqual(len(mesh["whole cell"].edges), mesh.total_mesh_points)


if __name__ == "__main__":
    print("Add -v for more debug output")
    import sys

    if "-v" in sys.argv:
        debug = True
    unittest.main()