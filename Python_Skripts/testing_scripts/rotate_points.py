import numpy as np

def normalize(v):
    return v / np.linalg.norm(v)

def get_rotation_matrix(vec1, vec2):
    """ Find the rotation matrix that aligns vec1 to vec2
    :param vec1: A 3d "source" vector
    :param vec2: A 3d "destination" vector
    :return mat: A transform matrix (3x3) which when applied to vec1, aligns it with vec2.
    """
    a, b = normalize(vec1), normalize(vec2)
    v = np.cross(a, b)
    c = np.dot(a, b)
    s = np.linalg.norm(v)
    kmat = np.array([[0, -v[2], v[1]],
                     [v[2], 0, -v[0]],
                     [-v[1], v[0], 0]])
    rotation_matrix = np.eye(3) + kmat + kmat.dot(kmat) * ((1 - c) / (s ** 2))
    return rotation_matrix

def rotate_points(points, rotation_matrix):
    # Rotate a point by a given rotation matrix
    # Apply the rotation matrix to the old trajectory vector
    rotated_point = np.dot(points, rotation_matrix.T)

    return rotated_point

def rotate_alpha_beta(vector, alpha, beta):
    # Convert angles from degrees to radians
    alpha = np.radians(alpha)
    beta = np.radians(beta)

    # Rotation matrix around the x-axis
    R_x = np.array([[1, 0, 0],
                    [0, np.cos(alpha), -np.sin(alpha)],
                    [0, np.sin(alpha), np.cos(alpha)]])

    # Rotation matrix around the y-axis
    R_y = np.array([[np.cos(beta), 0, np.sin(beta)],
                    [0, 1, 0],
                    [-np.sin(beta), 0, np.cos(beta)]])

    # Apply the rotations
    rotated_vector = np.dot(R_y, np.dot(R_x, vector))

    return rotated_vector

if __name__ == "__main__":

    trj = np.array([-0.9727202, -0.09483338, 0.21171216])
    desired_trj = np.array([1, 0, 0])

    rotation_matrix = get_rotation_matrix(trj, desired_trj)
    new_trj = rotate_points(trj, rotation_matrix)

    print("Old trajectory vector:\n", trj)
    print("New trajectory vector (aligned with x-axis):\n", new_trj)
