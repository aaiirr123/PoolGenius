class Constants:
 
    # 28.575 MM POOL BALL RADIUS
    # 76 and 43 incg
    # 1930.4 and 1092.2
    TICK_RATE = 60
    SLOW_MOTION_TICK_RATE = 5
    PLAYER_WIDTH = 1.5
    TIME_STEP = 1.0 / TICK_RATE
    STICK_LENGTH = 57 / 12
    STICK_WIDTH = 1 / 12
    VEL_ITERS = 8
    POS_ITERS = 3
    TABLE_WIDTH = 76 / 12
    TABLE_HEIGHT = 43 / 12
    TABLE_RATIO = TABLE_WIDTH / TABLE_HEIGHT
    BALL_RADIUS = 0.09375
    POCKET_RADIUS = 0.171875
    HEIGHT = 800
    WIDTH = HEIGHT * TABLE_RATIO
    CUE_BALL = 0
    MAX_REACH = 3.5
    
class Weights:
    TOTAL_COLLISIONS = 0.7
    COLLISIONS_WITH_TABLE = 50
    POCKETED_BALL_COLLISIONS = 2.5
    TOTAL_DISTANCE = 0.5
    DISTANCE_BEFORE_CONTACT = 1.1
    POSSESION = 55
    POCKETED = 6.7
    POCKETED_WALL_COLLISIONS = 4
    DISTANCE_PER_BALL = 1
    SCRATCH = 50
    GREAT_SHOT = 3.4
    GOOD_SHOT = 2.8
    WALL_EXPONENT = 2.7
    

class Bias:
    TOTAL_COLLISIONS = 1
    COLLISIONS_WITH_TABLE = 3
    POCKETED_BALL_COLLISIONS = 0
