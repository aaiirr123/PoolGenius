from Box2D.Box2D import *
from collections import deque
from datetime import datetime
from enum import IntEnum
import json
import math
import os.path
from pathlib import Path
import pygame.display
import pygame.draw
import pygame.event
from pygame.locals import (QUIT, KEYDOWN, K_ESCAPE, RESIZABLE, VIDEORESIZE)
import pygame.time
import random
import threading
from typing import List, Set, Tuple

import ai
from constants import Constants
from drawable import Drawable, ScreenInfo

def random_float(bottom, top):
    return random.random() * (top - bottom) + bottom

class Point:
    def __init__(self, x:int, y:int):
        self.x = x
        self.y = y

    def __getitem__(self, n):
        if n == 0:
            return self.x
        elif n == 1:
            return self.y
        else:
            raise IndexError

    def to_tuple(self):
        return (self.x, self.y)

class Shot:

    def __init__(self, angle:float, magnitude:float, cue_ball_position: Tuple[float, float] = None):
        self.angle = angle
        self.magnitude = magnitude
        self.cue_ball_position = cue_ball_position

    def calculate_force(self):
        rads = math.radians(self.angle)
        return b2Vec2(math.cos(rads) * self.magnitude, math.sin(rads) * self.magnitude)

    def __str__(self):
        return f"Angle: {self.angle} degrees, magnitude: {self.magnitude} N"

    @staticmethod
    def test_cue_ball_position(cue_ball_position, balls : List["Ball"]) -> bool:
        r_squared = Constants.BALL_RADIUS * Constants.BALL_RADIUS
        cue_x = cue_ball_position[0]
        cue_y = cue_ball_position[1]
        for ball in balls:
            if ball.pocketed:
                continue
            dist_x = cue_x - ball.position[0]
            dist_y = cue_y - ball.position[1]
            if dist_x * dist_x + dist_y * dist_y <= r_squared:
                return False
        return True

# Ball class, contains the color, number, starting position, and whether the
# ball has been pocketed or not
class Ball:

    COLORS = [Drawable.YELLOW, Drawable.BLUE, Drawable.RED, Drawable.PURPLE, Drawable.ORANGE, Drawable.GREEN, Drawable.BURGUNDY, Drawable.BLACK]

    def __init__(self, position, number, pocketed = False, angle = 0.0):
        self.position = b2Vec2(position[0], position[1])
        if number == Constants.CUE_BALL:
            self.color = Drawable.WHITE
        else:
            self.color = Ball.COLORS[(number - 1) % 8]
        self.number = number
        self.pocketed = pocketed
        self.angle = angle

    def __str__(self):
        return f"Ball {self.number}: [x: {self.position[0]:.3f}, y: {self.position[1]:.3f}], pocketed: {self.pocketed}, color: {self.color}"

    @staticmethod
    def from_b2_body(body : b2Body):
        if body.userData.number == Constants.CUE_BALL:
            return CueBall(body.position, body.userData.pocketed, body.angle)
        else:
            return Ball(body.position, body.userData.number, body.userData.pocketed, body.angle)

class CueBall(Ball):

    def __init__(self, position, pocketed = False, angle = 0.0):
        super().__init__(position, Constants.CUE_BALL, pocketed, angle)

class PoolState(IntEnum):
    ONGOING = 0
    PLAYER1_WIN = 1
    PLAYER2_WIN = 2

class PoolPlayer(IntEnum):
    PLAYER1 = 1
    PLAYER2 = 2

# Represents a board state, contains position and data of balls and the cue ball
class PoolBoard:

    def __init__(self, cue_ball:CueBall, balls:List[Ball], previous_board:"PoolBoard" = None):
        self.cue_ball = cue_ball
        self.balls = balls
        self.previous_board = previous_board
        self.first_hit : Ball = None
        self.player1_pocketed = 0
        self.player2_pocketed = 0
        self.eight_ball : Ball = None
        self.turn_number = 0 if previous_board is None else previous_board.turn_number + 1
        for ball in self.balls:
            if ball.number == 8:
                self.eight_ball = ball
            elif ball.pocketed and ball.number != Constants.CUE_BALL:
                if ball.number < 8:
                    self.player1_pocketed += 1
                else:
                    self.player2_pocketed += 1
        self.turn = self._get_turn()

    def _get_turn(self) -> PoolPlayer:
        if self.turn_number == 0:
            return PoolPlayer.PLAYER1 if random.random() > 0.5 else PoolPlayer.PLAYER2
        elif self.turn_number == 1:
            if self.previous_board.turn == PoolPlayer.PLAYER1:
                return PoolPlayer.PLAYER1 if not self.cue_ball.pocketed else PoolPlayer.PLAYER2
            else:
                return PoolPlayer.PLAYER2 if not self.cue_ball.pocketed else PoolPlayer.PLAYER1
        first_hit = self.previous_board.first_hit
        if self.previous_board.turn == PoolPlayer.PLAYER1:
            if self.cue_ball.pocketed or first_hit is None or first_hit.number > 7 or (first_hit.number == 8 and self.previous_board.player1_pocketed != 7) or self.player1_pocketed <= self.previous_board.player1_pocketed:
                return PoolPlayer.PLAYER2
            else:
                return PoolPlayer.PLAYER1
        else:
            if self.cue_ball.pocketed or first_hit is None or first_hit.number < 9 or (first_hit.number == 8 and self.previous_board.player2_pocketed != 7) or self.player2_pocketed <= self.previous_board.player2_pocketed:
                return PoolPlayer.PLAYER1
            else:
                return PoolPlayer.PLAYER2

    def get_state(self) -> PoolState:
        if self.eight_ball.pocketed:
            if self.cue_ball.pocketed:
                if self.previous_board.turn == PoolPlayer.PLAYER1:
                    return PoolState.PLAYER2_WIN
                else:
                    return PoolState.PLAYER1_WIN
            elif self.previous_board.turn == PoolPlayer.PLAYER1:
                if self.previous_board.player1_pocketed == 7:
                    return PoolState.PLAYER1_WIN
                else:
                    return PoolState.PLAYER2_WIN
            else:
                if self.previous_board.player2_pocketed == 7:
                    return PoolState.PLAYER2_WIN
                else:
                    return PoolState.PLAYER1_WIN
        return PoolState.ONGOING

    def __str__(self):
        ls = [f"Turn number: {self.turn_number}"]
        if self.previous_board is not None:
            ls.append(f"Prev board first hit: {self.previous_board.first_hit}")
        ls.append(f"Cue ball:\n{self.cue_ball}\nBalls:")
        for ball in self.balls:
            ls.append(str(ball))
        return "\n".join(ls)

# Used in userData
class PoolType(IntEnum):
    BALL = 1
    POCKET = 2
    WALL = 3

# userData Classes
class PoolData:

    def __init__(self, type : PoolType):
        self.type = type

class BallData(PoolData):

    def __init__(self, number : int, pocketed : bool):
        super().__init__(PoolType.BALL)
        self.number = number
        self.pocketed = pocketed  

# This can be used to simulate a given shot constructed from a PoolBoard
class PoolWorld(b2ContactListener):

    def __init__(self):
        super().__init__()
        # Using a deque as a linked list improves performance
        # Due to needing multiple remove() calls
        self.balls : deque[b2Body] = deque()
        self.pocketed_balls : List[Ball] = []
        self.drawables : List[Drawable] = []
        self.pockets = PoolWorld.create_pockets()

        self.to_remove : Set[b2Body] = set()

        self.board : PoolBoard = None
        self.cue_ball : b2Body = None

        self.world = b2World(gravity=(0, 0), doSleep=True)
        self.world.autoClearForces = True
        self.world.contactListener = self
        
        # Create the pocket fixtures which are sensors
        # The radius is such that a collision only occurs when the center of the ball
        # overlaps with the edge of the pocket
        pocket_fd = b2FixtureDef(shape=b2CircleShape(radius=Constants.POCKET_RADIUS - Constants.BALL_RADIUS))
        pocket_fd.isSensor = True
        for pocket in self.pockets:
            body:b2Body = self.world.CreateStaticBody(
                position=pocket.to_tuple(),
                fixtures=pocket_fd
            )
            body.userData = PoolData(PoolType.POCKET)
            self.drawables.append(Drawable(body, Drawable.BLUE, Drawable.draw_circle, outline_color=Drawable.RED))

        # Create the edges of the pool table
        top_left = self.pockets[0]
        top_middle = self.pockets[1]
        top_right = self.pockets[2]
        bottom_left = self.pockets[3]
        bottom_middle = self.pockets[4]
        bottom_right = self.pockets[5]
        
        thickness = Constants.POCKET_RADIUS
        self.create_boundary_wall(top_left, top_middle, True)
        self.create_boundary_wall(Point(top_middle.x, top_middle.y + 0.1), top_right, True)
        self.create_boundary_wall(top_right, bottom_right, False)
        self.create_boundary_wall(Point(top_left.x - thickness, top_left.y), Point(bottom_left.x - thickness, bottom_left.y), False)
        self.create_boundary_wall(Point(bottom_left.x, bottom_left.y + thickness), Point(bottom_middle.x, bottom_middle.y + thickness), True)
        self.create_boundary_wall(Point(bottom_middle.x, bottom_middle.y + thickness - 0.1), Point(bottom_right.x, bottom_right.y + thickness), True)

    def BeginContact(self, contact:b2Contact):
        body1 : b2Body = contact.fixtureA.body
        body2 : b2Body = contact.fixtureB.body
        data1 : BallData = body1.userData
        data2 : BallData = body2.userData
        type1 = data1.type
        type2 = data2.type
        # Pocket the ball if it comes into contact with a pocket
        if type1 == PoolType.BALL and type2 == PoolType.POCKET:
            data1.pocketed = True
            self.to_remove.add(body1)
        elif type2 == PoolType.BALL and type1 == PoolType.POCKET:
            data2.pocketed = True
            self.to_remove.add(body2)
        elif self.board.first_hit is None and type1 == PoolType.BALL and type2 == PoolType.BALL:
            if data1.number == Constants.CUE_BALL:
                self.board.first_hit = Ball.from_b2_body(body2)
            elif data2.number == Constants.CUE_BALL:
                self.board.first_hit = Ball.from_b2_body(body1)

    def load_board(self, board : PoolBoard):
        self.board = board
        for ball in self.balls:
            self.world.DestroyBody(ball)
        self.balls = deque()
        self.pocketed_balls = []
        if not board.cue_ball.pocketed:
            self.cue_ball = self.create_ball(board.cue_ball)
        else:
            self.cue_ball = None
            self.pocketed_balls.append(board.cue_ball)

        for b in board.balls:
            if not b.pocketed:
                ball = self.create_ball(b)
            else:
                self.pocketed_balls.append(b)
        
        self.first_hit = None

    def shoot(self, shot:Shot):
        self.board.first_hit = None
        if self.cue_ball is None:
            self.cue_ball = self.create_ball(CueBall(shot.cue_ball_position))
            self.pocketed_balls.remove(self.board.cue_ball)
        self.cue_ball.ApplyForce(shot.calculate_force(), self.cue_ball.localCenter, True)

    def create_ball(self, b:Ball) -> b2Body:
        # constants taken from here:
        # https://github.com/agarwl/eight-ball-pool/blob/master/src/dominos.cpp
        ball_fd = b2FixtureDef(shape=b2CircleShape(radius=Constants.BALL_RADIUS))
        ball_fd.density = 1.0
        ball_fd.friction = 0.2
        ball_fd.restitution = 0.8
    
        ball:b2Body = self.world.CreateDynamicBody(position=b.position, angle=b.angle, fixtures=ball_fd)
        ball.bullet = True
        ball.linearDamping = 0.6
        ball.angularDamping = 0.6
        ball.userData = BallData(b.number, False)
        self.balls.append(ball)
        return ball

    def create_boundary_wall(self, pocket1:Point, pocket2:Point, horizontal:bool):
        vertices = []
        diff = Constants.POCKET_RADIUS + 0.05
        thickness = Constants.POCKET_RADIUS
        if horizontal:
            vertices.append((pocket1.x + diff, pocket1.y))
            vertices.append((pocket2.x - diff, pocket1.y))
            vertices.append((pocket2.x - diff, pocket1.y - thickness))
            vertices.append((pocket1.x + diff, pocket1.y - thickness))
        else:
            vertices.append((pocket1.x, pocket1.y + diff))
            vertices.append((pocket1.x, pocket2.y - diff))
            vertices.append((pocket1.x + thickness, pocket2.y - diff))
            vertices.append((pocket1.x + thickness, pocket1.y + diff))
        vertices.append(vertices[0])
        fixture = b2FixtureDef(shape=b2ChainShape(vertices_chain=vertices))
        body:b2Body = self.world.CreateStaticBody(fixtures=fixture)
        body.userData = PoolData(PoolType.WALL)
        self.drawables.append(Drawable(body, Drawable.BROWN, Drawable.draw_rect, outline_color=(25, 14, 16)))

    def update_physics(self, time_step, vel_iters, pos_iters):
        # Make Box2D simulate the physics of our world for one step.
        self.world.Step(time_step, vel_iters, pos_iters)

        moving = False
        for ball in self.balls:
            if ball.linearVelocity.x > 0.001 or ball.linearVelocity.x < -0.001 or ball.linearVelocity.y > 0.001 or ball.linearVelocity.y < -0.001:
                moving = True
                break
        for ball in self.to_remove:
            self.pocketed_balls.append(Ball.from_b2_body(ball))
            self.balls.remove(ball)
            self.world.DestroyBody(ball)
        self.to_remove.clear()
        return moving

    def simulate_until_still(self, time_step, vel_iters, pos_iters, max_seconds=15):
        steps = 0
        still_frames = 0
        max_steps = int(max_seconds / time_step)
        while steps < max_steps and still_frames < 3:
            if not self.update_physics(time_step, vel_iters, pos_iters):
                still_frames += 1
            else:
                still_frames = 0
            steps += 1

    def get_board_state(self):
        cue_ball = None
        balls = []
        for ball in self.pocketed_balls:
            if ball.number == Constants.CUE_BALL:
                cue_ball = ball
            else:
                balls.append(ball)
        for ball in self.balls:
            if ball.userData.number == Constants.CUE_BALL:
                cue_ball = Ball.from_b2_body(ball)
            else:
                balls.append(Ball.from_b2_body(ball))
        if cue_ball is None:
            raise Exception("Cue ball doesn't exist")
        return PoolBoard(cue_ball, balls, self.board)

    def get_graphics(self):
        return PoolGraphics(self.pockets, self.drawables, self.pocketed_balls, [Ball.from_b2_body(body) for body in self.balls], self.board)

    @staticmethod
    def create_pockets() -> List[Point]:
        pockets = []
        for i in range(6):
            n = i % 3
            if n == 0:
                x = Constants.POCKET_RADIUS
            elif n == 1:
                x = Constants.TABLE_WIDTH / 2
            else:
                x = Constants.TABLE_WIDTH - Constants.POCKET_RADIUS
            if i == 1:
                y = Constants.POCKET_RADIUS - 0.1
            elif i == 4:
                y = Constants.TABLE_HEIGHT - Constants.POCKET_RADIUS + 0.1
            else:
                y = Constants.POCKET_RADIUS if i <= 2 else Constants.TABLE_HEIGHT - Constants.POCKET_RADIUS
            pockets.append(Point(x, y))
        return pockets

class PoolGraphics:

    def __init__(self, pockets : List[Point], drawables : List[Drawable], pocketed_balls : List[Ball], unpocketed_balls : List[Ball], board : PoolBoard):
        self.pockets = pockets
        self.drawables = drawables
        self.pocketed_balls = pocketed_balls
        self.unpocketed_balls = unpocketed_balls
        self.board = board

class GameLog:

    def __init__(self, player1, player2):
        self.player1_time = 0.0
        self.player2_time = 0.0
        self.boards : List[PoolBoard] = []
        self.player1 = player1
        self.player2 = player2

    def add_player_1_time(self, time):
        self.player1_time += time

    def add_player_2_time(self, time):
        self.player2_time += time

    def add_board(self, board : PoolBoard):
        self.boards.append(board)

    def get_break_shotter(self) -> PoolPlayer:
        if not self.boards:
            return None
        return self.boards[0].turn

    def get_winner(self) -> PoolPlayer:
        if not self.boards:
            return None
        state = self.boards[-1].get_state()
        if state == PoolState.PLAYER1_WIN:
            return PoolPlayer.PLAYER1
        elif state == PoolState.PLAYER2_WIN:
            return PoolPlayer.PLAYER2
        else:
            return None

class Pool:

    WORLD = PoolWorld()

    def __init__(self):
        pygame.init()

        s_fname = "settings.json"
        if not os.path.exists(s_fname):
            with open(s_fname, "w") as file:
                json.dump({"width": 1280}, file)

        with open(s_fname, "r") as file:
            width = int(json.load(file)["width"])
            Constants.WIDTH = width
            Constants.HEIGHT = width // 2

        self.screen = ScreenInfo(pygame.display.set_mode((Constants.WIDTH, (Constants.HEIGHT * 9) // 8)), Constants.WIDTH, Constants.HEIGHT, 0, 0, 0)
        pygame.display.set_caption("Billiards")
        self.clock = pygame.time.Clock()

        self.update_screen()

        self.log_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S.csv")
        self.log_folder = Path("../logs/").resolve()
        with open(self.log_folder / self.log_name, "w") as file:
            file.write("first turn,player1 time,player2 time,player1 shots,player2 shots,outcome,ai1,ai2\n")

    def log(self, game_log : GameLog):
        with open(self.log_folder / self.log_name, "a") as file:
            items = []
            items.append(game_log.get_break_shotter().name)
            items.append(f"{game_log.player1_time:.3f}")
            items.append(f"{game_log.player2_time:.3f}")
            player1_shots = 0
            player2_shots = 0
            for board in game_log.boards[:-1]:
                if board.turn == PoolPlayer.PLAYER1:
                    player1_shots += 1
                else:
                    player2_shots += 1
            items.append(str(player1_shots))
            items.append(str(player2_shots))
            winner = game_log.get_winner()
            if winner is not None:
                items.append(winner.name)
            else:
                items.append("n/a")
            items.append(game_log.player1.name())
            items.append(game_log.player2.name())
            file.write(",".join(items) + "\n")

    def update_screen(self):
        # update ppm
        if self.screen.screen_width / self.screen.screen_height <= Constants.TABLE_RATIO:
            self.screen.ppm = self.screen.screen_width / Constants.TABLE_WIDTH
        else:
            self.screen.ppm = self.screen.screen_height / Constants.TABLE_HEIGHT

        # update offsets
        ratio = self.screen.screen_width / self.screen.screen_height
        if ratio == Constants.TABLE_RATIO:
            self.screen.offset_x = 0
            self.screen.offset_y = 0
        elif ratio > Constants.TABLE_RATIO:
            self.screen.offset_x = int(self.screen.screen_width - (Constants.TABLE_RATIO * self.screen.screen_height)) // 2
            self.screen.offset_y = 0
        else:
            self.screen.offset_x = 0
            self.screen.offset_y = int((self.screen.screen_height - (self.screen.screen_width / Constants.TABLE_RATIO))) // 2

    def update_graphics(self, graphics:PoolGraphics):
        # Fill in background
        self.screen.screen.fill(Drawable.BILLIARD_GREEN)

        # Draw the separately pockets (because they don't actually exist)
        for pt in graphics.pockets:
            x = pt.x * self.screen.ppm
            y = pt.y * self.screen.ppm
            position = [x + self.screen.offset_x, self.screen.screen_height - y - self.screen.offset_y]
            pygame.draw.circle(self.screen.screen, Drawable.BLACK, position, Constants.POCKET_RADIUS * self.screen.ppm)

        # Draw drawables
        for drawable in graphics.drawables:
            drawable.draw(self.screen)

        # Draw the pocketed balls at the bottom of the screen
        for ball in graphics.pocketed_balls:
            r = Constants.BALL_RADIUS * self.screen.ppm
            h = self.screen.screen.get_height()
            y = h - (h - self.screen.screen_height) // 2
            x = (ball.number + 0.5) / 16 * self.screen.screen_width
            Drawable.draw_billiard_ball_helper([x, y], r, self.screen, ball.color, Drawable.WHITE if ball.number != Constants.CUE_BALL else Drawable.BLACK, ball.number, 0)

        for ball in graphics.unpocketed_balls:
            r = Constants.BALL_RADIUS * self.screen.ppm
            x = ball.position[0] * self.screen.ppm
            y = ball.position[1] * self.screen.ppm
            Drawable.draw_billiard_ball_helper([x, y], r, self.screen, ball.color, Drawable.WHITE if ball.number != Constants.CUE_BALL else Drawable.BLACK, ball.number, ball.angle)

        # Draw which players turn it is (blue bar if player 1, red bar if player 2)
        if graphics.board.get_state() == PoolState.ONGOING:
            width = self.screen.screen.get_width() // 2
            h = self.screen.screen.get_height()
            height = h // 96
            top = h - height
            if graphics.board.turn == PoolPlayer.PLAYER1:
                left = 0
                color = Drawable.BLUE
            else:
                left = width
                color = Drawable.RED
            pygame.draw.rect(self.screen.screen, color, [left, top, width, height])

        # Flip the screen and try to keep at the target FPS
        pygame.display.flip()
        self.clock.tick(Constants.TICK_RATE)

    def generate_random_board(self) -> PoolBoard:
        balls = []
        for i in range(8):
            balls.append(Ball([random_float(0.5, Constants.TABLE_WIDTH - 0.5), random_float(0.5, Constants.TABLE_HEIGHT - 0.5)], i))
        
        return PoolBoard(CueBall([2.5, 2.5]), balls)

    def generate_normal_board(self) -> PoolBoard:
        mid_x = Constants.TABLE_WIDTH / 4 - Constants.BALL_RADIUS
        mid_y = Constants.TABLE_HEIGHT / 2

        balls = []
        diameter = 2 * Constants.BALL_RADIUS

        # Randomize the order of the balls but make sure the 8 ball
        # is in the center
        order = []
        for i in range(1, 8):
            order.append(i)

        for i in range(9, 16):
            order.append(i)

        random.shuffle(order)
        order.insert(4, 8)

        # Generate 15 balls placed in a triangle like in a normal
        # billiards game
        for i in range(15):
            x = mid_x
            y = mid_y
            if i == 0:
                pass
            elif i < 3:
                x -= diameter * 0.85
                y += diameter * (i - 2) + Constants.BALL_RADIUS
            elif i < 6:
                x -= 2 * diameter * 0.85
                y += diameter * (i - 4)
            elif i < 10:
                x -= 3 * diameter * 0.85
                y += diameter * (i - 8) + Constants.BALL_RADIUS
            else:
                x = mid_x - 4 * diameter * 0.85
                y += diameter * (i - 12)
            balls.append(Ball([x, y], order[i]))
        
        return PoolBoard(CueBall([Constants.TABLE_WIDTH * 0.75, mid_y]), balls)

    def run(self):
        player1 = ai.SimpleAI(PoolPlayer.PLAYER1)
        player2 = ai.NerfedDepthAI(PoolPlayer.PLAYER2)
        shot_queue = []
        ai_thinking = False
        simulating = False
        fast_forward = True

        board = self.generate_normal_board()
        print(f"Turn: {board.turn}")
        Pool.WORLD.load_board(board)
        graphics = Pool.WORLD.get_graphics()

        log = GameLog(player1, player2)

        still_frames = 0
        # game loop
        running = True
        while running:
            # Check the event queue
            for event in pygame.event.get():
                if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                    # The user closed the window or pressed escape
                    running = False
                elif event.type == VIDEORESIZE:
                    self.screen.screen_height = event.h
                    self.screen.screen_width = event.w
                    self.update_screen()
                    self.screen.screen = pygame.display.set_mode((self.screen.screen_width, self.screen.screen_height), RESIZABLE)
            
            if not simulating and not ai_thinking and len(shot_queue) == 0:
                target = player1.take_shot if board.turn == PoolPlayer.PLAYER1 else player2.take_shot
                threading.Thread(target=target, args=(board, shot_queue)).start()
                ai_thinking = True
            elif len(shot_queue) > 0:
                ai_thinking = False
                simulating = True
                shot, time = shot_queue.pop()
                if board.turn == PoolPlayer.PLAYER1:
                    log.add_player_1_time(time)
                else:
                    log.add_player_2_time(time)
                log.add_board(board)
                Pool.WORLD.load_board(board)
                Pool.WORLD.shoot(shot)
            
            if simulating:
                for _ in range(5 if fast_forward else 1):
                    if not Pool.WORLD.update_physics(Constants.TIME_STEP, Constants.VEL_ITERS, Constants.POS_ITERS):
                        still_frames += 1
                    else:
                        still_frames = 0
                graphics = Pool.WORLD.get_graphics()
                if still_frames > 3:
                    board = Pool.WORLD.get_board_state()
                    state = board.get_state()
                    if state == PoolState.ONGOING:
                        print(f"Turn: {board.turn.name}")
                        simulating = False
                    else:
                        print(f"Outcome: {state.name}")
                        log.add_board(board)
                        self.log(log)
                        log = GameLog(player1, player2)
                        board = self.generate_normal_board()
                        simulating = False
                    print(board)
                    Pool.WORLD.load_board(board)
                    graphics = Pool.WORLD.get_graphics()

            self.update_graphics(graphics)

        print("Done!")   
        pygame.quit()

if __name__ == "__main__":
    pool = Pool()
    pool.run()