"""只读接触统计；速度来自积分前，力来自同一步约束求解。"""
import mujoco
import numpy as np


class ContactStatistics:
    def __init__(self):
        self.results = {name: {
            'contact_records': 0, 'normal_impulse_N_s': 0.,
            'world_impulse_on_probe_N_s': [0., 0., 0.],
            'peak_normal_force_N': 0., 'max_penetration_m': 0.,
            'first_contact_step': None, 'last_contact_step': None,
            'first_contact_normal_velocity_m_s': None,
            'max_separating_speed_during_contact_m_s': 0.,
            'first_resolved_contact': None, 'contact_intervals': [],
        } for name in ('asset_probe', 'ground_probe')}

    def sample(self, model, data, qvel_before, step, sample_time, dt):
        records = []
        for index, contact in enumerate(data.contact):
            names = [model.geom(int(i)).name for i in (contact.geom1, contact.geom2)]
            if set(names) == {'asset_collision', 'probe'}:
                key = 'asset_probe'
            elif set(names) == {'ground', 'probe'}:
                key = 'ground_probe'
            else:
                continue
            frame = np.asarray(contact.frame).reshape(3, 3)
            velocities = []
            for geom in (contact.geom1, contact.geom2):
                jac = np.zeros((3, model.nv))
                mujoco.mj_jac(model, data, jac, np.zeros_like(jac), contact.pos,
                              int(model.geom_bodyid[geom]))
                velocities.append(jac @ qvel_before)
            speed = float(frame[0] @ (velocities[1] - velocities[0]))
            force = np.zeros(6)
            mujoco.mj_contactForce(model, data, index, force)
            world = (frame.T @ force[:3]) * (1 if names[1] == 'probe' else -1)
            record = {
                'pair': key, 'index': index, 'geom1': names[0], 'geom2': names[1],
                'dist_m': float(contact.dist), 'penetration_m': max(0., -float(contact.dist)),
                'point_world_m': contact.pos.tolist(), 'normal_world': frame[0].tolist(),
                'normal_relative_velocity_m_s': speed,
                'force_contact_frame_N_Nm': force.tolist(),
                'force_world_on_probe_N': world.tolist(),
                **{k: getattr(contact, k).tolist() for k in ('solref', 'solimp', 'friction')},
            }
            records.append(record)
            stats = self.results[key]
            if stats['first_contact_step'] is None:
                stats.update(first_contact_step=step, first_contact_time_s=sample_time,
                             first_contact_normal_velocity_m_s=speed,
                             first_resolved_contact={k: record[k] for k in ('solref', 'solimp', 'friction')})
            previous = stats['last_contact_step']
            if previous is None or step > previous + 1:
                stats['contact_intervals'].append({'first_step': step, 'last_step': step})
            stats['contact_intervals'][-1]['last_step'] = step
            stats.update(last_contact_step=step, last_contact_time_s=sample_time,
                         last_contact_normal_velocity_m_s=speed)
            stats['contact_records'] += 1
            stats['normal_impulse_N_s'] += float(force[0]) * dt
            stats['world_impulse_on_probe_N_s'] = (
                np.asarray(stats['world_impulse_on_probe_N_s']) + world * dt).tolist()
            if float(force[0]) > stats['peak_normal_force_N']:
                stats.update(peak_normal_force_N=float(force[0]), peak_normal_force_step=step)
            if record['penetration_m'] > stats['max_penetration_m']:
                stats.update(max_penetration_m=record['penetration_m'], max_penetration_step=step)
            stats['max_separating_speed_during_contact_m_s'] = max(
                stats['max_separating_speed_during_contact_m_s'], speed)
        return records
