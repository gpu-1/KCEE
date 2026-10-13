import json,tempfile,unittest
from pathlib import Path
from kcee.bracket_analysis import analyze
class BracketRequestTests(unittest.TestCase):
    def test_non_default_material_is_explicitly_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent=Path(tmp)/'parent';parent.mkdir()
            (parent/'geometry-request.json').write_text(json.dumps({'geometry_mm':{'length':60,'width':30,'height':40,'thickness':3.5},'mounting_holes':True}))
            (parent/'requirements.json').write_text(json.dumps({'load_N':100,'youngs_modulus_MPa':123}))
            with self.assertRaises(ValueError):analyze(tmp,'parent',{})
            self.assertEqual(list(Path(tmp).iterdir()),[parent])
