"""Cell-centred FV verification of fully developed plane Poiseuille momentum."""
import math
INPUTS={'gap_m':.01,'pressure_gradient_Pa_m':.1,'dynamic_viscosity_Pa_s':.001,'density_kg_m3':1000.,'display_length_m':.2}
LIMITS=['Steady, incompressible, Newtonian, fully developed laminar flow between infinite parallel plates.','The transverse velocity is zero and streamwise convection vanishes by the fully developed assumption.','This reduced momentum benchmark does not solve general 2D/3D pressure-velocity coupling, entry flow, turbulence, heat transfer or bracket flow.','The displayed channel is an illustrative envelope; flow rates are per unit span, with no finite-width sidewall effects.','Numerical verification is not engineering validation.']
# Conservative demonstration envelope, not a physical transition criterion.
BOUNDS={'gap_m':(.001,.05),'pressure_gradient_Pa_m':(.001,10.),'dynamic_viscosity_Pa_s':(.0001,1.),'density_kg_m3':(1.,2000.),'display_length_m':(.05,2.)}
def case_inputs(inputs=None):
 x=dict(INPUTS)
 if inputs is not None:
  if not isinstance(inputs,dict) or set(inputs)-set(INPUTS):raise ValueError('Unknown channel input')
  x.update(inputs)
 for key,(low,high) in BOUNDS.items():
  value=x[key]
  if type(value) not in (float,int) or not math.isfinite(value) or not low<=value<=high:raise ValueError(key+' must be between '+str(low)+' and '+str(high)+' in SI units')
 reynolds=x['density_kg_m3']*x['pressure_gradient_Pa_m']*x['gap_m']**3/(6*x['dynamic_viscosity_Pa_s']**2)
 if reynolds>500:raise ValueError('Use an analytical hydraulic Reynolds number at most 500 for this conservative laminar demonstration; this is not a transition criterion')
 return x
def solve(cells,inputs=None):
 if type(cells) is not int or not 4<=cells<=512:raise ValueError('Use 4 to 512 cells')
 x=dict(INPUTS if inputs is None else inputs)
 if set(x)!=set(INPUTS) or any(type(v) not in (float,int) or not math.isfinite(v) or v<=0 for v in x.values()):raise ValueError('Use positive finite SI inputs')
 H=x['gap_m'];G=x['pressure_gradient_Pa_m'];mu=x['dynamic_viscosity_Pa_s'];rho=x['density_kg_m3'];h=H/cells
 # No-slip walls use the half-cell wall distance: diagonal 3 at each end.
 diagonal=[3.]+[2.]*(cells-2)+[3.];rhs=[G*h*h/mu]*cells;upper=[-1.]*(cells-1)
 for i in range(1,cells):
  multiplier=-1/diagonal[i-1];diagonal[i]-=multiplier*upper[i-1];rhs[i]-=multiplier*rhs[i-1]
 u=[0.]*cells;u[-1]=rhs[-1]/diagonal[-1]
 for i in range(cells-2,-1,-1):u[i]=(rhs[i]-upper[i]*u[i+1])/diagonal[i]
 profile=[{'y_m':(i+.5)*h,'velocity_m_s':v,'analytical_velocity_m_s':G*((i+.5)*h)*(H-(i+.5)*h)/(2*mu)} for i,v in enumerate(u)]
 exact_flow=G*H**3/(12*mu);flow=sum(u)*h;peak=G*H*H/(8*mu);left=2*mu*u[0]/h;right=2*mu*u[-1]/h
 residual=max(abs(mu*((3 if i in (0,cells-1) else 2)*v-(u[i-1] if i else 0)-(u[i+1] if i+1<cells else 0))/h**2-G) for i,v in enumerate(u))
 return {'cells':cells,'cell_size_m':h,'profile':profile,'maximum_velocity_error_m_s':max(abs(r['velocity_m_s']-r['analytical_velocity_m_s']) for r in profile),'relative_profile_error':max(abs(r['velocity_m_s']-r['analytical_velocity_m_s']) for r in profile)/peak,'flow_per_span_m2_s':flow,'analytical_flow_per_span_m2_s':exact_flow,'relative_flow_error':abs(flow-exact_flow)/exact_flow,'mean_velocity_m_s':flow/H,'analytical_peak_velocity_m_s':peak,'wall_shear_lower_Pa':left,'wall_shear_upper_Pa':right,'relative_momentum_balance_error':abs(left+right-G*H)/(G*H),'maximum_momentum_residual_Pa_m':residual,'relative_symmetry_error':max(abs(a-b) for a,b in zip(u,reversed(u)))/peak,'reynolds_hydraulic_diameter':rho*(exact_flow/H)*(2*H)/mu}
def benchmark(inputs=None):
 x=case_inputs(inputs)
 meshes=[solve(n,x) for n in (16,32,64,128)];orders=[math.log(a['maximum_velocity_error_m_s']/b['maximum_velocity_error_m_s'],2) for a,b in zip(meshes,meshes[1:])]
 tolerances={'relative_profile_error':1e-4,'relative_flow_error':2e-4,'relative_momentum_balance_error':1e-9,'maximum_momentum_residual_Pa_m':1e-7*x['pressure_gradient_Pa_m'],'relative_symmetry_error':1e-9,'observed_order_minimum':1.99,'observed_order_maximum':2.01}
 checks={'profile_accuracy':meshes[-1]['relative_profile_error']<tolerances['relative_profile_error'],'flow_accuracy':meshes[-1]['relative_flow_error']<tolerances['relative_flow_error'],'momentum_balance':all(m['relative_momentum_balance_error']<tolerances['relative_momentum_balance_error'] for m in meshes),'equation_residual':all(m['maximum_momentum_residual_Pa_m']<tolerances['maximum_momentum_residual_Pa_m'] for m in meshes),'symmetry':all(m['relative_symmetry_error']<tolerances['relative_symmetry_error'] for m in meshes),'second_order_refinement':all(1.99<o<2.01 for o in orders)}
 return {'kind':'cfd_benchmark','validation_status':'cfd_numerical_checks_passed_not_engineering_validated' if all(checks.values()) else 'cfd_numerical_checks_failed','method':'Cell-centred finite volume; tridiagonal direct solve of -mu d²u/dy² = G','inputs':x,'analytical_solution':'u(y)=G*y*(H-y)/(2*mu); q per span=G*H³/(12*mu); wall shear magnitude=G*H/2','mesh_study':meshes,'observed_orders':orders,'checks':checks,'tolerances':tolerances,'limits':LIMITS,'reference':'https://mfix.netl.doe.gov/doc/vvuq-manual/main/html/fluid/fld-01.html'}
