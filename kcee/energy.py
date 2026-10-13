"""Isotropic small-strain linear-elastic energy density in MPa (= N/mm²)."""
import math

def strain_energy_density(stress,youngs_modulus,poisson_ratio):
    if len(stress)!=6 or not all(math.isfinite(x) for x in stress):raise ValueError('Invalid stress tensor')
    if not math.isfinite(youngs_modulus) or youngs_modulus<=0 or not math.isfinite(poisson_ratio) or not -1<poisson_ratio<.5:raise ValueError('Invalid elastic material')
    sx,sy,sz,xy,xz,yz=stress;nu=poisson_ratio
    value=(sx*sx+sy*sy+sz*sz-2*nu*(sx*sy+sy*sz+sz*sx)+2*(1+nu)*(xy*xy+xz*xz+yz*yz))/(2*youngs_modulus)
    if not math.isfinite(value) or value<0:raise ValueError('Invalid strain energy density')
    return value
