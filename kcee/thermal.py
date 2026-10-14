"""Steady 1D conduction verification using a manufactured sine temperature solution.
SI units: -k T'' = q; insulated sides; fixed end temperatures.
"""
import math
LENGTH=.1
CONDUCTIVITY=15.
AREA=.0001
LEFT=20.
RIGHT=80.
AMPLITUDE=20.
def exact(x):return LEFT+(RIGHT-LEFT)*x/LENGTH+AMPLITUDE*math.sin(math.pi*x/LENGTH)
def source(x):return CONDUCTIVITY*AMPLITUDE*(math.pi/LENGTH)**2*math.sin(math.pi*x/LENGTH)
def solve(cells):
    if not isinstance(cells,int) or not 4<=cells<=1000:raise ValueError('Bounded mesh requires 4 to 1000 cells')
    h=LENGTH/cells;n=cells-1
    # Thomas elimination for the conservative central-difference tridiagonal system.
    diagonal=[2.]*n;rhs=[source((i+1)*h)*h*h/CONDUCTIVITY for i in range(n)]
    rhs[0]+=LEFT;rhs[-1]+=RIGHT
    for i in range(1,n):
        ratio=-1/diagonal[i-1];diagonal[i]+=ratio;rhs[i]-=ratio*rhs[i-1]
    inner=[0.]*n;inner[-1]=rhs[-1]/diagonal[-1]
    for i in range(n-2,-1,-1):inner[i]=(rhs[i]+inner[i+1])/diagonal[i]
    temperatures=[LEFT]+inner+[RIGHT]
    # Boundary half-cell generation completes second-order outward flux integration.
    left_out=CONDUCTIVITY*AREA*(temperatures[1]-LEFT)/h+source(0)*AREA*h/2
    right_out=CONDUCTIVITY*AREA*(temperatures[-2]-RIGHT)/h+source(LENGTH)*AREA*h/2
    generated=AREA*h*(sum(source(i*h) for i in range(1,cells))+(source(0)+source(LENGTH))/2)
    analytical_heat=2*CONDUCTIVITY*AREA*AMPLITUDE*math.pi/LENGTH
    residual=max(abs(CONDUCTIVITY*(2*temperatures[i]-temperatures[i-1]-temperatures[i+1])/h**2-source(i*h)) for i in range(1,cells))
    return {'cells':cells,'spacing_m':h,'maximum_temperature_error_C':max(abs(t-exact(i*h)) for i,t in enumerate(temperatures)),'peak_temperature_C':max(temperatures),'outward_left_heat_W':left_out,'outward_right_heat_W':right_out,'generated_heat_W':generated,'relative_heat_balance_error':abs(left_out+right_out-generated)/generated,'relative_generated_heat_error':abs(generated/analytical_heat-1),'maximum_equation_residual_W_m3':residual,'profile':[{'x_m':i*h,'temperature_C':t,'analytical_temperature_C':exact(i*h)} for i,t in enumerate(temperatures)]}
def benchmark():
    meshes=[solve(n) for n in (10,20,40,80)]
    orders=[math.log(a['maximum_temperature_error_C']/b['maximum_temperature_error_C'],2) for a,b in zip(meshes,meshes[1:])]
    checks={'temperature_accuracy':meshes[-1]['maximum_temperature_error_C']<.01,'second_order_refinement':all(1.95<order<2.05 for order in orders),'heat_balance':all(m['relative_heat_balance_error']<1e-9 for m in meshes),'integrated_source_accuracy':meshes[-1]['relative_generated_heat_error']<.001,'equation_residual':all(m['maximum_equation_residual_W_m3']<.001 for m in meshes)}
    return {'validation_status':'thermal_benchmark_verified_only' if all(checks.values()) else 'thermal_benchmark_checks_failed','method':'Conservative central finite differences; Thomas tridiagonal solve','units':'SI geometry, W heat, degrees Celsius temperature','inputs':{'length_m':LENGTH,'cross_section_m2':AREA,'conductivity_W_m_K':CONDUCTIVITY,'left_temperature_C':LEFT,'right_temperature_C':RIGHT,'sine_amplitude_C':AMPLITUDE},'analytical_temperature':'20 + 60*x/0.1 + 20*sin(pi*x/0.1) degrees Celsius','volumetric_source':'15*20*(pi/0.1)^2*sin(pi*x/0.1) W/m^3','mesh_study':meshes,'observed_orders':orders,'checks':checks,'tolerances':{'temperature_error_C':.01,'observed_order_minimum':1.95,'observed_order_maximum':2.05,'relative_heat_balance_error':1e-9,'relative_generated_heat_error':.001,'equation_residual_W_m3':.001},'limits':['Manufactured-solution verification of a 1D implementation, not physical validation','Constant illustrative conductivity; insulated sides and ideal fixed end temperatures','No transient response, radiation, convection, contact or bracket thermal analysis']}
