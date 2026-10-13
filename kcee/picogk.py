"""Bounded native PicoGK subprocess adapter."""
import json,math,os,subprocess
from pathlib import Path
class GeometryError(RuntimeError): pass
DEFAULT_OPTIONS={'voxel_size_mm':.5,'fillet_radius_mm':1.0,'hole_diameter_mm':5.0,'mounting_holes':True}
def generate(directory,geometry,options=None,executable=None):
    if options is not None and (not isinstance(options,dict) or set(options)-set(DEFAULT_OPTIONS)):raise GeometryError("Unsupported PicoGK geometry options")
    directory=Path(directory).resolve()
    command=Path(executable or os.environ.get('KCEE_PICOGK_EXECUTABLE') or Path(__file__).resolve().parents[1]/'host/macos/picogk/generate.sh')
    if not command.is_file():raise GeometryError('Native PicoGK executable is unavailable; provision it first')
    request=directory/'geometry-request.json';request.write_text(json.dumps({'geometry_mm':geometry,**DEFAULT_OPTIONS,**(options or {})},indent=2))
    try:subprocess.run([str(command),str(request),str(directory/'bracket.stl'),str(directory/'geometry.json')],capture_output=True,text=True,timeout=120,check=True)
    except subprocess.TimeoutExpired as exc:raise GeometryError('PicoGK generation timed out after 120 seconds') from exc
    except (OSError,subprocess.CalledProcessError) as exc:raise GeometryError('PicoGK generation failed: '+(getattr(exc,'stderr','') or str(exc))[-2000:]) from exc
    try:
        metadata=json.loads((directory/'geometry.json').read_text())
        if metadata['backend']!='PicoGK' or metadata['units']!='mm' or not metadata['triangle_count']>0 or not math.isfinite(metadata['volume_mm3']) or not metadata['volume_mm3']>0:raise ValueError('Invalid kernel result')
        if not (directory/'bracket.stl').is_file():raise ValueError('Missing STL')
    except (OSError,ValueError,KeyError,TypeError) as exc:raise GeometryError('Incomplete PicoGK output') from exc
    return metadata
