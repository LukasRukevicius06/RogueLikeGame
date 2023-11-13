import pygame as py
from sys import exit
import random
from settings import *
import math
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
screen = py.display.set_mode(screenSize)
py.display.set_caption('Top Down Shooter Game')
clock = py.time.Clock()
# creating the window, using dimensions from settings file, setting a name for the window, initialising the clock

# load images
background = py.transform.scale(py.image.load("background.jpg"), (display_width, display_height)).convert_alpha()


class Player(py.sprite.Sprite):
    # makes class for the player with methods inside to allow it to move
    def __init__(self):
        # initialising the function
        super().__init__()
        self.image = py.transform.rotozoom(py.image.load("player_sprite.png").convert_alpha(), 0, player_size)
        self.pos = py.math.Vector2(player_start_x, player_start_y)
        self.base_image = self.image
        self.hb_rect = self.base_image.get_rect(center = self.pos)
        self.rect = self.hb_rect.copy()
        self.speed = player_speed


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
        self.pos += py.math.Vector2(self.velocity_x, self.velocity_y)

    def update(self):
        self.user_input()
        self.move()


player = Player()

crashed = False
while not crashed:

    for event in py.event.get():
        if event.type == py.QUIT:
            crashed = True

        print(event)

    screen.blit(background, (0, 0))
    screen.blit(player.image, player.pos)
    player.update()

    py.display.update()
    clock.tick(FPS)


py.quit()
quit()
