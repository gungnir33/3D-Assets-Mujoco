"""T_origin S_scale R_yaw R_axis，节点世界变换由调用方先展开。"""
import numpy as np
from .contracts import TARGET_RTOL,TARGET_ATOL

def normalization(vertices,request):
    vertices=np.asarray(vertices,dtype=np.float64)
    if vertices.ndim!=2 or vertices.shape[1]!=3 or not len(vertices) or not np.isfinite(vertices).all():
        raise ValueError("无效顶点")
    up=request.source_up or "y"
    axis={"z":np.eye(3),"y":np.array([[1,0,0],[0,0,-1],[0,1,0]]),"x":np.array([[0,0,-1],[0,1,0],[1,0,0]])}[up]
    angle=np.deg2rad(request.yaw_deg)
    c,s=np.cos(angle),np.sin(angle)
    rot=np.array([[c,-s,0],[s,c,0],[0,0,1]])@axis
    posed=vertices@rot.T
    dims=np.ptp(posed,axis=0)
    if np.max(dims)<=0:
        raise ValueError("所有轴均退化")
    factors=np.full(3,request.scale if request.scale is not None else 1.)
    if request.target_size_m is not None:
        target=np.asarray(request.target_size_m)
        flat=dims<1e-14
        if np.any(target[flat]!=0):
            raise ValueError("不能为平面制造厚度")
        if request.scale_mode=="uniform":
            factors[:]=np.dot(dims,target)/np.dot(dims,dims)
            if np.any(np.abs(dims*factors-target)>TARGET_RTOL*target+TARGET_ATOL):
                raise ValueError("目标 XYZ 与 uniform 比例不一致")
        else:
            factors=np.divide(target,dims,out=np.ones(3),where=~flat)
            if np.any(factors<=0):
                raise ValueError("禁止将有效轴压扁")
    linear=np.diag(factors)@rot
    points=vertices@linear.T
    low,high=points.min(axis=0),points.max(axis=0)
    origin=np.array([(low[0]+high[0])/2,(low[1]+high[1])/2,low[2]])
    matrix=np.eye(4)
    matrix[:3,:3]=linear
    matrix[:3,3]=-origin
    return matrix,high-low
