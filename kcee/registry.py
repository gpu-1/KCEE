"""PostgreSQL append-only run registry. Credentials use PG* environment variables."""
import argparse
import json
from pathlib import Path
from uuid import UUID
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from kcee.provenance import IntegrityError, verify_directory

class Registry:
    def connect(self):
        return psycopg.connect(connect_timeout=3,row_factory=dict_row)

    def ready(self):
        with self.connect() as conn:
            conn.execute('SELECT id FROM design_runs LIMIT 0')

    def register(self,directory):
        manifest,digest=verify_directory(directory)
        with self.connect() as conn:
            conn.execute('INSERT INTO design_runs (id,parent_id,created_at,validation_status,manifest,manifest_sha256) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING',
                         (manifest['run_id'],manifest.get('parent_design_id'),manifest['created_at'],manifest['validation_status'],Jsonb(manifest),digest))
            stored=conn.execute('SELECT manifest, manifest_sha256 FROM design_runs WHERE id=%s',(manifest['run_id'],)).fetchone()
            if stored['manifest_sha256']!=digest or stored['manifest']!=manifest:
                raise IntegrityError('Run ID already registered with different provenance')
        from kcee.cfd_control import registered
        registered(manifest['run_id'])
        return manifest['run_id']

    def get(self,run_id):
        with self.connect() as conn:
            return conn.execute('SELECT id,parent_id,created_at,validation_status,manifest,manifest_sha256 FROM design_runs WHERE id=%s',(str(UUID(str(run_id))),)).fetchone()

    def list(self,limit=50,offset=0,hidden=False):
        with self.connect() as conn:
            return conn.execute("SELECT id,parent_id,created_at,validation_status,manifest_sha256,COALESCE(manifest->>'kind','bracket') AS kind FROM design_runs WHERE COALESCE((SELECT hidden FROM run_visibility_events WHERE run_id=design_runs.id ORDER BY id DESC LIMIT 1),false)=%s ORDER BY created_at DESC,id DESC LIMIT %s OFFSET %s",(hidden,limit,offset)).fetchall()

    def set_visibility(self,run_id,hidden):
        with self.connect() as conn:
            found=conn.execute('SELECT id FROM design_runs WHERE id=%s',(str(run_id),)).fetchone()
            if found is None:raise KeyError('Unknown run')
            conn.execute('INSERT INTO run_visibility_events(run_id,hidden) VALUES(%s,%s)',(str(run_id),hidden))
        return {'run_id':str(run_id),'hidden':hidden,'artifacts':'retained'}

    def verify(self,root,run_id):
        record=self.get(run_id)
        if record is None: raise KeyError('Unknown run')
        verify_directory(Path(root)/str(record['id']),record['manifest'],record['manifest_sha256'])
        return {'run_id':str(record['id']),'integrity':'verified','validation_status':record['validation_status']}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['register','verify']);parser.add_argument('directory');args=parser.parse_args()
    registry=Registry();directory=Path(args.directory).resolve()
    if args.command=='register': print(registry.register(directory))
    else: print(json.dumps(registry.verify(directory.parent,directory.name)))
