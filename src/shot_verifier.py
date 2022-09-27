from math import cos, sin
from constants import Constants

# Not currently implemented
def verifyShotReachable(shot):
    
    shot.cue_ball_position
    shot.angle
    
    extension_x, extension_y = getExtensionPosition(
        shot.cue_ball_position, 
        shot.angle
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
    x = sin(cue_angle) * Constants.MAX_REACH
    y = cos(cue_angle) * Constants.MAX_REACH
    cue_ball_x, cue_ball_y = cue_pos
    x += cue_ball_x
    y += cue_ball_y

    return (x,y)
