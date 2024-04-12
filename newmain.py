import pygame as py
import sys
import random

import settings
from settings import *
import math
import time
from tiles import *
from PIL import Image

py.init()

screenSize = (display_width, display_height)
display = py.display.set_mode(screenSize, py.RESIZABLE)
py.display.set_caption('BLAZE BRIGADEEE')
gameIcon = py.image.load('icon.png')
py.display.set_icon(gameIcon)
background = py.image.load('ground.png').convert_alpha()
w = background.get_width()
h = background.get_height()
background = py.transform.scale(background, (w * 3, h * 3))
crosshair = py.image.load('crosshair.png').convert_alpha()
crosshair = py.transform.smoothscale_by(crosshair, 0.1)
fireball = py.image.load("fireball_sprite.png").convert_alpha()


class Player(py.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = py.transform.rotozoom(py.image.load("player_sprite.png").convert_alpha(), 0, 1)
        self.image = py.transform.scale(self.image, (100 * player_size, 130 * player_size))
        self.base_image = self.image
        self.pos = py.math.Vector2(player_start_x, player_start_y)
        self.rect = self.image.get_rect(center=self.pos)
        self.pos = self.rect.topleft
        #self.arm_rect = py.draw.rect(display, "red", py.Rect(23 + self.pos[0], 73 + self.pos[1], 60, 23))
        self.speed = player_speed
        self.mouse_coordinates = [0, 0]
        self.vel_x = 0
        self.vel_y = 0
        self.shoot = False
        self.shoot_cooldown = 0

    def move(self):
        py.draw.rect(display, (0, 255, 0), self.rect, width=2)
        #py.draw.rect(display, (255, 0 , 0), self.arm_rect, width=2)
        display.blit(self.image, self.rect)

    def inputs(self):
        self.vel_x = 0
        self.vel_y = 0
        self.speed = player_speed

        keys = py.key.get_pressed()

        if keys[py.K_a]:
            #display_scroll[0] -= self.speed
            self.vel_x = -self.speed
            for bullet in player_bullets:
                bullet.x += self.speed
        if keys[py.K_d]:
            #display_scroll[0] += self.speed
            self.vel_x = self.speed
            for bullet in player_bullets:
                bullet.x -= self.speed
        if keys[py.K_w]:
            #display_scroll[1] -= self.speed
            self.vel_y = -self.speed
            for bullet in player_bullets:
                bullet.y += self.speed
        if keys[py.K_s]:
            #display_scroll[1] += self.speed
            self.vel_y = self.speed
            for bullet in player_bullets:
                bullet.y -= self.speed

        if self.vel_x != 0 and self.vel_y != 0:
            self.vel_x /= math.sqrt(2)
            self.vel_y /= math.sqrt(2)

        display_scroll[0] += self.vel_x
        display_scroll[1] += self.vel_y

        if keys[py.K_SPACE]:
            # if left mouse clicked or space bar pressed, will run function to shoot
            self.shoot = True
            self.shooting()
        else:
            self.shoot = False

        self.mouse_coordinates = [py.mouse.get_pos()[0], py.mouse.get_pos()[1]]

    def shooting(self):
        if self.shoot_cooldown == 0:
            # if shot cooldown is 0 so cooldown is over
            self.shoot_cooldown = SHOT_COOLDOWN
            # shot cooldown is reset to cooldown time in settings
            spawn_bullet_pos = (self.pos)
            print(spawn_bullet_pos)
            # spawn position of bullet is equal to
            player_bullets.append(Projectile((spawn_bullet_pos[0]), (spawn_bullet_pos[1]), self.angle, fireball))

    def mouse(self):
        display.blit(crosshair, (self.mouse_coordinates[0] - crosshair.get_width()/2, self.mouse_coordinates[1] - crosshair.get_height()/2))

    def player_rotation(self):
        self.x_change_mouse_player = self.mouse_coordinates[0] - self.rect.centerx
        self.y_change_mouse_player = self.mouse_coordinates[1] - self.rect.centery
        self.angle = math.degrees(math.atan2(self.y_change_mouse_player, self.x_change_mouse_player))
        self.image = py.transform.rotate(self.base_image, -self.angle)
        self.rect = self.image.get_rect(center=self.pos)

    def main(self):
        self.inputs()
        self.mouse()
        self.move()
        self.player_rotation()

        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1


class Projectile(py.sprite.Sprite):
    def __init__(self, x, y, angle, image):
        super().__init__()
        self.angle = angle
        self.speed = BULLET_SPEED
        self.image = image
        self.image = py.transform.rotozoom(self.image, (-self.angle - 90), BULLET_SCALE)
        # made the bullet sprite smaller or larger depending on the scale in the settings
        self.rect = self.image.get_rect()
        # self.rect = py.transform.rotate(self.rect, angle)
        self.x = x
        self.y = y
        # made image rotate based on the angle where the mouse is relative to the player and took away 90 degrees so it would face the right direction
        self.x_v = math.cos(self.angle * ((2 * math.pi) / 360)) * self.speed
        self.y_v = math.sin(self.angle * ((2 * math.pi) / 360)) * self.speed
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

        py.draw.rect(display, "yellow", (self.rect), width=2)
        display.blit(self.image, (self.x, self.y))

        if py.time.get_ticks() - self.spawn_time > self.bullet_lifetime:
            self.kill()

    def update(self):
        self.bullet_movement()


player = Player()

display_scroll = [0, 0]

player_bullets = []


def draw_display():
    display.fill((0, 0, 0))
    display.blit(background, (-1000 - display_scroll[0], -3000 - display_scroll[1]))
    py.draw.rect(display, (255, 255, 255), (100 - display_scroll[0], 100 - display_scroll[1], 16, 16))
    player.main()
    for bullet in player_bullets:
        bullet.update()
    # py.draw.rect(display, (255, 255, 255), (100 - display_scroll[0], 100 - display_scroll[1], 16, 16))
    py.display.update()


def main():
    clock = py.time.Clock()

    run = True
    while run:
        for event in py.event.get():
            if event.type == py.QUIT:
                sys.exit()
            if event.type == py.VIDEORESIZE:
                settings.display_width = display.get_width()
                settings.display_height = display.get_height()

        draw_display()
        clock.tick(FPS)


if __name__ == '__main__':
    main()

