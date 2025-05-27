import numpy as np

def convert_2d_to_3d(pt_2d, normal_vector, x_direction_vector, origin, units="m"):
    """
    Converts a 2D point [x, y] to 3D coordinates (x_3d, y_3d, z_3d)
    based on a plane defined by its normal vector, x-direction vector, and origin.
    Handles unit conversion of input coordinates to meters.

    Args:
        pt_2d: A list or tuple representing the 2D coordinates [x, y].
        normal_vector: A list or numpy array representing the plane's normal vector [x, y, z].
        x_direction_vector: A list or numpy array representing the plane's x-direction vector [x, y, z].
        origin: A list or numpy array representing the plane's origin point [x, y, z].
        units: The units of the input coordinates (pt_2d). 
               Defaults to "m" (meters). 
               Supported units: "in" (inches), "mm" (millimeters), "m" (meters), "ft" (feet).

    Returns:
        A string representing the 3D coordinates [x_3d, y_3d, z_3d] in meters, comma-separated.
    """

    # Unit conversion factors to meters
    unit_factors = {
        "in": 0.0254,
        "mm": 0.001,
        "m": 1.0,
        "ft": 0.3048
    }

    x_2d, y_2d = pt_2d
    # Convert x_2d and y_2d to meters
    x_2d_m = x_2d * unit_factors[units]
    y_2d_m = y_2d * unit_factors[units]

    # Convert to numpy arrays for vector operations
    normal_vector = np.array(normal_vector)
    x_direction_vector = np.array(x_direction_vector)
    origin = np.array(origin)

    # Calculate the 3D point (using converted coordinates)
    point_3d = origin + x_2d_m * x_direction_vector + y_2d_m * np.cross(normal_vector, x_direction_vector)
    point_3d_str = ",".join([str(coord) for coord in point_3d])  

    return point_3d_str  # Return as string