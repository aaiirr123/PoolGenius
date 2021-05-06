from typing import Callable, List, Tuple
import pygame.display
import pygame.draw
import pygame.event
from pygame.surface import Surface
import pygame.time
from pygame.locals import (QUIT, KEYDOWN, K_ESCAPE, RESIZABLE, VIDEORESIZE)
from Box2D.Box2D import *
import math
import time
import random
from collections import deque

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

class ScreenInfo:
    def __init__(self, screen:Surface, screen_width:int, screen_height:int, offset_x:int, offset_y:int, ppm:float):
        self.screen = screen
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.ppm = ppm

class Drawable:
    BILLIARD_GREEN = 39, 107, 64
    BLACK = 0, 0, 0
    RED = 255, 0, 0
    WHITE = 255, 255, 255
    BROWN = 50, 28, 32
    YELLOW = 255, 215, 0
    BLUE = 0, 0, 255
    PURPLE = 128, 0, 128
    GREEN = 0, 128, 0
    BURGUNDY = 128, 0, 32
    ORANGE = 255, 165, 0

    def __init__(self, body:b2Body, color:Tuple[int, int, int], draw:Callable[[b2Shape, b2Body, Tuple[int, int, int], ScreenInfo, bool, Tuple[int, int, int]], None], outline:bool=True, outline_color:Tuple[int, int, int]=WHITE):
        self.body = body
        self.color = color
        self.draw_func = draw
        self.outline = outline
        self.outline_color = outline_color

    def draw(self, screen:ScreenInfo):
        if self.body.active:
            for fixture in self.body.fixtures:
                self.draw_func(fixture.shape, self.body, self.color, screen, self.outline, self.outline_color)

    # https://github.com/openai/box2d-py/blob/master/examples/simple/simple_02.py
    # for the draw functions
    @staticmethod
    def draw_rect(polygon:b2PolygonShape, body:b2Body, color:Tuple[int, int, int], screen:ScreenInfo, outline:bool, outline_color:Tuple[int, int, int]):
        vertices = [(body.transform * v) * screen.ppm for v in polygon.vertices[:4]]
        vertices = [[x + screen.offset_x, screen.screen_height - y - screen.offset_y] for x, y in vertices]
        if outline:
            vertices.sort(key=lambda x : (x[0], x[1]))
            vertices = [vertices[0], vertices[2], vertices[3], vertices[1]]
            pygame.draw.polygon(screen.screen, outline_color, vertices)
            vertices[0][0] += 2
            vertices[0][1] += 2
            vertices[1][0] -= 2
            vertices[1][1] += 2
            vertices[2][0] -= 2
            vertices[2][1] -= 2
            vertices[3][0] += 2
            vertices[3][1] -= 2
            pygame.draw.polygon(screen.screen, color, vertices)
        else:
            pygame.draw.polygon(screen.screen, color, vertices)

    @staticmethod
    def draw_circle(circle:b2CircleShape, body:b2Body, color:Tuple[int, int, int], screen:ScreenInfo, outline:bool, outline_color:Tuple[int, int, int]):
        x, y = body.transform * circle.pos * screen.ppm
        position = (x + screen.offset_x, screen.screen_height - y - screen.offset_y)
        r = circle.radius * screen.ppm
        if outline:
            pygame.draw.circle(screen.screen, outline_color, position, r)
            pygame.draw.circle(screen.screen, color, position, r - 2)
        else:
            pygame.draw.circle(screen.screen, color, position, r)

    @staticmethod
    def draw_billiard_ball(circle:b2CircleShape, body:b2Body, color:Tuple[int, int, int], screen:ScreenInfo, outline:bool, outline_color:Tuple[int, int, int]):
        x, y = body.transform * circle.pos * screen.ppm
        position = [x + screen.offset_x, screen.screen_height - y - screen.offset_y]
        r = circle.radius * screen.ppm
        # stripes
        if body.userData["num"] > 8:
            pygame.draw.circle(screen.screen, color, position, r)
            pygame.draw.circle(screen.screen, Drawable.WHITE, position, r - 2)

            # draw the stipe using trig to draw straight lines across the circle
            angle = body.transform.angle
            r -= 2.5
            steps = 49
            half = steps // 2
            for i in range(steps):
                converted_angle1 = angle + (i - half) * 0.02
                converted_angle2 = angle + math.pi - (i - half) * 0.02
                x1 = r * math.cos(converted_angle1) + position[0]
                y1 = r * math.sin(converted_angle1) + position[1]
                x2 = r * math.cos(converted_angle2) + position[0]
                y2 = r * math.sin(converted_angle2) + position[1]
                pygame.draw.line(screen.screen, color, (x1, y1), (x2, y2), 3)
            r += 2.5
        # solids
        else:
            pygame.draw.circle(screen.screen, outline_color, position, r)
            pygame.draw.circle(screen.screen, color, position, r - 2)
        pygame.draw.circle(screen.screen, Drawable.WHITE, position, r / 3)

class Shot:

    def __init__(self, angle:float, magnitude:float):
        self.angle = angle
        self.magnitude = magnitude

    def calculate_force(self):
        rads = math.radians(self.angle)
        return b2Vec2(math.cos(rads) * self.magnitude, math.sin(rads) * self.magnitude)

class Ball:

    def __init__(self, position, color, number):
        self.position = position
        self.color = color
        self.number = number

class CueBall(Ball):

    def __init__(self, position, force = None):
        super().__init__(position, Drawable.WHITE, -1)
        self.force = force

class PoolBoard:

    def __init__(self, cue_ball_position, shot:Shot, balls:List[Ball]):
        self.cue_ball = CueBall(cue_ball_position, shot.calculate_force())
        self.balls = balls

class PoolWorld(b2ContactListener):

    BALL = 1
    POCKET = 2
    WALL = 3

    def BeginContact(self, contact):
        body1:b2Body = contact.fixtureA.body
        body2:b2Body = contact.fixtureB.body
        type1 = body1.userData["type"]
        type2 = body2.userData["type"]
        # Pocket the ball if it comes into contact with a pocket
        if type1 == PoolWorld.BALL and type2 == PoolWorld.POCKET:
            body1.userData["pocketed"] = True
        elif type2 == PoolWorld.BALL and type1 == PoolWorld.POCKET:
            body2.userData["pocketed"] = True

    def __init__(self, board:PoolBoard):
        super().__init__()
        self.world = b2World(gravity=(0, 0), doSleep=True)
        # Using a deque as a linked list improves performance
        # Due to needing multiple remove() calls
        self.balls:deque[b2Body] = deque()
        self.pockets:List[Point] = []
        self.drawables:List[Drawable] = []

        self.world.autoClearForces = True
        self.world.contactListener = self

        # Create the balls

        # constants taken from here:
        # https://github.com/agarwl/eight-ball-pool/blob/master/src/dominos.cpp
        ball_fd = b2FixtureDef(shape=b2CircleShape(radius=Pool.BALL_RADIUS))
        ball_fd.density = 1.0
        ball_fd.friction = 0.2
        ball_fd.restitution = 0.85

        for b in board.balls:
            ball = self.create_ball(b, ball_fd)
            self.drawables.append(Drawable(ball, b.color, Drawable.draw_billiard_ball))

        cue_ball = self.create_ball(board.cue_ball, ball_fd)
        cue_ball.ApplyForce(board.cue_ball.force, ball.worldCenter, True)
        self.drawables.append(Drawable(cue_ball, board.cue_ball.color, Drawable.draw_billiard_ball, outline_color=Drawable.BLACK))

        # Create the pockets
        
        # Create the points for each pocket
        for i in range(6):
            n = i % 3
            if n == 0:
                x = Pool.POCKET_RADIUS
            elif n == 1:
                x = Pool.TABLE_WIDTH / 2
            else:
                x = Pool.TABLE_WIDTH - Pool.POCKET_RADIUS
            y = Pool.POCKET_RADIUS if i <= 2 else Pool.TABLE_HEIGHT - Pool.POCKET_RADIUS
            self.pockets.append(Point(x, y))
        
        # Create the pocket fixtures which are sensors
        # The radius is such that a collision only occurs when the center of the ball
        # overlaps with the edge of the pocket
        pocket_fd = b2FixtureDef(shape=b2CircleShape(radius=Pool.POCKET_RADIUS - Pool.BALL_RADIUS))
        pocket_fd.isSensor = True
        for pocket in self.pockets:
            body:b2Body = self.world.CreateStaticBody(
                position=pocket.to_tuple(),
                fixtures=pocket_fd
            )
            body.userData = {"type": PoolWorld.POCKET}
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
        self.create_boundary_wall(Point(top_left.x - Pool.POCKET_RADIUS, top_left.y), Point(bottom_left.x - Pool.POCKET_RADIUS, bottom_left.y), False)
        self.create_boundary_wall(Point(bottom_left.x, bottom_left.y + Pool.POCKET_RADIUS), Point(bottom_middle.x, bottom_middle.y + Pool.POCKET_RADIUS), True)
        self.create_boundary_wall(Point(bottom_middle.x, bottom_middle.y + Pool.POCKET_RADIUS), Point(bottom_right.x, bottom_right.y + Pool.POCKET_RADIUS), True)

        self.still_steps = 0

    def create_ball(self, b:Ball, ball_fd:b2Fixture) -> b2Body:
        ball:b2Body = self.world.CreateDynamicBody(position=b.position, fixtures=ball_fd)
        ball.bullet = True
        ball.linearDamping = 0.6
        ball.angularDamping = 0.6
        ball.userData = {"type": PoolWorld.BALL, "num": b.number, "color": b.color, "pocketed": False}
        self.balls.append(ball)
        return ball

    def create_boundary_wall(self, pocket1:Point, pocket2:Point, horizontal:bool):
        vertices = []
        diff = Pool.POCKET_RADIUS + 0.05
        thickness = Pool.POCKET_RADIUS
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
        body.userData = {"type": PoolWorld.WALL}
        self.drawables.append(Drawable(body, Drawable.BROWN, Drawable.draw_rect, outline_color=(25, 14, 16)))

    def update_physics(self, time_step, vel_iters, pos_iters):
        # Make Box2D simulate the physics of our world for one step.
        self.world.Step(time_step, vel_iters, pos_iters)

        moving = False
        to_remove = []
        for ball in self.balls:
            if ball.userData["pocketed"]:
                to_remove.append(ball)
            elif not moving and (ball.linearVelocity.x > 0.001 or ball.linearVelocity.x < -0.001 or ball.linearVelocity.y > 0.001 or ball.linearVelocity.y < -0.001):
                moving = True
        for ball in to_remove:
            self.balls.remove(ball)
            self.world.DestroyBody(ball)
        if not moving:
            self.still_steps += 1
        else:
            self.still_steps = 0

    def simulate_until_still(self, time_step, vel_iters, pos_iters):
        while self.still_steps < 15:
            self.update_physics(time_step, vel_iters, pos_iters)

class Pool:
    TICK_RATE = 60
    TIME_STEP = 1.0 / TICK_RATE
    VEL_ITERS = 8
    POS_ITERS = 3
    TABLE_WIDTH = 9.0
    TABLE_HEIGHT = 4.5
    TABLE_RATIO = TABLE_WIDTH / TABLE_HEIGHT
    BALL_RADIUS = 2 / 12
    POCKET_RADIUS = 3 / 12

    def __init__(self):
        pygame.init()

        width = 1280
        height = width // 2
        self.screen = ScreenInfo(pygame.display.set_mode((1280, 720)), width, height, 0, 0, 0)
        pygame.display.set_caption("Billiards")
        self.clock = pygame.time.Clock()

        self.update_screen()

    def update_screen(self):
        # update ppm
        if self.screen.screen_width / self.screen.screen_height <= Pool.TABLE_RATIO:
            self.screen.ppm = self.screen.screen_width / Pool.TABLE_WIDTH
        else:
            self.screen.ppm = self.screen.screen_height / Pool.TABLE_HEIGHT

        # update offsets
        ratio = self.screen.screen_width / self.screen.screen_height
        if ratio == Pool.TABLE_RATIO:
            self.screen.offset_x = 0
            self.screen.offset_y = 0
        elif ratio > Pool.TABLE_RATIO:
            self.screen.offset_x = int(self.screen.screen_width - (Pool.TABLE_RATIO * self.screen.screen_height)) // 2
            self.screen.offset_y = 0
        else:
            self.screen.offset_x = 0
            self.screen.offset_y = int((self.screen.screen_height - (self.screen.screen_width / Pool.TABLE_RATIO))) // 2

    def update_graphics(self, world:PoolWorld):
        self.screen.screen.fill(Drawable.BILLIARD_GREEN)

        for pt in world.pockets:
            x = pt.x * self.screen.ppm
            y = pt.y * self.screen.ppm
            position = (x + self.screen.offset_x, self.screen.screen_height - y - self.screen.offset_y)
            pygame.draw.circle(self.screen.screen, Drawable.BLACK, position, Pool.POCKET_RADIUS * self.screen.ppm)

        for drawable in world.drawables:
            drawable.draw(self.screen)

        pygame.display.update()

        # Flip the screen and try to keep at the target FPS
        pygame.display.flip()
        self.clock.tick(Pool.TICK_RATE)

    def random_float(self, bottom, top):
        return random.random() * (top - bottom) + bottom

    def generate_random_board(self) -> PoolBoard:
        colors = [Drawable.YELLOW, Drawable.BLUE, Drawable.RED, Drawable.PURPLE, Drawable.ORANGE, Drawable.GREEN, Drawable.BURGUNDY, Drawable.BLACK]

        balls = []
        for i in range(8):
            balls.append(Ball((self.random_float(0.5, Pool.TABLE_WIDTH - 0.5), self.random_float(0.5, Pool.TABLE_HEIGHT - 0.5)), colors[i], (self.random_float(-300.0, 300.0), self.random_float(-300.0, 300.0))))
        
        return PoolBoard((2.5, 2.5), Shot(0, 0), balls)

    def generate_normal_board(self) -> PoolBoard:
        colors = [Drawable.YELLOW, Drawable.BLUE, Drawable.RED, Drawable.PURPLE, Drawable.ORANGE, Drawable.GREEN, Drawable.BURGUNDY, Drawable.BLACK]

        mid_x = Pool.TABLE_WIDTH / 4 - Pool.BALL_RADIUS
        mid_y = Pool.TABLE_HEIGHT / 2

        balls = []
        diameter = 2 * Pool.BALL_RADIUS

        # Generate 15 balls placed in a triangle like in a normal
        # billiards game
        for i in range(15):
            x = mid_x
            y = mid_y
            if i == 0:
                pass
            elif i < 3:
                x -= diameter * 0.85
                if i == 1:
                    y -= Pool.BALL_RADIUS
                else:
                    y += Pool.BALL_RADIUS
            elif i < 6:
                x -= 2 * diameter * 0.85
                y += diameter * (i - 4)
            elif i < 10:
                x -= 3 * diameter * 0.85
                y += diameter * (i - 8) + Pool.BALL_RADIUS
            else:
                x = mid_x - 4 * diameter * 0.85
                y += diameter * (i - 12)
            balls.append(Ball((x, y), colors[i % 8], i + 1))
        
        # Place cue ball and give it a random shot facing in the general direction
        # of the other balls
        return PoolBoard((Pool.TABLE_WIDTH * 0.75, mid_y), Shot(self.random_float(165, 195), self.random_float(100, 150)), balls)

    def run(self):
        balls = self.generate_normal_board()

        world = PoolWorld(balls)
        t0 = time.time()
        world.simulate_until_still(Pool.TIME_STEP, 6, 2)
        t1 = time.time()
        print(f"estimated shot time taken: {t1 - t0} s")
        self.update_graphics(world)
        pygame.time.wait(3000)

        world = PoolWorld(balls)
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
            
            self.update_graphics(world)
            world.update_physics(Pool.TIME_STEP, Pool.VEL_ITERS, Pool.POS_ITERS)

        pygame.quit()

if __name__ == "__main__":
    pool = Pool()
    pool.run()