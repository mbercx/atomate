# coding: utf-8

from __future__ import division, print_function, unicode_literals, \
    absolute_import

import os
import unittest

from fireworks.utilities.fw_serializers import load_object
from matmethods.vasp.firetasks.write_inputs import WriteVaspFromIOSet, \
    WriteVaspFromPMGObjects, ModifyIncar, WriteVaspStaticFromPrev
from matmethods.vasp.input_sets import StructureOptimizationVaspInputSet, StaticVaspInputSet
from pymatgen import IStructure, Lattice
from pymatgen.io.vasp import Incar, Poscar, Potcar, Kpoints

__author__ = 'Anubhav Jain, Kiran Mathew'
__email__ = 'ajain@lbl.gov, kmathew@lbl.gov'

module_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))

# TODO: for "preserve_incar", the most important test is to retain LDA+U and MAGMOM orderings even when the cell changes setting

class TestWriteVasp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.environ.get("VASP_PSP_DIR"):
            raise unittest.SkipTest(
                'This system is not set up to run VASP jobs. '
                'Please set your VASP_PSP_DIR environment variable.')

        coords = [[0, 0, 0], [0.75, 0.5, 0.75]]
        lattice = Lattice([[3.8401979337, 0.00, 0.00],
                           [1.9200989668, 3.3257101909, 0.00],
                           [0.00, -2.2171384943, 3.1355090603]])
        cls.struct_si = IStructure(lattice, ["Si"] * 2, coords)

        cls.ref_incar = Incar.from_file(
            os.path.join(module_dir, "reference_files", "setup_test", "INCAR"))
        cls.ref_poscar = Poscar.from_file(
            os.path.join(module_dir, "reference_files", "setup_test",
                         "POSCAR"))
        cls.ref_potcar = Potcar.from_file(
            os.path.join(module_dir, "reference_files", "setup_test",
                         "POTCAR"))
        cls.ref_kpoints = Kpoints.from_file(
            os.path.join(module_dir, "reference_files", "setup_test",
                         "KPOINTS"))
        cls.ref_incar_preserve = Incar.from_file(os.path.join(module_dir,
                                                              "reference_files",
                                                              "Si_structure_optimization_plain",
                                                              "outputs",
                                                              "INCAR"))
        cls.ref_incar_preserve.update(StaticVaspInputSet.STATIC_SETTINGS)

    def setUp(self):
        os.chdir(module_dir)

    def tearDown(self):
        for x in ["INCAR", "POSCAR", "POTCAR", "KPOINTS"]:
            if os.path.exists(os.path.join(module_dir, x)):
                os.remove(os.path.join(module_dir, x))

    def _verify_files(self, skip_kpoints=False, preserve_incar=False):
        if not preserve_incar:
            self.assertEqual(
                Incar.from_file(os.path.join(module_dir, "INCAR")),
                self.ref_incar)
            self.assertEqual(
                str(Poscar.from_file(os.path.join(module_dir, "POSCAR"))),
                str(self.ref_poscar))
            self.assertEqual((Potcar.from_file(os.path.join(module_dir,
                                                            "POTCAR"))).symbols,
                             self.ref_potcar.symbols)
            if not skip_kpoints:
                self.assertEqual(
                    str(Kpoints.from_file(
                        os.path.join(module_dir, "KPOINTS"))),
                    str(self.ref_kpoints))
        else:
            #self.ref_incar_preserve.update({"KPOINT_BSE":"-1", "LVTOT": True})
            self.assertEqual(
                Incar.from_file(os.path.join(module_dir, "INCAR")),
                self.ref_incar_preserve)

    def test_ioset_explicit(self):
        ft = WriteVaspFromIOSet(dict(structure=self.struct_si,
                                     vasp_input_set=StructureOptimizationVaspInputSet()))
        ft = load_object(ft.to_dict())  # simulate database insertion
        ft.run_task({})
        self._verify_files()

    def test_ioset_implicit(self):
        ft = WriteVaspFromIOSet(
            dict(structure=self.struct_si, vasp_input_set="MPVaspInputSet"))
        ft = load_object(ft.to_dict())  # simulate database insertion
        ft.run_task({})
        self._verify_files(skip_kpoints=True)

    def test_ioset_params(self):
        ft = WriteVaspFromIOSet(
            dict(structure=self.struct_si, vasp_input_set="MPVaspInputSet",
                 vasp_input_params={"user_incar_settings": {"ISMEAR": 1000}}))
        ft = load_object(ft.to_dict())  # simulate database insertion
        ft.run_task({})
        incar = Incar.from_file(os.path.join(module_dir, "INCAR"))
        self.assertEqual(incar["ISMEAR"], 1000)  # make sure override works
        incar['ISMEAR'] = -5  # switch back to default
        incar.write_file("INCAR")
        self._verify_files(skip_kpoints=True)

    def test_pmgobjects(self):
        mpvis = StructureOptimizationVaspInputSet()
        ft = WriteVaspFromPMGObjects({"incar": mpvis.get_incar(self.struct_si),
                                      "poscar": mpvis.get_poscar(
                                          self.struct_si),
                                      "kpoints": mpvis.get_kpoints(
                                          self.struct_si),
                                      "potcar": mpvis.get_potcar(
                                          self.struct_si)})
        ft = load_object(ft.to_dict())  # simulate database insertion
        ft.run_task({})
        self._verify_files()

    def test_preserve_incar(self):
        ft = WriteVaspStaticFromPrev(prev_dir=os.path.join(module_dir,
                                                           "reference_files",
                                                           "Si_structure_optimization",
                                                           "outputs"),
                                     preserve_old_incar=True)
        ft = load_object(ft.to_dict())
        ft.run_task({})
        self._verify_files(preserve_incar=True)

    def test_modifyincar(self):
        # create an INCAR
        incar = self.ref_incar
        incar.write_file(os.path.join(module_dir, "INCAR"))

        # modify and test
        ft = ModifyIncar(
            {"key_update": {"ISMEAR": 1000}, "key_multiply": {"ENCUT": 1.5},
             "key_dictmod": {"_inc": {"ISPIN": -1}}})
        ft = load_object(ft.to_dict())  # simulate database insertion
        ft.run_task({})

        incar_mod = Incar.from_file("INCAR")
        self.assertEqual(incar_mod['ISMEAR'], 1000)
        self.assertEqual(incar_mod['ENCUT'], 780)
        self.assertEqual(incar_mod['ISPIN'], 1)


if __name__ == '__main__':
    unittest.main()
