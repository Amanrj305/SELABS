import pygame

class Brick:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.alive = True

    def rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)
