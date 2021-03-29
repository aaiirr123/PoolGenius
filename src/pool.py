from typing import Callable, List, Tuple
import pygame.display
import pygame.draw
import pygame.event
from pygame.surface import Surface
import pygame.time
from pygame.locals import (QUIT, KEYDOWN, K_ESCAPE, RESIZABLE, VIDEORESIZE)
import Box2D
from Box2D.Box2D import *

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
        pygame.draw.circle(screen.screen, color, [int(i) for i in position], int(circle.radius * screen.ppm))

class Pool:
    TICK_RATE = 60
    TIME_STEP = 1.0 / TICK_RATE
    VEL_ITERS = 10
    POS_ITERS = 10
    TABLE_WIDTH = 9.0
    TABLE_HEIGHT = 4.5
    TABLE_RATIO = TABLE_WIDTH / TABLE_HEIGHT

    def __init__(self):
        self.world = b2World(gravity=(0, 0), doSleep=True)
        self.drawables:List[Drawable] = []

        # constants taken from here:
        # https://github.com/agarwl/eight-ball-pool/blob/master/src/dominos.cpp
        ball_fd = b2FixtureDef(shape=b2CircleShape(radius=2.25/12))
        ball_fd.density = 1.0
        ball_fd.friction = 0.2
        ball_fd.restitution = 0.8

        for _ in range(10):
            ball:b2Body = self.world.CreateDynamicBody(position=(random.randint(1, 8), random.randint(1, 4)), fixtures=ball_fd)
            ball.linearDamping = 0.6
            ball.angularDamping = 0.6
            ball.ApplyForce((random.randint(-300, 300), random.randint(-300, 300)), ball.worldCenter, True)
            ball_drawable = Drawable(ball, Drawable.RED, Drawable.draw_circle)
            self.drawables.append(ball_drawable)

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

    def run(self):
        # game loop
        running = True
        while running:
            # Check the event queue
            for event in pygame.event.get():
                if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                    # The user closed the window or pressed escape
                    running = False
                if event.type == VIDEORESIZE:
                    self.screen.screen_height = event.h
                    self.screen.screen_width = event.w
                    self.update_screen()
                    self.screen.screen = pygame.display.set_mode((self.screen.screen_width, self.screen.screen_height), RESIZABLE)

            self.screen.screen.fill((0, 0, 0, 0))
            self.table.draw(self.screen)

            for drawable in self.drawables:
                drawable.draw(self.screen)

            pygame.display.update()

            # Make Box2D simulate the physics of our world for one step.
            self.world.Step(Pool.TIME_STEP, Pool.VEL_ITERS, Pool.POS_ITERS)

            self.world.ClearForces()

            # Flip the screen and try to keep at the target FPS
            pygame.display.flip()
            self.clock.tick(Pool.TICK_RATE)

        pygame.quit()
        print('Done!')

if __name__ == "__main__":
    pool = Pool()
    pool.run()