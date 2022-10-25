from math import acos, cos, degrees, pi, radians, sin, sqrt, tan
from typing import List

from pytest import skip
from constants import Constants
from pool import Ball, Shot

# Not currently implemented
def verifyShotReachable(shot, balls: List[Ball]):
    
    shot.cue_ball_position
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

    

    if not checkClearPath(shot, balls):
        return False

    return True

def getExtensionPosition(cue_pos, cue_angle):
    # x = sin = op / hyp 
    x = cos(radians(cue_angle)) * Constants.MAX_REACH
    y = sin(radians(cue_angle)) * Constants.MAX_REACH
    cue_ball_x, cue_ball_y = cue_pos
    cue_ball_x += x
    cue_ball_y -= y

    return (cue_ball_x,cue_ball_y)

def getBodyExtension(handedness, cue_pos, original_angle):
    
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

def checkClearPath(shot: Shot, balls: List[Ball]):
    # create unit vector
    origin_x, origin_y = shot.cue_ball_position
    unit_vector = (cos(radians(shot.angle)), sin(radians(shot.angle)))

    for ball in balls:
        if ball.number == 0: continue
        ball_center_x, ball_center_y = ball.position
        origin_to_ball_vector = (origin_x - ball_center_x, origin_y - ball_center_y)
        mag_bal_vector = sqrt(pow(origin_to_ball_vector[0], 2) + pow(origin_to_ball_vector[1], 2))
        # get dot product
        intersection = unit_vector[0] * origin_to_ball_vector[0] + unit_vector[1] * origin_to_ball_vector[1]
        b = sqrt(pow(mag_bal_vector,2) - pow(intersection, 2)) 
        if b < Constants.BALL_RADIUS:
            return False
    
    return True
