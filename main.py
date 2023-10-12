import pygame as py
import random

black = (0, 0, 0)
white = (255, 255, 255)
lightRed = ("#F00022")
weakRed = ("#BD263A")
greyRed = ("#8A3742")
grey = ("#574544")


py.init()

display_width = int(1440)
display_height = int(720)
screenSize = (display_width, display_height)

x_change = 0

screen = py.display.set_mode(screenSize)
py.display.set_caption('Platform Game')
clock = py.time.Clock()
screen.fill(lightRed)

py.draw.rect(screen, weakRed, py.Rect(30, 30, 60, 60))

crashed = False

ballImg = py.image.load("RedBall.png")
py.transform.scale(ballImg, (0.2, 0.2))

x = 0
y = 0


def ball(x, y):
    screen.blit(ballImg, (x, y))


while not crashed:

    for event in py.event.get():
        if event.type == py.QUIT:
            crashed = True

        print(event)

        if event.type == py.KEYDOWN:
            if event.key == py.K_LEFT:
                x_change = -5
            elif event.key == py.K_RIGHT:
                x_change = 5
        if event.type == py.KEYUP:
            if event.key == py.K_LEFT or event.key == py.K_RIGHT:
                x_change = 0

    x += x_change

    screen.fill(lightRed)
    ball(x, y)

    py.display.update()
    clock.tick(60)


py.quit()
quit()


