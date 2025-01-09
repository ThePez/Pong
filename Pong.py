# Simple Pong Game
import sys
import random
from math import pi, sin, cos
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QBrush, QColor, QPen, QPainterPath, QKeyEvent, QFont
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsScene, QGraphicsView, QGraphicsEllipseItem,
    QAction, QWidget, QVBoxLayout, QGraphicsPathItem, QGraphicsTextItem, QGridLayout, QLabel)

WIDTH: int = 1500
HEIGHT: int = 700
BALL_DIAMETER: int = 40
BALL_RADIUS: int = BALL_DIAMETER // 2
PADDLE_WIDTH: int = 60
PADDLE_MOVE_PIXELS: int = 15
BORDER_MARGIN: int = 10
FPS: int = 60
UPDATE_RATE: int = 1000 // FPS  # in milliseconds


class Controller(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        # Window setup
        self.setWindowTitle('Pong')
        self.setMinimumSize(1526, 920)
        central_widget: QWidget = QWidget(self)
        self.setCentralWidget(central_widget)
        central_layout: QVBoxLayout = QVBoxLayout()
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_widget.setLayout(central_layout)

        self.cpu_labels: list[QLabel] = []
        self.setup_control_text(central_layout)

        # Engine and Graphic scene setup
        self.engine = Engine(WIDTH, HEIGHT)
        self.scene_height: int = self.engine.board_height + 2 * BORDER_MARGIN
        self.scene_width: int = self.engine.board_width + 2 * BORDER_MARGIN
        self.scene = QGraphicsScene(0, 0, self.scene_width, self.scene_height)
        self.game_view = QGraphicsView(self.scene, self)
        central_layout.addWidget(self.game_view)

        # View update timer
        self.view_timer = QTimer(self)
        self.view_timer.timeout.connect(self.update_game)  # type: ignore

        # Add menu and border
        self.add_menus()
        self.add_border()

        # Values to track
        self.paused: bool = False
        self.playing: bool = True
        self.paddles: list[Paddle] = []
        self.hints: list[Paddle] = []
        self.guides: list[bool] = [False, False]
        self.ball: Ball | None = None
        self.keys_held: set[int] = set()
        self.notification_text: QGraphicsTextItem | None = None
        self.player_score_and_rally: list[QGraphicsTextItem] = []

        # Start the game
        self.init_game()

    def print_window_size(self):
        size = self.size()  # Get the current size of the window
        print(f"Window size: {size.width()}x{size.height()}")  # Print width and height

    def add_menus(self) -> None:
        menu_bar = self.menuBar()
        # Game menu
        game_menu = menu_bar.addMenu("Game")
        game_menu.aboutToShow.connect(self.pause_game)  # type: ignore
        game_menu.aboutToHide.connect(self.un_pause_game)  # type: ignore
        # Add actions to the "Game" menu
        restart_action = QAction("Restart", self)
        restart_action.triggered.connect(self.init_game)  # type: ignore
        game_menu.addAction(restart_action)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)  # type: ignore
        game_menu.addAction(exit_action)

    def setup_control_text(self, layout) -> None:
        # Create the control layout
        control_layout = QGridLayout()
        layout.addLayout(control_layout)

        controls = QLabel("Controls")
        controls.setFont(QFont('Arial', 16, QFont.Bold))
        controls.setAlignment(Qt.AlignCenter)  # Center the text inside the label
        player_one = QLabel("Player One\nUp: W  Hints: E\nDown: S  CPU: D")
        player_one.setFont(QFont('Arial', 16, QFont.Bold))
        player_one.setAlignment(Qt.AlignCenter)
        player_two = QLabel("Player Two\nUp: O  Hints: I\nDown: K  CPU: J")
        player_two.setFont(QFont('Arial', 16, QFont.Bold))
        player_two.setAlignment(Qt.AlignCenter)

        for player in range(2):
            label = QLabel(f"CPU Inactive")
            label.setFont(QFont('Arial', 16, QFont.Bold))
            label.setAlignment(Qt.AlignCenter)
            self.cpu_labels.append(label)
            control_layout.addWidget(label, 2, 0 + player * 2, 1, 2)

        control_layout.addWidget(controls, 0, 0, 1, 4)
        control_layout.addWidget(player_one, 1, 0, 1, 2)
        control_layout.addWidget(player_two, 1, 2, 1, 2)

    def init_game(self) -> None:
        self.engine.initialise()
        self.playing = True
        self.render_ball()
        self.render_paddles()
        self.update_score_and_rally_text()
        if self.notification_text:
            self.scene.removeItem(self.notification_text)
            self.notification_text = None

        self.view_timer.start(UPDATE_RATE)

    def game_over(self, message: str) -> None:
        self.view_timer.stop()
        self.playing = False
        self.engine.reset()
        self.render_ball()
        self.render_paddles()
        self.add_notification_text(message)

    def update_game(self) -> None:
        if message := self.engine.check_game_over():
            self.game_over(message)

        if _ := self.engine.check_goal():
            # Update score, reset ball
            self.engine.reset()

        # Ensure that player 1's cpu is off before trying to move
        if not self.engine.cpus[0]:
            # Check for player one wanting to move paddle
            if Qt.Key_W in self.keys_held:
                self.engine.move_paddle(player=0, direction=-1)
            elif Qt.Key_S in self.keys_held:
                self.engine.move_paddle(player=0, direction=1)

        # Ensure the player 2's cpu is off before trying to move
        if not self.engine.cpus[1]:
            # Check for player two wanting to move paddle
            if Qt.Key_O in self.keys_held:
                self.engine.move_paddle(player=1, direction=-1)
            elif Qt.Key_K in self.keys_held:
                self.engine.move_paddle(player=1, direction=1)

        for player in range(2):
            text = "Active" if self.engine.cpus[player] else "Inactive"
            self.cpu_labels[player].setText(f"CPU {text}")

        self.engine.move_ball()
        self.engine.cpu_move_paddles()
        self.render_paddles()
        self.render_guides()
        self.render_ball()
        self.update_score_and_rally_text()

    def pause_game(self) -> None:
        if not self.playing:
            return

        if not self.paused:
            self.view_timer.stop()
            self.paused = True
            self.add_notification_text("GAME PAUSED")

    def un_pause_game(self) -> None:
        if not self.playing:
            return

        self.paused = False
        if self.notification_text:
            self.scene.removeItem(self.notification_text)
            self.notification_text = None

        self.view_timer.start(UPDATE_RATE)

    def toggle_pause_game(self) -> None:
        if not self.playing:
            return

        if self.view_timer.isActive():
            self.pause_game()
        else:
            self.un_pause_game()

    def update_score_and_rally_text(self) -> None:
        for text_item in self.player_score_and_rally:
            self.scene.removeItem(text_item)

        self.player_score_and_rally.clear()
        for player in range(2):
            score = self.engine.scores[player]
            rally = self.engine.rally_counter[player]
            text_item = QGraphicsTextItem(f"Score: {score}\nRally: {rally}")
            text_item.setDefaultTextColor(QColor("grey"))
            text_item.setFont(QFont("Arial", 30, QFont.Bold))
            text_rectangle = text_item.boundingRect()
            if player == 0:
                x_pos = (self.scene_width // 2 - text_rectangle.width()) // 2
                y_pos = (self.scene_height - text_rectangle.height()) // 2

            else:
                x_pos = int(self.scene_width * 0.75 - text_rectangle.width())
                y_pos = (self.scene_height - text_rectangle.height()) // 2

            text_item.setPos(x_pos, y_pos)
            self.player_score_and_rally.append(text_item)
            self.scene.addItem(text_item)

    def add_notification_text(self, message: str) -> None:
        self.notification_text = QGraphicsTextItem(message)
        self.notification_text.setDefaultTextColor(QColor("blue"))
        self.notification_text.setFont(QFont("Arial", 30, QFont.Bold))
        text_rectangle = self.notification_text.boundingRect()
        x_pos = (self.scene_width - text_rectangle.width()) // 2
        y_pos = (self.scene_height - text_rectangle.height()) // 2
        self.notification_text.setPos(x_pos, y_pos)
        self.notification_text.setZValue(5)
        self.scene.addItem(self.notification_text)

    def add_border(self) -> None:
        pen = QPen(QColor("black"))
        pen.setWidth(20)
        height = self.engine.board_height + 2 * BORDER_MARGIN
        width = self.engine.board_width + 2 * BORDER_MARGIN
        self.scene.addRect(0, 0, width, height, pen)

    def render_paddles(self) -> None:
        for paddle in self.paddles:
            self.scene.removeItem(paddle)

        self.paddles.clear()
        for player, paddle_position in enumerate(self.engine.paddles):
            self.render_paddle(paddle_position, player)

    def render_paddle(self, center: tuple[int, int], player: int, hint: bool = False) -> None:
        x, y = center
        length: int = self.engine.paddle_sizes[player]
        x_top_left = x - PADDLE_WIDTH // 2
        y_top_left = y - length // 2
        paddle = Paddle(x_top_left, y_top_left, PADDLE_WIDTH, length, guide=hint)
        self.scene.addItem(paddle)
        if hint:
            self.hints.append(paddle)
        else:
            self.paddles.append(paddle)

    def render_ball(self) -> None:
        if self.ball:
            self.scene.removeItem(self.ball)

        x, y = self.engine.ball_position
        x_top_left = x - BALL_RADIUS
        y_top_left = y - BALL_RADIUS
        self.ball = Ball(x_top_left, y_top_left, BALL_DIAMETER)
        self.scene.addItem(self.ball)

    def render_guides(self) -> None:
        for guide in self.hints:
            self.scene.removeItem(guide)

        self.hints.clear()
        y: int = self.engine.ball_position[1]
        one_x_pos: int = self.engine.paddles[0][0]
        two_x_pos: int = self.engine.paddles[1][0]
        for player in range(2):
            # Guide must be on and CPU must be off for guides to be rendered
            if self.guides[player] and not self.engine.cpus[player]:
                new_y = min(y, self.engine.board_height - self.engine.paddle_sizes[player] // 2 - 1)
                new_y = max(new_y, self.engine.paddle_sizes[player] // 2 + 1)
                x = one_x_pos if player == 0 else two_x_pos
                self.render_paddle((x, new_y), player, hint=True)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        self.keys_held.add(event.key())
        if event.key() == Qt.Key_Space:  # Pause the game
            self.toggle_pause_game()
        elif event.key() == Qt.Key_E:  # Player 1 Guide
            self.guides[0] = self.guides[0] ^ True
        elif event.key() == Qt.Key_I:  # Player 2 Guide
            self.guides[1] = self.guides[1] ^ True
        elif event.key() == Qt.Key_D:  # Player 1 activate CPU
            self.engine.cpus[0] = self.engine.cpus[0] ^ True
        elif event.key() == Qt.Key_J:  # Player 2 Activate CPU
            self.engine.cpus[1] = self.engine.cpus[1] ^ True

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        self.keys_held.discard(event.key())  # will not throw an exception if event.key is not in the set


class Paddle(QGraphicsPathItem):
    def __init__(self, x: int, y: int, width: int, height: int, radius: int = 10, guide: bool = False) -> None:
        super().__init__()
        # Use a QPainterPath for a Rounded rectangle
        path = QPainterPath()
        path.addRoundedRect(x + BORDER_MARGIN, y + BORDER_MARGIN, width, height, radius, radius)
        self.setPath(path)
        if guide:
            self.setBrush(QBrush(QColor("light blue")))
            pen = QPen(QColor("dark blue"))
        else:
            self.setBrush(QBrush(QColor("light green")))
            pen = QPen(QColor("dark green"))
            self.setZValue(1)

        pen.setWidth(2)
        self.setPen(pen)


class Ball(QGraphicsEllipseItem):
    def __init__(self, x: int, y: int, diameter: int) -> None:
        super().__init__(x + BORDER_MARGIN, y + BORDER_MARGIN, diameter, diameter)
        self.setBrush(QBrush(QColor("red")))
        self.setZValue(2)


class Engine:
    def __init__(self, width, height) -> None:
        super().__init__()
        # X will be left to right position data
        # Y will be top to bottom position data
        self.board_width: int = width
        self.board_height: int = height

        # Ball variables
        self._ball_directions: list[tuple[int, int]] = [(1, 0), (1, -1), (1, 1), (-1, 0), (-1, -1), (-1, 1)]
        self.ball_move_amounts: list[tuple[int, int]] = [(x, y) for x in range(10, 16) for y in range(5, 16)]
        self.ball_move_pixels: tuple[int, int] = 10, 5  # Defaults to 3 pixels each direction
        self.current_ball_direction: tuple[int, int] = (0, 0)
        self.ball_position: tuple[int, int] = (0, 0)  # Position data for the middle of the ball

        # Paddles variables
        self.paddles: list[tuple[int, int]] = [(0, 0), (0, 0)]  # Stored is the exact middle of the paddles
        self.paddle_sizes: list[int] = [120, 120]  # Each player's paddle Length in pixels

        # Other variables
        self.cpus: list[bool] = [False, False]
        self.scores: list[int] = [0, 0]  # Player scores
        self.rally_counter: list[int] = [0, 0]  # Each player's rally counter

    def initialise(self) -> None:
        self.scores = [0, 0]
        initial_paddle_y = self.board_height // 2
        self.paddles = [(0 + PADDLE_WIDTH // 2, initial_paddle_y),
                        (self.board_width - PADDLE_WIDTH // 2, initial_paddle_y)]
        self.reset()

    def reset(self) -> None:
        self.current_ball_direction = random.choice(self._ball_directions)
        self.rally_counter = [0, 0]
        self.ball_position = self.board_width // 2, self.board_height // 2

    def check_wall_collision(self, new_y: int, offset: int) -> bool:
        top = new_y + offset
        bottom = new_y - offset
        return top > self.board_height or bottom < 0

    def check_ball_collision(self, player: int, new_y: int, offset: int) -> bool:
        ball_x = self.ball_position[0]
        if PADDLE_WIDTH * 2 < ball_x < self.board_width - PADDLE_WIDTH * 2:
            return False

        ball_perimeter = get_circle_points(self.ball_position, BALL_RADIUS)
        paddle = self.paddles[player]
        paddle_perimeter = get_rounded_rectangle_points((paddle[0], new_y), PADDLE_WIDTH, offset, 10)
        # Check top and bottom edges/corners for collision
        if not paddle_perimeter[2].isdisjoint(ball_perimeter):
            return True
        elif not paddle_perimeter[3].isdisjoint(ball_perimeter):
            return True

        return False

    def move_paddle(self, player: int, direction: int, pixels: int = PADDLE_MOVE_PIXELS) -> None:
        new_y = self.paddles[player][1] + pixels * direction
        # Ensure the paddles reach the borders
        if direction > 0:
            # Down
            new_y = min(new_y, self.board_height - self.paddle_sizes[player] // 2 - 1)
        else:
            # Up
            new_y = max(new_y, self.paddle_sizes[player] // 2 + 1)

        if (self.check_wall_collision(new_y, self.paddle_sizes[player] // 2)
                or self.check_ball_collision(player, new_y, self.paddle_sizes[player])):
            new_y = self.paddles[player][1]

        self.paddles[player] = (self.paddles[player][0], new_y)

    def check_paddle_collision(self) -> bool:
        current_x, current_y = self.current_ball_direction
        new_ball_x = self.ball_position[0] + self.current_ball_direction[0] * self.ball_move_pixels[0]
        new_ball_y = self.ball_position[1] + self.current_ball_direction[1] * self.ball_move_pixels[1]
        if PADDLE_WIDTH * 2 < new_ball_x < self.board_width - PADDLE_WIDTH * 2:
            return False

        ball_perimeter: set[tuple[int, int]] = get_circle_points((new_ball_x, new_ball_y), BALL_RADIUS)
        for player, paddle in enumerate(self.paddles):
            paddle_perimeter = get_rounded_rectangle_points(paddle, PADDLE_WIDTH, self.paddle_sizes[player], 10)
            # left or right edge
            if not ball_perimeter.isdisjoint(paddle_perimeter[player]):
                self.current_ball_direction = (-current_x, random.choice(range(-1, 2)))  # Swap X, random Y
                self.ball_move_pixels = random.choice(self.ball_move_amounts)
                self.rally_counter[player] += 1
                return True
            # Top edge of paddle
            elif not ball_perimeter.isdisjoint(paddle_perimeter[2]):
                self.current_ball_direction = (-current_x, -1)  # Swap X, Y to go up
                self.ball_move_pixels = random.choice(self.ball_move_amounts)
                self.rally_counter[player] += 1
                return True
            # Bottom edge of paddle
            elif not ball_perimeter.isdisjoint(paddle_perimeter[3]):
                self.current_ball_direction = (-current_x, 1)  # Swap X, Y to go down
                self.ball_move_pixels = random.choice(self.ball_move_amounts)
                self.rally_counter[player] += 1
                return True

        return False

    def move_ball(self) -> None:
        current_x_dir, current_y_dir = self.current_ball_direction
        new_x = self.ball_position[0] + self.current_ball_direction[0] * self.ball_move_pixels[0]
        new_y = self.ball_position[1] + self.current_ball_direction[1] * self.ball_move_pixels[1]
        if self.check_paddle_collision():
            new_x, new_y = self.ball_position  # Keep current position, will move on next update
        elif self.check_wall_collision(new_y, BALL_RADIUS):
            self.current_ball_direction = (current_x_dir, -current_y_dir)
            new_y = self.ball_position[1] + self.current_ball_direction[1] * self.ball_move_pixels[1]

        self.ball_position = new_x, new_y

    def cpu_move_paddles(self) -> None:
        ball_y = self.ball_position[1]
        for player in range(2):
            # If cpu active, try to move, otherwise skip
            if self.cpus[player]:
                paddle_y = self.paddles[player][1]
                gap: int = abs(paddle_y - ball_y)
                pixels: int = min(gap, PADDLE_MOVE_PIXELS)
                if paddle_y > ball_y:
                    self.move_paddle(player, -1, pixels=pixels)
                elif paddle_y < ball_y:
                    self.move_paddle(player, 1, pixels=pixels)

    def check_goal(self) -> str | None:
        new_x = self.ball_position[0] + self.current_ball_direction[0] * self.ball_move_pixels[0]
        if new_x <= BALL_RADIUS:
            self.scores[1] += 1
            return "two"

        if new_x >= self.board_width - BALL_RADIUS:
            self.scores[0] += 1
            return "one"

        return None

    def check_game_over(self) -> str | None:
        for player, score in enumerate(self.scores):
            winner: str = "one" if player == 0 else "two"
            if score == 10:
                return f"Player {winner.capitalize()} won!"

        return None


def get_circle_points(center: tuple[int, int],
                      radius: int,
                      number_points: int = 360,
                      start_angle: float = 0,
                      end_angle: float = 2 * pi
                      ) -> set[tuple[int, int]]:
    points: set[tuple[int, int]] = set()
    for i in range(number_points + 1):  # +1 to include the endpoint
        theta = start_angle + (end_angle - start_angle) * i / number_points
        x = int(center[0] + radius * cos(theta))
        y = int(center[1] + radius * sin(theta))
        points.add((x, y))  # Add point to the set

    return points


def get_rounded_rectangle_points(center: tuple[int, int],
                                 width: int,
                                 height: int,
                                 radius: int,
                                 num_arc_points: int = 90
                                 ) -> list[set[tuple[int, int]]]:
    # Ensure the radius is not larger than half of the rectangle's width or height
    radius = min(radius, width // 2, height // 2)

    # Rectangle boundaries
    left = center[0] - width // 2
    right = center[0] + width // 2
    top = center[1] - height // 2
    bottom = center[1] + height // 2

    # Centers of the four corner arcs
    top_left = (left + radius, top + radius)
    top_right = (right - radius, top + radius)
    bottom_right = (right - radius, bottom - radius)
    bottom_left = (left + radius, bottom - radius)

    # Generate points for the four quarter-circle arcs
    arc_tl = get_circle_points(top_left, radius, num_arc_points, start_angle=pi / 2, end_angle=pi)
    arc_tr = get_circle_points(top_right, radius, num_arc_points, start_angle=0, end_angle=pi / 2)
    arc_br = get_circle_points(bottom_right, radius, num_arc_points, start_angle=-pi / 2, end_angle=0)
    arc_bl = get_circle_points(bottom_left, radius, num_arc_points, start_angle=pi, end_angle=3 * pi / 2)

    # Generate points for the straight edges
    top_edge = {(x, top) for x in range(left + radius, right - radius + 1)}
    right_edge = {(right, y) for y in range(top + radius, bottom - radius + 1)}
    bottom_edge = {(x, bottom) for x in range(right - radius, left + radius - 1, -1)}
    left_edge = {(left, y) for y in range(bottom - radius, top + radius - 1, -1)}

    # Combine all points into a set to ensure uniqueness
    bottom_set = arc_br | bottom_edge | arc_bl
    top_set = arc_tl | top_edge | arc_tr
    return [right_edge, left_edge, top_set, bottom_set]


if __name__ == '__main__':
    app = QApplication(sys.argv)
    controller = Controller()
    controller.show()
    sys.exit(app.exec_())
