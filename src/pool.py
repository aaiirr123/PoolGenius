from Box2D.Box2D import *
from collections import deque
from enum import Enum
import math
import pygame.display
import pygame.draw
import pygame.event
from pygame.locals import (QUIT, KEYDOWN, K_ESCAPE, RESIZABLE, VIDEORESIZE)
import pygame.time
import random
import threading
import time
from typing import List, Tuple

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
        self.position = position
        if number == Constants.CUE_BALL:
            self.color = Drawable.WHITE
        else:
            self.color = Ball.COLORS[(number - 1) % 8]
        self.number = number
        self.pocketed = pocketed
        self.angle = angle

    def __str__(self):
        return f"Ball {self.number}: [x: {self.position[0]:.3f}, y: {self.position[1]:.3f}], pocketed: {self.pocketed}, color: {self.color}"

class CueBall(Ball):

    def __init__(self, position, pocketed = False, angle = 0.0):
        super().__init__(position, Constants.CUE_BALL, pocketed, angle)

class PoolState(Enum):
    ONGOING = 0
    PLAYER1_WIN = 1
    PLAYER2_WIN = 2

class PoolPlayer(Enum):
    PLAYER1 = 1
    PLAYER2 = 2

# Represents a board state, contains position and data of balls and the cue ball
class PoolBoard:

    def __init__(self, cue_ball:CueBall, balls:List[Ball], previous_board:"PoolBoard" = None):
        self.cue_ball = cue_ball
        self.balls = balls
        self.previous_board = previous_board
        self.player1_pocketed = 0
        self.player2_pocketed = 0
        self.eight_ball = None
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
        if self.previous_board is None:
            return PoolPlayer.PLAYER1 if random.random() > 0.5 else PoolPlayer.PLAYER2
        elif self.previous_board.turn == PoolPlayer.PLAYER1:
            if self.cue_ball.pocketed:
                return PoolPlayer.PLAYER2
            elif self.player1_pocketed > self.previous_board.player1_pocketed:
                return PoolPlayer.PLAYER1
            else:
                return PoolPlayer.PLAYER2
        else:
            if self.cue_ball.pocketed:
                return PoolPlayer.PLAYER1
            elif self.player2_pocketed > self.previous_board.player2_pocketed:
                return PoolPlayer.PLAYER2
            else:
                return PoolPlayer.PLAYER1

    def get_state(self) -> PoolState:
        if self.eight_ball.pocketed:
            if self.previous_board is None:
                return PoolState.PLAYER1_WIN if self.turn == PoolPlayer.PLAYER1 else PoolState.PLAYER2_WIN
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
        ls = [f"Cue ball:\n{self.cue_ball}\nBalls:"]
        for ball in self.balls:
            ls.append(str(ball))
        return "\n".join(ls)

# Used in userData
class PoolType(Enum):
    BALL = 1
    POCKET = 2
    WALL = 3

# userData Classes
class PoolData:

    def __init__(self, type):
        self.type = type

class BallData(PoolData):

    def __init__(self, number, pocketed):
        super().__init__(PoolType.BALL)
        self.number = number
        self.pocketed = pocketed  

# This can be used to simulate a given shot constructed from a PoolBoard
class PoolWorld(b2ContactListener):

    def BeginContact(self, contact:b2Contact):
        data1 = contact.fixtureA.body.userData
        data2 = contact.fixtureB.body.userData
        type1 = data1.type
        type2 = data2.type
        # Pocket the ball if it comes into contact with a pocket
        if type1 == PoolType.BALL and type2 == PoolType.POCKET:
            data1.pocketed = True
        elif type2 == PoolType.BALL and type1 == PoolType.POCKET:
            data2.pocketed = True

    def __init__(self, board:PoolBoard):
        super().__init__()
        self.world = b2World(gravity=(0, 0), doSleep=True)
        # Using a deque as a linked list improves performance
        # Due to needing multiple remove() calls
        self.balls : deque[b2Body] = deque()
        self.pocketed_balls : List[Ball] = []
        self.pockets : List[Point] = []
        self.drawables : List[Drawable] = []

        self.initial_board = board

        self.world.autoClearForces = True
        self.world.contactListener = self

        # Create the balls

        # constants taken from here:
        # https://github.com/agarwl/eight-ball-pool/blob/master/src/dominos.cpp
        self.ball_fd = b2FixtureDef(shape=b2CircleShape(radius=Constants.BALL_RADIUS))
        self.ball_fd.density = 1.0
        self.ball_fd.friction = 0.2
        self.ball_fd.restitution = 0.8

        if not board.cue_ball.pocketed:
            self.cue_ball = self.create_ball(board.cue_ball)
            self.drawables.append(Drawable(self.cue_ball, board.cue_ball.color, Drawable.draw_billiard_ball, outline_color=Drawable.BLACK))
        else:
            self.cue_ball = None
            self.pocketed_balls.append(board.cue_ball)

        for b in board.balls:
            if not b.pocketed:
                ball = self.create_ball(b)
                self.drawables.append(Drawable(ball, b.color, Drawable.draw_billiard_ball))
            else:
                self.pocketed_balls.append(b)

        # Create the pockets
        
        # Create the points for each pocket
        for i in range(6):
            n = i % 3
            if n == 0:
                x = Constants.POCKET_RADIUS
            elif n == 1:
                x = Constants.TABLE_WIDTH / 2
            else:
                x = Constants.TABLE_WIDTH - Constants.POCKET_RADIUS
            y = Constants.POCKET_RADIUS if i <= 2 else Constants.TABLE_HEIGHT - Constants.POCKET_RADIUS
            self.pockets.append(Point(x, y))
        
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
        
        self.create_boundary_wall(top_left, top_middle, True)
        self.create_boundary_wall(top_middle, top_right, True)
        self.create_boundary_wall(top_right, bottom_right, False)
        self.create_boundary_wall(Point(top_left.x - Constants.POCKET_RADIUS, top_left.y), Point(bottom_left.x - Constants.POCKET_RADIUS, bottom_left.y), False)
        self.create_boundary_wall(Point(bottom_left.x, bottom_left.y + Constants.POCKET_RADIUS), Point(bottom_middle.x, bottom_middle.y + Constants.POCKET_RADIUS), True)
        self.create_boundary_wall(Point(bottom_middle.x, bottom_middle.y + Constants.POCKET_RADIUS), Point(bottom_right.x, bottom_right.y + Constants.POCKET_RADIUS), True)

    def shoot(self, shot:Shot):
        if self.cue_ball is None:
            self.cue_ball = self.create_ball(CueBall(shot.cue_ball_position))
            self.pocketed_balls.remove(self.initial_board.cue_ball)
            self.drawables.append(Drawable(self.cue_ball, self.initial_board.cue_ball.color, Drawable.draw_billiard_ball, outline_color=Drawable.BLACK))
        self.cue_ball.ApplyForce(shot.calculate_force(), self.cue_ball.localCenter, True)

    def create_ball(self, b:Ball) -> b2Body:
        ball:b2Body = self.world.CreateDynamicBody(position=b.position, angle=b.angle, fixtures=self.ball_fd)
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
        to_remove:List[b2Body] = []
        for ball in self.balls:
            if ball.userData.pocketed:
                to_remove.append(ball)
            elif not moving and (ball.linearVelocity.x > 0.001 or ball.linearVelocity.x < -0.001 or ball.linearVelocity.y > 0.001 or ball.linearVelocity.y < -0.001):
                moving = True
        for ball in to_remove:
            self.balls.remove(ball)
            self.pocketed_balls.append(Ball([0, 0], ball.userData.number, True))
            self.world.DestroyBody(ball)
        return moving

    def simulate_until_still(self, time_step, vel_iters, pos_iters):
        still_frames = 0
        while still_frames < 3:
            if not self.update_physics(time_step, vel_iters, pos_iters):
                still_frames += 1
            else:
                still_frames = 0

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
                cue_ball = CueBall(ball.position, False, ball.angle)
            else:
                balls.append(Ball(ball.position, ball.userData.number, False, ball.angle))
        if cue_ball is None:
            raise Exception("Cue ball doesn't exist")
        return PoolBoard(cue_ball, balls, self.initial_board)

class Pool:

    def __init__(self):
        pygame.init()

        self.screen = ScreenInfo(pygame.display.set_mode((Constants.WIDTH, (Constants.HEIGHT * 9) // 8)), Constants.WIDTH, Constants.HEIGHT, 0, 0, 0)
        pygame.display.set_caption("Billiards")
        self.clock = pygame.time.Clock()

        self.update_screen()

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

    def update_graphics(self, world:PoolWorld):
        # Fill in background
        self.screen.screen.fill(Drawable.BILLIARD_GREEN)

        # Draw the separately pockets (because they don't actually exist)
        for pt in world.pockets:
            x = pt.x * self.screen.ppm
            y = pt.y * self.screen.ppm
            position = [x + self.screen.offset_x, self.screen.screen_height - y - self.screen.offset_y]
            pygame.draw.circle(self.screen.screen, Drawable.BLACK, position, Constants.POCKET_RADIUS * self.screen.ppm)

        # Draw drawables
        for drawable in world.drawables:
            drawable.draw(self.screen)

        # Draw the pocketed balls at the bottom of the screen
        for ball in world.pocketed_balls:
            r = Constants.BALL_RADIUS * self.screen.ppm
            h = self.screen.screen.get_height()
            y = h - (h - self.screen.screen_height) // 2
            x = (ball.number + 0.5) / 16 * self.screen.screen_width
            Drawable.draw_billiard_ball_helper([x, y], r, self.screen, ball.color, Drawable.WHITE if ball.number != Constants.CUE_BALL else Drawable.BLACK, ball.number, 0)

        # Draw which players turn it is (blue bar if player 1, red bar if player 2)
        width = self.screen.screen.get_width() // 2
        h = self.screen.screen.get_height()
        height = h // 96
        top = h - height
        if world.initial_board.turn == PoolPlayer.PLAYER1:
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
        #board = self.generate_normal_board()
        #shot = Shot(random_float(165, 195), random_float(100, 150))
        # world = PoolWorld(board, shot)
        # t0 = time.time()
        # world.simulate_until_still(Constants.TIME_STEP, Constants.VEL_ITERS, Constants.POS_ITERS)
        # t1 = time.time()
        # print(f"estimated shot time taken: {t1 - t0} s")
        # self.update_graphics(world)
        # pygame.time.wait(3000)

        player1 = ai.RandomAI(PoolPlayer.PLAYER1)
        player2 = ai.RandomAI(PoolPlayer.PLAYER2)
        shot_queue = []
        ai_thinking = False
        simulating = False
        game_over = False

        #world = PoolWorld(board, shot)
        board = self.generate_normal_board()
        print(f"Turn: {board.turn}")
        world = PoolWorld(board)

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
            
            if not game_over:
                if not simulating and not ai_thinking and len(shot_queue) == 0:
                    target = player1.take_shot if board.turn == PoolPlayer.PLAYER1 else player2.take_shot
                    threading.Thread(target=target, args=(board, shot_queue)).start()
                    ai_thinking = True
                elif len(shot_queue) > 0:
                    ai_thinking = False
                    simulating = True
                    shot = shot_queue.pop()
                    world.shoot(shot)
                
                if simulating:
                    if not world.update_physics(Constants.TIME_STEP, Constants.VEL_ITERS, Constants.POS_ITERS):
                        still_frames += 1
                    else:
                        still_frames = 0
                    if still_frames > 3:
                        board = world.get_board_state()
                        state = board.get_state()
                        if state == PoolState.ONGOING:
                            print(f"Turn: {board.turn}")
                            world = PoolWorld(board)
                            simulating = False
                        else:
                            print(f"Outcome: {state}")
                            game_over = True

            self.update_graphics(world)
                        
        pygame.quit()

if __name__ == "__main__":
    pool = Pool()
    pool.run()