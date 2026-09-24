"""Causal, class-agnostic baseline. Scores express evidence, not probabilities.

No global map or frame-to-frame point subtraction: ego-motion is not available.
The corridor is an estimate and must be validated against train calibration.
"""
import itertools
import time
import numpy as np
from .cloud import canonical
from .config import Config
from .geometry import estimate_corridor
from .baseline_geometry import estimate_corridor as estimate_baseline
from .surface import roadbed_height, rail_pair


NEIGHBORS = tuple(itertools.product((-1,0,1), repeat=3))


def clusters(points, cell_size):
    """Connected occupied voxels; retain point counts and actual, not voxel bounds."""
    if not len(points):
        return []
    grid = np.floor(points / cell_size).astype(np.int32)
    cells, inverse, counts = np.unique(grid, axis=0, return_inverse=True, return_counts=True)
    lookup = {tuple(cell): i for i,cell in enumerate(cells)}
    labels = np.full(len(cells), -1, dtype=np.int32)
    components = []
    for i in range(len(cells)):
        if labels[i] >= 0:
            continue
        label = len(components)
        labels[i] = label
        stack, members = [i], []
        while stack:
            j = stack.pop()
            members.append(j)
            x,y,z = cells[j]
            for dx,dy,dz in NEIGHBORS:
                k = lookup.get((x+dx,y+dy,z+dz))
                if k is not None and labels[k] < 0:
                    labels[k] = label
                    stack.append(k)
        components.append(members)
    point_labels = labels[inverse]
    order = np.argsort(point_labels, kind='stable')
    lengths = np.bincount(point_labels, minlength=len(components))
    groups = np.split(order, np.cumsum(lengths)[:-1])
    return [points[g] for g in groups]


class Detector:
    def __init__(self, config=None):
        self.config = (config or Config()).validate()
        self.last_stamp = None
        self.tracks = []
        self.next_id = 1

    def corridor(self, p):
        estimator=estimate_corridor if self.config.geometry_model=='rail_guided' else estimate_baseline
        return estimator(p, self.config)

    def process(self, xyz, stamp):
        started = time.perf_counter()
        c = self.config
        if not np.isfinite(stamp):
            raise ValueError('Nonfinite timestamp')
        gap = self.last_stamp is not None and (stamp<=self.last_stamp or stamp-self.last_stamp>c.max_frame_gap)
        dt = stamp-self.last_stamp if self.last_stamp is not None and not gap else 0.1
        if gap:
            self.tracks = []
        self.last_stamp = stamp
        if xyz.ndim != 2 or xyz.shape[1] != 3:
            raise ValueError('Expected Nx3 points')
        valid = np.isfinite(xyz).all(axis=1)&np.any(xyz!=0,axis=1)
        p = canonical(xyz[valid],c.forward_axis)
        p = p[(p[:,0]>=c.min_range)&(p[:,0]<=c.max_range)&(np.abs(p[:,1])<60)&(np.abs(p[:,2])<25)]
        nodes = self.corridor(p) if len(p)>=c.min_ground_points else np.empty((0,5))
        candidates = []
        usable = np.zeros(len(p),dtype=bool)
        if len(nodes)>=3:
            centers = np.interp(p[:,0],nodes[:,0],nodes[:,1])
            floors = np.interp(p[:,0],nodes[:,0],nodes[:,2])
            nearest = np.searchsorted(nodes[:,0],p[:,0]).clip(0,len(nodes)-1)
            previous = (nearest-1).clip(0,len(nodes)-1)
            distance_to_node = np.minimum(np.abs(p[:,0]-nodes[nearest,0]),np.abs(p[:,0]-nodes[previous,0]))
            usable = distance_to_node<=c.bin_size
            relative = p[:,2]-floors
            ceilings=np.interp(p[:,0],nodes[:,0],nodes[:,4])
            half_width=c.underbody_half_width+(c.half_width-c.underbody_half_width)*np.clip(relative/c.full_width_height,0,1)
            mask = usable&(np.abs(p[:,1]-centers)<half_width)&(relative>c.min_height)&(relative<c.max_height)&(p[:,2]<ceilings-0.2)
            q = p[mask]
            # Fixed voxel size keeps component boundaries continuous across ranges.
            for group in clusters(q,0.35):
                lo,hi = group.min(axis=0),group.max(axis=0)
                extent = hi-lo
                if len(group)<c.min_cluster_points or max(extent[1:])<c.min_cluster_extent:
                    continue
                position = (lo+hi)/2
                confidence = float(np.interp(position[0],nodes[:,0],nodes[:,3]))
                local_center=np.interp(group[:,0],nodes[:,0],nodes[:,1])
                local_height=group[:,2]-np.interp(group[:,0],nodes[:,0],nodes[:,2])
                local_width=c.underbody_half_width+(c.half_width-c.underbody_half_width)*np.clip(local_height/c.full_width_height,0,1)
                penetration=local_width-np.abs(group[:,1]-local_center)
                interior_points=int((penetration>c.boundary_margin).sum())
                candidates.append({'min':lo.tolist(),'max':hi.tolist(), 'center':position.tolist(),
                    'distance_m':float(lo[0]), 'points':len(group), 'geometry_support':round(confidence,3),
                    'interior_points':interior_points,'boundary_uncertain':interior_points<c.min_cluster_points,
                    'evidence_score':round(min(1.,len(group)/30.)*min(1.,max(extent[1:])/0.4)*confidence,3)})
        candidates.sort(key=lambda o:o['distance_m'])
        overflow = len(candidates)>c.max_candidates
        candidates = candidates[:c.max_candidates]
        unmatched = set(range(len(self.tracks)))
        for obj in candidates:
            choices = []
            for i in unmatched:
                old = self.tracks[i]
                delta = np.abs(np.array(obj['center'])-old['center'])
                if delta[0]<1.0+c.max_relative_speed*dt and delta[1]<0.8 and delta[2]<0.8:
                    choices.append((float(delta[0]+2*delta[1]+2*delta[2]),i))
            if choices:
                _,idx = min(choices)
                unmatched.remove(idx)
                old = self.tracks[idx]
                obj.update(id=old['id'],hits=old['hits']+1)
            else:
                obj.update(id=self.next_id,hits=1)
                self.next_id+=1
            obj['temporally_confirmed'] = obj['hits']>=c.confirm_frames
            obj['confirmed'] = obj['temporally_confirmed'] and not obj['boundary_uncertain']
        self.tracks = candidates
        confirmed = [o for o in candidates if o['confirmed']]
        reasons = []
        if gap: reasons.append('timestamp_discontinuity')
        if len(nodes)<3: reasons.append('insufficient_corridor_geometry')
        if len(nodes) and float(np.mean(nodes[:,3]))<0.8: reasons.append('ambiguous_corridor_geometry')
        if overflow: reasons.append('candidate_limit_reached')
        if any(o['boundary_uncertain'] for o in candidates): reasons.append('clearance_boundary_uncertainty')
        status = 'obstacle' if confirmed else ('candidate' if candidates else ('unknown' if reasons else 'no_obstacle_observed'))
        elapsed = (time.perf_counter()-started)*1000
        return {'timestamp':float(stamp),'status':status,'obstacle_detected':bool(confirmed),
                'distance_m':min((o['distance_m'] for o in confirmed),default=None),
                'candidate_distance_m':min((o['distance_m'] for o in candidates),default=None),
                'input_points':len(xyz),'valid_points':int(valid.sum()),'roi_points':len(p),
                'geometry_supported_points':int(usable.sum()),
                'geometry_range_m':float(nodes[-1,0]) if len(nodes) else 0.,
                'degraded':bool(reasons),'reasons':reasons,'processing_ms':elapsed,
                'corridor':nodes.tolist(),'objects':candidates},p
