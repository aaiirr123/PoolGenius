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
    YELLOW = 255, 255, 0
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
        if outline:
            pygame.draw.circle(screen.screen, outline_color, position, circle.radius * screen.ppm)
            pygame.draw.circle(screen.screen, color, position, circle.radius * screen.ppm - 2)
        else:
            pygame.draw.circle(screen.screen, color, position, circle.radius * screen.ppm)

class Pool:
    TICK_RATE = 60
    TIME_STEP = 1.0 / TICK_RATE
    VEL_ITERS = 6
    POS_ITERS = 2
    TABLE_WIDTH = 9.0
    TABLE_HEIGHT = 4.5
    TABLE_RATIO = TABLE_WIDTH / TABLE_HEIGHT
    BALL_RADIUS = 2 / 12
    POCKET_RADIUS = 3 / 12
    POCKET_RADIUS_SQUARED = POCKET_RADIUS * POCKET_RADIUS

    def __init__(self):
        self.world = b2World(gravity=(0, 0), doSleep=True)
        self.drawables:List[Drawable] = []
        self.balls:List[b2Body] = []
        self.pockets:List[Point] = []

        # constants taken from here:
        # https://github.com/agarwl/eight-ball-pool/blob/master/src/dominos.cpp
        ball_fd = b2FixtureDef(shape=b2CircleShape(radius=Pool.BALL_RADIUS))
        ball_fd.density = 1.0
        ball_fd.friction = 0.2
        ball_fd.restitution = 0.85

        colors = [Drawable.YELLOW, Drawable.BLUE, Drawable.RED, Drawable.PURPLE, Drawable.ORANGE, Drawable.GREEN, Drawable.BURGUNDY, Drawable.BLACK]
        colors = random.sample(colors, 8)

        for i in range(8):
            ball:b2Body = self.world.CreateDynamicBody(position=(random.randint(1, 8), random.randint(1, 4)), fixtures=ball_fd)
            ball.bullet = True
            ball.linearDamping = 0.6
            ball.angularDamping = 0.6
            ball.ApplyForce((random.randint(-300, 300), random.randint(-300, 300)), ball.worldCenter, True)
            ball_drawable = Drawable(ball, colors[i], Drawable.draw_circle)
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
            self.pockets.append(Point(x, y))

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

        pygame.init()

        width = 1280
        height = width // 2
        self.screen = ScreenInfo(pygame.display.set_mode((1280, 720)), width, height, 0, 0, 0)
        pygame.display.set_caption("Billiards")
        self.clock = pygame.time.Clock()

        self.update_screen()

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
        body = self.world.CreateStaticBody(
            shapes=b2ChainShape(vertices_chain=vertices)
        )
        self.drawables.append(Drawable(body, Drawable.BROWN, Drawable.draw_rect, outline_color=(25, 14, 16)))

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
            for pt in self.pockets:
                x2 = ball_x - pt.x
                x2 = x2 * x2
                y2 = ball_y - pt.y
                y2 = y2 * y2
                if x2 + y2 <= Pool.POCKET_RADIUS_SQUARED:
                    self.balls.remove(ball)
                    self.world.DestroyBody(ball)
                    break

    def simulate_until_still(self):
        t0 = time.time()
        self.update_physics()
        self.world.ClearForces()
        while self.are_balls_moving():
            self.update_physics()
        t1 = time.time()
        print(f"time elapsed: {t1 - t0} s")
        
    def are_balls_moving(self):
        for ball in self.balls:
            if ball.linearVelocity[0] > 0.01 or ball.linearVelocity[1] > 0.01:
                return True
        return False

    def update_graphics(self):
        self.screen.screen.fill(Drawable.BILLIARD_GREEN)

        for pt in self.pockets:
            x = pt.x * self.screen.ppm
            y = pt.y * self.screen.ppm
            position = (x + self.screen.offset_x, self.screen.screen_height - y - self.screen.offset_y)
            pygame.draw.circle(self.screen.screen, Drawable.BLACK, position, Pool.POCKET_RADIUS * self.screen.ppm)

        for drawable in self.drawables:
            drawable.draw(self.screen)

        pygame.display.update()

        # Flip the screen and try to keep at the target FPS
        pygame.display.flip()
        self.clock.tick(Pool.TICK_RATE)

    def run(self):
        self.simulate_until_still()
        # self.update_physics()
        # self.world.ClearForces()
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
            # self.update_physics()

        pygame.quit()
        print('Done!')

if __name__ == "__main__":
    pool = Pool()
    pool.run()