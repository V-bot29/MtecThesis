from Object3D import Sensor, Hexapod
import numpy as np
import matplotlib.pyplot as plt


def align_center(sensor, hexapod, depth = 0):
    # allign beam to center of sensor recursivly
    resolutions = [0.1, 0.01, 0.001, 0.0001]

    if depth == len(resolutions):
        return True

    step_size = resolutions[depth]

    iterations = 0
    center = 0.5

    aligned = False

    while iterations < 20:
        iterations += 1

        #signal = sensor.get_test_signal() TODO uncomment comments 
        #xpos = signal.xpos
        #ypos = signal.ypos 

        plt.plot(sensor.xpos, sensor.ypos, 'o')

        if sensor.xpos > center+step_size:
            #hexapod.move([-step_size, 0, 0, 0, 0, 0], flag = "relative") # TODO xpos and ypos changes only for testing purposes
            sensor.xpos -= step_size
            
        elif sensor.xpos < center-step_size:
            #hexapod.move([step_size, 0, 0, 0, 0, 0], flag = "relative")
            sensor.xpos += step_size
        
        elif sensor.ypos > center+step_size:
            #hexapod.move([0, 0, -step_size, 0, 0, 0], flag = "relative")
            sensor.ypos -= step_size
            
        elif sensor.ypos < center-step_size:
            #hexapod.move([0, 0, step_size, 0, 0, 0], flag = "relative")
            sensor.ypos += step_size

        else:
            align_center(sensor, hexapod, depth+1)
            aligned = True
            break

    return aligned

def fine_alignment(sensor, hexapod):
    
    aligned = False

    Signal = sensor.get_test_signal() # TODO rename to get_signal
   

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(sensor.xpos, sensor.ypos, 'o')

    ax.set_xlabel('X Position')
    ax.set_ylabel('Y Position')
    ax.set_title('Sensor Output')
    ax.grid(True)
    ax.legend(['Signal Position'])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    aligned = align_center(sensor, hexapod)
        
    plt.show()
    print(f'Aligned: {aligned}')
    print(f'Final Position: {sensor.xpos}, {sensor.ypos}')

    return aligned

def rough_alignment(sensor, hexapod, probe):
    aligned = False
    
    
    hexapod.move_to_default_position()

    
   


    return aligned


if __name__ == "__main__":
    
    sensor = Sensor()
    hexapod = Hexapod()

    aligned = fine_alignment(sensor, hexapod)
    
    print(aligned)



        # align x coordinate


