from abc import ABC, abstractmethod
import heapq
import math
import time
from typing import List

from Box2D.Box2D import b2Vec2

from pool import Ball, PoolBoard, Shot, random_float, PoolPlayer, PoolState, Pool
from constants import Constants

class PoolAI(ABC):

    def __init__(self, player : PoolPlayer):
        self.player = player

    def take_shot(self, board : PoolBoard, queue : List):
        print(f"In shot handler: player {self.player}")
        t0 = time.time()
        s = self.shot_handler(board)
        t1 = time.time()
        t = t1 - t0
        print(f"time elapsed taking shot: {t} s")
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
        time.sleep(1)
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

    def __init__(self, shot : Shot, heuristic : float, board : PoolBoard):
        self.shot = shot
        self.heuristic = heuristic
        self.board = board

    def __gt__(self, other):
        return self.heuristic < other.heuristic

    def __lt__(self, other):
        return self.heuristic > other.heuristic

class SimpleAI(PoolAI):

    def name(self) -> str:
        return "simple"

    def shot_handler(self, board: PoolBoard) -> Shot:
        shots = self.compute_best_shots(board)
        for shot in shots:
            print(f"Heuristic: {shot.heuristic}, Shot: {shot.shot}")
        return shots[0].shot

    # returns the 10 best shots sorted from best to worst
    def compute_best_shots(self, board : PoolBoard, magnitudes=[75.0, 100.0, 125.0], angles=range(0, 360), length=10) -> List[ComparableShot]:
        position = None
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
        heuristic = self.compute_heuristic(the_board)
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

class DepthAI(SimpleAI):

    def name(self) -> str:
        return "depth"

    def shot_handler(self, board: PoolBoard) -> Shot:
        shots = self.compute_best_shots(board, length=5)
        for shot in shots:
            if shot.board.get_state() == PoolState.ONGOING:
                theory_shot = self.compute_best_shots(shot.board, [100], range(0, 360, 2), 1)[0]
                if shot.board.turn != self.player:
                    theory_shot.heuristic *= -1.0
                shot.heuristic = theory_shot.heuristic
        best_shot = shots[0]
        for shot in shots[1:]:
            if shot.heuristic > best_shot.heuristic:
                best_shot = shot
        for shot in shots:
            print(f"Heuristic: {shot.heuristic}, Shot: {shot.shot}")
        return best_shot.shot
