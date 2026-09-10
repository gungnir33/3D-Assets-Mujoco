import numpy as np
from .contracts import GEOMETRY_RTOL,GEOMETRY_ATOL,INERTIA_RTOL,INERTIA_ATOL

def box_inertia(mass,size):
    size=np.asarray(size,dtype=float)
    if mass<=0 or not np.isfinite(mass) or not np.isfinite(size).all() or np.any(size<=0):
        raise ValueError("box 惯量要求正质量和三个正尺寸")
    x,y,z=size
    return np.diag(np.array([y*y+z*z,x*x+z*z,x*x+y*y])*mass/12)

def supplied_inertia(value,mass,size):
    if not np.isclose(value.mass_kg,mass,rtol=1e-8,atol=1e-9):
        raise ValueError("supplied 质量不匹配")
    if not np.allclose(value.final_size_m,size,rtol=GEOMETRY_RTOL,atol=GEOMETRY_ATOL):
        raise ValueError("supplied 最终尺寸不匹配")
    tensor=np.asarray(value.tensor,dtype=float)
    if not np.allclose(tensor,tensor.T,rtol=INERTIA_RTOL,atol=INERTIA_ATOL):
        raise ValueError("惯量不对称")
    tensor=(tensor+tensor.T)/2
    eigen=np.linalg.eigvalsh(tensor)
    if eigen[0]<=0 or eigen[2]>eigen[0]+eigen[1]+INERTIA_ATOL+INERTIA_RTOL*eigen[2]:
        raise ValueError("惯量非正定或违反三角不等式")
    # 已为最终 normalized_body 中关于 COM 的张量，不应用 G。
    return np.asarray(value.com),tensor
