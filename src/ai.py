from abc import ABC, abstractmethod
import heapq
import math
import time
import traceback
from typing import List

from pool import Ball, PoolBoard, Shot, random_float, PoolWorld, PoolPlayer, PoolState
from constants import Constants

class PoolAI(ABC):

    def __init__(self, player : PoolPlayer):
        self.player = player

    def take_shot(self, board : PoolBoard, queue : List):
        print(f"In shot handler: player {self.player}")
        try:
            queue.append(self.shot_handler(board))
        except Exception as e:
            traceback.print_tb(e.__traceback__)
            queue.append(Shot(0,0,[3,3]))

    @abstractmethod
    def shot_handler(self, board : PoolBoard) -> Shot:
        pass

class RandomAI(PoolAI):

    def shot_handler(self, board: PoolBoard) -> Shot:
        time.sleep(1)
        shot = Shot(random_float(0, 360), random_float(100, 150))
        if board.cue_ball.pocketed:
            x = -1.0
            y = -1.0
            while True:
                x = random_float(Constants.BALL_RADIUS + 0.5, Constants.TABLE_WIDTH - Constants.BALL_RADIUS - 0.5)
                y = random_float(Constants.BALL_RADIUS + 0.5, Constants.TABLE_HEIGHT - Constants.BALL_RADIUS - 0.5)
                if Shot.test_cue_ball_position((x, y), board.balls):
                    break
            shot.cue_ball_position = (x, y)
        return shot

class ComparableShot:

    def __init__(self, shot : Shot, heuristic : float):
        self.shot = shot
        self.heuristic = heuristic

    def __gt__(self, other):
        return self.heuristic < other.heuristic

    def __lt__(self, other):
        return self.heuristic > other.heuristic

class SimpleAI(PoolAI):

    def __init__(self, player: PoolPlayer):
        super().__init__(player)
        self.pockets = PoolWorld.create_pockets()

    def shot_handler(self, board: PoolBoard) -> Shot:
        position = None
        if board.cue_ball.pocketed:
            x = -1.0
            y = -1.0
            while True:
                x = random_float(Constants.BALL_RADIUS + 0.5, Constants.TABLE_WIDTH - Constants.BALL_RADIUS - 0.5)
                y = random_float(Constants.BALL_RADIUS + 0.5, Constants.TABLE_HEIGHT - Constants.BALL_RADIUS - 0.5)
                if Shot.test_cue_ball_position((x, y), board.balls):
                    break
            position = (x, y)
        queue : List[ComparableShot] = []
        magnitudes = [75, 100, 125]
        max_steps = Constants.TICK_RATE * 8
        for angle in range(0, 360, 2):
            for magnitude in magnitudes:
                if len(queue) % 50 == 0:
                    print(f"Shots generated: {len(queue)}")
                shot = Shot(angle, magnitude, position)
                world = PoolWorld(board)
                world.shoot(shot)
                world.simulate_until_still(Constants.TIME_STEP, Constants.VEL_ITERS, Constants.POS_ITERS, max_steps)
                heapq.heappush(queue, ComparableShot(shot, self.compute_heuristic(world.get_board_state())))
        best = heapq.heappop(queue)
        print(f"Heuristic: {best.heuristic}, Shot: {best.shot}")
        for _ in range(10):
            shot = heapq.heappop(queue)
            print(f"Heuristic: {shot.heuristic}, Shot: {shot.shot}")
        return best.shot

    def compute_heuristic(self, board: PoolBoard) -> float:
        state = board.get_state()
        if state == PoolState.PLAYER1_WIN:
            if self.player == PoolPlayer.PLAYER1:
                return 1000.0
            else:
                return -1000.0
        elif state == PoolState.PLAYER2_WIN:
            if self.player == PoolPlayer.PLAYER1:
                return -1000.0
            else:
                return 1000.0

        heuristic = board.player1_pocketed * 5.0
        heuristic -= board.player2_pocketed * 5.0

        for ball in board.balls:
            if ball.number == 8:
                continue
            dist = self.distance_to_closest_pocket(ball)
            value = min(1 / dist, 1.0)
            if ball.number < 8:
                heuristic += value
            else:
                heuristic -= value

        if self.player == PoolPlayer.PLAYER2:
            heuristic *= -1.0

        if board.cue_ball.pocketed:
            heuristic -= 50

        return heuristic

    def distance_to_closest_pocket(self, ball : Ball):
        closest = 999.0
        for pocket in self.pockets:
            x2 = ball.position[0] - pocket.x
            y2 = ball.position[1] - pocket.y
            dist = x2 * x2 + y2 * y2
            if dist < closest:
                closest = dist
        return math.sqrt(closest)