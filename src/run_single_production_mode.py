import threading
from constants import Constants
# Do not change order of import, ai must be imported before pool
import ai
from pool import CueBall, Ball, Pool, PoolPlayer, PoolState, Shot

# production mode means that there are no graphics
# single means that only one simulatation will be made

def runSingleProductionMode(balls, cueBall, magnitudes, angles, pool: Pool, turn: PoolPlayer):
        
        player1 = ai.SimpleAI(PoolPlayer.PLAYER1, magnitudes, angles)
        shot_queue = []
        ai_thinking = False
        simulating = False
        fast_forward = True
        finalShot = Shot(0,0)
        finalTime = 0

        board = pool.generate_board_from_list(balls, cueBall)
        if turn is not None: board.turn = turn
        Pool.WORLD.load_board(board)
        shots = 0

        # game loop
        
        while shots < 2:
       
            if not simulating and not ai_thinking and len(shot_queue) == 0:
                target = player1.take_shot
                if shots < 1:
                    threading.Thread(target=target, args=(board, shot_queue)).start()
                shots += 1
                ai_thinking = True
            elif len(shot_queue) > 0:
                ai_thinking = False
                simulating = True
                shot, time = shot_queue.pop()
                finalShot, finalTime = shot, time
                Pool.WORLD.load_board(board)
                Pool.WORLD.shoot(shot)                
            
            if simulating:
                for _ in range(5 if fast_forward else 1):
                    if not Pool.WORLD.update_physics(Constants.TIME_STEP, Constants.VEL_ITERS, Constants.POS_ITERS):
                        still_frames += 1
                    else:
                        still_frames = 0
            
                if still_frames > 3:
                    board = Pool.WORLD.get_board_state()
                    state = board.get_state()
                    if state == PoolState.ONGOING:
                        simulating = False
                    else:
                        board = pool.generate_normal_board()
                        simulating = False
                    Pool.WORLD.load_board(board)
        print("Done!")   
        print(finalShot)
        print(finalTime)
 


if __name__ == "__main__":
    ##########################################
    ##This must be updated to pass in values##

    balls = [
        Ball([2, 2], 1),
        Ball([3, 3], 8),
        Ball([6, 3.7], 9),  
        Ball([2.7, 3.6], 11),      
    ]
    cueBall = CueBall([2.5, 2.5])
 
    # Player 1 is solids and Player 2 is stripes
    playerTurn = PoolPlayer.PLAYER2
    ##########################################

    pool = Pool(slowMotion=False, graphics=False)
    magnitudes=[75.0, 100.0, 125.0]
    angles=range(0, 360, 2)
    runSingleProductionMode(balls, cueBall, magnitudes, angles, pool, playerTurn)
    