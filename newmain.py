import pygame as py
import sys
import random
from settings import *
import math
import time
from tiles import *
from PIL import Image

py.init()

screenSize = (display_width, display_height)
display = py.display.set_mode(screenSize, py.RESIZABLE)
py.display.set_caption('BLAZE BRIGADEEE')
clock = py.time.Clock()
gameIcon = py.image.load('icon.png')
py.display.set_icon(gameIcon)
background = py.image.load('ground.png').convert_alpha()
w = background.get_width()
h = background.get_height()
background = py.transform.scale(background, (w * 3, h * 3))


class Player(py.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = py.transform.rotozoom(py.image.load("player_sprite.png").convert_alpha(), 0, 1)
        self.image = py.transform.scale(self.image, (100 * player_size, 130 * player_size))
        self.pos = py.math.Vector2(player_start_x, player_start_y)
        self.rect = self.image.get_rect(center=self.pos)
        self.center = self.rect.center
        self.speed = player_speed

    def main(self):
        self.inputs()
        py.draw.rect(display, (0, 255, 0), self.rect)
        display.blit(self.image, (self.pos[0], self.pos[1]))

    def inputs(self):
        self.speed = player_speed

        keys = py.key.get_pressed()

        if keys[py.K_a]:
            display_scroll[0] -= self.speed
        if keys[py.K_d]:
            display_scroll[0] += self.speed
        if keys[py.K_w]:
            display_scroll[1] -= self.speed
        if keys[py.K_s]:
            display_scroll[1] += self.speed

        if display_scroll[0] != 0 and display_scroll[1] != 0:
            self.speed /= math.sqrt(2)
            self.speed /= math.sqrt(2)


player = Player()

display_scroll = [0, 0]


def draw_display():
    display.blit(background, (-1000, -3000))
    player.main()
    py.draw.rect(display, (255, 255, 255), (100 - display_scroll[0], 100 - display_scroll[1], 16, 16))
    py.display.update()


def main():
    run = True
    while run:
        for event in py.event.get():
            if event.type == py.QUIT:
                sys.exit()

        draw_display()
        clock.tick(FPS)


if __name__ == '__main__':
    main()