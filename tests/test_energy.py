import unittest
from kcee.energy import strain_energy_density

class EnergyTests(unittest.TestCase):
    def test_known_uniaxial_hydrostatic_and_shear_cases(self):
        self.assertAlmostEqual(strain_energy_density([10,0,0,0,0,0],100,.3),.5)
        self.assertAlmostEqual(strain_energy_density([10,10,10,0,0,0],100,.3),.6)
        self.assertAlmostEqual(strain_energy_density([0,0,0,10,0,0],100,.3),1.3)
    def test_invalid_material_and_tensor(self):
        for E,nu in ((0,.3),(100,.5),(100,-1),(float('nan'),.3)):
            with self.assertRaises(ValueError):strain_energy_density([0]*6,E,nu)
        with self.assertRaises(ValueError):strain_energy_density([float('nan')]*6,100,.3)
