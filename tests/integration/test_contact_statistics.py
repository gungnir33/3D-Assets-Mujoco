import json
import numpy as np
import pytest
from asset_mujoco.contact_diagnostics import trace_fixture

def test_impulse_and_ground_are_measured_without_force_limit(tmp_path):
    fixture=tmp_path/'fixture.xml'
    fixture.write_text('''<mujoco><option timestep=".002"><flag energy="enable" autoreset="disable"/></option>
    <worldbody><geom name="asset_collision" type="box" size=".1 .1 .1" pos="10 0 0"/>
    <geom name="ground" type="plane" size="5 5 .1" solref=".006 1" solimp=".9 .95 .001 .5 2"/>
    <body name="probe_body" pos="0 0 .3"><freejoint/>
    <geom name="probe" type="sphere" size=".025" mass=".1" solref=".006 1" solimp=".9 .95 .001 .5 2"/>
    </body></worldbody></mujoco>''')
    result=trace_fixture(fixture,tmp_path)
    assert result['application_force_limit']=='not_specified'
    stats=result['contact_statistics']['ground_probe']
    rows=[json.loads(line) for line in (tmp_path/'contact_trace.jsonl').read_text().splitlines()]
    contacts=[c for r in rows for c in r['secondary_contacts']]
    assert stats['contact_records']==len(contacts)>0
    assert stats['normal_impulse_N_s']==pytest.approx(sum(c['force_contact_frame_N_Nm'][0]*.002 for c in contacts),abs=1e-12)
    assert stats['peak_normal_force_N']==pytest.approx(max(c['force_contact_frame_N_Nm'][0] for c in contacts))
    assert stats['normal_impulse_N_s']>0
    assert stats['first_contact_normal_velocity_m_s']<0
    assert stats['max_separating_speed_during_contact_m_s']>=0
    assert stats['first_resolved_contact']['solref']==pytest.approx([.006,1])
    assert not result['contact_statistics']['asset_probe']['contact_records']
    assert np.isfinite(stats['world_impulse_on_probe_N_s']).all()
