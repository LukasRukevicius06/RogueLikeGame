import pygame as py
from sys import exit
import random
from settings import *
import math
import time
from PIL import Image
# imported pygame as py so it is easier to write


black = (0, 0, 0)
white = (255, 255, 255)
lightRed = "#F00022"
weakRed = "#BD263A"
greyRed = "#8A3742"
grey = "#574544"
# initialising different colour values and assigning them to specific variables to reference later

py.init()
# initialising pygame

screenSize = (display_width, display_height)
screen = py.display.set_mode(screenSize,py.RESIZABLE)
py.display.set_caption('Top Down Shooter Game')
clock = py.time.Clock()
# creating the window, using dimensions from settings file, setting a name for the window, initialising the clock

platform = py.image.load('platform.png')
gameIcon = py.image.load("icon.png")
# load images
background = py.transform.scale(py.image.load("background2.jpg"), (display_width, display_height)).convert_alpha()
crosshair = py.image.load('crosshair.png')
crosshair = py.transform.smoothscale(crosshair, (50,50))
py.display.set_icon(gameIcon)
# chImage = Image.open('crosshair.png')
# chImage = chImage.resize((50,50), Image.LANCZOS)
# chStr = chImage.tobytes("raw", "RGBA")
# crosshair = py.image.fromstring(chStr, (50,50), "RGBA")

class Player(py.sprite.Sprite):
    # makes class for the player with methods inside to allow it to move
    def __init__(self):
        # initialising the function
        super().__init__()
        self.image = py.transform.rotozoom(py.image.load("player_sprite.png").convert_alpha(), 0, player_size)
        self.image = py.transform.scale(self.image, (100, 130))
        self.pos = py.math.Vector2(player_start_x, player_start_y)
        self.base_image = self.image
        self.hb_rect = self.base_image.get_rect(center = self.pos)
        self.rect = self.hb_rect.copy()
        self.speed = player_speed

    def player_rotation(self):
        self.mouse_coords = py.mouse.get_pos()
        self.x_change_mouse_player = self.mouse_coords[0] - self.hb_rect.centerx
        self.y_change_mouse_player = self.mouse_coords[1] - self.hb_rect.centery
        self.angle= math.degrees(math.atan2(self.y_change_mouse_player, self.x_change_mouse_player))
        self.image = py.transform.rotate(self.base_image, -self.angle)
        self.rect = self.image.get_rect(center = self.hb_rect.center)


    def user_input(self):
        self.velocity_x = 0
        self.velocity_y = 0

        keys = py.key.get_pressed()

        if keys[py.K_w]:
            self.velocity_y = -self.speed
        if keys[py.K_s]:
            self.velocity_y = self.speed
        if keys[py.K_a]:
            self.velocity_x = -self.speed
        if keys[py.K_d]:
            self.velocity_x = self.speed



        if self.velocity_x != 0 and self.velocity_y != 0:
            self.velocity_x /= math.sqrt(2)
            self.velocity_y /= math.sqrt(2)
        # makes diagonal speed the same as horizontal and vertical speed

    def move(self):
        # movement function for player
        self.pos += py.math.Vector2(self.velocity_x, self.velocity_y)
        self.hb_rect.center = self.pos
        self.rect.center = self.hb_rect.center

    def update(self):
        self.user_input()
        self.move()
        self.player_rotation()


#class Projectile(object):
#    def __init__(self,x,y,radius,colour):




player = Player()

crashed = False
while not crashed:
    for event in py.event.get():
        if event.type == py.QUIT:
            crashed = True

        print(event)

    #py.draw.rect(lightRed, py.Rect(30, 30, 60, 60))
    x_point = py.mouse.get_pos()[0]
    y_point = py.mouse.get_pos()[1]
    screen.blit(background, (0, 0))
    screen.blit(platform, (display_width/2, display_height/2))
    screen.blit(player.image, player.rect)
    screen.blit(crosshair,((x_point-23),(y_point-20)))
    player.update()
    py.draw.rect(screen, "red", player.hb_rect, width=2)
    py.draw.rect(screen, "yellow", player.rect, width=2)

    py.display.update()
    clock.tick(FPS)


py.quit()
quit()
