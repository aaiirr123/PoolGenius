import pygame.display
import pygame.draw
import pygame.event
from pygame.surface import Surface
import pygame.time
from pygame.locals import (QUIT, KEYDOWN, K_ESCAPE, RESIZABLE, VIDEORESIZE)
import Box2D
from Box2D.Box2D import *

import random

class Pool:
    TICK_RATE = 60
    TIME_STEP = 1.0 / TICK_RATE
    VEL_ITERS = 10
    POS_ITERS = 10
    TABLE_WIDTH = 9.0
    TABLE_HEIGHT = 4.5
    TABLE_RATIO = TABLE_WIDTH / TABLE_HEIGHT
    GREEN = 0, 255, 0
    BLACK = 0, 0, 0
    RED = 255, 0, 0

    def __init__(self):
        self.screen_width = 1280
        self.screen_height = 640
        self.offset_x = 0 # offset in pixels used for resizing
        self.offset_y = 0 # offset in pixels used for resizing
        self.ppm = 0 # pixels per meter

        self.world = b2World(gravity=(0, 0), doSleep=True)
        self.balls = []

        ball_fd = b2FixtureDef(shape=b2CircleShape(radius=2.25/12))
        ball_fd.density = 1.0
        ball_fd.friction = 0.2
        ball_fd.restitution = 0.8

        for _ in range(10):
            ball:b2Body = self.world.CreateDynamicBody(position=(random.randint(1, 8), random.randint(1, 4)), fixtures=ball_fd)
            ball.linearDamping = 0.6
            ball.angularDamping = 0.6
            ball.ApplyForce((random.randint(-100, 100), random.randint(-300, 300)), ball.worldCenter, True)
            self.balls.append(ball)

        # This is the pool table
        self.table:b2Body = self.world.CreateStaticBody(
            position=(0, 0),
            shapes=b2ChainShape(vertices_chain=[
                (0, 0),
                (Pool.TABLE_WIDTH, 0),
                (Pool.TABLE_WIDTH, Pool.TABLE_HEIGHT),
                (0, Pool.TABLE_HEIGHT),
                (0, 0)
            ])
        )

        self.type_to_draw = {
            b2PolygonShape: self.draw_poly,
            b2CircleShape: self.draw_circle,
            b2ChainShape: self.draw_poly
        }

        pygame.init()

        self.screen:Surface = pygame.display.set_mode((self.screen_width, self.screen_height), RESIZABLE)
        pygame.display.set_caption("Billiards")
        self.clock = pygame.time.Clock()

        self.update_screen()

    def update_screen(self):
        # update ppm
        if self.screen_width / self.screen_height <= Pool.TABLE_RATIO:
            self.ppm = self.screen_width / Pool.TABLE_WIDTH
        else:
            self.ppm = self.screen_height / Pool.TABLE_HEIGHT

        # update offsets
        ratio = self.screen_width / self.screen_height
        if ratio == Pool.TABLE_RATIO:
            self.offset_x = 0
            self.offset_y = 0
        elif ratio > Pool.TABLE_RATIO:
            self.offset_x = int(self.screen_width - (Pool.TABLE_RATIO * self.screen_height)) // 2
            self.offset_y = 0
        else:
            self.offset_x = 0
            self.offset_y = int((self.screen_height - (self.screen_width / Pool.TABLE_RATIO))) // 2

    # https://github.com/openai/box2d-py/blob/master/examples/simple/simple_02.py
    # for the draw functions
    def draw_poly(self, polygon:b2PolygonShape, body:b2Body):
        vertices = [(body.transform * v) * self.ppm for v in polygon.vertices]
        vertices = [(x + self.offset_x, self.screen_height - y - self.offset_y) for x, y in vertices]
        pygame.draw.polygon(self.screen, Pool.GREEN, vertices)

    def draw_circle(self, circle:b2CircleShape, body:b2Body):
        x, y = body.transform * circle.pos * self.ppm
        position = (x + self.offset_x, self.screen_height - y - self.offset_y)
        pygame.draw.circle(self.screen, Pool.RED, [int(i) for i in position], int(circle.radius * self.ppm))

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
                    self.screen_height = event.h
                    self.screen_width = event.w
                    self.update_screen()
                    self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), RESIZABLE)

            self.screen.fill((0, 0, 0, 0))
            self.draw_poly(self.table.fixtures[0].shape, self.table)
            
            # Draw the world
            for body in self.world.bodies:
                if body == self.table:
                    continue
                for fixture in body.fixtures:
                    self.type_to_draw[type(fixture.shape)](fixture.shape, body)

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