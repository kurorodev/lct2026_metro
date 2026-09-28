from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    geometry_model: str = 'baseline'
    forward_axis: str = '-y'
    min_range: float = 2.0
    max_range: float = 220.0
    half_width: float = 1.45
    underbody_half_width: float = 0.85
    full_width_height: float = 0.8
    boundary_margin: float = 0.0
    min_height: float = 0.28
    max_height: float = 3.2
    initial_center: float = 0.0
    lidar_height: Optional[float] = None
    nominal_wall_offset: float = 2.5
    rail_gauge: float = 1.52
    rail_gauge_tolerance: float = 0.12
    bin_size: float = 5.0
    max_center_slope: float = 0.15
    min_ground_points: int = 24
    min_cluster_points: int = 5
    min_cluster_extent: float = 0.12
    confirm_frames: int = 3
    max_frame_gap: float = 0.5
    max_relative_speed: float = 35.0
    max_candidates: int = 100

    def validate(self):
        if self.forward_axis not in ('x','-x','y','-y'):
            raise ValueError('Invalid forward_axis')
        if self.geometry_model not in ('baseline','rail_guided'):
            raise ValueError('geometry_model must be baseline or rail_guided')
        for name,value in asdict(self).items():
            if name == 'lidar_height' and value is None:
                continue
            if name not in ('forward_axis','geometry_model') and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value)):
                raise ValueError('Invalid numeric parameter: '+name)
        for name in ('min_ground_points','min_cluster_points','confirm_frames','max_candidates'):
            if not isinstance(getattr(self,name),int) or getattr(self,name) < 1:
                raise ValueError(name+' must be a positive integer')
        if not 0 < self.min_range < self.max_range <= 1000:
            raise ValueError('Invalid detection range')
        if self.lidar_height is not None and (self.lidar_height <= 0 or self.geometry_model != 'rail_guided'):
            raise ValueError('lidar_height must be positive and requires rail_guided geometry')
        if not 0 < self.min_height < self.max_height or not 0 < self.underbody_half_width <= self.half_width < self.nominal_wall_offset:
            raise ValueError('Invalid clearance envelope')
        if not 0 <= self.boundary_margin < self.underbody_half_width:
            raise ValueError('boundary_margin must be nonnegative and smaller than underbody_half_width')
        if not 0 < self.rail_gauge_tolerance < self.rail_gauge:
            raise ValueError('Invalid rail gauge tolerance')
        if any(getattr(self,n) <= 0 for n in ('full_width_height','bin_size','rail_gauge','rail_gauge_tolerance','max_center_slope','min_cluster_extent','max_frame_gap','max_relative_speed')):
            raise ValueError('Thresholds must be positive')
        return self

    @classmethod
    def load(cls, path=None):
        return cls(**(json.loads(Path(path).read_text()) if path else {})).validate()

    def to_dict(self):
        return asdict(self)
