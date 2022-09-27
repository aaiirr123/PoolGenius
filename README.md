# PoolGenius
This is a version of pool genius which we are creating for our senior design project at UCF
# New Modes
You will see that there are some new modes added to allow for simulating specific shots

# run_single_test_mode 
This will run a single shot with graphics based on the input given
the paramaters which need to be added are: balls, magnitudes, angles, pool, playerTurn.

balls = [
    Ball([2, 2], 1),
    Ball([3, 3], 8),
    Ball([6, 3.7], 9),  
    Ball([2.7, 3.6], 11),      
]

magnitudes=[75.0, 100.0, 125.0] 
angles=range(0, 360, 2)

pool variable will most likely not be changed
 
PLAYER1 is solid's and PLAYER2 is stripe's
playerTurn = PoolPlayer.PLAYER2

# run_single_production_mode 
This functions in the same way as the previous function
except that the graphics are disabled and only a value
for force and angle are returned

# Steps for running
You need pip and python

Optional - create virtual env: 
    python -m venv env
    env/Scripts/activate

1: pip install -r requirements.txt

2: cd src

3: python3 pool.py

Can also run:
python3 run_single_production_mode.py
python3 run_single_test_mode.py

# Notes on angles and X,Y pos

angle is based upon the direction your cue ball would be shot in. For our algorithms dealing with the cuestick, we must flip
this angle measurment by 180 degrees. 

X and Y posistion start at the normal origin point we would expect
