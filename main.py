import pygame
import random

black = (0, 0, 0)
white = (255, 255, 255)
lightRed = ("#F00022")
weakRed = ("#BD263A")
greyRed = ("#8A3742")
grey = ("#574544")


pygame.init()

display_width = int(1440)
display_height = int(720)
screenSize = (display_width, display_height)

screen = pygame.display.set_mode(screenSize)
pygame.display.set_caption('Platform Game')
clock = pygame.time.Clock()
screen.fill(lightRed)

crashed = False

ballImg = pygame.image.load("RedBall.png")


def ball(x, y):
    screen.blit(ballImg, (x, y))


while not crashed:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            crashed = True

        print(event)

    screen.fill(lightRed)
    ball(0, 0)

    pygame.display.update()
    clock.tick(60)

pygame.quit()
quit()