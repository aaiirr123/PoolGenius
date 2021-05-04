from typing import Callable, List, Tuple
import pygame.display
import pygame.draw
import pygame.event
from pygame.surface import Surface
import pygame.time
from pygame.locals import (QUIT, KEYDOWN, K_ESCAPE, RESIZABLE, VIDEORESIZE)
import Box2D
from Box2D.Box2D import *
import math
import time

import random

class ScreenInfo:
    def __init__(self, screen:Surface, screen_width:int, screen_height:int, offset_x:int, offset_y:int, ppm:float):
        self.screen = screen
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.ppm = ppm

class Drawable:
    GREEN = 0, 255, 0
    BLACK = 0, 0, 0
    RED = 255, 0, 0

    def __init__(self, body:b2Body, color:Tuple[int, int, int], draw:Callable[[b2Shape, b2Body, Tuple[int, int, int], ScreenInfo], None]):
        self.body = body
        self.color = color
        self.draw_func = draw

    def draw(self, screen:ScreenInfo):
        if self.body.active:
            for fixture in self.body.fixtures:
                self.draw_func(fixture.shape, self.body, self.color, screen)

    # https://github.com/openai/box2d-py/blob/master/examples/simple/simple_02.py
    # for the draw functions
    @staticmethod
    def draw_poly(polygon:b2PolygonShape, body:b2Body, color:Tuple[int, int, int], screen:ScreenInfo):
        vertices = [(body.transform * v) * screen.ppm for v in polygon.vertices]
        vertices = [(x + screen.offset_x, screen.screen_height - y - screen.offset_y) for x, y in vertices]
        pygame.draw.polygon(screen.screen, color, vertices)

    @staticmethod
    def draw_circle(circle:b2CircleShape, body:b2Body, color:Tuple[int, int, int], screen:ScreenInfo):
        x, y = body.transform * circle.pos * screen.ppm
        position = (x + screen.offset_x, screen.screen_height - y - screen.offset_y)
        pygame.draw.circle(screen.screen, color, position, circle.radius * screen.ppm)

class Pool:
    TICK_RATE = 60
    TIME_STEP = 1.0 / TICK_RATE
    VEL_ITERS = 6
    POS_ITERS = 2
    TABLE_WIDTH = 9.0
    TABLE_HEIGHT = 4.5
    TABLE_RATIO = TABLE_WIDTH / TABLE_HEIGHT
    BALL_RADIUS = 2.25 / 12
    POCKET_RADIUS = 2.5 / 12
    POCKET_RADIUS_SQUARED = POCKET_RADIUS * POCKET_RADIUS

    def __init__(self):
        self.world = b2World(gravity=(0, 0), doSleep=True)
        self.drawables:List[Drawable] = []
        self.balls:List[b2Body] = []
        self.pockets:List[Tuple[int, int]] = []

        # constants taken from here:
        # https://github.com/agarwl/eight-ball-pool/blob/master/src/dominos.cpp
        ball_fd = b2FixtureDef(shape=b2CircleShape(radius=Pool.BALL_RADIUS))
        ball_fd.density = 1.0
        ball_fd.friction = 0.2
        ball_fd.restitution = 0.9

        for _ in range(10):
            ball:b2Body = self.world.CreateDynamicBody(position=(random.randint(1, 8), random.randint(1, 4)), fixtures=ball_fd)
            ball.bullet = True
            ball.linearDamping = 0.6
            ball.angularDamping = 0.6
            ball.ApplyForce((random.randint(-300, 300), random.randint(-300, 300)), ball.worldCenter, True)
            ball_drawable = Drawable(ball, Drawable.RED, Drawable.draw_circle)
            self.drawables.append(ball_drawable)
            self.balls.append(ball)

        for i in range(6):
            n = i % 3
            if n == 0:
                x = Pool.POCKET_RADIUS
            elif n == 1:
                x = Pool.TABLE_WIDTH / 2
            else:
                x = Pool.TABLE_WIDTH - Pool.POCKET_RADIUS
            y = Pool.POCKET_RADIUS if i <= 2 else Pool.TABLE_HEIGHT - Pool.POCKET_RADIUS
            self.pockets.append((x, y))

        # This is the pool table
        table_body:b2Body = self.world.CreateStaticBody(
            position=(0, 0),
            shapes=b2ChainShape(vertices_chain=[
                (0, 0),
                (Pool.TABLE_WIDTH, 0),
                (Pool.TABLE_WIDTH, Pool.TABLE_HEIGHT),
                (0, Pool.TABLE_HEIGHT),
                (0, 0)
            ])
        )
        self.table = Drawable(table_body, Drawable.GREEN, Drawable.draw_poly)

        pygame.init()

        width = 1280
        height = 640
        self.screen = ScreenInfo(pygame.display.set_mode((width, height), RESIZABLE), width, height, 0, 0, 0)
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

    def update_physics(self):
        # Make Box2D simulate the physics of our world for one step.
        self.world.Step(Pool.TIME_STEP, Pool.VEL_ITERS, Pool.POS_ITERS)
        
        for ball in self.balls:
            ball_x = ball.position[0]
            ball_y = ball.position[1]
            for x, y in self.pockets:
                x2 = ball_x - x
                x2 = x2 * x2
                y2 = ball_y - y
                y2 = y2 * y2
                if x2 + y2 <= Pool.POCKET_RADIUS_SQUARED:
                    self.balls.remove(ball)
                    self.world.DestroyBody(ball)
                    break

    def simulate_until_still(self):
        self.update_physics()
        self.world.ClearForces()
        while self.are_balls_moving():
            self.update_physics()
        
    def are_balls_moving(self):
        for ball in self.balls:
            if ball.active and (ball.linearVelocity[0] > 0.01 or ball.linearVelocity[1] > 0.01):
                return True
        return False

    def update_graphics(self):
        self.screen.screen.fill((0, 0, 0, 0))
        self.table.draw(self.screen)

        for x, y in self.pockets:
            x *= self.screen.ppm
            y *= self.screen.ppm
            position = (x + self.screen.offset_x, self.screen.screen_height - y - self.screen.offset_y)
            pygame.draw.circle(self.screen.screen, Drawable.BLACK, position, Pool.POCKET_RADIUS * self.screen.ppm)

        for drawable in self.drawables:
            drawable.draw(self.screen)

        pygame.display.update()

        # Flip the screen and try to keep at the target FPS
        pygame.display.flip()
        self.clock.tick(Pool.TICK_RATE)

    def run(self):
        #self.simulate_until_still()
        self.update_physics()
        self.world.ClearForces()
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
            
            self.update_graphics()
            self.update_physics()

        pygame.quit()
        print('Done!')

if __name__ == "__main__":
    pool = Pool()
    pool.run()