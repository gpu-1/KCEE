"""Consistent quadratic face weights integrated over a clipped planar triangle."""
import math

def strip_weights(corners,x_min=55):
    polygon=[(list(p),[float(i==j) for j in range(3)]) for i,p in enumerate(corners)]
    clipped=[]
    for a,b in zip(polygon,polygon[1:]+polygon[:1]):
        inside_a=a[0][0]>=x_min;inside_b=b[0][0]>=x_min
        if inside_a:clipped.append(a)
        if inside_a!=inside_b:
            t=(x_min-a[0][0])/(b[0][0]-a[0][0])
            clipped.append(([a[0][j]+t*(b[0][j]-a[0][j]) for j in range(3)],[a[1][j]+t*(b[1][j]-a[1][j]) for j in range(3)]))
    weights=[0.]*6;total=0.
    for index in range(1,len(clipped)-1):
        triangle=[clipped[0],clipped[index],clipped[index+1]];a,b,c=[p for p,l in triangle]
        u=[b[j]-a[j] for j in range(3)];v=[c[j]-a[j] for j in range(3)]
        cross=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]);area=math.sqrt(sum(x*x for x in cross))/2;total+=area
        for q in ((2/3,1/6,1/6),(1/6,2/3,1/6),(1/6,1/6,2/3)):
            l=[sum(q[k]*triangle[k][1][j] for k in range(3)) for j in range(3)]
            shape=[l[j]*(2*l[j]-1) for j in range(3)]+[4*l[0]*l[1],4*l[1]*l[2],4*l[2]*l[0]]
            for j in range(6):weights[j]+=area*shape[j]/3
    return total,weights
