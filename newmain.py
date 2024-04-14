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
player_gun = py.image.load("gun_sprite.png").convert_alpha()
#player_gun.set_colorkey((255, 255, 255))
slime0 = py.image.load("slime_animation_0.png")
slime1 = py.image.load("slime_animation_1.png")
slime2 = py.image.load("slime_animation_2.png")
slime3 =py.image.load("slime_animation_3.png")
slime0 = py.transform.scale(slime0, (64, 60))
slime1 = py.transform.scale(slime1, (64, 60))
slime2 = py.transform.scale(slime2, (64, 60))
slime3 = py.transform.scale(slime3, (64, 60))
bullet_sound = py.mixer.Sound("344312__musiclegends__laser-shoot7.wav")
death_sound = py.mixer.Sound("173126__replix__death-sound-male.wav")


class Player(py.sprite.Sprite):
    # class for player
    def __init__(self):
        super().__init__()
        self.image = py.image.load("player_sprite.png").convert_alpha()
        # stores player image in self.image and removes transparent pixels and smooths edges
        self.image = py.transform.smoothscale(self.image, (200 * player_size, 260 * player_size))
        # This will scale the image based on the player_size stored in settings allowing me to
        # change the player size for a powerup for example, while keeping it to the same resolution
        # ratio of the original image
        self.base_image = self.image
        # stores a copy of the original player sprite
        self.pos = py.math.Vector2(player_start_x, player_start_y)
        # variable to store position of player set to starting position in settings
        self.rect = self.image.get_rect(center=self.pos)
        # makes a rectangle with the center being the position of the player
        self.pos = self.rect.topleft
        # sets player position to top left of rectangle for purpose of centering player on screen
        self.speed = PLAYER_SPEED
        # sets variable for player speed to constant in settings
        self.mouse_coordinates = [0, 0]
        # initialises mouse coordinates as a variable at (0,0)
        self.vel_x = 0
        # sets x velocity to 0
        self.vel_y = 0
        # sets y velocity to 0
        self.shoot = False
        # boolean to see whether player is trying to shoot
        self.shoot_cooldown = 0
        # sets shooting cooldown to 0 so player can shoot off spawn

    def player_collision(self):
        for enemy in enemies:
            if self.rect.colliderect(enemy.rect):
                player.kill()

    def move(self):
        py.draw.rect(display, (0, 255, 0), self.rect, width=2)
        display.blit(self.image, self.rect)

    def inputs(self):
        self.vel_x = 0
        self.vel_y = 0
        # resets horizontal and vertical velocities to 0

        keys = py.key.get_pressed()
        # stores which keys are pressed down

        if keys[py.K_a]:
            # if "a" key is pressed
            self.vel_x = -self.speed
            # velocity in x direction = negative of player speed
            for bullet in player_bullets:
                # for every bullet in the bullet list
                bullet.x += self.speed
                # player speed is added to bullet x position
        if keys[py.K_d]:
            # if "d" key is pressed
            self.vel_x = self.speed
            # velocity in x direction = player speed
            for bullet in player_bullets:
                # for every bullet in the bullet list
                bullet.x -= self.speed
                # player speed is taken away from bullet x position
        if keys[py.K_w]:
            # if "w" key is pressed
            self.vel_y = -self.speed
            # velocity in y direction = negative of player speed
            for bullet in player_bullets:
                # for every bullet in the bullet list
                bullet.y += self.speed
                # player speed is added to bullet y position
        if keys[py.K_s]:
            # if "s" key is pressed
            self.vel_y = self.speed
            # velocity in y direction = player speed
            for bullet in player_bullets:
                # for every bullet in the bullet list
                bullet.y -= self.speed
                # player speed is taken away from bullet y position

        if keys[py.K_g]:
            enemy = SlimeEnemy(self.pos[0] + random.randint(-600, 600) - display_scroll[0], self.pos[1] + random.randint(-600, 600) - display_scroll[1])
            enemies.append(enemy)

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
            bullet_sound.play()

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
        self.player_collision()

        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1


class Projectile(py.sprite.Sprite):
    def __init__(self, x, y, angle, image):
        super().__init__()
        self.angle = angle
        # set self.angle to angle given as parameter
        self.speed = BULLET_SPEED
        # set bullet speed to variable in settings file
        self.image = image
        # set image to image given as parameter for different bullets
        self.image = py.transform.rotozoom(self.image, (-self.angle - 90), BULLET_SCALE)
        # made the bullet sprite smaller or larger depending on the scale in the settings
        self.rect = self.image.get_rect()
        # made a rectangle for the hitbox of bullet
        self.x = x
        self.y = y
        # set x and y positions to position in parameters
        self.x_v = math.cos(self.angle * ((2 * math.pi) / 360)) * self.speed
        self.y_v = math.sin(self.angle * ((2 * math.pi) / 360)) * self.speed
        # self.angle * 2pi/360 converts from degrees to radians for function to work
        self.bullet_lifetime = BULLET_LIFETIME
        # sets how long bullet should exist for to prevent bullets existing once they've gone past
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

    def render(self):
        py.draw.rect(display, "yellow", self.rect, width=2)
        # renders bullet hit box
        display.blit(self.image, (self.x, self.y))
        # renders actual image of bullet

    def bullet_kill(self):
        if py.time.get_ticks() - self.spawn_time > self.bullet_lifetime:
            player_bullets.remove(self)
            self.kill()

    def update(self):
        self.bullet_movement()
        self.render()
        self.bullet_kill()


class SlimeEnemy(py.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.x = x
        self.y = y
        self.animation_images = [slime0, slime1, slime2, slime3]
        self.animation_count = 0
        self.reset_offset = 0
        self.offset_x = random.randrange(-150, 150)
        self.offset_y = random.randrange(-150, 150)
        self.rect = py.Rect(self.x, self.y, 64, 60)

    def main(self):
        py.draw.rect(display, "green", self.rect, width=2)
        if self.animation_count + 1 == 16:
            self.animation_count = 0
        self.animation_count += 1

        if self.reset_offset == 0:
            self.offset_x = random.randrange(-150, 150)
            self.offset_y = random.randrange(-150, 150)
            self.reset_offset = random.randrange(120, 150)
        else:
            self.reset_offset -= 1

        self.enemy_movement()

        display.blit(self.animation_images[self.animation_count//4], (self.x - display_scroll[0], self.y - display_scroll[1]))

    def enemy_movement(self):
        if (player.pos[0] + self.offset_x) > (self.x - display_scroll[0]):
            self.x += SLIME_SPEED
        elif (player.pos[0] + self.offset_x) < (self.x - display_scroll[0]):
            self.x -= SLIME_SPEED
        if (player.pos[1] + self.offset_y) > (self.y - display_scroll[1]):
            self.y += SLIME_SPEED
        elif (player.pos[1] + self.offset_y) < (self.y - display_scroll[1]):
            self.y -= SLIME_SPEED

        self.rect.topleft = (self.x - display_scroll[0], self.y - display_scroll[1])


player = Player()

enemies = []

display_scroll = [0, 0]

player_bullets = []


def bullet_collision():
    for enemy in enemies:
        for bullet in player_bullets:
            if bullet.rect.colliderect(enemy.rect):
                bullet.kill()
                player_bullets.remove(bullet)
                enemy.kill()
                enemies.remove(enemy)
                death_sound.play()


def draw_display():
    display.fill((0, 0, 0))
    display.blit(background, (-1000 - display_scroll[0], -3000 - display_scroll[1]))
    py.draw.rect(display, (255, 255, 255), (100 - display_scroll[0], 100 - display_scroll[1], 16, 16))
    player.main()
    for bullet in player_bullets:
        bullet.update()
    for enemy in enemies:
        enemy.main()
    bullet_collision()
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

