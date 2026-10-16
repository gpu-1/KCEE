export function samplingLabel(result){
 const data=result.flow??result.flow_refinement??result.domain_study??result.combined_flow??result.local_refinement;
 if(!data)return '';
 if(!data.sampling)return 'Historical sampling: see the saved report for the recorded method. Original probe values are preserved.';
 const version=data.sampling.version;
 if(version==='compact-radius-v1')return 'Sampling: Compact v1 · minimum support radius within the bounded candidate pool. Custom interpolation; native OpenFOAM sampling is not established.';
 if(version==='first-enclosing-v1')return 'Historical sampling: First enclosing v1. This saved study retains its original interpolation method.';
 throw Error('Unsupported saved CFD sampling version');
}
