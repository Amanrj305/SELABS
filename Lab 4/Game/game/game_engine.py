from unicodedata import name

import pygame
import math
from array import array
from .paddle import Paddle
from .ball import Ball
from .brick import Brick
from game import brick

# Game Engine

WHITE = (255, 255, 255)
BG = (15, 15, 25)
BRICK_COLORS = [
    (200, 60, 60),
    (200, 140, 60),
    (200, 200, 60),
    (80, 180, 80),
    (80, 140, 200),
]

class GameEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.difficulty = "Medium"
        self.ball_speed = 4

        self.paddle = Paddle(width // 2 - 50, height - 30, 100, 14)

        self.ball = Ball(width // 2, height - 50, radius=8)
        self.ball.vx, self.ball.vy = self.ball_speed, -self.ball_speed

        self.rows, self.cols = 5, 8
        self.bricks = self._build_bricks(self.rows, self.cols)

        self.lives = 3
        self.score = 0
        self.font = pygame.font.SysFont("Arial", 28)
        self.title_font = pygame.font.SysFont("Arial", 52, bold=True)
        self.end_font = pygame.font.SysFont("Arial", 30)
        self.game_over = False
        self.result = None  # "win" or "lose"
        self.audio_enabled = False
        self.sounds = {}
        self._init_audio()

    def _build_bricks(self, rows, cols):
        bricks = []
        margin, gap, top = 30, 6, 60
        brick_w = (self.width - margin * 2 - gap * (cols - 1)) // cols
        brick_h = 22
        for r in range(rows):
            for c in range(cols):
                x = margin + c * (brick_w + gap)
                y = top + r * (brick_h + gap)
                bricks.append(Brick(x, y, brick_w, brick_h))
        return bricks

    def _resolve_ball_collision(self, target_rect, previous_ball_rect):
        ball_rect = self.ball.rect()

        # Work out which side the ball crossed during this frame.
        possible_hits = []

        # Ball came from above.
        if previous_ball_rect.bottom <= target_rect.top:
            possible_hits.append(
                ("top", ball_rect.bottom - target_rect.top)
            )

        # Ball came from below.
        if previous_ball_rect.top >= target_rect.bottom:
            possible_hits.append(
                ("bottom", target_rect.bottom - ball_rect.top)
            )

        # Ball came from the left.
        if previous_ball_rect.right <= target_rect.left:
            possible_hits.append(
                ("left", ball_rect.right - target_rect.left)
            )

        # Ball came from the right.
        if previous_ball_rect.left >= target_rect.right:
            possible_hits.append(
                ("right", target_rect.right - ball_rect.left)
            )

        # If more than one side was crossed at a corner,
        # use the side with the smallest penetration.
        if possible_hits:
            side = min(possible_hits, key=lambda hit: hit[1])[0]
        else:
            # Fallback for an unusual overlap, such as the paddle
            # moving into the ball during the same frame.
            overlaps = {
                "left": ball_rect.right - target_rect.left,
                "right": target_rect.right - ball_rect.left,
                "top": ball_rect.bottom - target_rect.top,
                "bottom": target_rect.bottom - ball_rect.top,
            }

            side = min(overlaps, key=overlaps.get)

        # Move the ball outside the object and send it away from
        # the side that it hit.
        if side == "top":
            self.ball.y = target_rect.top - self.ball.radius
            self.ball.vy = -abs(self.ball.vy)

        elif side == "bottom":
            self.ball.y = target_rect.bottom + self.ball.radius
            self.ball.vy = abs(self.ball.vy)

        elif side == "left":
            self.ball.x = target_rect.left - self.ball.radius
            self.ball.vx = -abs(self.ball.vx)

        elif side == "right":
            self.ball.x = target_rect.right + self.ball.radius
            self.ball.vx = abs(self.ball.vx)

    def handle_event(self, event):
        if not self.game_over:
            return

        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_1:
                self._restart_game("Easy")

            elif event.key == pygame.K_2:
                self._restart_game("Medium")

            elif event.key == pygame.K_3:
                self._restart_game("Hard")

            elif event.key in (pygame.K_ESCAPE, pygame.K_q):
                pygame.event.post(
                    pygame.event.Event(pygame.QUIT)
                )

    def handle_input(self):
        if self.game_over:
            return
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.paddle.move(-self.paddle.speed, self.width)
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.paddle.move(self.paddle.speed, self.width)

    def update(self):
        if self.game_over:
            return

        # Remember where the ball was before this frame.
        previous_ball_rect = self.ball.rect()

        self.ball.move()

        # Left and right wall collisions.
        wall_hit = False

        if self.ball.x - self.ball.radius <= 0:
            self.ball.x = self.ball.radius
            self.ball.vx = abs(self.ball.vx)
            wall_hit = True

        elif self.ball.x + self.ball.radius >= self.width:
            self.ball.x = self.width - self.ball.radius
            self.ball.vx = -abs(self.ball.vx)
            wall_hit = True

        if self.ball.y - self.ball.radius <= 0:
            self.ball.y = self.ball.radius
            self.ball.vy = abs(self.ball.vy)
            wall_hit = True

        if wall_hit:
            self._play_sound("hit")

        # Paddle collision.
        paddle_rect = self.paddle.rect()

        if self.ball.rect().colliderect(paddle_rect):
            self._resolve_ball_collision(
                paddle_rect,
                previous_ball_rect
            )

            self._play_sound("hit")

        # Brick collisions.
        for brick in self.bricks:
            if brick.alive:
                brick_rect = brick.rect()

                if self.ball.rect().colliderect(brick_rect):
                    self._resolve_ball_collision(
                        brick_rect,
                        previous_ball_rect
                    )

                    brick.alive = False
                    self.score += 1

                    self._play_sound("brick")

                    break

        # Ball fell below the screen.
        if self.ball.y - self.ball.radius > self.height:
            self.lives -= 1

            if self.lives <= 0:
                self._finish_game("lose")
            else:
                self._reset_ball()

        # All bricks destroyed.
        if all(not b.alive for b in self.bricks):
            self._finish_game("win")

    def _init_audio(self):
        try:
            # pygame.init() may already have initialized the mixer.
            # If not, initialize it ourselves.
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(
                    frequency=44100,
                    size=-16,
                    channels=2,
                    buffer=512
                )

            mixer_info = pygame.mixer.get_init()

            if mixer_info is None:
                return

            # Our generated samples use signed 16-bit audio.
            # Reinitialize only if the mixer is using another format.
            if mixer_info[1] != -16:
                pygame.mixer.quit()
                pygame.mixer.init(
                    frequency=44100,
                    size=-16,
                    channels=2,
                    buffer=512
                )

            self.sounds = {
                "brick": self._make_tone(
                    frequency=750,
                    duration=0.07,
                    volume=0.30
                ),

                "hit": self._make_tone(
                    frequency=420,
                    duration=0.045,
                    volume=0.25
                ),

                "win": self._make_tone(
                    frequency=950,
                    duration=0.30,
                    volume=0.35
                ),

                "game_over": self._make_tone(
                    frequency=180,
                    duration=0.40,
                    volume=0.35
                )
            }

            self.audio_enabled = True

        except pygame.error as error:
            # Audio failure must not stop gameplay.
            self.audio_enabled = False
            self.sounds = {}
            print("Audio disabled:", error)

    def _make_tone(self, frequency, duration, volume):
        sample_rate, _, channels = pygame.mixer.get_init()

        sample_count = int(sample_rate * duration)

        samples = array("h")

        # A short fade reduces clicking at the start/end of a tone.
        fade_samples = max(
            1,
            int(sample_rate * 0.01)
        )

        for i in range(sample_count):
            start_fade = min(
                1.0,
                i / fade_samples
            )

            end_fade = min(
                1.0,
                (sample_count - 1 - i) / fade_samples
            )

            envelope = max(
                0.0,
                min(start_fade, end_fade)
            )

            value = int(
                32767
                * volume
                * envelope
                * math.sin(
                    2 * math.pi
                    * frequency
                    * i
                    / sample_rate
                )
            )

            # Duplicate each sample for every mixer channel.
            for _ in range(channels):
                samples.append(value)

        return pygame.mixer.Sound(
            buffer=samples.tobytes()
        )

    def _play_sound(self, name):
        if not self.audio_enabled:
            return

        sound = self.sounds.get(name)

        if sound is None:
            return

        try:
            sound.play()
        except pygame.error:
            # If the audio device disappears while the game is running,
            # continue silently instead of crashing.
            self.audio_enabled = False

    def _finish_game(self, result):
        if self.game_over:
            return

        self.game_over = True
        self.result = result

        if result == "win":
            self._play_sound("win")
        else:
            self._play_sound("game_over")

    def _restart_game(self, difficulty):
        settings = {
            "Easy": {
                "ball_speed": 3,
                "paddle_width": 130
            },
            "Medium": {
                "ball_speed": 4,
                "paddle_width": 100
            },
            "Hard": {
                "ball_speed": 6,
                "paddle_width": 75
            }
        }

        selected = settings[difficulty]

        self.difficulty = difficulty
        self.ball_speed = selected["ball_speed"]

        paddle_width = selected["paddle_width"]

        self.paddle = Paddle(
            self.width // 2 - paddle_width // 2,
            self.height - 30,
            paddle_width,
            14
        )

        self.ball = Ball(
            self.width // 2,
            self.height - 50,
            radius=8
        )

        self.ball.vx = self.ball_speed
        self.ball.vy = -self.ball_speed

        self.bricks = self._build_bricks(
            self.rows,
            self.cols
        )

        self.lives = 3
        self.score = 0

        self.game_over = False
        self.result = None

    def _reset_ball(self):
        self.ball.x = self.width // 2
        self.ball.y = self.height - 50

        self.ball.vx = self.ball_speed
        self.ball.vy = -self.ball_speed

    def render(self, screen):
        screen.fill(BG)

        pygame.draw.rect(screen, WHITE, self.paddle.rect())
        pygame.draw.circle(screen, WHITE, (int(self.ball.x), int(self.ball.y)), self.ball.radius)

        for i, brick in enumerate(self.bricks):
            if brick.alive:
                row = i // self.cols
                color = BRICK_COLORS[row % len(BRICK_COLORS)]
                pygame.draw.rect(screen, color, brick.rect())

        score_text = self.font.render(f"Score: {self.score}", True, WHITE)
        screen.blit(score_text, (10, 10))
        lives_text = self.font.render(f"Lives: {self.lives}", True, WHITE)
        screen.blit(lives_text, (self.width - 130, 10))

        if self.game_over:
            overlay = pygame.Surface(
            (self.width, self.height),
            pygame.SRCALPHA
            )
            overlay.fill((0, 0, 0, 190))
            screen.blit(overlay, (0, 0))

            if self.result == "win":
                title = self.title_font.render(
                "YOU WIN!",
                True,
                (80, 220, 100)
                )
            else:
                title = self.title_font.render(
                "GAME OVER",
                True,
                (230, 70, 70)
                )

            score_text = self.end_font.render(
                f"Final Score: {self.score}",
                True,
                WHITE
            )

            difficulty_text = self.end_font.render(
                "1 - Easy    2 - Medium    3 - Hard",
                True,
                WHITE
            )

            exit_text = self.end_font.render(
                "Q or ESC - Exit",
                True,
                WHITE
            )

            current_text = self.font.render(
                f"Difficulty: {self.difficulty}",
                True,
                WHITE
            )

            title_rect = title.get_rect(
                center=(self.width // 2, self.height // 2 - 70)
            )

            score_rect = score_text.get_rect(
                center=(self.width // 2, self.height // 2)
            )

            difficulty_rect = difficulty_text.get_rect(
                center=(self.width // 2, self.height // 2 + 60)
            )

            exit_rect = exit_text.get_rect(
                center=(self.width // 2, self.height // 2 + 105)
            )

            current_rect = current_text.get_rect(
                center=(self.width // 2, self.height // 2 + 145)
            )

            screen.blit(title, title_rect)
            screen.blit(score_text, score_rect)
            screen.blit(difficulty_text, difficulty_rect)
            screen.blit(exit_text, exit_rect)
            screen.blit(current_text, current_rect)
