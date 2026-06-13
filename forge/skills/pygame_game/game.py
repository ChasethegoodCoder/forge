"""
Working pygame side-scroller skeleton (geometry-dash base). RUNS as-is.

This is a SCAFFOLD: the game loop, player physics, jump, ground, and scrolling
background already work. To turn it into a full game, fill in the three TODOs:
  TODO 1: spawn obstacles (spikes/blocks) that scroll left
  TODO 2: collision -> set self.dead = True
  TODO 3: score / restart

Controls: SPACE/UP/click = jump. R = restart.
"""
import sys
import pygame

W, H = 900, 500
GROUND_Y = H - 90
FPS = 60
GRAVITY = 0.9
JUMP_V = -15
SPEED = 7
CUBE = 40


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("pygame game")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 22)
        self.reset()

    def reset(self):
        self.px = 140                 # player x (fixed)
        self.py = GROUND_Y - CUBE     # player y
        self.vy = 0.0
        self.on_ground = True
        self.scroll = 0
        self.dead = False
        self.score = 0
        self.obstacles = []           # TODO 1: fill with obstacle rects/objects

    @property
    def player_rect(self):
        return pygame.Rect(int(self.px), int(self.py), CUBE, CUBE)

    def jump(self):
        if self.on_ground and not self.dead:
            self.vy = JUMP_V
            self.on_ground = False

    def update(self):
        if self.dead:
            return
        self.vy += GRAVITY
        self.py += self.vy
        if self.py >= GROUND_Y - CUBE:
            self.py = GROUND_Y - CUBE
            self.vy = 0
            self.on_ground = True
        self.scroll = (self.scroll + SPEED) % 40
        self.score += 1

        # TODO 1: spawn + move obstacles here (move each left by SPEED, drop off-screen)
        # TODO 2: collision -> if self.player_rect.colliderect(obstacle): self.dead = True

    def draw(self):
        self.screen.fill((24, 24, 38))
        for gx in range(-40, W + 40, 40):
            pygame.draw.line(self.screen, (38, 38, 58), (gx - self.scroll, 0),
                             (gx - self.scroll, GROUND_Y))
        pygame.draw.rect(self.screen, (45, 45, 70), (0, GROUND_Y, W, H - GROUND_Y))
        pygame.draw.rect(self.screen, (90, 200, 255), self.player_rect, border_radius=6)
        # TODO 1: draw obstacles
        self.screen.blit(self.font.render(f"Score {self.score}", True, (235, 235, 245)), (16, 14))
        if self.dead:
            t = self.font.render("CRASHED — press R", True, (255, 90, 110))
            self.screen.blit(t, t.get_rect(center=(W // 2, H // 2)))  # TODO 3
        pygame.display.flip()

    def run(self):
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if (e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE, pygame.K_UP)) \
                        or e.type == pygame.MOUSEBUTTONDOWN:
                    self.jump()
                if e.type == pygame.KEYDOWN and e.key == pygame.K_r and self.dead:
                    self.reset()
            self.update()
            self.draw()
            self.clock.tick(FPS)


if __name__ == "__main__":
    Game().run()
