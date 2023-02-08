from abc import ABC, abstractmethod
import heapq
import math
import time
from typing import List
from shot_verifier import verifyShotReachable

from Box2D.Box2D import b2Vec2

from pool import Ball, Complexity, PoolBoard, Shot, random_float, PoolPlayer, PoolState, Pool
from constants import Constants, Weights

class PoolAI(ABC):

    def __init__(self, player : PoolPlayer, magnitudes=[75.0, 100.0, 125.0], angles=range(0, 360)):
        self.player = player
        self.magnitudes = magnitudes
        self.angles = angles

    def take_shot(self, board : PoolBoard, queue : List ):
        t0 = time.time()
        s = self.shot_handler(board, self.magnitudes, self.angles)
        t1 = time.time()
        t = t1 - t0
        queue.append((s, t))

    @abstractmethod
    def shot_handler(self, board : PoolBoard) -> Shot:
        pass

    @abstractmethod
    def name(self) -> str:
        pass

class RandomAI(PoolAI):

    def name(self) -> str:
        return "random"

    def shot_handler(self, board: PoolBoard) -> Shot:
        shot = Shot(random_float(0, 360), random_float(100, 150))
        if board.cue_ball.pocketed:
            x = -1.0
            y = -1.0
            while True:
                x = random_float(Constants.BALL_RADIUS + 0.5, Constants.TABLE_WIDTH - Constants.BALL_RADIUS - 0.5)
                y = random_float(Constants.BALL_RADIUS + 0.5, Constants.TABLE_HEIGHT - Constants.BALL_RADIUS - 0.5)
                if Shot.test_cue_ball_position(b2Vec2(x, y), board.balls):
                    break
            shot.cue_ball_position = b2Vec2(x, y)
        return shot

class ComparableShot:

    def __init__(self, shot : Shot, heuristic : float, board : PoolBoard, complexity : Complexity = Complexity()):
        self.shot = shot
        self.heuristic = heuristic
        self.board = board
        self.complexity = complexity

    def __gt__(self, other):
        return self.heuristic < other.heuristic

    def __lt__(self, other):
        return self.heuristic > other.heuristic

class SimpleAI(PoolAI):

    def name(self) -> str:
        return "simple"

    def shot_handler(self, board: PoolBoard, magnitudes, angles) -> Shot:
        shots = self.compute_best_shots(board, magnitudes, angles)
        return shots[0].shot

    # returns the 10 best shots sorted from best to worst
    def compute_best_shots(self, board : PoolBoard, magnitudes, angles, length=10) -> List[ComparableShot]:
        position = board.cue_ball.position
        if board.cue_ball.pocketed:
            while True:
                x = random_float(Constants.BALL_RADIUS + 0.5, Constants.TABLE_WIDTH - Constants.BALL_RADIUS - 0.5)
                y = random_float(Constants.BALL_RADIUS + 0.5, Constants.TABLE_HEIGHT - Constants.BALL_RADIUS - 0.5)
                position = b2Vec2(x, y)
                if Shot.test_cue_ball_position(position, board.balls):
                    break
        queue : List[ComparableShot] = []
        for angle in angles:
            for magnitude in magnitudes:
                if len(queue) % 50 == 0:
                    print(f"Shots generated: {len(queue)}")
                shot = Shot(angle, magnitude, position)
                
                if verifyShotReachable(shot, board.balls):
                    heapq.heappush(queue, self.compute_shot_heuristic(shot, board))
        shots = []
        for _ in range(length):
            shots.append(heapq.heappop(queue))
        return shots

    def compute_shot_heuristic(self, shot : Shot, board : PoolBoard) -> ComparableShot:
        Pool.WORLD.load_board(board)
        Pool.WORLD.shoot(shot)
        Pool.WORLD.simulate_until_still(Constants.TIME_STEP, Constants.VEL_ITERS, Constants.POS_ITERS)
        the_board = Pool.WORLD.get_board_state()
        heuristic = self.compute_heuristic(the_board, board.turn)

        if board.turn == PoolPlayer.PLAYER2:
            heuristic *= -1.0
        return ComparableShot(shot, heuristic, the_board)

    # Computes the heuristic of a given board. This is computed in terms of
    # player 1 where a higher score means a better board for player 1.
    def compute_heuristic(self, board: PoolBoard) -> float:
        state = board.get_state()
        if state == PoolState.PLAYER1_WIN:
            return 1000.0
        elif state == PoolState.PLAYER2_WIN:
            return -1000.0

        heuristic = board.player1_pocketed * 5.0
        if board.player1_pocketed == 7:
            heuristic += 15.0
        heuristic -= board.player2_pocketed * 5.0
        if board.player2_pocketed == 7:
            heuristic -= 15.0

        if board.turn == PoolPlayer.PLAYER1:
            heuristic += 50
        else:
            heuristic -= 50

        for ball in board.balls:
            if ball.number == 8:
                if board.player1_pocketed == 7:
                    dist = self.distance_to_closest_pocket(ball)
                    value = 1 / dist
                    heuristic += value
                if board.player2_pocketed == 7:
                    dist = self.distance_to_closest_pocket(ball)
                    value = 1 / dist
                    heuristic -= value
            else:
                dist = self.distance_to_closest_pocket(ball)
                value = min(1 / dist, 1.0)
                if ball.number < 8:
                    heuristic += value
                else:
                    heuristic -= value

        return heuristic

    def distance_to_closest_pocket(self, ball : Ball):
        closest = 999.0
        for pocket in Pool.WORLD.pockets:
            x2 = ball.position[0] - pocket.x
            y2 = ball.position[1] - pocket.y
            dist = x2 * x2 + y2 * y2
            if dist < closest:
                closest = dist
        return math.sqrt(closest)



class RealisticAI(PoolAI):

    def name(self) -> str:
        return "realistic"
    def generate_easy_shots(self, board: PoolBoard):
        angles = []
        for ball in board.balls:
            if board.turn == PoolPlayer.PLAYER1:
                if ball.pocketed == False and ball.number > 0 and ball.number <= 8:
                    vector2 = (ball.position.x - board.cue_ball.position.x, ball.position.y - board.cue_ball.position.y)
                    vector1 = (1,0) 
                    angle = math.atan2(vector2[0], vector2[1]) - math.atan2(vector1[0], vector1[1])
                    angle = math.degrees(angle)
                    angle *= -1
                    angle = (angle + 360) % 360
                    angles.append(angle)
            else:
                if ball.pocketed == False and ball.number >= 8 and ball.number < 16:
                    vector2 = (ball.position.x - board.cue_ball.position.x, ball.position.y - board.cue_ball.position.y)
                    vector1 = (0, 1) 
                    angle = math.atan2(vector2[0], vector2[1]) - math.atan2(vector1[0], vector1[1])
                    
        return angles
    
    def shot_handler(self, board: PoolBoard, magnitudes, angles) -> Shot:
        if board.turn_number == 0:
            return Shot(180, 50, board.cue_ball.position)
        shots = self.compute_best_shots(board, magnitudes, angles)
        
       
        i = 0
        shot_complexity : Complexity = shots[i].complexity
        print("Shot total collisions " + str(shot_complexity.total_collisions))
        print("Shot bank shot modifier " + str(shot_complexity.collisions_with_table))
        
        print(self.compute_shot_heuristic(shots[i].shot, board))
        print("heureistic before " + str(self.compute_heuristic(shots[i].board, board)))
        print("Total heursitic " + str(shots[i].heuristic))
        print("distance before contact" + str(shots[i].complexity.distance_before_contact))
        print("cue ball pocketed: " + str(board.cue_ball.pocketed))

        return shots[0].shot


    # returns the 10 best shots sorted from best to worst
    def compute_best_shots(self, board : PoolBoard, magnitudes, angles, length=10) -> List[ComparableShot]:
        position = board.cue_ball.position
        if board.cue_ball.pocketed:
            while True:
                x = random_float(Constants.BALL_RADIUS + 0.5, Constants.TABLE_WIDTH - Constants.BALL_RADIUS - 0.5)
                y = random_float(Constants.BALL_RADIUS + 0.5, Constants.TABLE_HEIGHT - Constants.BALL_RADIUS - 0.5)
                position = b2Vec2(x, y)
                if Shot.test_cue_ball_position(position, board.balls):
                    break
        queue : List[ComparableShot] = []
        
        easy_shots : List[float] = self.generate_easy_shots(board)
               
        for angle in range(360*3):  
            angle = angle / 3;
            for magnitude in magnitudes:
                if len(queue) % 50 == 0:
                    print(f"Shots generated: {len(queue)}")
                shot = Shot(angle, magnitude, position)
            
                
                if verifyShotReachable(shot, board.balls):
                    shot = self.compute_shot_heuristic(shot, board)
                    for easy_angle in easy_shots:
                        great_shot_lower, great_shot_higher = easy_angle - 0.5, easy_angle + 0.5
                        good_shot_lower, good_shot_higher = easy_angle - 1, easy_angle + 1
                        
                        if angle > great_shot_lower and angle < great_shot_higher:
                            shot.heuristic += Weights.GREAT_SHOT
                            break     
                        elif angle > good_shot_lower and angle < good_shot_higher:
                            shot.heuristic += Weights.GOOD_SHOT
                            break              
                    heapq.heappush(queue, shot)
        shots = []
        for _ in range(length):
            shots.append(heapq.heappop(queue))
        return shots

    def compute_shot_heuristic(self, shot : Shot, original_board : PoolBoard) -> ComparableShot:
        Pool.WORLD.load_board(original_board)
        Pool.WORLD.shoot(shot)
        Pool.WORLD.simulate_until_still(Constants.TIME_STEP, Constants.VEL_ITERS, Constants.POS_ITERS)
        current_board = Pool.WORLD.get_board_state()
        complexity = Pool.WORLD.complexity
        simplicity_heuristic = complexity.compute_complexity_heuristic(current_board)
        heuristic = self.compute_heuristic(current_board, original_board.turn)
        
        if original_board.turn == PoolPlayer.PLAYER1:
            heuristic += (simplicity_heuristic)
            # calc scratches
            if original_board.first_hit == None:
                heuristic -= Weights.SCRATCH
            elif original_board.first_hit.number > 7:
                heuristic -= Weights.SCRATCH
            elif original_board.cue_ball.pocketed:
                heuristic -= Weights.SCRATCH
        else:
            heuristic -= (simplicity_heuristic)
            # calc scratches
            if original_board.first_hit == None:
                heuristic += Weights.SCRATCH
            elif original_board.first_hit.number < 9:
                heuristic += Weights.SCRATCH
            elif original_board.cue_ball.pocketed:
                heuristic += Weights.SCRATCH
                
        if original_board.turn == PoolPlayer.PLAYER2:
            heuristic *= -1.0
        return ComparableShot(shot, heuristic, current_board, complexity)

    # Computes the heuristic of a given board. This is computed in terms of
    # player 1 where a higher score means a better board for player 1.

    def compute_heuristic(self, board: PoolBoard, player : PoolPlayer) -> float:

        state = board.get_state()
        
        if state == PoolState.PLAYER1_WIN:
            return 1000.0
        elif state == PoolState.PLAYER2_WIN:
            return -1000.0
        pocketed_1 = board.player1_pocketed - board.previous_board.player1_pocketed
        pocketed_2 = board.player2_pocketed - board.previous_board.player2_pocketed

        heuristic = 0
        
        if player == PoolPlayer.PLAYER1:
            heuristic += pow(pocketed_1, 0.5) * Weights.POCKETED 
            heuristic -= pow(pocketed_2, 2) * Weights.POCKETED
        else:
            heuristic -= pow(pocketed_1, 2) * Weights.POCKETED 
            heuristic += pow(pocketed_1, 0.5) * Weights.POCKETED

        if board.turn == PoolPlayer.PLAYER1:
            heuristic += Weights.POSSESION
        else:
            heuristic -= Weights.POSSESION

        for ball in board.balls:
            if ball.number == 8:
                if board.player1_pocketed == 7:
                    dist = self.distance_to_closest_pocket(ball)
                    value = 1 / dist
                    heuristic += value
                if board.player2_pocketed == 7:
                    dist = self.distance_to_closest_pocket(ball)
                    value = 1 / dist
                    heuristic -= value
            else:
                dist = self.distance_to_closest_pocket(ball)
                value = min(1 / dist, 1.0)
                if ball.number < 8:
                    heuristic += value
                else:
                    heuristic -= value

        return heuristic

    def distance_to_closest_pocket(self, ball : Ball):
        closest = 999.0
        for pocket in Pool.WORLD.pockets:
            x2 = ball.position[0] - pocket.x
            y2 = ball.position[1] - pocket.y
            dist = x2 * x2 + y2 * y2
            if dist < closest:
                closest = dist
        return math.sqrt(closest)


class DepthAI(SimpleAI):

    def name(self) -> str:
        return "depth"

    def shot_handler(self, board: PoolBoard, magnitudes, angles) -> Shot:
        shots = self.compute_best_shots(board, length=5)
        for shot in shots:
            if shot.board.get_state() == PoolState.ONGOING:
                theory_shot = self.compute_best_shots(shot.board, magnitudes, angles, 1)[0]
                if shot.board.turn != self.player:
                    theory_shot.heuristic *= -1.0
                shot.heuristic = theory_shot.heuristic
        best_shot = shots[0]
        for shot in shots[1:]:
            if shot.heuristic > best_shot.heuristic:
                best_shot = shot
        return best_shot.shot

class NerfedDepthAI(SimpleAI):

    def name(self) -> str:
        return "nerfed depth"

    def shot_handler(self, board: PoolBoard, magnitudes, angles) -> Shot:
        shots = self.compute_best_shots(board, magnitudes, angles, length=5)
        for shot in shots:
            if shot.board.get_state() == PoolState.ONGOING:
                theory_shot = self.compute_best_shots(shot.board, [115], range(0, 360, 2), 1)[0]
                if shot.board.turn != self.player:
                    theory_shot.heuristic *= -1.0
                shot.heuristic = theory_shot.heuristic
        best_shot = shots[0]
        for shot in shots[1:]:
            if shot.heuristic > best_shot.heuristic:
                best_shot = shot
        return best_shot.shot
