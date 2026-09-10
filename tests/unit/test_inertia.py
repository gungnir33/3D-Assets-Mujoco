import numpy as np
import pytest
from asset_mujoco.inertia import box_inertia, supplied_inertia
from asset_mujoco.contracts import SuppliedInertia

def test_box_scale_law():
    a=box_inertia(2,np.array([1.,2.,3.]))
    b=box_inertia(2,np.array([2.,4.,6.]))
    np.testing.assert_allclose(b,4*a)

def payload(**kw):
    args=dict(frame="normalized_body",reference="com",com_unit="m",inertia_unit="kg*m^2",com=[.1,.2,.3],tensor=[[1,0,0],[0,1,0],[0,0,1]],mass_kg=2,final_size_m=[.13,1,2])
    args.update(kw)
    return SuppliedInertia(**args)

def test_supplied_float32_dimensions():
    com,tensor=supplied_inertia(payload(),2,np.array([.13,1,2],dtype=np.float32))
    np.testing.assert_allclose(com,[.1,.2,.3])
    np.testing.assert_allclose(tensor,np.eye(3))

@pytest.mark.parametrize("tensor",[[[1,0,0],[0,1,0],[0,0,3]],[[0,0,0],[0,1,0],[0,0,1]],[[1,.1,0],[0,1,0],[0,0,1]]])
def test_unphysical_tensor(tensor):
    with pytest.raises(ValueError):
        supplied_inertia(payload(tensor=tensor),2,[.13,1,2])
