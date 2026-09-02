import numpy as np

def generate_pe_addresses_and_times(T, iteration_vectors, computation_duration=1):
    pe_addresses = []
    spatial_coords = []

    #print("iteration_vectors",iteration_vectors)
    for I in iteration_vectors:
        I = np.array(I)
        S = T.dot(I)
        spatial_coord = S[:-1]
        time = S[-1]
        spatial_coords.append(spatial_coord)
        pe_addresses.append({
            'iteration': tuple(I),
            'PE_address': spatial_coord,
            'time': time
        })
     
    spatial_coords_array = np.array(spatial_coords)
    
    #min_coords = spatial_coords_array.min(axis=0)
    #offsets = 1 - min_coords
    
    pe_times = {}

    for entry in pe_addresses:
        spatial_coord = entry['PE_address']
        adjusted_coord = spatial_coord# + offsets
        adjusted_coord = adjusted_coord.astype(int)
        pe_address = tuple(adjusted_coord)

        time = entry['time']
        start_time = time
        end_time = time

        if pe_address not in pe_times:
            pe_times[pe_address] = {'start_time': start_time, 'end_time': end_time}
        else:
            pe_times[pe_address]['start_time'] = min(pe_times[pe_address]['start_time'], start_time)
            pe_times[pe_address]['end_time'] = max(pe_times[pe_address]['end_time'], end_time)

    unique_pe_addresses = set(pe_times.keys())

    return unique_pe_addresses, pe_times

def get_edge_points_with_times(points, vector, pe_times=None):
    # Normalize the vector
    vector = np.array(vector, dtype=float)
    vector_norm = np.linalg.norm(vector)
    if vector_norm == 0:
        raise ValueError("The direction vector cannot be zero.")
    vector = vector / vector_norm  # Unit vector in the direction

    # Get the orthogonal vector for 2D case
    orthogonal_vector = np.array([-vector[1], vector[0]])
    orthogonal_vector = orthogonal_vector / np.linalg.norm(orthogonal_vector)

    # Dictionary to hold the minimum point along the vector for each projection
    projection_dict = {}
    for point in points:
        point_array = np.array(point, dtype=float)
        # Project point onto the orthogonal vector
        projection_orth = np.dot(point_array, orthogonal_vector)
        # Round the projection to handle floating-point precision
        projection_orth = round(projection_orth, 6)
        # Project point onto the given vector
        projection_vector = np.dot(point_array, vector)
        # If this projection is not in the dictionary or if it's closer along the vector, update it
        if projection_orth not in projection_dict or projection_vector < projection_dict[projection_orth]['projection_vector']:
            projection_dict[projection_orth] = {
                'point': point,
                'projection_vector': projection_vector
            }
       
    # Extract the points from the dictionary
    edge_points = [value['point'] for value in projection_dict.values()]
    # Sort the edge points for consistent output
    edge_points.sort()

    # Get times for edge points
    edge_times = {}
    if pe_times is not None:
        for point in edge_points:
            if point in pe_times:
                edge_times[point] = pe_times[point]
            else:
                edge_times[point] = {'start_time': None, 'end_time': None}
    else:
        edge_times = {point: {'start_time': None, 'end_time': None} for point in edge_points}

    return edge_points, edge_times

def find_first_occurrence(lst, target):

    for i, sublist in enumerate(lst):
        for j, item in enumerate(sublist):
            if item == target:
                return (i, j)
    return None
