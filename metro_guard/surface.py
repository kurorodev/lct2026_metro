"""Local roadbed and paired rail hypotheses."""
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
    # The dominant low surface may already be the rail head when it has many
    # returns. Include it, but require lateral peaks over the floor background.
    low = section[(section[:,2]>floor-0.08)&(section[:,2]<floor+0.8)]
    edges = np.arange(center-2.0,center+2.051,0.05)
    hist,_=np.histogram(low[:,1],bins=edges)
    minimum_peak=max(4.,1.8*float(np.median(hist)))
    possibilities=[]
    gap_min=int(np.ceil((config.rail_gauge-config.rail_gauge_tolerance)/0.05))
    gap_max=int(np.floor((config.rail_gauge+config.rail_gauge_tolerance)/0.05))
    for i in range(len(hist)):
        if hist[i]<minimum_peak: continue
        for j in range(i+gap_min,min(i+gap_max+1,len(hist))):
            middle=(edges[i]+edges[j]+0.05)/2
            if hist[j]<minimum_peak or abs(middle-center)>0.65: continue
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

