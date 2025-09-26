import cv2
import numpy as np

# ----------------------------------------------------------------
# Utility functions
# ----------------------------------------------------------------
def getSlope(line):
    # We take it such that numerically y2>y1
    x1,y1,x2,y2 = line[0]
    if(y2>y1):
        return (y2-y1)/(x2-x1)
    else:
        return (y1-y2)/(x1-x2)

def extendLine(line,frame):
        '''
            use equation of straight line to extend the line such that:
            higher y value is close to 0.65* height
            similarly make lower y value close to 0.95 * height
            (higher and lower in the visual sense)
        '''
        x1,y1,x2,y2 = line[0]
        m = getSlope(line)
        c = y1 - m*x1
        if(y1>y2):
            y1_new = int(0.65*frame.shape[0])
            x1_new = int((y1_new-c)/m)

            y2_new = int(0.95*frame.shape[0]) 
            x2_new = int((y2_new-c)/m)
        else:
            y2_new = int(0.65*frame.shape[0])
            x2_new = int((y2_new-c)/m)

            y1_new = int(0.95*frame.shape[0]) 
            x1_new = int((y1_new-c)/m)
            
        return x1_new,y1_new,x2_new,y2_new
# ----------------------------------------------------------------

# Functions for frame processing 
# ----------------------------------------------------------------
def ROI(frame):
    '''
    region of interest is taken as the rectangle drawn with vertices: 
    (0,0.6*height), (width,0.6*height), (width,height), (0,height)    
    must be passed in order: lower left, upper left, upper right, lower right
    '''
    vertices = np.array([[0,frame.shape[0]],[0,frame.shape[0]*0.6],[frame.shape[1],frame.shape[0]*0.6],[frame.shape[1],frame.shape[0]]],dtype=np.int32)
    mask = np.zeros_like(frame)
    cv2.fillPoly(mask, [vertices], 255)
    masked_image = cv2.bitwise_and(frame,mask)
    return masked_image

def houghWithMask(frame,lower,upper):
    '''
    Applies Hough line transform on the frame on which masking has been done with "lower" and "upper" bounds 
    Returns the processed video as well as the list of lines obtained from hough transform
    '''
    if(type(lower)==np.ndarray):
        hsv = cv2.cvtColor(frame,cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv,lower,upper) 
        masked_image = cv2.bitwise_and(hsv,hsv,mask=mask)
        blur = cv2.GaussianBlur(masked_image,(5,5),0)
        final = cv2.cvtColor(blur,cv2.COLOR_BGR2GRAY)
    else:
        gray = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        mask = cv2.inRange(gray,lower,upper)
        masked_image = cv2.bitwise_and(gray,gray,mask=mask)
        final = cv2.GaussianBlur(masked_image,(5,5),0)

    edges = cv2.Canny(final, 50, 150)
    edges = ROI(edges)
    # Erode and dilute
    edges = cv2.erode(edges,(3,3))
    edges = cv2.dilate(edges,(3,3))
    # Hough Line Transform
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, np.array([]), 50, 10)

    return edges,lines

def getLR(lines):
    '''
    identifies  the leftmost and the rightmost lines in the list "lines" and returns them
    ie, it choose the lines with highest and lowest x1
    '''

    global last_left_line,last_right_line
    
    max_x1 = np.argmax(lines[:,0,0])
    min_x1 = np.argmin(lines[:,0,0])

    left_line = lines[max_x1] if getSlope(lines[max_x1])>0 else None
    right_line = lines[min_x1] if getSlope(lines[min_x1])<0 else None

    if(left_line is not None):
        last_left_line = left_line
    if(right_line is not None):
        last_right_line = right_line
    if(left_line is None and last_left_line is not None):
        left_line = last_left_line
    if(right_line is None and last_right_line is not None):
        right_line = last_right_line

    return left_line,right_line

def drawBox(frame,left_line,right_line):
    '''
    Draws a box of sorts to denote the detected lane` 
    '''

    # Extend the lines so that they have same y coordinates
    x1,y1,x2,y2 = extendLine(left_line,frame)
    x3,y3,x4,y4 = extendLine(right_line,frame)

    # Draw the box (along with border lines on the left and right)
    cv2.line(frame, (x1, y1), (x2, y2), (0, 0, 255),3,cv2.LINE_AA)
    cv2.line(frame, (x3, y3), (x4, y4), (0, 0, 255),3,cv2.LINE_AA)

    # must be passed in order: lower left, upper left, upper right, lower right
    vertices = np.array([[x1,y1],[x2,y2],[x3,y3],[x4,y4]],dtype=np.int32)

    cv2.fillPoly(frame, [vertices], (144,238,144)) # light green

    return frame

def processYWLines(frame,lower_y,upper_y,lower_w,upper_w):

    global last_y_lines, last_w_lines

    y_processed,y_lines = houghWithMask(frame,lower_y,upper_y)
    w_processed,w_lines = houghWithMask(frame,lower_w,upper_w)

    if(y_lines is not None):
        last_y_lines = y_lines
    if(w_lines is not None):
        last_w_lines = w_lines
    if(y_lines is not None and w_lines is not None):
        all_lines = np.concatenate((y_lines,w_lines),axis=0)
    elif(y_lines is None):
        all_lines = w_lines
    elif(w_lines is None):
        all_lines = y_lines
    if(y_lines is None and w_lines is None):
        all_lines = np.concatenate((last_y_lines,last_w_lines),axis=0)

    return all_lines
