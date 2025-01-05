# Simple Pong Game
import sys
import random
from math import pi, sin, cos
from PyQt5.QtCore import Qt, QObject, QTimer, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QPen, QPainterPath, QKeyEvent, QFont
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsScene, QGraphicsView, QGraphicsEllipseItem,
    QAction, QWidget, QVBoxLayout, QGraphicsPathItem, QGraphicsTextItem)

WIDTH: int = 1500
HEIGHT: int = 700
BALL_DIAMETER: int = 40
BALL_RADIUS: int = BALL_DIAMETER // 2
PADDLE_WIDTH: int = 60
BORDER_MARGIN: int = 10
FPS: int = 60
UPDATE_RATE: int = 1000 // FPS


class Controller(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        # Window setup
        self.setWindowTitle('Pong')
        central_widget: QWidget = QWidget(self)
        self.setCentralWidget(central_widget)
        central_layout: QVBoxLayout = QVBoxLayout()
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_widget.setLayout(central_layout)

        # Engine and Graphic scene setup
        self.engine = Engine(WIDTH, HEIGHT)
        self.engine.game_over.connect(self.game_over)  # type: ignore
        self.scene_height: int = self.engine.board_height + 2 * BORDER_MARGIN
        self.scene_width: int = self.engine.board_width + 2 * BORDER_MARGIN
        self.scene = QGraphicsScene(0, 0, self.scene_width, self.scene_height)
        self.game_view = QGraphicsView(self.scene, self)
        central_layout.addWidget(self.game_view)

        # View update timer
        self.view_timer = QTimer(self)
        self.view_timer.timeout.connect(self.update_game)  # type: ignore

        # Add menu
        self.add_menus()

        # Values to track
        self.paused: bool = False
        self.playing: bool = True
        self.paddles: list[Paddle] = []
        self.ball: Ball | None = None
        self.keys_held: set[int] = set()
        self.notification_text: QGraphicsTextItem | None = None
        self.player_score_and_rally: list[QGraphicsTextItem] = []

        # Start the game
        self.add_border()
        self.init_game()

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
        self.engine.initialise()
        self.render_ball()
        self.render_paddles()
        self.add_notification_text(message)

    def update_game(self) -> None:
        self.engine.check_game_over()
        if self.engine.check_goal() != "none":
            # Update score, reset ball
            self.engine.reset()

        # Check for player one wanting to move paddle
        if Qt.Key_W in self.keys_held:
            self.engine.move_paddle(player=0, direction=-1)
        elif Qt.Key_S in self.keys_held:
            self.engine.move_paddle(player=0, direction=1)

        # Check for player two wanting to move paddle
        if Qt.Key_O in self.keys_held:
            self.engine.move_paddle(player=1, direction=-1)
        elif Qt.Key_K in self.keys_held:
            self.engine.move_paddle(player=1, direction=1)

        self.engine.move_ball()
        self.render_paddles()
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

            # print(f"player: {player}, {x_pos, y_pos}")
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
        self.notification_text.setZValue(2)
        # Add the text item to the scene
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
            x, y = paddle_position
            length: int = self.engine.paddle_sizes[player]
            x_top_left = x - PADDLE_WIDTH // 2
            y_top_left = y - length // 2
            paddle = Paddle(x_top_left, y_top_left, PADDLE_WIDTH, length)
            self.scene.addItem(paddle)
            self.paddles.append(paddle)

    def render_ball(self) -> None:
        if self.ball:
            self.scene.removeItem(self.ball)

        x, y = self.engine.ball_position
        x_top_left = x - BALL_RADIUS
        y_top_left = y - BALL_RADIUS
        self.ball = Ball(x_top_left, y_top_left, BALL_DIAMETER)
        self.ball.setZValue(1)
        self.scene.addItem(self.ball)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        self.keys_held.add(event.key())
        if event.key() == Qt.Key_Space:
            self.toggle_pause_game()

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        self.keys_held.discard(event.key())  # will not throw an exception if event.key is not in the set


class Paddle(QGraphicsPathItem):
    def __init__(self, x: int, y: int, width: int, height: int, radius: int = 10) -> None:
        super().__init__()
        # Use a QPainterPath for a Rounded rectangle
        path = QPainterPath()
        path.addRoundedRect(x + BORDER_MARGIN, y + BORDER_MARGIN, width, height, radius, radius)
        self.setPath(path)
        self.setBrush(QBrush(QColor("light green")))
        pen = QPen(QColor("dark green"))
        pen.setWidth(2)
        self.setPen(pen)


class Ball(QGraphicsEllipseItem):
    def __init__(self, x: int, y: int, diameter: int) -> None:
        super().__init__(x + BORDER_MARGIN, y + BORDER_MARGIN, diameter, diameter)
        self.setBrush(QBrush(QColor("red")))


class Engine(QObject):
    game_over: pyqtSignal = pyqtSignal(str)

    def __init__(self, width, height) -> None:
        super().__init__()
        # X will be left to right position data
        # Y will be top to bottom position data
        self.board_width: int = width
        self.board_height: int = height

        # Ball variables
        self._ball_directions: list[tuple[int, int]] = [(1, 0), (1, -1), (1, 1), (-1, 0), (-1, -1), (-1, 1)]
        self.ball_move_amounts: list[tuple[int, int]] = [(x, y) for x in range(4, 11) for y in range(4, 11)]
        self.ball_move_pixels: tuple[int, int] = 10, 5  # Defaults to 3 pixels each direction
        self.current_ball_direction: tuple[int, int] = (0, 0)
        self.ball_position: tuple[int, int] = (0, 0)  # Position data for the middle of the ball

        # Paddles variables
        self.paddles: list[tuple[int, int]] = [(0, 0), (0, 0)]  # Stored is the exact middle of the paddles
        self.paddle_sizes: list[int] = [120, 120]  # Each player's paddle Length in pixels
        self.paddle_move_pixels: int = 10

        # Other variables
        self.scores: list[int] = [0, 0]  # Player scores
        self.rally_counter: list[int] = [0, 0]  # Each player's rally counter

    def initialise(self) -> None:
        self.scores = [0, 0]
        self.reset()

    def reset(self) -> None:
        self.current_ball_direction = random.choice(self._ball_directions)
        self.rally_counter = [0, 0]
        self.ball_position = self.board_width // 2, self.board_height // 2
        initial_paddle_y = self.board_height // 2
        self.paddles = [(0 + PADDLE_WIDTH // 2, initial_paddle_y),
                        (self.board_width - PADDLE_WIDTH // 2, initial_paddle_y)]

    def check_wall_collision(self, new_y: int, offset: int) -> bool:
        top = new_y + offset
        bottom = new_y - offset
        return top > self.board_height or bottom < 0

    def check_ball_collision(self, player: int, new_y: int, offset: int) -> bool:
        ball_perimeter = get_circle_points(self.ball_position, BALL_RADIUS)
        paddle = self.paddles[player]
        paddle_perimeter = get_rounded_rectangle_points((paddle[0], new_y), PADDLE_WIDTH, offset, 10)
        # Check top and bottom edges/corners for collision
        if not paddle_perimeter[2].isdisjoint(ball_perimeter):
            return True
        elif not paddle_perimeter[3].isdisjoint(ball_perimeter):
            return True

        return False

    def move_paddle(self, player: int, direction: int) -> None:
        new_y = self.paddles[player][1] + self.paddle_move_pixels * direction
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
        ball_perimeter: set[tuple[int, int]] = get_circle_points((new_ball_x, new_ball_y), BALL_RADIUS)
        # print(sorted(ball_perimeter))
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

    def check_goal(self) -> str:
        new_x = self.ball_position[0] + self.current_ball_direction[0] * self.ball_move_pixels[0]
        if new_x <= BALL_RADIUS:
            self.scores[1] += 1
            return "two"

        if new_x >= self.board_width - BALL_RADIUS:
            self.scores[0] += 1
            return "one"

        return "none"

    def check_game_over(self) -> None:
        for player, score in enumerate(self.scores):
            winner: str = "one" if player == 0 else "two"
            if score == 3:
                self.game_over.emit(f"Player {winner.capitalize()} won!")  # type: ignore


def get_circle_points(center: tuple[int, int],
                      radius: int,
                      number_points: int = 72,
                      start_angle: float = 0,
                      end_angle: float = 2 * pi
                      ) -> set[tuple[int, int]]:
    """
    Generate unique points on an arc or a full circle.
    Args:
        center (tuple[int, int]): Center of the circle (x, y).
        radius (int): Radius of the circle.
        number_points (int): Number of points to generate along the arc.
        start_angle (float): Starting angle in radians (default: 0).
        end_angle (float): Ending angle in radians (default: 2*pi).
    Returns: set[tuple[int, int]]: Set of unique (x, y) points on the arc.
    """
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
                                 num_arc_points: int = 15
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
    # perimeter_points = arc_tl | top_edge | arc_tr | right_edge | arc_br | bottom_edge | arc_bl | left_edge

    return [right_edge, left_edge, arc_tl | top_edge | arc_tr, arc_br | bottom_edge | arc_bl]


if __name__ == '__main__':
    app = QApplication(sys.argv)
    controller = Controller()
    controller.show()
    sys.exit(app.exec_())
