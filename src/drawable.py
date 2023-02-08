from ast import Constant
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
            
            # This is to verify direction and length of pool stick
            cue_x, cue_y = shot_verifier.getExtensionPosition( 
                cue_ball_pos,
                angle
            )
            # draws line matching pool stick, for geometry check
            pygame.draw.line(screen.screen, (255,255,255), (start_x * screen.ppm, start_y * screen.ppm), (cue_x * screen.ppm, cue_y * screen.ppm), 4)

           

            
            
    @staticmethod
    def draw_player_pos(screen:ScreenInfo, cue_ball_pos, angle, shot_ready, balls):

        if shot_ready:
            pygame.font.init() # you have to call this at the start, 
            # if you want to use this module.
            my_font = pygame.font.SysFont('Comic Sans MS', 18)
            
            angle = (angle + 180) % 360
            angle *= -1
            body_pos_x, body_pos_y = shot_verifier.getPlayerPosition (
                cue_ball_pos,
                angle
            )
                
            shooter_angle = round(shot_verifier.getRelativeAngle(angle=angle, body_pos_x=body_pos_x, body_pos_y=body_pos_y), 3)
            
            # angle text
            angle_text_surface = my_font.render('Relative Angle: ' + str(shooter_angle), False, (255, 255, 255))
            screen.screen.blit(angle_text_surface, (0.9 * screen.ppm, 3.42 * screen.ppm))
            
            # position text
            wall_number = shot_verifier.getWallNum(body_pos_x=body_pos_x, body_pos_y=body_pos_y)
            
            position_text_surface = my_font.render('Wall Number: ' + str(wall_number) + ' Position: x=' + str(round(body_pos_x, 4)) + ', y=' 
                                                   + str(round(body_pos_y, 4)), False, (255, 255, 255))
            screen.screen.blit(position_text_surface, (3.75 * screen.ppm, 3.42 * screen.ppm))
            
            pygame.draw.circle(screen.screen, (255,0,0), (body_pos_x * screen.ppm, body_pos_y * screen.ppm), 0.05 * screen.ppm)
            
            # draw angle line
            # how far the cue stick peaks over the table edge
            dif_x = body_pos_x - cue_ball_pos[0] 
            dif_y = body_pos_y - cue_ball_pos[1]
            cue_stick_peak = math.sqrt(pow(dif_x, 2) + pow(dif_y, 2))
            
            angle_length = cue_stick_peak / math.cos(math.radians(7.5))
            
            left_angle = angle + 180 - 7.5
            right_angle = angle + 180 + 7.5
            
            left_unit_vector = (math.cos(math.radians(left_angle)), math.sin(math.radians(left_angle)))
            right_unit_vector = (math.cos(math.radians(right_angle)), math.sin(math.radians(right_angle)))

            left_end_vector = (left_unit_vector[0] * angle_length, left_unit_vector[1] * angle_length)
            right_end_vector = (right_unit_vector[0] * angle_length, right_unit_vector[1] * angle_length)
            
            left_end_pos = (left_end_vector[0] + body_pos_x, -left_end_vector[1] + body_pos_y)
            right_end_pos = (right_end_vector[0] + body_pos_x, -right_end_vector[1] + body_pos_y)
            
            
            # Draws the angle lines to the screen
            pygame.draw.line(screen.screen, (255,255,255),
                             ( body_pos_x * screen.ppm, body_pos_y * screen.ppm), 
                             (left_end_pos[0] * screen.ppm, left_end_pos[1] * screen.ppm),
                             4)
            pygame.draw.line(screen.screen, (255,255,255),
                             ( body_pos_x * screen.ppm, body_pos_y * screen.ppm), 
                             (right_end_pos[0] * screen.ppm, right_end_pos[1] * screen.ppm), 
                             4)
            
        
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