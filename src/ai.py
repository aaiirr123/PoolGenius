from abc import ABC, abstractmethod
from typing import List
from pool import PoolBoard, Shot, random_float
import time
from constants import Constants

class PoolAI(ABC):

    def take_shot(self, board : PoolBoard, queue : List):
        queue.append(self.shot_handler(board))

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
        