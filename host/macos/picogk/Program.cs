using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;
if(args.Length!=3){Console.Error.WriteLine("Usage: Kcee.Geometry request.json bracket.stl geometry.json");return 2;}
try {
 using var input=JsonDocument.Parse(File.ReadAllText(args[0]));var g=input.RootElement.GetProperty("geometry_mm");
 float L=g.GetProperty("length").GetSingle(),W=g.GetProperty("width").GetSingle(),H=g.GetProperty("height").GetSingle(),T=g.GetProperty("thickness").GetSingle();
 float voxel=input.RootElement.GetProperty("voxel_size_mm").GetSingle(),rounding=input.RootElement.GetProperty("fillet_radius_mm").GetSingle(),diameter=input.RootElement.GetProperty("hole_diameter_mm").GetSingle();
 bool holes=input.RootElement.GetProperty("mounting_holes").GetBoolean();
 if(!new[]{L,W,H,T,voxel,rounding,diameter}.All(float.IsFinite)||new[]{L,W,H,T,voxel}.Any(x=>x<=0)||rounding<0||diameter<0)throw new ArgumentException("Invalid dimensions");
 if(Math.Max(L,Math.Max(W,H))>200||voxel<.25f||voxel>Math.Min(T/4,1f)||L*W*H/(voxel*voxel*voxel)>8_000_000)throw new ArgumentException("Geometry exceeds bounded demo budget");
 if(T>=Math.Min(L,H)||rounding>T/2||(holes&&(diameter<4*voxel||diameter>Math.Min(W/3,Math.Min(L/8,H/8))||T+rounding+diameter/2>=Math.Min(.4f*H,.55f*L))))throw new ArgumentException("Incompatible holes/fillet dimensions");
 using var lib=new Library(voxel);var shape=new Bracket(L,W,H,T);
 using var vox=new Voxels(lib,shape,new BBox3(new Vector3(-2*voxel),new Vector3(L+2*voxel,W+2*voxel,H+2*voxel)));
 if(rounding>0)vox.Fillet(rounding);
 if(holes){
  foreach(var x in new[]{.55f*L,.8f*L}){using var cut=Voxels.voxLatticeBeam(lib,new Vector3(x,W/2,-diameter),diameter/2,new Vector3(x,W/2,T+diameter),diameter/2);vox.BoolSubtract(cut);}
  foreach(var z in new[]{.4f*H,.75f*H}){using var cut=Voxels.voxLatticeBeam(lib,new Vector3(-diameter,W/2,z),diameter/2,new Vector3(T+diameter,W/2,z),diameter/2);vox.BoolSubtract(cut);}
 }
 if(vox.bIsEmpty())throw new InvalidOperationException("Empty kernel geometry");
 using var mesh=new Mesh(vox);vox.CalculateProperties(out float volume,out BBox3 bounds);using var clean=new Mesh(lib);int removed=0;
 for(int i=0;i<mesh.nTriangleCount();i++){mesh.GetTriangle(i,out Vector3 a,out Vector3 b,out Vector3 c);if(a==b||a==c||b==c){removed++;continue;}clean.nAddTriangle(a,b,c);}
 clean.SaveToStlFile(args[1],Mesh.EStlUnit.MM);
 var hashes=Directory.GetFiles(AppContext.BaseDirectory,"*.dylib",SearchOption.AllDirectories).Order().ToDictionary(p=>Path.GetRelativePath(AppContext.BaseDirectory,p),p=>Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(p))).ToLowerInvariant());
 var metadata=new{schema_version=1,backend="PicoGK",package_version="2.3.0",kernel_version=Library.strVersion(),kernel_build=Library.strBuildInfo(),units="mm",voxel_size_mm=voxel,fillet_radius_mm=rounding,hole_diameter_mm=diameter,mounting_holes=holes,volume_mm3=volume,triangle_count=clean.nTriangleCount(),removed_duplicate_vertex_triangles=removed,native_library_sha256=hashes,adapter_assembly_sha256=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(typeof(Bracket).Assembly.Location))).ToLowerInvariant(),bounds_min_mm=new[]{bounds.vecMin.X,bounds.vecMin.Y,bounds.vecMin.Z},bounds_max_mm=new[]{bounds.vecMax.X,bounds.vecMax.Y,bounds.vecMax.Z},validation_status="geometry_generated_not_engineering_validated"};
 File.WriteAllText(args[2],JsonSerializer.Serialize(metadata,new JsonSerializerOptions{WriteIndented=true}));Console.WriteLine("PicoGK bracket generated");return 0;
}catch(Exception error){Console.Error.WriteLine(error.Message);return 1;}
sealed class Bracket(float length,float width,float height,float thickness):IImplicit {
 static float Box(in Vector3 p,Vector3 center,Vector3 half){Vector3 q=Vector3.Abs(p-center)-half;return Vector3.Max(q,Vector3.Zero).Length()+MathF.Min(MathF.Max(q.X,MathF.Max(q.Y,q.Z)),0);}
 public float fSignedDistance(in Vector3 p)=>MathF.Min(Box(p,new Vector3(length/2,width/2,thickness/2),new Vector3(length/2,width/2,thickness/2)),Box(p,new Vector3(thickness/2,width/2,height/2),new Vector3(thickness/2,width/2,height/2)));
}
