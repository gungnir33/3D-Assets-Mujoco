"""公开工程接触约定；不是材料测量，不对宿主或机器人作安全保证。"""
import copy
import xml.etree.ElementTree as ET

ENGINEERING_SOLREF=(.006,1.)
ENGINEERING_SOLIMP=(.9,.95,.001,.5,2.)

def contact_attributes(profile):
    if profile=='preserve':
        return {}
    if profile!='engineering_static_v1':
        raise ValueError('unknown contact profile')
    return {'solref':' '.join(map(str,ENGINEERING_SOLREF)),
            'solimp':' '.join(map(str,ENGINEERING_SOLIMP))}

def profile_manifest(profile):
    return {'id':profile,'source':'explicit_project_engineering_convention_not_measured_material',
            'scope':'static+hull' if profile!='preserve' else 'unchanged_legacy_behavior',
            'counterparty_contract':'same_parameters_on_both_geoms_no_priority_override',
            'parameters':contact_attributes(profile),
            'users':{'asset_collision':['model.xml','scene.xml','contact_scene.xml'],
                     'ground':['scene.xml','contact_scene.xml'],'probe':['contact_scene.xml']} if profile!='preserve' else {},
            'runtime_resolution_manifest':'contact_result_manifest.json',
            'application_force_limit':'not_specified','material_calibration':'not_performed',
            'robot_contact_safety':'not_validated','host_integration':'pending'}

def contact_scene(scene,size,profile):
    """导出阶段构造公开演示/验收场景；探针与历史工况完全一致。"""
    root=copy.deepcopy(scene)
    radius=max(size)*.025
    initial=[0,0,size[2]+max(size)*.2+radius]
    body=ET.SubElement(root.find('worldbody'),'body',name='probe_body',pos=' '.join(map(str,initial)))
    ET.SubElement(body,'freejoint')
    inertia=.4*.1*radius**2
    ET.SubElement(body,'inertial',pos='0 0 0',mass='.1',diaginertia=f'{inertia} {inertia} {inertia}')
    ET.SubElement(body,'geom',name='probe',type='sphere',size=str(radius),mass='.1',**contact_attributes(profile))
    return root
