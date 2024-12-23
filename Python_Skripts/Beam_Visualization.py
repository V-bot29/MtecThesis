from data_handling import load_data, save_data
import matplotlib.pyplot as plt
import numpy as np
import cv2
from tkinter import filedialog
from scipy.spatial import ConvexHull
from matplotlib.widgets import Slider
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression
from matplotlib.patches import Ellipse
from scipy.interpolate import griddata
from scipy.spatial.transform import Rotation as R

def create_slices(data):
    # Sort Measurment Points by x coordinate 
    # reverse=True because x coordinates are descending <0
    sorted_measurements = sorted(data["Measurements"].items(), key=lambda item: item[1]["Measurement_point"][0], reverse=True)
    
    last_x = None
    last_measurement_id = 0
    slice_index = 1 # Start with slice 1
    
    current_slice = {}

    for measurement_id, measurement in sorted_measurements:
        #measurement = data["Measurements"][str(measurement_id)]
        point = measurement["Measurement_point"]
        current_x = point[0] # slice at different x coordinates
        

        if last_x is None:
            last_x = current_x # for first iteration

        if current_x != last_x:
            # Store the current slice
            data["Slices"][str(slice_index)] = current_slice
            slice_index += 1
            current_slice = {}

        current_slice[measurement_id] = measurement
        last_x = current_x
        last_measurement_id = measurement_id

    # Store the last slice
    if current_slice:
        data["Slices"][str(slice_index)] = current_slice

    return data

def create_heatmap(points, sum_values, data):
    
    # Convert points to numpy array for easier manipulation
    points = np.array(points)
    sum_values = np.array(sum_values)

    if len(points[0] > 3):
        points = points[:, 1:]  # Remove the first column
   
    # Determine the size of the grid
    grid_size = data['3D']['grid_size'] # [x, y, z]
    step_size = data['3D']['step_size'] # [x, y, z]

    num_elements_y = int(grid_size[2] / step_size[2])
    num_elements_x = int(grid_size[1] / step_size[1])

    x_min = int(-grid_size[1] / 2)
    x_max = int(grid_size[1] / 2)
    y_min = int(-grid_size[2] / 2)
    y_max = int(grid_size[2] / 2)

    x,y = np.meshgrid(np.linspace(x_min, x_max, num_elements_x), np.linspace(y_min, y_max, num_elements_y))
    
    z = griddata(points, sum_values, (x, y), method='nearest')
    
    heatmap_extent = [x_min, x_max, y_min, y_max]

    heatmap = z
    #heatmap = [z, extent]

    return heatmap, heatmap_extent

def detect_beam_points(points, sum_values, treshhold = 3):
    beam_points = []
    beam_sum_values = []
    for i, sum in enumerate(sum_values):
        if sum > treshhold:
            # assume sum>3 is enough for a point to be part of the beam
            beam_points.append(points[i])
            beam_sum_values.append(sum)

    return beam_points, beam_sum_values

def select_edge_points(beam_points):
    # Use ConvexHull to find the outermost points
    hull = ConvexHull(beam_points) #TODO research ConvexHull documentation
    edge_points = beam_points[hull.vertices]

    return edge_points, hull

def extract_slice_data(slice):
    points = []
    sum_values = []
    # extract the points and sum values from the slice
    for measurement_id in slice:
        point = slice[measurement_id]["Measurement_point"]
        sum = slice[measurement_id]["Signal_sum"]
        points.append(point)
        sum_values.append(sum)

    return points, sum_values

def find_slice_beam_center(points, sum_values):
    # Find the center of the beam in the slice
    # Weigh the points by their sum values

    # Convert points and sum_values to numpy arrays if they are not already
    points = np.array(points)
    sum_values = np.array(sum_values)
    exp_weights = sum_values**2  # Square the sum values to emphasize the importance of the points
    # Calculate the weighted sum of the points
    weighted_sum = np.sum(points * exp_weights[:, np.newaxis], axis=0)

    # Calculate the total sum of the sum values
    total_sum = np.sum(exp_weights)

    # Calculate the weighted average (beam center)
    beam_center = weighted_sum / total_sum
    #print(f'Beam center: {beam_center}')

    return beam_center

def analyze_slice_2D(slice, data):

    points, sum_values = extract_slice_data(slice)
    heatmap, heatmap_extent = create_heatmap(points, sum_values, data)
    
    # First find the beam center
    beam_center = find_slice_beam_center(points, sum_values)  
    # Then use the beam center to find the beam points with w(z)
    beam_points, beam_sum_values = detect_beam_points(points, sum_values)
    beam_points = np.array(beam_points)
    beam_sum_values = np.array(beam_sum_values)
    beam_points_2D = np.array(beam_points)[:, 1:]  # Remove the first column


    edge_points_2D, hull_2D = select_edge_points(beam_points_2D)

    slice_data = {
        'points': points,
        'sum_values': sum_values,
        'beam_center': beam_center,
        'beam_points': beam_points,
        'beam_sum_values': beam_sum_values,
        'beam_points_2D': beam_points_2D,
        'edge_points_2D': edge_points_2D,
        'hull_2D_vertices': hull_2D.vertices,
        'hull_2D_simplices': hull_2D.simplices,
        'heatmap': heatmap,
        'heatmap_extent': heatmap_extent
        }

    return slice_data

def calculate_beam_trajectory_LR(center_points):
    # Fit a line to the center_points from the center of the first beam slice
    start_point = center_points[0]
    start_point = np.array([0, start_point[1], start_point[2]])

    # Shift the points to be relative to the start point
    shifted_points = center_points - start_point

    # Perform linear regression on the shifted points
    X = shifted_points[:, 0].reshape(-1, 1)  # Independent variable (x-axis)
    Y = shifted_points[:, 1]  # Dependent variable (y-axis)
    Z = shifted_points[:, 2]  # Dependent variable (z-axis)

    # Fit linear regression models
    reg_y = LinearRegression().fit(X, Y)
    reg_z = LinearRegression().fit(X, Z)

    # Get the coefficients (slopes) and intercepts
    slope_y = reg_y.coef_[0]
    #intercept_y = reg_y.intercept_
    slope_z = reg_z.coef_[0]
    #intercept_z = reg_z.intercept_

    # Define the trajectory vector
    trajectory_vector = np.array([1, slope_y, slope_z])

    # Invert the trajectory vector 
    trajectory_vector = -trajectory_vector

    # Normalize the trajectory vector
    trajectory_vector = trajectory_vector / np.linalg.norm(trajectory_vector)

    return trajectory_vector

def calculate_angles(trajectory):
    # Normalize the trajectory vector
    trajectory = trajectory / np.linalg.norm(trajectory)

    # Extract the components of the trajectory vector
    x_component = trajectory[0]
    y_component = trajectory[1]
    z_component = trajectory[2]

    # Calculate the angles between the trajectory vector components and the respective axes
    # TODO: check angle_x
    angle_x = np.arctan2(np.abs(x_component), np.sqrt(y_component**2 + z_component**2))
    angle_y = np.arctan2(np.abs(y_component), np.sqrt(x_component**2 + z_component**2))
    angle_z = np.arctan2(np.abs(z_component), np.sqrt(x_component**2 + y_component**2))

    '''
    # Convert the angles from radians to degrees
    angle_x = np.degrees(angle_x)
    angle_y = np.degrees(angle_y)
    angle_z = np.degrees(angle_z)
    '''
    
    angles = np.degrees(np.array([angle_x, angle_y, angle_z]))

    return angles

def create_beam_approximation(data):
    slices = data['Visualization']['Slices']
    first_slice = slices['Slice_1']
    last_slice = slices[f'Slice_{len(slices)+1}']

    ellipse = fit_ellipse(first_slice['edge_points_2D'])
    # TODO extrapolate

def fit_ellipse(edge_points): # TODO delete
    # Perform PCA on the edge points
    pca = PCA(n_components=2)
    pca.fit(edge_points)

    # Get the center of the ellipse
    center = np.mean(edge_points, axis=0)

    # Get the lengths of the semi-major and semi-minor axes
    axes_lengths = np.sqrt(pca.explained_variance_)

    # Get the angle of rotation of the ellipse
    angle = np.degrees(np.arctan2(pca.components_[0, 1], pca.components_[0, 0]))

    # create the ellipse
    ellipse = Ellipse(xy=center, width=2*axes_lengths[0], height=2*axes_lengths[1], angle=angle, edgecolor='blue', facecolor='none')
   
    return ellipse

def process_slices(data):
    slices = data['Slices']
    all_beam_points = []
    all_beam_sum_values = []
    all_center_points = []
    
    data['Visualization'] = {}
    data['Visualization']['Slices'] = {}

    # Sort the keys in ascending order
    sorted_keys = sorted(slices.keys(), key=int)

    for key in sorted_keys:
        slice = slices[key]

        slice_data = analyze_slice_2D(slice, data)

        data['Visualization']['Slices'][f'Slice_{key}'] = slice_data
     
        beam_sum_values = slice_data['beam_sum_values']
        beam_center = slice_data['beam_center']
        beam_points = slice_data['beam_points']

        all_center_points.append(beam_center)
        all_beam_points.append(beam_points)
        all_beam_sum_values.extend(beam_sum_values)

    all_center_points = np.vstack(all_center_points)
    all_beam_sum_values = np.vstack(all_beam_sum_values)
    all_beam_points = np.vstack(all_beam_points)
    edge_points, hull = select_edge_points(all_beam_points)
    
    data['Visualization']['Beam_Models'] = {}

    data['Visualization']['Beam_Models']['Measured_Beam'] = {
        'beam_points': all_beam_points,
        'beam_sum_values': all_beam_sum_values,
        'center_points': all_center_points,
        'edge_points': edge_points,   
        # 'hull': hull, not saved because not hdf5 compatible
        'hull_vertices': hull.vertices,
        'hull_simplices': hull.simplices,
    }

    # TODO maybe move trajectory and angles to a separate file?
    trajectory = calculate_beam_trajectory_LR(all_center_points) 
    angles = calculate_angles(trajectory)
    
    data['Visualization']['Beam_Models']['Measured_Beam']['trajectory'] = trajectory
    data['Visualization']['Beam_Models']['Measured_Beam']['angles'] = angles
    
    # Rotate the beam to align with the x-axis
    beam = data['Visualization']['Beam_Models']['Measured_Beam']
    beam = rotate_beam(beam, angles)

    data['Visualization']['Beam_Models']['Rotated_Beam'] = beam

    return data    

def rotate_beam(beam, angles):
    # pass the beam dictionary

    # get the rotation matrix
    desired_angles = np.array([90, 0, 0]) # desired trj = [1, 0, 0]
    angles_to_rotate = desired_angles - angles
    rotation = R.from_euler('xyz', angles_to_rotate, degrees=True)

    # rotate the beam points
    rotated_beam = {}
    rotated_beam['beam_points'] = rotation.apply(beam['beam_points'])
    rotated_beam['center_points'] = rotation.apply(beam['center_points'])
    rotated_beam['edge_points'] = rotation.apply(beam['edge_points'])
    rotated_beam['trajectory'] = rotation.apply(beam['trajectory'])
    rotated_beam['angles'] = desired_angles
    rotated_beam['hull_simplices'] = beam['hull_simplices']
    rotated_beam['hull_vertices'] = beam['hull_vertices']

    return rotated_beam

def plot_slice(data):
    
    # Create the figure and axes
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    plt.subplots_adjust(left=0.1, bottom=0.25)

    # Plot the initial heatmap
    heatmap = data['Visualization']['Slices']['Slice_1']['heatmap']
    extent = data['Visualization']['Slices']['Slice_1']['heatmap_extent']

    heatmap_plot = ax1.imshow(heatmap, extent=extent,cmap='hot', interpolation='nearest')
    fig.colorbar(heatmap_plot, ax=ax1, label='Signal Sum')
    
    #ax1.invert_yaxis()  # invert y axis 
    ax1.set_title('Heatmap')
    ax1.set_xlabel('X Coordinate')
    ax1.set_ylabel('Y Coordinate')
    
    ax2.set_title('2D Edge Points')
    ax2.set_xlabel('X Coordinate')
    ax2.set_ylabel('Y Coordinate')
    ax2.set_xlim(-3, 3)
    ax2.set_ylim(-3, 3)

    # Plot the beam points
    beam_points = data['Visualization']['Slices']['Slice_1']['beam_points_2D']
    edge_points = data['Visualization']['Slices']['Slice_1']['edge_points_2D']

    ax2.scatter(beam_points[:, 0], beam_points[:, 1], c='red', s=1)
    ax2.scatter(edge_points[:, 0], edge_points[:, 1], c='green', s=5)

    # Plot the convex hull
    hull_simplices = data['Visualization']['Slices']['Slice_1']['hull_2D_simplices']
    
    # plot the ellipse
    ellipse = fit_ellipse(edge_points)
    ax2.add_patch(ellipse)

    for simplex in hull_simplices:
        ax2.plot(beam_points[simplex, 0], beam_points[simplex, 1], 'k-')
        # TODO test simply plotting the edge points
    
    # Create a slider for changing the slice
    slices = data['Slices']
    ax_slider = plt.axes([0.1, 0.1, 0.8, 0.03], facecolor='lightgoldenrodyellow')
    slice_slider = Slider(ax_slider, 'Slice', 1, max(int(key)for key in slices.keys()), valinit=0, valstep=1)

    # Update function for the slider
    def update(val):
        slices = data['Visualization']['Slices']
        slice_index = int(slice_slider.val)
        current_slice = slices[f'Slice_{slice_index}']

        # Update heatmap
        heatmap_plot.set_data(current_slice['heatmap'])

        # Update beam points and convex hull
        ax2.clear()
        ax2.scatter(current_slice['beam_points_2D'][:, 0], current_slice['beam_points_2D'][:, 1], c='red', s=1)
        ax2.scatter(current_slice['edge_points_2D'][:, 0], current_slice['edge_points_2D'][:, 1], c='green', s=5)
        for simplex in current_slice['hull_2D_simplices']:
            ax2.plot(current_slice['beam_points_2D'][simplex, 0], current_slice['beam_points_2D'][simplex, 1], 'k-')
       
        # plot the ellipse
        edge_points = current_slice['edge_points_2D']
        ellipse = fit_ellipse(edge_points)
        ax2.add_patch(ellipse)
       
        ax2.set_title('2D Edge Points')
        ax2.set_xlabel('X Coordinate')
        ax2.set_ylabel('Y Coordinate')

        grid_size = data['3D']['grid_size']
        ax2.set_xlim(-grid_size[1] /2, grid_size[1] / 2)
        ax2.set_ylim(-grid_size[2] / 2, grid_size[2] / 2)

        fig.canvas.draw_idle()

    # Connect the slider to the update function
    slice_slider.on_changed(update)

    plt.show()

def plot_beam(data, beam_model='Measured_Beam'):

    # Create a new figure for the 3D plot
    fig_3d = plt.figure()
    ax_3d = fig_3d.add_subplot(111, projection='3d')

    ax_3d.set_title('3D Edge Points')
    ax_3d.set_xlabel('X')
    ax_3d.set_ylabel('Y')
    ax_3d.set_zlabel('Z')

    grid_size = data['3D']['grid_size'] 
    grid_size[1] += 2
    grid_size[2] += 2
    grid_size[0] += 2

    ax_3d.set_xlim(-grid_size[0],1)
    ax_3d.set_ylim(-grid_size[1]/2, grid_size[1]/2)
    ax_3d.set_zlim(-grid_size[2]/2, grid_size[2]/2)

    ax_3d.set_box_aspect([grid_size[1], grid_size[1], grid_size[2]])

    # Plot Points 
    all_beam_points = data['Visualization']['Beam_Models'][beam_model]['beam_points']
    edge_points = data['Visualization']['Beam_Models'][beam_model]['edge_points']
    center_points = data['Visualization']['Beam_Models'][beam_model]['center_points']

    #ax_3d.scatter(all_beam_points[:, 0], all_beam_points[:, 1], all_beam_points[:, 2], c='red', s=1, label='Beam Points')
    #ax_3d.scatter(edge_points[:, 0], edge_points[:, 1], edge_points[:, 2], c='green', s=5, label = 'Edge Points')
    ax_3d.scatter(center_points[:, 0], center_points[:, 1], center_points[:, 2], c='blue', s=5, label='Center Points')

    # Plot the convex hull
    hull_simplices = data['Visualization']['Beam_Models'][beam_model]['hull_simplices']
    if hull_simplices is not None:
        ax_3d.plot_trisurf(all_beam_points[:, 0], all_beam_points[:, 1], all_beam_points[:, 2], triangles=hull_simplices, color='cyan', alpha=0.5, edgecolor='black', label='Convex Hull')

    # Plot the trajectory
    trajectory = data['Visualization']['Beam_Models'][beam_model]['trajectory']

    start_point = center_points[0]
    start_point = np.array([0, start_point[1], start_point[2]]) 


    # Plot the trajectory vector as an arrow
    ax_3d.quiver(start_point[0], start_point[1], start_point[2],
                trajectory[0], trajectory[1], trajectory[2],
                length=3, color='b', label='Trajectory Vector')

    ax_3d.legend()

    plt.show()
    

if __name__ == "__main__":

    file_path = r'C:/Users/Valen/Documents/Git-Repositorys/MtecThesis/Python_Skripts/Experiment_data/01TSPDKtube_good_inversed_slices.h5'
    data = load_data(file_path) 

    data['Visualization'] = {}
    process_slices(data)
    
    plot_slice(data)
    plot_beam(data, beam_model='Measured_Beam')
    plot_beam(data, beam_model='Rotated_Beam')
    print(data['Visualization']['Beam_Models']['Measured_Beam']['trajectory'])
    print(data['Visualization']['Beam_Models']['Rotated_Beam']['trajectory'])
    
    '''
    folder_path = r'C:/Users/Valen/Documents/Git-Repositorys/MtecThesis/Python_Skripts/Experiment_data'
    save_data(folder_path, data, '01TSPDKtube_now_with_visualization.h5')
    # save once to add Visualization to the data
    '''
   