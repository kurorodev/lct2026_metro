"""Frozen initial geometry for reproducible comparison with rail-guided geometry."""
import numpy as np


def roadbed_height(ground):
    # A low percentile follows drainage troughs and falsely lifts the rails.
    # Select the dominant low surface, excluding the ceiling and tall obstacles.
    low = float(np.percentile(ground[:,2],8))
    values = ground[(ground[:,2]>=low)&(ground[:,2]<=low+0.6),2]
    edges = np.arange(low,low+0.681,0.08)
    counts,_ = np.histogram(values,bins=edges)
    index = int(np.argmax(counts))
    return float((edges[index]+edges[index+1])/2)


def rail_pair(section, center, floor, config):
    """Optional pair hypothesis; never infer a rail from a single lateral peak."""
    low = section[(section[:,2]>floor+0.15)&(section[:,2]<floor+0.8)]
    edges = np.arange(center-2.0,center+2.051,0.05)
    hist,_=np.histogram(low[:,1],bins=edges)
    possibilities=[]
    gap_min=int(np.ceil((config.rail_gauge-config.rail_gauge_tolerance)/0.05))
    gap_max=int(np.floor((config.rail_gauge+config.rail_gauge_tolerance)/0.05))
    for i in range(len(hist)):
        if hist[i]<4: continue
        for j in range(i+gap_min,min(i+gap_max+1,len(hist))):
            middle=(edges[i]+edges[j]+0.05)/2
            if hist[j]<4 or abs(middle-center)>0.65: continue
            score=min(hist[i],hist[j])/(1+2*abs(middle-center))
            possibilities.append((score,i,j,middle))
    if not possibilities: return None
    _,i,j,middle=max(possibilities)
    heads=[]
    for k in (i,j):
        strip=low[np.abs(low[:,1]-(edges[k]+0.025))<0.06]
        heads.append(float(np.percentile(strip[:,2],80)))
    if abs(heads[0]-heads[1])>0.25: return None
    return float(middle),float(np.mean(heads))


def estimate_corridor(p, config):
    c = config
    nodes = []
    center = c.initial_center
    # Sorted bins avoid scanning the entire cloud for each cross section.
    indices = np.floor((p[:,0]-c.min_range)/c.bin_size).astype(int)
    order = np.argsort(indices, kind='stable')
    bins, starts = np.unique(indices[order], return_index=True)
    groups = {int(b):p[g] for b,g in zip(bins,np.split(order,starts[1:]))}
    last_floor = None
    for i in range(int(np.ceil((c.max_range-c.min_range)/c.bin_size))):
        x = c.min_range+(i+0.5)*c.bin_size
        section = groups.get(i)
        if section is None:
            continue
        # Estimate roadbed first, independently of wall/ceiling density.
        ground = section[(np.abs(section[:,1]-center)<c.half_width+0.4)]
        if len(ground) < c.min_ground_points:
            continue
        floor = roadbed_height(ground)
        wall = section[(section[:,2]>floor+0.6)&(section[:,2]<floor+2.6)]
        left = wall[(wall[:,1]<center-c.half_width)&(wall[:,1]>center-4.0),1]
        right = wall[(wall[:,1]>center+c.half_width)&(wall[:,1]<center+4.0),1]
        proposals = []
        # Use nearest structural wall modes, not the center of a double tunnel.
        if len(left)>=12:
            proposals.append(float(np.percentile(left,75))+c.nominal_wall_offset)
        if len(right)>=12:
            proposals.append(float(np.percentile(right,25))-c.nominal_wall_offset)
        reliable = len(proposals)==2 and abs(proposals[0]-proposals[1])<1.2
        if proposals:
            proposal = float(np.mean(proposals)) if reliable else min(proposals,key=lambda v:abs(v-center))
            change = np.clip(proposal-center,-c.max_center_slope*c.bin_size,c.max_center_slope*c.bin_size)
            center += float(change)*0.7
        # Refresh floor at updated center; reject unphysical jumps, not obstacles.
        ground = section[np.abs(section[:,1]-center)<c.half_width+0.3]
        if len(ground)<c.min_ground_points:
            continue
        floor = roadbed_height(ground)
        if last_floor is not None and abs(floor-last_floor)>0.65:
            continue
        ceiling=float(np.percentile(section[:,2],98))
        nodes.append([x,center,floor,1.0 if reliable else 0.5,ceiling])
        last_floor = floor
    nodes=np.asarray(nodes,dtype=np.float32).reshape(-1,5)
    rails=[]
    for row in nodes:
        section=groups[int(round((float(row[0])-c.min_range)/c.bin_size-0.5))]
        pair=rail_pair(section,float(row[1]),float(row[2]),c)
        if pair is not None:
            rails.append([float(row[0]),pair[0],pair[1]-float(row[2])])
    # Roadbed is not the train running surface. Use paired rail evidence to
    # estimate their height difference; this also avoids alarming on rails.
    if len(rails)>=2:
        rails=np.asarray(rails)
        elevation=float(np.median(rails[:,2]))
        nodes[:,2]+=elevation
        for row in nodes:
            if rails[0,0]-c.bin_size <= row[0] <= rails[-1,0]+c.bin_size:
                rail_center=float(np.interp(row[0],rails[:,0],rails[:,1]))
                row[1]=rail_center
    return nodes

