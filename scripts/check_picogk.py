"""Real native kernel regression checks, independent of FEA validation."""
import json,math,struct,tempfile
from collections import Counter
from pathlib import Path
from kcee.demo import DEFAULT,run
from kcee.provenance import verify_directory

def check_mesh(path):
    raw=path.read_bytes();count=struct.unpack_from('<I',raw,80)[0]
    assert len(raw)==84+count*50 and count>100
    edges=Counter();vertices=set();signed=0
    for i in range(count):
        values=struct.unpack_from('<12fH',raw,84+i*50)
        a,b,c=[tuple(values[j:j+3]) for j in (3,6,9)]
        assert all(math.isfinite(x) for v in (a,b,c) for x in v)
        vertices.update((a,b,c))
        for p,q in ((a,b),(b,c),(c,a)):edges[tuple(sorted((p,q)))]+=1
        signed+=(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6
    assert all(value==2 for value in edges.values()),'Mesh has open/non-manifold edges'
    assert signed>0,'Mesh must have positive oriented volume'
    return len(vertices)-len(edges)+count,signed

def main():
    with tempfile.TemporaryDirectory() as tmp:
        directory=Path(tmp)
        plain=json.loads(DEFAULT.read_text());plain['geometry_options']={'mounting_holes':False,'fillet_radius_mm':0}
        request=directory/'plain.json';request.write_text(json.dumps(plain))
        dest=run(directory/'runs',request,'picogk');verify_directory(dest)
        result=json.loads((dest/'result.json').read_text());g=plain['geometry_mm'];t=result['selected']['thickness_mm']
        expected=g['width']*t*(g['length']+g['height']-t)
        topology,volume=check_mesh(dest/'bracket.stl');assert topology==2
        assert abs(result['geometry']['volume_mm3']/expected-1)<.03
        assert abs(volume/expected-1)<.03
        dest=run(directory/'runs',geometry_backend='picogk');verify_directory(dest)
        topology,volume=check_mesh(dest/'bracket.stl');assert topology==-6,'Four through holes expected'
        result=json.loads((dest/'result.json').read_text())
        assert result['geometry']['mounting_holes'] is True
        assert abs(volume/result['geometry']['volume_mm3']-1)<.03
        assert result['validation_status']=='unvalidated_analytical_screening'
        print('Native PicoGK checks passed: closed oriented meshes, four holes, benchmark volume and provenance')
if __name__=='__main__':main()
