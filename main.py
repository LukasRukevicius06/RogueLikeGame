######################################## IMPORT LIBRARIES ########################################
import pygame as py
from sys import exit
import random
from settings import *
import math
import time
from tiles import *
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
        self.image = py.transform.rotozoom(py.image.load("player_sprite.png").convert_alpha(), 0, 1)
        self.image = py.transform.scale(self.image, (100*player_size, 130*player_size))
        self.pos = py.math.Vector2(player_start_x, player_start_y)
        self.arm_rect = py.draw.rect(self.image, "red", py.Rect(23, 73, 60, 23))
        self.base_image = self.image
        self.hb_rect = self.base_image.get_rect(center = self.pos)
        self.rect = self.hb_rect.copy()
        self.speed = player_speed
        self.shoot = False
        # boolean to state whether player has shot
        self.shoot_cooldown = 0
        # variable for the cooldown of how often player can shoot
        self.gun_barrel_offset = py.math.Vector2(GUN_OFFSET_X, GUN_OFFSET_Y)

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

        if keys[py.K_SPACE]:
            # if left mouse clicked or space bar pressed, will run function to shoot
            self.shoot = True
            self.is_shooting()
        else:
            self.shoot = False

    def is_shooting(self):
        if self.shoot_cooldown == 0:
            # if shot cooldown is 0 so there's no cooldown
            self.shoot_cooldown = shot_cd
            # shot cooldown is changed to time in settings for cooldown
            x = self.pos.x + self.arm_rect.x
            y = self.pos.y + self.arm_rect.y
            # spawn position of bullet is equal to
            self.bullet = Projectile((x), (y), self.angle)
            bullet_group.add(self.bullet)
            all_sprites_group.add(self.bullet)

    def move(self):
        # movement function for player
        self.pos += py.math.Vector2(self.velocity_x, self.velocity_y)
        # position of player is increased by the vector of x velocity and y velocity after the players input
        self.hb_rect.center = self.pos
        self.rect.center = self.hb_rect.center

    def update(self):
        self.user_input()
        self.move()
        self.player_rotation()

        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1


class Projectile(py.sprite.Sprite):
    # made a class for every projectile that will be in my game, so I can use it for enemies later on
    def __init__(self, x, y, angle):
        super().__init__()
        self.angle = angle
        self.image = py.image.load("fireball_sprite.png").convert_alpha()
        # imported image and made its background transparent as it's a png
        self.image = py.transform.rotozoom(self.image,(-self.angle - 90), BULLET_SCALE)
        # made the bullet sprite smaller or larger depending on the scale in the settings
        self.rect = self.image.get_rect()
        #self.rect = py.transform.rotate(self.rect, angle)
        self.x = x
        self.y = y
        # made image rotate based on the angle where the mouse is relative to the player and took away 90 degrees so it would face the right direction
        self.speed = BULLET_SPEED
        self.x_v = math.cos(self.angle * ((2*math.pi)/360)) * self.speed
        self.y_v = math.sin(self.angle * ((2*math.pi)/360)) * self.speed
        self.x += self.x_v
        self.y += self.y_v
        # self.rect.center = (x, y)
        self.bullet_lifetime = BULLET_LIFETIME
        self.spawn_time = py.time.get_ticks()
        # gets the specific time that the bullet was created
        print("start", self.x)
        print("start", self.y)
        # prints starting coordinates of bullet sprite when the bullet class is made

    def bullet_movement(self):
        # function that makes the bullet actually move and moves the rect position as well for when collision is added
        print("move", self.x)
        print("move", self.y)
        # prints coordinates of where the bullet is every frame while moving

        self.rect.x = int(self.x)
        self.rect.y = int(self.y)
        self.x += self.x_v
        self.y += self.y_v

        py.draw.rect(screen, "yellow", self.rect, width=2)


        if py.time.get_ticks() - self.spawn_time > self.bullet_lifetime:
            self.kill()


    def update(self):
        self.bullet_movement()


#class Enemy(py.sprite.Sprite):
#    def __init__(self):

player = Player()

all_sprites_group = py.sprite.Group()
# made a group for all sprites to easily display them all on the screen at the same time
bullet_group = py.sprite.Group()
# made a group for all bullets in case I want to alter how they appear on the screen

all_sprites_group.add(player)
crashed = False
while not crashed:
    for event in py.event.get():
        if event.type == py.QUIT:
            crashed = True

        print(event)

    x_point = py.mouse.get_pos()[0]
    # stores the x of the mouse position
    y_point = py.mouse.get_pos()[1]
    # stores the y of the mouse position
    screen.blit(background, (0, 0))
    all_sprites_group.draw(screen)
    all_sprites_group.update()
    screen.blit(platform, (display_width/2, display_height/2))
    screen.blit(crosshair,((x_point-23),(y_point-20)))
    py.draw.rect(screen, "red", player.hb_rect, width=2)
    py.draw.rect(screen, "yellow", player.rect, width=2)

    py.display.update()
    clock.tick(FPS)


py.quit()
quit()
