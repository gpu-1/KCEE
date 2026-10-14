import io,json,math,tempfile,unittest,zipfile
from pathlib import Path
from kcee.bracket_thermal_run import temperature_surface
class ThermalSurfaceTests(unittest.TestCase):
 def archive(self,data):
  output=io.BytesIO()
  with zipfile.ZipFile(output,'w') as archive:archive.writestr('mesh-1.5/thermal-surface.json',json.dumps(data))
  output.seek(0);return output
 def fixture(self):return {'positions':[[0,0,0],[1,0,0],[0,1,0]],'temperatures_C':[20,80,50],'triangles':[[0,1,2]],'minimum_temperature_C':20,'maximum_temperature_C':80}
 def test_valid_surface(self):
  data=self.fixture();self.assertEqual(temperature_surface(self.archive(data)),data)
 def test_invalid_temperature_geometry_and_range(self):
  for change in ({'temperatures_C':[20,80]},{'temperatures_C':[20,float('nan'),50]},{'triangles':[[0,1,3]]},{'maximum_temperature_C':100},{'positions':[[0,0],[1,0,0],[0,1,0]]}):
   with self.assertRaises(ValueError):temperature_surface(self.archive(dict(self.fixture(),**change)))
