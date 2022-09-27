from cmath import exp
from math import acos, atan, cos, degrees, pi, radians, sin, sqrt, tan
from constants import Constants

# Not currently implemented
def verifyShotReachable(shot):
    
    shot.cue_ball_position
    cue_angle = (shot.angle + 180) % 360
    
    # extension_x, extension_y = getExtensionPosition(
    #     shot.cue_ball_position, 
    #     shot.angle
    #     )
    
    extension_x, extension_y = getBodyExtension(
        1,
        shot.cue_ball_position, 
        cue_angle,
        width = 1
    )

    if ((extension_x < Constants.TABLE_WIDTH and
        extension_x > 0) and
        (extension_y < (Constants.TABLE_HEIGHT) and
        extension_y > 0)
        ):
        #print("false")
        return False

    return True

def getExtensionPosition(cue_pos, cue_angle):
    # x = sin = op / hyp 
    x = cos(radians(cue_angle)) * Constants.MAX_REACH
    y = sin(radians(cue_angle)) * Constants.MAX_REACH
    cue_ball_x, cue_ball_y = cue_pos
    x -= cue_ball_x
    y -= cue_ball_y

    return (x,y)

def getBodyExtension(handedness, cue_pos, original_angle, width):
    
    new_hype = sqrt(pow(Constants.MAX_REACH, 2) + pow(width, 2))
    angle = degrees(acos(Constants.MAX_REACH / new_hype)) 
    angle = original_angle - angle
    if angle < 0: angle = 360 + angle
    if angle >= 360: angle % 360

    x = cos(radians(angle)) * new_hype
    y = sin(radians(angle)) * new_hype

    cue_ball_x, cue_ball_y = cue_pos
    x += cue_ball_x
    y += cue_ball_y

    return(round(x,2),round(y,2))

def convertToDegrees(radians):
    return radians * (180 / pi)

def testExtension():
    res = getBodyExtension(1, (2.5,2.5),180, 1)
    expected = (0,3.5)
    print("passed") if res == expected else print("failed")
    print("expected" + str(expected) + " : " + str(res))

    res = getBodyExtension(1, (2.5,2.5), 0, 1)
    expected = (5,1.5)
    print("passed") if res == expected else print("failed")
    print("expected" + str(expected) + " : " + str(res))
    
    res = getBodyExtension(1, (2.5,2.5), 90, 1)
    expected = (3.5, 5)
    print("passed") if res == expected else print("failed")
    print("expected" + str(expected) + " : " + str(res))

    res = getBodyExtension(1, (2.5,2.5), 270, 1)
    expected = (1.5, 0)
    print("passed") if res == expected else print("failed")
    print("expected" + str(expected) + " : " + str(res))

