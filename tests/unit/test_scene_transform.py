import numpy as np
import pytest
from asset_mujoco.transforms import normalization
from asset_mujoco.contracts import ConversionRequest

def request(**kw):
    return ConversionRequest(input="a.glb",output="out",**kw)

def test_float32_size():
    vertices=np.array([[0,0,0],[.13,1,2]],dtype=np.float32)
    matrix, size=normalization(vertices,request(source_up="z",target_size_m=(.13,1,2)))
    np.testing.assert_allclose(size,[.13,1,2],rtol=1e-6,atol=1e-7)

def test_yaw_precedes_scale():
    matrix,size=normalization(np.array([[0,0,0],[1,3,2]]),request(source_up="z",yaw_deg=90,target_size_m=(6,2,4)))
    np.testing.assert_allclose(size,[6,2,4],atol=1e-7)

def test_uniform_rule():
    _,size=normalization(np.array([[0,0,0],[1,2,3]]),request(source_up="z",target_size_m=(2,4,6.01)))
    np.testing.assert_allclose(size,np.array([1,2,3])*28.03/14)

def test_wrong_axis_rejected():
    with pytest.raises(ValueError):
        normalization(np.array([[0,0,0],[1,3,2]]),request(source_up="z",target_size_m=(6,2,4)))

def test_plane_not_rejected():
    _,size=normalization(np.array([[0,0,0],[1,2,0]]),request(source_up="z",target_size_m=(2,4,0)))
    np.testing.assert_allclose(size,[2,4,0])
