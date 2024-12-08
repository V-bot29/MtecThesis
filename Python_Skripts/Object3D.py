# Objects.py
#from pylablib.devices import Thorlabs
import numpy as np
import socket

#TODO delet signal class
class Signal:
    def __init__(self, xpos, ypos, xdiff, ydiff, sum):
        self.xpos = xpos
        self.ypos = ypos
        self.xdiff = xdiff
        self.ydiff = ydiff
        self.sum = sum

class Object3D:
    def __init__(self, marker_id = None, marker_size = None):
        self.marker_id = marker_id
        self.marker_size = marker_size
        self.position = (None, None, None)
        self.rotation = (None, None, None)

        self.xposition = None
        self.yposition = None
        self.zposition = None


    def __repr__(self):
        return f"Object3D(position={self.position}, rotation={self.rotation})"

class Sensor(Object3D):
    def __init__(self, marker_id = 0, marker_size = 16):
        super().__init__(marker_id, marker_size)
        self.Unique_rvecs = []  # edit this
        self.Unique_tvecs = []  # edit this --> Translation Matrix from Marker to Sensor array

        self.xpos = None
        self.ypos = None
        self.xdiff = None
        self.ydiff = None
        self.sum = None

        # initialize stage
        #self.stage = Thorlabs.KinesisQuadDetector("69251980") # 69251980 is the serial number of the Cube KPA101
        self.stage = None

    def get_signal(self):
        self.stage.open()
        signal = self.stage.get_readings()
        self.xpos = signal.xpos
        self.ypos = signal.ypos
        self.xdiff = signal.xdiff
        self.ydiff = signal.ydiff
        self.sum = signal.sum
        self.stage.close()
        return signal # TODO decide weather to decide to return signal or always get values from sensor object

    def get_test_signal(self): # used for working at home
        self.xpos = np.random.rand()
        self.ypos = np.random.rand()
        self.xdiff = np.random.rand()
        self.ydiff = np.random.rand()
        self.sum = np.random.rand()
        signal = Signal(self.xpos, self.ypos, self.xdiff, self.ydiff, self.sum)  # return same data type as get_signal
        
        """
        # change size of random numbers
        keys = list(signal.__dict__.keys())
        for key in keys:
            signal.__dict__[key] = (signal.__dict__[key] - 0.5) * 0.5

        """
        return signal


    def __repr__(self):
        return f"Sensor(position={self.position}, rotation={self.rotation})"

class Probe(Object3D):
    def __init__(self, marker_id = 1, marker_size = 0):
        super().__init__(marker_id, marker_size)
        self.Unique_rvecs = []  # edit this (maybe also GUI input?)
        self.Unique_tvecs = []  # edit this --> Translation Matrix from Marker to the Tip of the Probe

    def __repr__(self):
        return f"Probe(position={self.position}, rotation={self.rotation})"

class Hexapod():
    def __init__(self):

        # Command Dictionary
        self.commands = {
            'set_sub_folder': 'setSubFolder Huehnerherz/2_Vascularized/Tracking/Hexapod/blabla/',
            'get_pos': 'get_pos',
            'set_local_file_name': 'setLocalFileName testfolder2',
            'start_rt_local': 'startRTLocal',
            'stop_rt_local': 'stopRTLocal',
            'set_vel ': 'set_vel ', # + str(vel),
            'disconnect': 'disconnect',
            'quit': 'quit',
            'stop': 'stop'
        }
        
        self.default_position = [0, 0, 0, 0, 0, 0] # [x, y, z, roll, pitch, yaw]


        self.position = [None, None, None, None, None, None] # [x, y, z, roll, pitch, yaw]
        self.velocity = None # TODO: set default velocity

        # Set up Sockets to connect to Server later
        self.tcpipObj_Hexapod_1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Socket for Commands
        self.tcpipObj_Hexapod_2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Socket for Emergency Stop

        self.connection_status = False #self.connect_sockets() # TODO show in UI event_log uncomment later
        self.server_response = None # to show server respons in UI event_log later

    def move_to_default_position(self):
        if not self.connection_status:
            self.server_response = 'Hexpod not connected to server'
            return False

        self.move_hex(self.default_position, flag = "absolute")
    
    def connect_sockets(self, IP= '134.28.45.71', port_1 = 5464, port_2 = 5465): # TODO implement in GUI and change to actual default adresses
        # Connect to Hexapod Server
        # TODO : implement Ip and port input in gui


        try:
            self.tcpipObj_Hexapod_1.connect((IP, port_1))
            self.tcpipObj_Hexapod_2.connect((IP, port_2))

            self.tcpipObj_Hexapod_1.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            self.tcpipObj_Hexapod_2.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            self.connection_status = True
            return True
        
        except socket.gaierror:
            self.connection_status = False
            return False
        except socket.error:
            self.connection_status = False
            return False

    def send_command(self, command):
        # Send command to TCP/IP server
        # Use tcpipObj_Hexapod_1 for regular commands, tcpipObj_Hexapod_2 as emergency stop

        if not self.connection_status:
            self.server_response = 'Hexpod not connected to server'
            return self.server_response
        
        elif command == 'stop':
            self.tcpipObj_Hexapod_2.write(command.encode())
            rcv = b''
            while not rcv:
                rcv = self.tcpipObj_Hexapod_2.read() # Reads the response from the TCP/IP server
            
            self.server_response = rcv.decode()
            return self.server_response

        else:
            self.tcpipObj_Hexapod_1.write(command.encode()) # Encodes the command string to bytestring UTF-8
            rcv = b''
            while not rcv:
                rcv = self.tcpipObj_Hexapod_1.read() # Reads the response from the TCP/IP server
            
            self.server_response = rcv.decode()
            return self.server_response

    def move_hex(self, pos, flag = "relative"):
        
        if not self.connection_status:
            self.server_response = 'Hexpod not connected to server'
            return self.server_response
        
        # Send command to get current position
        self.tcpipObj_Hexapod_1.write(b'get_pos\n')
        rcv = b''
        while not rcv:
            rcv = self.tcpipObj_Hexapod_1.read()
        pos_current = list(map(float, rcv.decode().split()))[1:] # remove first element which is the command

        if flag == "relative": # relative movement
            pos_new = [curr + p for curr, p in zip(pos_current, pos)] # add relative movement to current position for each coordinate
        elif flag == "absolute": # absolute movement
            pos_new = pos
        else:
            self.server_response = 'Incorrect input for flag'
            return self.server_response

        # Send command to set new position
        self.tcpipObj_Hexapod_1.write(f'set_pos {" ".join(map(str, pos_new))}\n'.encode()) # TODO check if this works, translated from matlab
        rcv = b''
        while not rcv:
            rcv = self.tcpipObj_Hexapod_1.read()

        self.server_response = rcv.decode()
        self.position = pos_new # update position attribute
        return self.server_response

    def set_velocity(self, velocity):
        if not self.connection_status:
            self.server_response = 'Hexpod not connected to server'
            return self.server_response
        
        self.velocity = velocity
        self.server_response = self.send_command(f'set_vel {velocity}\n')
        return self.server_response

    def __repr__(self):
        return f"Hexapod(position={self.position})"
    

if __name__ == "__main__":
    sensor = Sensor()

    signal = sensor.get_test_signal()
    print(signal.xpos, signal.ypos)
