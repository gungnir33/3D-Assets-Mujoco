"""仅用于显式诊断：新副本、固定少量控制变量，不改变正式验收配置。"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import xml.etree.ElementTree as ET
import mujoco
import numpy as np
from .manifest import compile_resources,write_evidence
from .validation import check_state

CASES=[
    {'name':'baseline'},
    {'name':'A_dt_001','dt':.001},
    {'name':'A_dt_0005','dt':.0005},
    {'name':'B_tangent_plane','geometry':'tangent_plane'},
    {'name':'C_timeconst_01','solref':[.01,1]},
    {'name':'C_timeconst_006','solref':[.006,1]},
    {'name':'D_d0_095','solimp':[.95,.95,.001,.5,2]},
    {'name':'D_dwidth_099','solimp':[.9,.99,.001,.5,2]},
]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def configure_fixture(source,target,config,plane=None):
    root=ET.parse(source).getroot()
    if root.find('.//pair') is not None:
        raise ValueError('diagnostic baseline must not contain forced pair')
    if 'dt' in config:
        root.find('option').set('timestep',str(config['dt']))
    for field in ('solref','solimp'):
        if field in config:
            for name in ('asset_collision','probe'):
                root.find(f".//geom[@name='{name}']").set(field,' '.join(map(str,config[field])))
    if config.get('geometry')=='tangent_plane':
        if plane is None:
            raise ValueError('缺少基线首次接触切平面')
        geom=root.find(".//geom[@name='asset_collision']")
        for key in ('mesh','pos','quat','euler','axisangle','xyaxes','zaxis','size'):
            geom.attrib.pop(key,None)
        geom.set('type','plane'); geom.set('size','5 5 .1')
        geom.set('pos',' '.join(map(str,plane['point_world'])))
        quat=np.empty(4)
        mujoco.mju_quatZ2Vec(quat,np.asarray(plane['normal_world'],dtype=float))
        geom.set('quat',' '.join(map(str,quat)))
    ET.ElementTree(root).write(target)

def _serial(value):
    if isinstance(value,dict):
        return {k:_serial(v) for k,v in value.items()}
    if isinstance(value,list):
        return [_serial(v) for v in value]
    if isinstance(value,float) and not np.isfinite(value):
        return None
    return value

def trace_fixture(fixture,output,*,total_time=2.,limit=.005):
    """第k步采样t=(k-1)dt；step1保存状态/接触，step2取同次求解力。

    step2只支持本诊断的Euler路径；qacc/force属于积分前求解，qpos_after/
    qvel_after及integrated_time另列。不会在step后额外forward改变warm-start。
    """
    fixture=Path(fixture); output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    model=mujoco.MjModel.from_xml_path(str(fixture))
    if model.opt.integrator!=mujoco.mjtIntegrator.mjINT_EULER:
        raise ValueError('diagnostic trace only supports the baseline Euler integrator')
    if not model.opt.enableflags & int(mujoco.mjtEnableBit.mjENBL_ENERGY):
        raise ValueError('energy must be enabled')
    if not model.opt.disableflags & int(mujoco.mjtDisableBit.mjDSBL_AUTORESET):
        raise ValueError('autoreset must be disabled')
    if model.opt.enableflags & int(mujoco.mjtEnableBit.mjENBL_OVERRIDE):
        raise ValueError('contact override forbidden')
    dt=float(model.opt.timestep)
    steps=round(total_time/dt)
    if steps<=0 or not np.isclose(steps*dt,total_time,rtol=0,atol=1e-12):
        raise ValueError('total_time must be an integer number of steps')
    data=mujoco.MjData(model); mujoco.mj_forward(model,data)
    check_state(model,data,0,0)
    ids={model.geom(name).id for name in ('asset_collision','probe')}
    summary={'diagnostic':True,'dt':dt,'requested_steps':steps,'requested_time_s':total_time,
             'threshold_m':limit,'first_contact_step':None,'first_exceedance_step':None,
             'max_penetration_step':None,'max_penetration_m':0.,'contact_record_count':0,
             'max_normal_force_N':0.,'first_abnormal_step':None,'numerically_stable':True,
             'sampling':'step k: pre-integration t=(k-1)*dt; force/qacc from same step2 solve; post-state separately labeled',
             'force_coordinates':'contact frame [normal,tangent1,tangent2], force then torque; world force on geom2',
             'normal_velocity_definition':'dot(v_geom2_at_contact-v_geom1_at_contact, normal_geom1_to_geom2)',
             'mujoco':mujoco.__version__,'fixture_sha256':sha(fixture),
             'initial_qpos':data.qpos.tolist(),'initial_qvel':data.qvel.tolist()}
    summary['resolved_geoms']={}
    for name in ('asset_collision','probe'):
        i=model.geom(name).id
        summary['resolved_geoms'][name]={key:np.asarray(getattr(model,'geom_'+key)[i]).tolist()
            for key in ('type','size','contype','conaffinity','solref','solimp','solmix','priority','friction','margin','gap')}
    probe_body=model.geom_bodyid[model.geom('probe').id]
    summary['probe_mass_kg']=float(model.body_mass[probe_body])
    summary['solver']={'integrator':'Euler','solver':int(model.opt.solver),'iterations':int(model.opt.iterations),
                       'tolerance':float(model.opt.tolerance),'enableflags':int(model.opt.enableflags),'disableflags':int(model.opt.disableflags)}
    trace=output/'contact_trace.jsonl'
    with trace.open('w') as file:
        for step in range(1,steps+1):
            mujoco.mj_step1(model,data)
            row={'step':step,'sample_time_s':float(data.time),'qpos':data.qpos.tolist(),
                 'qvel':data.qvel.tolist(),'energy':data.energy.tolist(),'contacts':[]}
            indexes=[]
            for index,c in enumerate(data.contact):
                if {int(c.geom1),int(c.geom2)}!=ids:
                    continue
                frame=np.asarray(c.frame).reshape(3,3).copy()
                velocities=[]
                for geom in (c.geom1,c.geom2):
                    jac=np.zeros((3,model.nv)); jacrot=np.zeros_like(jac)
                    mujoco.mj_jac(model,data,jac,jacrot,c.pos,int(model.geom_bodyid[geom]))
                    velocities.append(jac@data.qvel)
                contact={'index':index,'geom1':model.geom(int(c.geom1)).name,'geom2':model.geom(int(c.geom2)).name,
                         'dist_m':float(c.dist),'penetration_m':max(0.,-float(c.dist)),
                         'point_world_m':c.pos.tolist(),'normal_world':frame[0].tolist(),
                         'frame_rows_world':frame.tolist(),
                         'normal_relative_velocity_m_s':float(frame[0]@(velocities[1]-velocities[0])),
                         'solref':c.solref.tolist(),'solimp':c.solimp.tolist(),'friction':c.friction.tolist()}
                row['contacts'].append(contact); indexes.append(index)
            mujoco.mj_step2(model,data)
            row.update(qacc=data.qacc.tolist(),qpos_after=data.qpos.tolist(),qvel_after=data.qvel.tolist(),
                       integrated_time_s=float(data.time),warning_counts=data.warning.number.tolist())
            for contact,index in zip(row['contacts'],indexes):
                force=np.zeros(6); mujoco.mj_contactForce(model,data,index,force)
                contact['force_contact_frame_N_Nm']=force.tolist()
                contact['force_world_on_geom2_N']=(np.asarray(contact['frame_rows_world']).T@force[:3]).tolist()
                summary['contact_record_count']+=1
                if summary['first_contact_step'] is None:
                    summary.update(first_contact_step=step,first_contact_time_s=row['sample_time_s'],first_contact=contact.copy())
                penetration=contact['penetration_m']
                if penetration>summary['max_penetration_m']:
                    summary.update(max_penetration_m=penetration,max_penetration_step=step,max_penetration_time_s=row['sample_time_s'])
                if penetration>limit and summary['first_exceedance_step'] is None:
                    summary.update(first_exceedance_step=step,first_exceedance_time_s=row['sample_time_s'])
                summary['max_normal_force_N']=max(summary['max_normal_force_N'],abs(float(force[0])))
            finite=all(np.isfinite(row[k]).all() for k in ('qpos','qvel','qacc','energy','qpos_after','qvel_after'))
            time_valid=bool(np.isclose(row['sample_time_s'],(step-1)*dt,atol=1e-10,rtol=1e-8) and np.isclose(data.time,step*dt,atol=1e-10,rtol=1e-8))
            row['checks']={'state_finite':bool(finite),'time_valid':time_valid,'warnings_zero':not bool(np.any(data.warning.number))}
            valid=all(row['checks'].values())
            if not valid:
                summary['numerically_stable']=False; summary['first_abnormal_step']=step
            file.write(json.dumps(_serial(row),allow_nan=False)+'\n')
            if not valid:
                break
    summary.update(steps=step,total_time_s=float(data.time),warning_counts=data.warning.number.tolist())
    summary['contact_exists']=summary['contact_record_count']>0
    summary['threshold_passed']=bool(summary['contact_exists'] and summary['numerically_stable'] and summary['max_penetration_m']<=limit)
    summary['hashes']={'fixture.xml':sha(fixture),'contact_trace.jsonl':sha(trace)}
    write_evidence(output,'contact_summary.json',_serial(summary))
    return summary

def run_diagnostics(package,output):
    package=Path(package).resolve(); output=Path(output).resolve()
    output.mkdir(parents=True,exist_ok=True)
    root=Path(tempfile.mkdtemp(prefix='diagnostic-',dir=output))
    source_fixture=package/'physics_native.xml'
    reference=json.loads((package/'physics_evidence.json').read_text())['native']
    plan={'diagnostic':True,'package':str(package),'source_fixture_sha256':sha(source_fixture),'cases':CASES,
          'total_time_s':2.,'threshold_m':reference['penetration_limit_m'],
          'normal_mixing':'C/D set same changed parameter on both geoms; priority/solmix/friction unchanged',
          'baseline_gate':'match native max penetration within 1e-10 m and same first-contact step before scanning',
          'B_geometry':'infinite tangent plane at first contact surface point; same probe/state/gravity, no finite mesh curvature'}
    write_evidence(root,'experiment_plan.json',plan)  # 在所有实验之前保存参数组。
    results=[]; plane=None
    for config in CASES:
        directory=root/config['name']; directory.mkdir()
        for relative in compile_resources(package):
            dest=directory/relative; dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(package/relative,dest)
        fixture=directory/'fixture.xml'
        configure_fixture(source_fixture,fixture,config,plane)
        write_evidence(directory,'experiment_config.json',dict(config,diagnostic=True,plane=plane if config.get('geometry') else None))
        try:
            summary=trace_fixture(fixture,directory,total_time=2.,limit=plan['threshold_m'])
            summary['execution_status']='completed'
        except Exception as error:
            summary={'diagnostic':True,'execution_status':'error','error':{'type':type(error).__name__,'message':str(error)}}
            write_evidence(directory,'contact_summary.json',summary)
        record={'name':config['name'],'directory':str(directory),'summary':summary}
        results.append(record)
        files={str(p.relative_to(directory)):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}
        write_evidence(directory,'output_hashes.json',files)
        write_evidence(root,'diagnosis.json',{'diagnostic':True,'directory':str(root),'results':results})
        if config['name']=='baseline':
            matched=summary.get('execution_status')=='completed' and abs(summary['max_penetration_m']-reference['max_penetration_m'])<=1e-10 and summary['first_contact_step']==reference['first_contact_step']
            if not matched:
                raise ValueError('BASELINE_MISMATCH: stop experiments; see '+str(directory))
            c=summary['first_contact']
            normal=np.array(c['normal_world'])*(1 if c['geom1']=='asset_collision' else -1)
            point=np.array(c['point_world_m'])-normal*c['dist_m']/2
            plane={'point_world':point.tolist(),'normal_world':normal.tolist()}
    return {'directory':str(root),'diagnostic':True,'results':results}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=run_diagnostics(args.package,args.output)
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':
    main()
