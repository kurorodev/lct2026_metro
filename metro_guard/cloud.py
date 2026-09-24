"""PointCloud2 decoding without assuming packed XYZ or a specific ROS driver."""
import numpy as np

FIELD_TYPES = {1:'i1', 2:'u1', 3:'i2', 4:'u2', 5:'i4', 6:'u4', 7:'f4', 8:'f8'}


def decode(msg):
    if msg.height < 1 or msg.width < 1:
        return np.empty((0, 3), dtype=np.float32)
    if msg.point_step <= 0 or msg.row_step < msg.width * msg.point_step:
        raise ValueError('Invalid PointCloud2 stride')
    if len(msg.data) != msg.row_step * msg.height:
        raise ValueError('PointCloud2 payload length does not match row_step * height')
    names, formats, offsets = [], [], []
    for field in msg.fields:
        if field.datatype not in FIELD_TYPES or field.count < 1:
            raise ValueError('Unsupported PointField datatype or count')
        dtype = np.dtype(('>' if msg.is_bigendian else '<') + FIELD_TYPES[field.datatype])
        if field.offset < 0 or field.offset + dtype.itemsize*field.count > msg.point_step:
            raise ValueError('PointField exceeds point_step')
        names.append(field.name)
        formats.append(dtype if field.count == 1 else (dtype, (field.count,)))
        offsets.append(field.offset)
    if len(set(names)) != len(names):
        raise ValueError('Duplicate PointField names')
    if not {'x','y','z'}.issubset(names):
        raise ValueError('Missing XYZ fields')
    for field in msg.fields:
        if field.name in ('x','y','z') and (field.count != 1 or field.datatype not in (7,8)):
            raise ValueError('XYZ must be scalar floating point fields')
    dtype = np.dtype(dict(names=names, formats=formats, offsets=offsets, itemsize=msg.point_step))
    data = memoryview(msg.data)
    array = np.ndarray((msg.height,msg.width), dtype=dtype, buffer=data,
                       strides=(msg.row_step,msg.point_step))
    return np.column_stack([array[n].ravel() for n in ('x','y','z')]).astype(np.float32, copy=False)


def canonical(xyz, forward_axis='-y'):
    # Right-handed frame: forward, left, up. No unverified mounting translation.
    if forward_axis == '-y':
        return xyz[:, [1,0,2]] * np.array([-1,1,1], dtype=np.float32)
    if forward_axis == 'x':
        return xyz.copy()
    if forward_axis == 'y':
        return xyz[:, [1,0,2]] * np.array([1,-1,1], dtype=np.float32)
    if forward_axis == '-x':
        return xyz * np.array([-1,-1,1], dtype=np.float32)
    raise ValueError('forward_axis must be x, -x, y, or -y')
