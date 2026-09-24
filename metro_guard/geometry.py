"""Track corridor from local rail evidence and observed side offsets.

Wall distance is learned from the same frame where paired rails are visible.
A platform edge is not assumed to have the radius of a circular tunnel.
"""
import numpy as np

from .surface import rail_pair, roadbed_height


def predict(history, x, column, max_slope):
    if not history:
        raise ValueError('Prediction needs an anchor')
    recent = np.asarray(history[-4:], dtype=float)
    if len(recent) == 1:
        return float(recent[-1, column])
    dx = recent[:, 0] - recent[-1, 0]
    dy = recent[:, column] - recent[-1, column]
    slope = float(np.dot(dx, dy) / max(np.dot(dx, dx), 1e-6))
    slope = float(np.clip(slope, -max_slope, max_slope))
    return float(recent[-1, column] + slope * (x - recent[-1, 0]))


def estimate_corridor(points, config):
    c = config
    indices = np.floor((points[:, 0] - c.min_range) / c.bin_size).astype(int)
    order = np.argsort(indices, kind='stable')
    bins, starts = np.unique(indices[order], return_index=True)
    groups = {int(b): points[g] for b, g in zip(bins, np.split(order, starts[1:]))}
    nodes, rails = [], []
    offsets = [[], []]

    for i in range(int(np.ceil((c.max_range - c.min_range) / c.bin_size))):
        x = c.min_range + (i + 0.5) * c.bin_size
        section = groups.get(i)
        if section is None:
            continue
        center = predict(nodes, x, 1, c.max_center_slope) if nodes else c.initial_center
        ground = section[np.abs(section[:, 1] - center) < c.half_width + 0.4]
        if len(ground) < c.min_ground_points:
            continue
        bed = roadbed_height(ground)
        pair = rail_pair(section, center, bed, c)
        # Do not let a newly observed raised structure produce a vertical jump.
        if pair and rails:
            expected_z = predict(rails, x, 2, 0.12)
            if abs(pair[1] - expected_z) > 0.15:
                pair = None
        if pair:
            center, floor = pair
            rails.append([x, center, floor])
            support = 1.0
        else:
            floor = predict(rails, x, 2, 0.12) if rails else bed
            # Limit extrapolation over changing grade using current roadbed evidence.
            if rails and len(nodes):
                floor = float(np.clip(floor, bed - 0.1, bed + 0.6))
            support = 0.5

        wall = section[(section[:, 2] > floor + 0.6) & (section[:, 2] < floor + 2.6)]
        observed = []
        for side in (-1, 1):
            distance = (wall[:, 1] - center) * side
            values = distance[(distance > c.underbody_half_width) & (distance < 4.5)]
            observed.append(float(np.percentile(values, 25)) if len(values) >= 12 else None)

        if pair:
            for side, distance in enumerate(observed):
                if distance is not None:
                    offsets[side].append(distance)
        else:
            proposals = []
            for index, side in enumerate((-1, 1)):
                distance = observed[index]
                if distance is None:
                    continue
                offset = float(np.median(offsets[index][-6:])) if offsets[index] else c.nominal_wall_offset
                proposal = center + side * (distance - offset)
                if abs(proposal - center) <= c.max_center_slope * c.bin_size:
                    proposals.append(proposal)
            if len(proposals) == 2 and abs(proposals[0] - proposals[1]) < 0.5:
                center = 0.4 * center + 0.6 * float(np.mean(proposals))
                support = 1.0
            elif proposals:
                center = 0.75 * center + 0.25 * min(proposals, key=lambda p: abs(p-center))
                support = 0.5
            else:
                # Prediction still provides candidate search, not evidence of a clear path.
                support = 0.25

        if nodes and abs(floor - nodes[-1][2]) > 0.65:
            continue
        ceiling_points = section[np.abs(section[:, 1] - center) <= c.nominal_wall_offset + 0.25]
        ceiling = float(np.percentile(ceiling_points[:, 2], 98)) if len(ceiling_points) else floor
        nodes.append([x, center, floor, support, ceiling])
    return np.asarray(nodes, dtype=np.float32).reshape(-1, 5)
