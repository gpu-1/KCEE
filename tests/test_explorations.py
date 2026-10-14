import json,tempfile,unittest,uuid
from pathlib import Path
from kcee.explorations import recorded_explorations
from kcee.provenance import IntegrityError
class ExplorationTests(unittest.TestCase):
    def test_linked_evidence_and_rejection_of_changed_source(self):
        run_id=uuid.uuid4()
        record={'id':run_id,'manifest_sha256':'m','manifest':{'artifacts':{'bracket.stl':'s'}}}
        report={'run_id':str(run_id),'manifest_sha256':'m','source_stl_sha256':'s','solve_1_3':{'summary':{'target_size_mm':1.3,'nodes':100,'elements':50,'tip_deflection_mm':.8,'maximum_von_mises_MPa':230},'archive_sha256':'a'*64}}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'finer-mesh-exploration.json';path.write_text(json.dumps(report))
            items=recorded_explorations(directory,record);self.assertEqual(items[0]['rows'][0]['peak_stress_MPa'],230);self.assertEqual(len(items[0]['report_sha256']),64)
            report['source_stl_sha256']='changed';path.write_text(json.dumps(report))
            with self.assertRaises(IntegrityError):recorded_explorations(directory,record)
            report['run_id']='other';path.write_text(json.dumps(report));self.assertEqual(recorded_explorations(directory,record),[])
    def test_invalid_measurement_cannot_be_displayed(self):
        record={'id':'source','manifest_sha256':'m','manifest':{'artifacts':{'bracket.stl':'s'}}}
        report={'run_id':'source','manifest_sha256':'m','source_stl_sha256':'s','solve_1_3':{'summary':{'target_size_mm':1.3,'nodes':100,'elements':50,'tip_deflection_mm':float('nan'),'maximum_von_mises_MPa':230},'archive_sha256':'a'*64}}
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory)/'finer-mesh-exploration.json').write_text(json.dumps(report))
            with self.assertRaises(ValueError):recorded_explorations(directory,record)
