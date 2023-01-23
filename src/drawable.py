from asyncio import constants
from cmath import rect
from distutils import extension
from Box2D.Box2D import *
import math
from pygame import Rect
import pygame
import pygame.display
import pygame.draw
from pygame.surface import Surface
from typing import Callable, Tuple
from constants import Constants
import shot_verifier

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
    def draw_pool_cue(screen:ScreenInfo, cue_ball_pos, angle, shot_ready):

        if shot_ready:

            
            cue_img = pygame.image.load('poolplayer.png')
            cue_img = pygame.transform.scale(cue_img, (Constants.STICK_LENGTH * screen.ppm * 2, Constants.PLAYER_WIDTH * screen.ppm))
            angle = (angle + 180) % 360
            angle *= -1

            extension_x, extension_y = shot_verifier.getBodyExtension(
                1,
                cue_ball_pos,
                angle
            )

            cue_x, cue_y = shot_verifier.getExtensionPosition( 
                cue_ball_pos,
                angle + 180
            )

            start_x, start_y = cue_ball_pos
            pygame.draw.line(screen.screen, (0,0,0), (start_x * screen.ppm, start_y * screen.ppm), (extension_x * screen.ppm, extension_y * screen.ppm), 4)

            pygame.draw.line(screen.screen, (255,255,255), (start_x * screen.ppm, start_y * screen.ppm), (cue_x * screen.ppm, cue_y * screen.ppm), 4)


            radian_angle = math.radians(angle)
            orthaganal_radian_angle = angle - 90
            if orthaganal_radian_angle <= -360: orthaganal_radian_angle %= 360
            orthaganal_radian_angle = math.radians(orthaganal_radian_angle)


            ball_offset_x, ball_offset_y = math.cos(radian_angle) * Constants.BALL_RADIUS, math.sin(radian_angle) * Constants.BALL_RADIUS
            # This is just an issue that needs to be adjusted due to the added width of the pool cue
            pool_stick_mod = 0.85
            body_offset_x = math.cos(orthaganal_radian_angle) * Constants.PLAYER_WIDTH / 2 * pool_stick_mod 
            body_offset_y = math.sin(orthaganal_radian_angle) * Constants.PLAYER_WIDTH / 2 * pool_stick_mod
            offset_x, offset_y = ball_offset_x + body_offset_x , ball_offset_y + body_offset_y
            offset_x, offset_y = body_offset_x + ball_offset_x, ball_offset_y + body_offset_y
            cue_img = pygame.transform.rotate(cue_img, angle)
            center_img = cue_img.get_rect()
            
            x, y = cue_ball_pos
            center_img.center = ((x + offset_x) * screen.ppm, (y - offset_y) * screen.ppm)
            screen.screen.blit(cue_img, center_img) 
            cue_x, cue_y = shot_verifier.getExtensionPosition( 
                cue_ball_pos,
                angle
            )
            pygame.draw.line(screen.screen, (255,255,255), (start_x * screen.ppm, start_y * screen.ppm), (cue_x * screen.ppm, cue_y * screen.ppm), 4)



    @staticmethod
    def draw_rect(polygon:b2PolygonShape, body:b2Body, color:Tuple[int, int, int], screen:ScreenInfo, outline:bool, outline_color:Tuple[int, int, int]):
        vertices = [(body.transform * v) * screen.ppm for v in polygon.vertices[:4]]
        vertices = [[x + screen.offset_x, screen.screen_height - y - screen.offset_y] for x, y in vertices]
        if outline:
            thickness = screen.screen.get_height() // 360
            vertices.sort(key=lambda x : (x[0], x[1]))
            vertices = [vertices[0], vertices[2], vertices[3], vertices[1]]
            pygame.draw.polygon(screen.screen, outline_color, vertices)
            vertices[0][0] += thickness
            vertices[0][1] += thickness
            vertices[1][0] -= thickness
            vertices[1][1] += thickness
            vertices[2][0] -= thickness
            vertices[2][1] -= thickness
            vertices[3][0] += thickness
            vertices[3][1] -= thickness
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
            pygame.draw.circle(screen.screen, color, position, r * 0.90)
        else:
            pygame.draw.circle(screen.screen, color, position, r)
            
    @staticmethod
    def draw_billiard_ball(circle:b2CircleShape, body:b2Body, color:Tuple[int, int, int], screen:ScreenInfo, outline:bool, outline_color:Tuple[int, int, int]):
        x, y = body.transform * circle.pos * screen.ppm
        position = [x + screen.offset_x, screen.screen_height - y - screen.offset_y]
        r = circle.radius * screen.ppm
        Drawable.draw_billiard_ball_helper(position, r, screen, color, outline_color, body.userData.number, body.transform.angle)

    @staticmethod
    def draw_billiard_ball_helper(position, r, screen:ScreenInfo, color, outline_color, num, angle):
        # stripes
        if num > 8:
            pygame.draw.circle(screen.screen, color, position, r)
            pygame.draw.circle(screen.screen, Drawable.WHITE, position, r * 0.90)

            # draw the stripe using trig to draw straight lines across the circle
            r -= 2.5
            steps = 49
            half = steps // 2
            thickness = screen.screen.get_height() // 240
            x = position[0]
            y = position[1]
            for i in range(steps):
                converted_angle1 = angle + (i - half) * 0.02
                converted_angle2 = angle + math.pi - (i - half) * 0.02
                x1 = r * math.cos(converted_angle1) + x
                y1 = r * math.sin(converted_angle1) + y
                x2 = r * math.cos(converted_angle2) + x
                y2 = r * math.sin(converted_angle2) + y
                pygame.draw.line(screen.screen, color, (x1, y1), (x2, y2), thickness)
            r += 2.5
        # solids
        else:
            pygame.draw.circle(screen.screen, outline_color, position, r)
            pygame.draw.circle(screen.screen, color, position, r * 0.90)
        pygame.draw.circle(screen.screen, Drawable.WHITE, position, r / 3)