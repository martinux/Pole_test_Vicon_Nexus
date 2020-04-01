
__filename__ = "Pole Test"
__version__ = "1.0"
__date__ = "2019"
__author__ = "mmolloy"

import ctypes
import math
import numpy as np
import os
import sys
import xlsxwriter

import ViconNexus

debug = False

currentdirectory = os.getcwd()
if debug: print(currentdirectory)
sys.path.append("C:\Program Files (x86)\Vicon\Nexus2.1\SDK\Python")

vicon = ViconNexus.ViconNexus()

# Extract information from active trial
Pole = vicon.GetSubjectNames()[0]
if debug: print(Pole)

#===========================================================
# Marker data
#===========================================================
framecount = vicon.GetFrameCount()
vicon.CreateModeledMarker(Pole, 'pole low')
vicon.CreateModeledMarker(Pole, 'pole high')
vicon.CreateModeledMarker(Pole, 'pole point')
(XP1, YP1, ZP1, EP1) = vicon.GetTrajectory(Pole, 'Pole1')
(XP2, YP2, ZP2, EP2) = vicon.GetTrajectory(Pole, 'Pole2')
(XP3, YP3, ZP3, EP3) = vicon.GetTrajectory(Pole, 'Pole3')
(XP4, YP4, ZP4, EP4) = vicon.GetTrajectory(Pole, 'Pole4')
(XP5, YP5, ZP5, EP5) = vicon.GetTrajectory(Pole, 'Pole5')

def markers_available(EP1, EP2, EP3, EP4, EP5):
    # If a marker is not in the trial EP* will be []
    available = {"Pole1":EP1, "Pole2":EP2, "Pole3":EP3, "Pole4":EP4, "Pole5":EP5}
    missing_marker = False
    for mkr in available.keys():
        if not available[mkr]:     # If mkr is not []
            # Show a dialogue box
            ctypes.windll.user32.MessageBoxA(0, "No {0} marker data.".format(mkr), "ERROR", 1)
            missing_marker = True
    if missing_marker:
        sys.exit(0)

def frame_data_complete(EP1, EP2, EP3, EP4, EP5):
    # build vector describing if each frame has marker data for all pole markers.
    valid_frames = [False] * framecount
    for ii in range(0, framecount):
        if EP1[ii] and EP2[ii] and EP3[ii] and EP4[ii] and EP5[ii]:
            valid_frames[ii] = True
            
    return valid_frames

def midpoint(x1, y1, z1, x2, y2, z2, valid_frames):
    # method: average the x-values, y-values and z-values in three dimensions.
    # general calculation: M = ((x1 + x2)/2, (y1 + y2)/2, (z1 + z2)/2)
    x_mid = [0] * framecount  # Nexus needs doubles as input.
    y_mid = [0] * framecount
    z_mid = [0] * framecount
    for ii in range(0, framecount):
        if valid_frames[ii]:
            x_mid[ii] = (x1[ii] + x2[ii]) / 2
            y_mid[ii] = (y1[ii] + y2[ii]) / 2
            z_mid[ii] = (z1[ii] + z2[ii]) / 2

    return (x_mid, y_mid, z_mid)

def dist_between_3D_points(x1, y1, z1, x2, y2, z2, valid_frames):
    # Equation:  d = sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)
    d = [float('nan')] * framecount
    for ii in range(0, framecount):
        if valid_frames[ii]:
            d[ii] = np.sqrt( (x2[ii] - x1[ii])**2 + \
                             (y2[ii] - y1[ii])**2 + \
                             (z2[ii] - z1[ii])**2
                           )
            
    return d

def unit_vector_from_two_points(vect1, vect2, scaling_vect):
    # Scale values in array to produce a vector of magnitude == 1
    # Equation: u = (x2 - x1)/d, (y2 - y1)/d, (z2 - z1)/d
    x = [float('nan')] * framecount
    y = [float('nan')] * framecount
    z = [float('nan')] * framecount
    for ii in range(0, framecount):
        x[ii] = (vect2[0][ii] - vect1[0][ii]) / scaling_vect[ii]
        y[ii] = (vect2[1][ii] - vect1[1][ii]) / scaling_vect[ii]
        z[ii] = (vect2[2][ii] - vect1[2][ii]) / scaling_vect[ii]
        
    return (x,y,z)

print("Frames of data: {0}".format(framecount))
markers_available(EP1, EP2, EP3, EP4, EP5)
valid_frames = frame_data_complete(EP1, EP2, EP3, EP4, EP5) # frames with all markers.
M1 = midpoint(XP1, YP1, ZP1, XP2, YP2, ZP2, valid_frames)  # midpoint between markers 1 and 2
M2 = midpoint(XP3, YP3, ZP3, XP4, YP4, ZP4, valid_frames)  # midpoint between markers 3 and 4

# Calculate virtual marker position in line with the pole:
dist_between_points = dist_between_3D_points(M2[0],M2[1],M2[2],M1[0],M1[1],M1[2],valid_frames)
print("Mean distance is: {0}  SD: {1}  (Distance between points should be around 1170mm)".format(np.nanmean(dist_between_points), np.nanstd(dist_between_points)))
u = unit_vector_from_two_points(M2, M1, dist_between_points)  # in direction of M2 to M1

# scale unit vector to pole point originating at virtual marker M2
pole_point_distance = 98  # Measured manually from midpoint of markers P1 and P2 (in mm)
pole_point_position_x = [0] * framecount  # Nexus needs doubles as input.
pole_point_position_y = [0] * framecount
pole_point_position_z = [0] * framecount
for ii in range(0, framecount):
    if valid_frames[ii]:
        # General formula is: (length of pole * unit vector) + origin of vector
        pole_point_position_x[ii] = ((dist_between_points[ii] + pole_point_distance) * u[0][ii]) + M2[0][ii]
        pole_point_position_y[ii] = ((dist_between_points[ii] + pole_point_distance) * u[1][ii]) + M2[1][ii]
        pole_point_position_z[ii] = ((dist_between_points[ii] + pole_point_distance) * u[2][ii]) + M2[2][ii]
pole_point_position = (pole_point_position_x, pole_point_position_y, pole_point_position_z)

# Add the calculated virtual markers to the model outputs in Nexus
vicon.SetModelOutput(Pole, 'pole low', M1, valid_frames)
vicon.SetModelOutput(Pole, 'pole high', M2, valid_frames)
vicon.SetModelOutput(Pole, 'pole point', pole_point_position, valid_frames)


#===========================================================
# Force platform data
#===========================================================
Devices = vicon.GetDeviceIDs()
DeviceNames = vicon.GetDeviceNames()
if debug: print(DeviceNames)
# Extract and organise data.
if len(Devices) > 0:
    for dev in Devices:
        try:
            DeviceName = DeviceNames[dev - 1]
        except IndexError:
            print('Name', DeviceNames, dev)
            sys.exit(1)
        
        #DeviceNumber = vicon.GetDeviceDetails(dev)[0]
        #Type = vicon.GetDeviceDetails(dev)[1]
        #Rate = vicon.GetDeviceDetails(dev)[2]
        OutputIDs = vicon.GetDeviceDetails(dev)[3]
        if debug: print('Name', DeviceName, dev)
        for devoutput in OutputIDs:
            Type = vicon.GetDeviceOutputDetails(dev, devoutput)[1]
            #units = vicon.GetDeviceOutputDetails(dev, devoutput)[2]
            components = vicon.GetDeviceOutputDetails(dev, devoutput)[4]
            channels = vicon.GetDeviceOutputDetails(dev, devoutput)[5]
            for channelsoutput in channels:
                currentchannel = vicon.GetDeviceChannel(dev, devoutput, channelsoutput)[0]
                if DeviceName == "Force Plate 1":
                    if Type == "Force":
                        if debug: print(components[channelsoutput-1])
                        if components[channelsoutput-1] == "Fx":
                            FP1_Fx = currentchannel
                        elif components[channelsoutput-1] == "Fy":
                            FP1_Fy = currentchannel
                        elif components[channelsoutput-1] == "Fz":
                            FP1_Fz = currentchannel
                    elif Type == "Moment":
                        if components[channelsoutput-1] == "Mx":
                            FP1_Mx = currentchannel
                        elif components[channelsoutput-1] == "My":
                            FP1_My = currentchannel
                        elif components[channelsoutput-1] == "Mz":
                            FP1_Mz = currentchannel 
                    elif Type == "CoP":
                        if components[channelsoutput-1] == "Cx":
                            FP1_Cx = currentchannel
                        elif components[channelsoutput-1] == "Cy":
                            FP1_Cy = currentchannel
                        elif components[channelsoutput-1] == "Cz":
                            FP1_Cz = currentchannel
                if DeviceName == "Force Plate 2":
                    if Type == "Force":
                        if debug: print (components[channelsoutput-1])
                        if components[channelsoutput-1] == "Fx":
                            FP2_Fx = currentchannel
                        elif components[channelsoutput-1] == "Fy":
                            FP2_Fy = currentchannel
                        elif components[channelsoutput-1] == "Fz":
                            FP2_Fz = currentchannel 
                    elif Type == "Moment":
                        if components[channelsoutput-1] == "Mx":
                            FP2_Mx = currentchannel
                        elif components[channelsoutput-1] == "My":
                            FP2_My = currentchannel
                        elif components[channelsoutput-1] == "Mz":
                            FP2_Mz = currentchannel
                    elif Type=="CoP":
                        if components[channelsoutput-1] == "Cx":
                            FP2_Cx = currentchannel
                        elif components[channelsoutput-1] == "Cy":
                            FP2_Cy = currentchannel
                        elif components[channelsoutput-1] == "Cz":
                            FP2_Cz = currentchannel

# Check that force platform Fz data was found:
try:
    FP1_Fz == True
except NameError:
    # Show a dialogue box
    ctypes.windll.user32.MessageBoxA(0, "FP1 does not seem to be available.", "ERROR", 1)
    sys.exit(0)

try:
    FP2_Fz == True
except NameError:
    # Show a dialogue box
    ctypes.windll.user32.MessageBoxA(0, "FP2 does not seem to be available.", "ERROR", 1)
    sys.exit(0)

# Determine which frames of Force platform data have FZ's greater than a specified threshold.
FP_framecount = len(FP1_Fz) # At 1000Hz (10x marker data capture rate)
FP1_X_position_offset = -232; FP1_Y_position_offset = -254  # in mm
FP2_X_position_offset = 232; FP2_Y_position_offset = -255
force_threshold = -50  # Newtons
# Predefine lists:
COP_X_FP1 = [0] * FP_framecount
COP_Y_FP1 = [0] * FP_framecount
COP_X_FP2 = [0] * FP_framecount
COP_Y_FP2 = [0] * FP_framecount
FP1_valid = [False] * FP_framecount # Keep track of frames where Fz exceeds threshold.
FP2_valid = [False] * FP_framecount
for ii in range(0, FP_framecount):
    if FP1_Fz[ii] < force_threshold:  # remember that FPZ is NEGATIVE!
        COP_X_FP1[ii] = (FP1_Cx[ii] + FP1_X_position_offset) * -1
        COP_Y_FP1[ii] = (FP1_Cy[ii] + FP1_Y_position_offset) * -1
        FP1_valid[ii] = True
    elif FP2_Fz[ii] < force_threshold:
        COP_X_FP2[ii] = (FP2_Cx[ii] + FP2_X_position_offset)
        COP_Y_FP2[ii] = (FP2_Cy[ii] + FP2_Y_position_offset)
        FP2_valid[ii] = True

# Calculate the differences between the offset FP COP and the apparent pole COP
COP_1diff = []  # magnitude of differences
COP_1diffx = [] # differences in x axis
COP_1diffy = [] # differences in y axis
COP_2diff = []
COP_2diffx = []
COP_2diffy = []
for ii in range(0, framecount):
    if valid_frames[ii] and FP1_valid[ii*10]:   # every ten FP frames
        COP_1diff.append(np.sqrt(np.power(COP_X_FP1[ii*10] - pole_point_position[0][ii], 2) \
                                + np.power(COP_Y_FP1[ii*10] - pole_point_position[1][ii], 2)))
        COP_1diffx.append(COP_X_FP1[ii*10] - pole_point_position[0][ii])
        COP_1diffy.append(COP_Y_FP1[ii*10] - pole_point_position[1][ii])
        
meanCOP_1diff = np.average(COP_1diff)
stdCOP_1diff = np.std(COP_1diff)

for ii in range(0, framecount):
    if valid_frames[ii] and FP2_valid[ii*10]:   # every ten FP frames
        COP_2diff.append(np.sqrt(np.power(COP_X_FP2[ii*10] - pole_point_position[0][ii],2) \
                                + np.power(COP_Y_FP2[ii*10] - pole_point_position[1][ii],2)))
        COP_2diffx.append(COP_X_FP2[ii*10] - pole_point_position[0][ii])
        COP_2diffy.append(COP_Y_FP2[ii*10] - pole_point_position[1][ii])

meanCOP_2diff = np.average(COP_2diff) 
stdCOP_2diff = np.std(COP_2diff)

# Create modelled markers that represent where the offset plate COP has been calculated:
vicon.CreateModeledMarker(Pole, 'COP+X')
vicon.CreateModeledMarker(Pole, 'COP-X')
vicon.CreateModeledMarker(Pole, 'COP+Y')
vicon.CreateModeledMarker(Pole, 'COP-Y')

aa = [0] * framecount    # predefine vector
COP_posX = [[0]*framecount, [0]*framecount, [0]*framecount]     # predefine coords.
COP_negX = [[0]*framecount, [0]*framecount, [0]*framecount]
COP_posY = [[0]*framecount, [0]*framecount, [0]*framecount]
COP_negY = [[0]*framecount, [0]*framecount, [0]*framecount]
for ii in range(0, framecount):
    if FP1_valid[ii*10]:    # Every 10th frame
        # X
        COP_posX[0][ii] = COP_X_FP1[ii*10] + 15  # shift virtual marker 15mm in X from COP
        COP_posX[1][ii] = COP_Y_FP1[ii*10]
        COP_posX[2][ii] = 0   # At zero height
        COP_negX[0][ii] = COP_X_FP1[ii*10] - 15
        COP_negX[1][ii] = COP_Y_FP1[ii*10]
        COP_negX[2][ii] = 0
        # Y
        COP_posY[0][ii] = COP_X_FP1[ii*10]
        COP_posY[1][ii] = COP_Y_FP1[ii*10] + 15
        COP_posY[2][ii] = 0
        COP_negY[0][ii] = COP_X_FP1[ii*10]
        COP_negY[1][ii] = COP_Y_FP1[ii*10] - 15
        COP_negY[2][ii] = 0
    elif FP2_valid[ii*10]:
        # X
        COP_posX[0][ii] = COP_X_FP2[ii*10] + 15
        COP_posX[1][ii] = COP_Y_FP2[ii*10]
        COP_posX[2][ii] = 0   # At zero height
        COP_negX[0][ii] = COP_X_FP2[ii*10] - 15
        COP_negX[1][ii] = COP_Y_FP2[ii*10]
        COP_negX[2][ii] = 0
        # Y
        COP_posY[0][ii] = COP_X_FP2[ii*10]
        COP_posY[1][ii] = COP_Y_FP2[ii*10] + 15
        COP_posY[2][ii] = 0
        COP_negY[0][ii] = COP_X_FP2[ii*10]
        COP_negY[1][ii] = COP_Y_FP2[ii*10] - 15
        COP_negY[2][ii] = 0

vicon.SetModelOutput(Pole, 'COP+X', COP_posX, valid_frames)
vicon.SetModelOutput(Pole, 'COP-X', COP_negX, valid_frames)
vicon.SetModelOutput(Pole, 'COP+Y', COP_posY, valid_frames)
vicon.SetModelOutput(Pole, 'COP-Y', COP_negY, valid_frames)

# Check that mean COP data is not absent.
COP_check = True
if np.isnan(meanCOP_1diff):
    print("No FP1 data.")
    # Show a dialogue box
    ctypes.windll.user32.MessageBoxA(0, "No FP1 COP data.", "ERROR", 1)
    COP_check = False
if np.isnan(meanCOP_2diff):
    print("No FP2 data.")
    # Show a dialogue box
    ctypes.windll.user32.MessageBoxA(0, "No FP2 COP data.", "ERROR", 1)
    COP_check = False
if not COP_check:
    sys.exit(0)

# ===================================================
# Output to MS Excel document.
# ===================================================
SessionLoc = vicon.GetTrialName()[0]
trialname = vicon.GetTrialName()[1]
os.chdir(SessionLoc)

book = xlsxwriter.Workbook(SessionLoc + "/COPPCHECK_MM_" + trialname + ".xlsx")
sheet1 = book.add_worksheet("Sheet1")

format = book.add_format()
format.set_border(1)
format.set_bold()
format.set_bg_color("#00FF00")

sheet1.write('A1', "FP1 meanCOPdiff")
sheet1.write('A2', "FP1 stdCOPdiff")
sheet1.write('B1', meanCOP_1diff)
sheet1.write('B2', stdCOP_1diff)
if meanCOP_1diff <= 5:
    sheet1.write('C1', "PASS", format)
else:
    sheet1.write('C2', "FAIL")
    
sheet1.write('A3', "FP2 meanCOPdiff")
sheet1.write('A4', "FP2 stdCOPdiff")
sheet1.write('B3', meanCOP_2diff)
sheet1.write('B4', stdCOP_2diff)
if meanCOP_2diff <= 5:
    sheet1.write('C3', "PASS", format)
else:
    sheet1.write('C3', "FAIL")
    
sheet1.write('A6', "FP1 X meanCOPdiff")
sheet1.write('B6', np.average(COP_1diffx))
sheet1.write('A7', "FP1 Y meanCOPdiff")
sheet1.write('B7', np.average(COP_1diffy))
sheet1.write('A8', "FP2 X meanCOPdiff")
sheet1.write('B8', np.average(COP_2diffx))
sheet1.write('A9', "FP2 Y meanCOPdiff")
sheet1.write('B9', np.average(COP_2diffy))

sheet1.write(0, 3, "FP1 Difference in COP X")
sheet1.write(0, 4, "FP1 Difference in COP Y")
for diff in range(0, len(COP_1diffx)):
    sheet1.write(diff + 1, 3, COP_1diffx[diff])
    sheet1.write(diff + 1, 4, COP_1diffy[diff])

sheet1.write(0, 5, "FP2 Difference in COP X")
sheet1.write(0, 6, "FP2 Difference in COP Y")
for diff in range(0, len(COP_2diffx)):
    sheet1.write(diff + 1, 5, COP_2diffx[diff])
    sheet1.write(diff + 1, 6, COP_2diffy[diff])
    
# Adjust column widths for readability
col_width = [16.5, 10.00, 5.00, 21.50, 21.50, 21.50, 21.50]
for ii, this_width in enumerate(col_width):
    sheet1.set_column(0, ii, this_width)

chart1 = book.add_chart({'type': 'scatter'})
chart1.add_series({'name': 'FP1 COP DIFFERENCE',
    'categories': '=Sheet1!$D$2:$D$' + str(len(COP_1diffy) - 1),
    'values': '=Sheet1!$E$2:$E$' + str(len(COP_1diffx) - 1)
})
chart1.add_series({'name': 'FP2 COP DIFFERENCE',
    'categories': '=Sheet1!$F$2:$F$' + str(len(COP_2diffy) - 1),
    'values': '=Sheet1!$G$2:$G$' + str(len(COP_2diffx) - 1)
})
chart1.set_title ({'name':'Differences between calculated pole and Force Plate COP'})
chart1.set_x_axis({'name':'X deviation (mm)', 'min':-10, 'max':10})
chart1.set_y_axis({'name':'Y deviation (mm)', 'min':-10, 'max':10})

chart1.set_style(10)
sheet1.insert_chart('$B$13', chart1, {'x_scale':2, 'y_scale':2})
book.close()
os.startfile(SessionLoc + "/COPPCHECK_MM_" + trialname + ".xlsx")
