from math import acos, cos, degrees, pi, radians, sin, sqrt, tan
import math
from typing import List

from pytest import skip
from constants import Constants
from pool import Ball, Shot

def verifyShotReachable(shot: Shot, balls: List[Ball]):
    
    cue_ball_pos = shot.cue_ball_position
    cue_angle = (shot.angle + 180) % 360
    cue_angle *= -1
    
    extension_x, extension_y = getBodyExtension(
        1,
        shot.cue_ball_position, 
        cue_angle
    )

    stick_extension_x, stick_extension_y = getExtensionPosition(
        shot.cue_ball_position, 
        cue_angle
    )

    if ((extension_x < Constants.TABLE_WIDTH and
        extension_x > 0) and
        (extension_y < (Constants.TABLE_HEIGHT) and
        extension_y > 0)
        ):
        return False

    if ((stick_extension_x < Constants.TABLE_WIDTH and
        stick_extension_x > 0) and
        (stick_extension_y < (Constants.TABLE_HEIGHT) and
        stick_extension_y > 0)
        ):
        return False

    
    if not checkClearPath(cue_bal_pos=cue_ball_pos, angle=cue_angle, balls=balls):
        return False

    return True


def getPlayerPosition(cue_ball_pos, angle):

    endPos = getExtensionPosition(
        cue_ball_pos, 
        angle
    )
    
    return lineRectRayCast(cue_ball_pos, endPos)
  

def getWallNum(body_pos_x, body_pos_y):
    # Find wall number
    #            2
    #   ------------------  
    #   |                |
    # 3 |                | 1
    #   |                |
    #   |                |
    #   ------------------
    #            4
    
    if round(body_pos_x, 2) == round(Constants.TABLE_WIDTH, 2):
        # right wall
        return 1
    if round(body_pos_y, 2) == 0:
        # top wall
        return 2
    if round(body_pos_x, 2) == 0:
        # left wall
        return 3
    if round(body_pos_y, 2) == round(Constants.TABLE_HEIGHT, 2):
        # bottom wall
        return 4
    
def getRelativeAngle(angle, body_pos_x, body_pos_y):  
    # left side of player is negative, right is positive
    # Perpendicular to wall is 0 degrees
    
    if round(body_pos_x, 2) == round(Constants.TABLE_WIDTH, 2):
        # right wall
        shooter_angle = angle
        return shooter_angle * -1
    if round(body_pos_y,2) == 0:
        # top wall
        shooter_angle = angle + 270
        return shooter_angle * -1
    if round(body_pos_x, 2) == 0:
        # left wall
        shooter_angle = angle + 180
        return shooter_angle * -1
    if round(body_pos_y,2) == round(Constants.TABLE_HEIGHT, 2):
        # bottom wall
        shooter_angle = angle + 90
        return shooter_angle * -1
    
    print("something messed up")
    return 180

def lineRectRayCast(startPoint, endPoint):
    # This is the raycast system used to deteremine
    # where a line colides with a box
    
    A = (Constants.TABLE_WIDTH, Constants.TABLE_HEIGHT)
    B = endPoint
    C = (0,0)
    
    vecA = (A[0] - startPoint[0],  A[1] - startPoint[1])
    vecB = (B[0] - startPoint[0], B[1] - startPoint[1])
    vecC = (C[0] - startPoint[0], C[1] - startPoint[1])
    
    magB = sqrt(pow(vecB[0], 2) + pow(vecB[1], 2))
    unitB = ((vecB[0] / magB), (vecB[1] / magB))
    
    if unitB[0] == 0:
        if unitB[1] > 0:
            return(startPoint[0], Constants.TABLE_HEIGHT)
        else:
            return(startPoint[0], 0)
    if unitB[1] == 0:
        if unitB[0] > 0:
            return(Constants.TABLE_WIDTH, startPoint[1])
        else:
            return(0, startPoint[1])
    
    # Length to reach point
    AXDir = vecA[0] / unitB[0]
    CXDir = vecC[0] / unitB[0]
    AYDir = vecA[1] / unitB[1]
    CYDir = vecC[1] / unitB[1]
    
    smallerX = None
    largerX = None
    smallerY = None
    largerY = None
    
    if AXDir < CXDir:
        smallerX = AXDir 
        largerX = CXDir
    else:
        smallerX = CXDir
        largerX = AXDir

    if AYDir < CYDir:
        smallerY = AYDir 
        largerY = CYDir
    else:
        smallerY = CYDir
        largerY = AYDir
        
    tMin = max(smallerX, smallerY)
    tMax = min(largerX, largerY)
    
    finalCord = ((0,0),(0,0))
    
    if tMin < 0:
        finalCord = (( startPoint[0] + tMax * unitB[0]),( startPoint[1] + tMax * unitB[1]))
                        
    else:
        finalCord = (( startPoint[0] + tMin * unitB[0]),( startPoint[1] + tMin * unitB[1]))

    return finalCord

def getExtensionPosition(cue_ball_pos, cue_angle):
    # Returns the end coordinates of the pool stick
    x = cos(radians(cue_angle)) * Constants.MAX_REACH
    y = sin(radians(cue_angle)) * Constants.MAX_REACH
    
    cue_ball_x, cue_ball_y = cue_ball_pos
    cue_ball_x += x
    cue_ball_y -= y

    return (cue_ball_x, cue_ball_y)

def getBodyExtension(handedness, cue_pos, original_angle):
    # Returns the end coordinates of the
    # players body width, assuming right handed
    new_hype = sqrt(pow(Constants.MAX_REACH, 2) + pow(Constants.PLAYER_WIDTH, 2))
    angle = degrees(acos(Constants.MAX_REACH / new_hype)) 
    angle = original_angle - angle
    if angle < 0: angle = 360 + angle
    
    x = cos(radians(angle)) * new_hype
    y = sin(radians(angle)) * new_hype

    cue_ball_x, cue_ball_y = cue_pos
    cue_ball_x += x
    cue_ball_y -= y

    return(round(cue_ball_x,2),round(cue_ball_y,2))


def checkClearPath(cue_bal_pos, angle, balls: List[Ball]):
    # Ensure that there is 15 degrees of room for user to
    # maneuver pool stick, or 7.5 degrees left and right
    
    #  \ 7.5 | 7.5 /
    #   \    |    / 
    #    \   |   /
    #     \   |  /
    #      \ | /
    #       \|/
    
    # send out 15 ray cast, 1 at each degree
    
    start_angle = angle - 7.5
    player_pos = getPlayerPosition(cue_ball_pos=cue_bal_pos, angle=angle)
    
    for i in range(16):
        current_angle = start_angle + i
        
        unit_vector = (math.cos(math.radians(current_angle)), -math.sin(math.radians(current_angle)))
        ray_origin = lineSweep(start_seg=player_pos, stop_seg=cue_bal_pos, angle=angle, angle_increase=(current_angle - angle))
        
        for ball in balls:
            
            if ball.number == 0: continue
            
            ball_center_x, ball_center_y = ball.position
            
            origin_to_ball_vector = (ball_center_x - ray_origin[0], ball_center_y - ray_origin[1])
            
            mag_bal_vector = math.sqrt(pow(origin_to_ball_vector[0], 2) + pow(origin_to_ball_vector[1], 2))
            # get dot product
            intersection = unit_vector[0] * origin_to_ball_vector[0] + unit_vector[1] * origin_to_ball_vector[1]
            if intersection < 0:
                continue
            
            b = math.sqrt(pow(mag_bal_vector,2) - pow(intersection, 2)) 
            
            if b < Constants.BALL_RADIUS:
                return False
        
    return True

def lineSweep(start_seg, stop_seg, angle, angle_increase):
    # find end position when sweeping line segment
    
    #  |      /
    #  | deg /
    #  |    /
    #  |   /
    #  |  /
    #  | /
    
    dif_x = start_seg[0] - stop_seg[0] 
    dif_y = start_seg[1] - stop_seg[1]
    cue_stick_peak = math.sqrt(pow(dif_x, 2) + pow(dif_y, 2))
    
    angle_length = cue_stick_peak / math.cos(math.radians(angle_increase))
    
    increased_angle = angle + 180 + angle_increase
   
    
    unit_vector = (math.cos(math.radians(increased_angle)), math.sin(math.radians(increased_angle)))

    end_vector = (unit_vector[0] * angle_length, unit_vector[1] * angle_length)
    
    end_pos = (end_vector[0] + start_seg[0], - end_vector[1] + start_seg[1])

    return end_pos            
    
# def checkClearPath(shot: Shot, balls: List[Ball]):
#     # Loops through balls and raycasts to check for
#     # collisions
    
#     # create unit vector
#     origin_x, origin_y = shot.cue_ball_position
#     unit_vector = (cos(radians(shot.angle)), sin(radians(shot.angle)))

#     for ball in balls:
#         if ball.number == 0: continue
#         ball_center_x, ball_center_y = ball.position
#         origin_to_ball_vector = (origin_x - ball_center_x, origin_y - ball_center_y)
#         mag_bal_vector = sqrt(pow(origin_to_ball_vector[0], 2) + pow(origin_to_ball_vector[1], 2))
#         # get dot product
#         intersection = unit_vector[0] * origin_to_ball_vector[0] + unit_vector[1] * origin_to_ball_vector[1]
#         b = sqrt(pow(mag_bal_vector,2) - pow(intersection, 2)) 
#         if b < Constants.BALL_RADIUS:
#             return False
    
#     return True
