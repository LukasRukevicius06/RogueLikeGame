import pygame as py

class Spritesheet:
    def __init__(self, filename):
        self.filename = filename
        self.sprite_sheet = py.image.load(filename).convert()

    def get_sprite(self, x, y, w, h):