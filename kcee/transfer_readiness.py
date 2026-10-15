"""Read-only source transfer inventory; destination native acceptance remains separate."""
import hashlib,json
from kcee.library_coverage import compare_library

def study_fingerprint(groups):
    h=hashlib.sha256();counts={}
    for table in ('design_runs','run_visibility_events'):
        count=0
        for row in groups[table]:
            raw=json.dumps([table,row],sort_keys=True,separators=(',',':'),ensure_ascii=True).encode();h.update(len(raw).to_bytes(8,'big'));h.update(raw);count+=1
        counts[table]=count
    return {'scheme':'kcee.study-metadata.v1','sha256':h.hexdigest(),'counts':counts}
def study_snapshot(conn):
    conn.execute("SET LOCAL TIME ZONE 'UTC'")
    return study_fingerprint({table:(r['record'] for r in conn.execute("SELECT to_jsonb(t) - 'manifest' AS record FROM "+table+' t ORDER BY id')) for table in ('design_runs','run_visibility_events')})
def restore_link(backup,restore):
    if not backup or not restore or not restore.get('tested_bundle_sha256'):return {'status':'unknown','message':'The latest restore has no recorded archive fingerprint to compare.'}
    if backup['bundle_sha256']!=restore['tested_bundle_sha256']:return {'status':'different_backup','message':'The latest restore tested a different backup archive.'}
    return {'status':'matches','message':'The latest successful restore tested this exact backup SHA-256.'}
def transfer_readiness(saved,library,studies):
    backup=saved['backup'];restored=saved['restore'];link=restore_link(backup,restored);lib=compare_library(backup,library)
    checks=[{'name':'Backup archive present','status':'pass' if backup and backup.get('bundle_present') else 'attention','detail':backup['bundle_name'] if backup else 'No available backup receipt'}, {'name':'Current document library','status':'pass' if lib['status']=='matches_metadata' else 'unknown' if lib['status']=='unknown' else 'attention','detail':lib['message']}]
    old=backup.get('study_snapshot') if backup else None
    if backup and any(k in backup['counts'] and backup['counts'][k]!=v for k,v in studies['counts'].items()):state='attention';detail='Saved-study counts differ: '+', '.join(k+' backup '+str(backup['counts'].get(k,'unknown'))+' / current '+str(v) for k,v in studies['counts'].items())
    elif not isinstance(old,dict) or old.get('scheme')!=studies['scheme']:state='unknown';detail='This receipt has no compatible saved-study fingerprint.'
    elif old!=studies:state='attention';detail='Saved studies or their visibility history differ from the backup.'
    else:state='pass';detail='Saved-study metadata and visibility history match the receipt.'
    checks.extend([{'name':'Current saved studies','status':state,'detail':detail},{'name':'Restore of this archive','status':'pass' if link['status']=='matches' else 'unknown' if link['status']=='unknown' else 'attention','detail':link['message']},{'name':'Browser saved searches','status':'manual','detail':'Export saved searches separately in Documents → Search. Browser storage is outside the bundle.'},{'name':'Mac Studio native acceptance','status':'pending','detail':'Install and verify native runtimes, model files, Metal AI, PicoGK, voice and reference solves on the destination.'}])
    data_ready=all(c['status']=='pass' for c in checks[:4])
    return {'status':'source_data_ready' if data_ready else 'needs_attention','checks':checks,'backup_receipt':backup['record_name'] if backup else None,'bundle_sha256':backup['bundle_sha256'] if backup else None,'source_commit':backup.get('source_commit') if backup else None,'restore_record':restored['record_name'] if restored else None,'restore_link':link,'current_library':library,'current_studies':studies,'limitations':['Metadata freshness and recorded restore result only; this endpoint does not rehash the archive or source files.','Code snapshot refers to the recorded backup commit; current source code and untracked host files are not compared.','Destination hardware, native services, solver reproduction and audible voice quality need separate acceptance.'],'warnings':saved['warnings']}
