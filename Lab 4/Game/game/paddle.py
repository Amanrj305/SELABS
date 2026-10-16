import pygame

class Paddle:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.speed = 7

    def move(self, dx, screen_width):
        self.x += dx
        self.x = max(0, min(self.x, screen_width - self.width))

    def rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)
