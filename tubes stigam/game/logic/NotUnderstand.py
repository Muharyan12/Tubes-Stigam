import random
from typing import Optional, List, Tuple
from game.logic.base import BaseLogic
from game.models import GameObject, Board, Position, Properties
from game.util import clamp

def get_direction_v2(current_x, current_y, dest_x, dest_y):
    delta_x = clamp(dest_x - current_x, -1, 1)
    delta_y = clamp(dest_y - current_y, -1, 1)
    if delta_x == 0 or delta_y == 0:
        return delta_x, delta_y
    else:
        if current_x % 2 == 1:
            return delta_x, 0
        else:
            return 0, delta_y

def count_steps(a: Position, b: Position) -> int:
    return abs(a.x - b.x) + abs(a.y - b.y)

def position_equals(p1: Position, p2: Position) -> bool:
    return p1.x == p2.x and p1.y == p2.y

def same_direction(pivot: Position, a: Position, b: Position) -> bool:
    if a.x > pivot.x and b.x > pivot.x and a.y > pivot.y and b.y > pivot.y:
        return True
    if a.x < pivot.x and b.x < pivot.x and a.y > pivot.y and b.y > pivot.y:
        return True
    if a.x < pivot.x and b.x < pivot.x and a.y < pivot.y and b.y < pivot.y:
        return True
    if a.x > pivot.x and b.x > pivot.x and a.y < pivot.y and b.y < pivot.y:
        return True
    return False

def dodge_tele(curr_po: Position, near_tele: Position, far_tele: Position, goal_po: Position) -> Position:
    delta_x = goal_po.x - curr_po.x
    delta_y = goal_po.y - curr_po.y

    if curr_po.y == goal_po.y:
        if curr_po.y + 1 == far_tele.y or curr_po.y - 1 == far_tele.y:
            return Position(x=curr_po.x, y=curr_po.y + 1 if curr_po.y + 1 == far_tele.y else curr_po.y - 1)
        elif near_tele.y + 1 == far_tele.y or near_tele.y - 1 == far_tele.y:
            return Position(x=near_tele.x, y=near_tele.y)
        return Position(x=curr_po.x, y=curr_po.y + 1 if curr_po.y + 1 < 15 else curr_po.y - 1)

    elif curr_po.x == goal_po.x:
        if curr_po.x + 1 == far_tele.x or curr_po.x - 1 == far_tele.x:
            return Position(x=curr_po.x + 1 if curr_po.x + 1 == far_tele.x else curr_po.x - 1, y=curr_po.y)
        elif near_tele.x + 1 == far_tele.x or near_tele.x - 1 == far_tele.x:
            return Position(x=near_tele.x, y=near_tele.y)
        return Position(x=curr_po.x + 1 if curr_po.x + 1 < 15 else curr_po.x - 1, y=curr_po.y)

    elif curr_po.y == near_tele.y:
        return Position(x=curr_po.x, y=curr_po.y + 1 if delta_y > 0 else curr_po.y - 1)

    elif curr_po.x == near_tele.x:
        return Position(x=curr_po.x + 1 if delta_x > 0 else curr_po.x - 1, y=curr_po.y)

    else:
        return goal_po

class Portals:
    closest_portal: GameObject
    farthest_portal: GameObject

    def __init__(self, portal_list: List[GameObject], current_position: Position):
        if count_steps(current_position, portal_list[0].position) < count_steps(current_position, portal_list[1].position):
            self.closest_portal = portal_list[0]
            self.farthest_portal = portal_list[1]
        else:
            self.closest_portal = portal_list[1]
            self.farthest_portal = portal_list[0]

    def count_steps_by_portal(self, current_position: Position, target_position: Position) -> int:
        return count_steps(current_position, self.closest_portal.position) + count_steps(self.farthest_portal.position, target_position)

    def is_closer_by_portal(self, current_position: Position, target_position: Position) -> bool:
        return self.count_steps_by_portal(current_position, target_position) < count_steps(current_position, target_position)

class Player:
    current_position: Position
    target_position: Optional[Position]
    base_position: Position
    next_move: Tuple[int, int]
    current_target: Optional[GameObject]
    inventory_size: int
    diamonds_being_held: int
    is_inside_portal: bool
    is_avoiding_portal: bool
    milliseconds_left: int

    def __init__(self, current_position: Position, props: Properties):
        self.current_position = current_position
        self.base_position = props.base
        self.inventory_size = props.inventory_size
        self.diamonds_being_held = props.diamonds
        self.milliseconds_left = props.milliseconds_left
        self.is_inside_portal = False
        self.is_avoiding_portal = False
        self.current_target = None
        self.target_position = None
        self.next_move = (0, 0)

    def is_inventory_full(self) -> bool:
        return self.diamonds_being_held >= self.inventory_size

    def set_target(self, obj: GameObject):
        self.current_target = obj
        self.target_position = obj.position

    def set_target_position(self, pos: Position):
        self.target_position = pos
        self.current_target = None

    def is_invalid_move(self, delta_x: int, delta_y: int, board: Board) -> bool:
        nx = self.current_position.x + delta_x
        ny = self.current_position.y + delta_y
        return nx < 0 or nx >= board.width or ny < 0 or ny >= board.height

    def avoid_obstacles(self, portals: Portals, is_avoiding_portal: bool, board: Board):
        if not self.target_position:
            return

        delta_x, delta_y = get_direction_v2(self.current_position.x, self.current_position.y, self.target_position.x, self.target_position.y)
        next_x, next_y = self.current_position.x + delta_x, self.current_position.y + delta_y

        if (is_avoiding_portal or (self.current_target is None or self.current_target.type != "TeleportGameObject") and
            (position_equals(Position(next_x, next_y), portals.closest_portal.position) or position_equals(Position(next_x, next_y), portals.farthest_portal.position))):
            
            alt_dx, alt_dy = 0, 0
            if delta_x == 0:
                alt_dx, alt_dy = delta_y, delta_x
            else:
                alt_dx, alt_dy = delta_y, delta_x

            if self.is_invalid_move(alt_dx, alt_dy, board):
                alt_dx, alt_dy = -alt_dx, -alt_dy

            if alt_dy == 0:
                self.is_avoiding_portal = True

            delta_x, delta_y = alt_dx, alt_dy

        self.next_move = delta_x, delta_y

class Diamonds:
    diamonds_list: List[GameObject]
    chosen_diamond: Optional[GameObject]
    chosen_diamond_distance: int
    chosen_target: Optional[GameObject]
    red_button: GameObject

    def __init__(self, diamonds_list: List[GameObject], red_button: GameObject, diamonds_being_held: int):
        self.diamonds_list = [d for d in diamonds_list if d.properties.points == 1 or diamonds_being_held < 4]
        self.chosen_diamond = None
        self.chosen_diamond_distance = float('inf')
        self.red_button = red_button
        self.chosen_target = None

    def filter_diamond(self, current_position: Position, enemy_position: Position):
        self.diamonds_list = [d for d in self.diamonds_list if d and not same_direction(current_position, enemy_position, d.position)]

    def choose_diamond(self, player: Player, portals: Portals):
        max_step_diff = 2
        for diamond in self.diamonds_list:
            diamond_distance = count_steps(player.current_position, diamond.position)
            if player.diamonds_being_held == 4:
                diamond_to_base = count_steps(diamond.position, player.base_position)
                diamond_to_portal1 = count_steps(diamond.position, portals.closest_portal.position) + count_steps(portals.farthest_portal.position, player.base_position)
                diamond_to_portal2 = count_steps(diamond.position, portals.farthest_portal.position) + count_steps(portals.closest_portal.position, player.base_position)
                diamond_distance += min(diamond_to_base, diamond_to_portal1, diamond_to_portal2)

            point_diff = (diamond.properties.points - (self.chosen_diamond.properties.points if self.chosen_diamond else 0))
            if self.chosen_diamond_distance > diamond_distance - (point_diff * max_step_diff):
                self.chosen_diamond = diamond
                self.chosen_diamond_distance = diamond_distance
                self.chosen_target = diamond

        if (not player.is_inside_portal and self.chosen_diamond):
            for diamond in self.diamonds_list:
                diamond_distance = portals.count_steps_by_portal(player.current_position, diamond.position)
                if player.diamonds_being_held == 4:
                    diamond_to_base = count_steps(diamond.position, player.base_position)
                    diamond_to_portal1 = count_steps(diamond.position, portals.closest_portal.position) + count_steps(portals.farthest_portal.position, player.base_position)
                    diamond_to_portal2 = count_steps(diamond.position, portals.farthest_portal.position) + count_steps(portals.closest_portal.position, player.base_position)
                    diamond_distance += min(diamond_to_base, diamond_to_portal1, diamond_to_portal2)
                point_diff = (diamond.properties.points - (self.chosen_diamond.properties.points if self.chosen_diamond else 0))
                if self.chosen_diamond_distance > diamond_distance - (point_diff * max_step_diff):
                    self.chosen_diamond = diamond
                    self.chosen_diamond_distance = diamond_distance
                    self.chosen_target = portals.closest_portal

    def check_red_button(self, player: Player, portals: Portals):
        if not player.is_inside_portal:
            red_button_distance = min(count_steps(player.current_position, self.red_button.position),
                                      portals.count_steps_by_portal(player.current_position, self.red_button.position))
        else:
            red_button_distance = count_steps(player.current_position, self.red_button.position)

        if player.diamonds_being_held == 4:
            red_button_to_base = count_steps(self.red_button.position, player.base_position)
            red_button_to_portal1 = count_steps(self.red_button.position, portals.closest_portal.position) + count_steps(portals.farthest_portal.position, player.base_position)
            red_button_to_portal2 = count_steps(self.red_button.position, portals.farthest_portal.position) + count_steps(portals.closest_portal.position, player.base_position)
            red_button_distance += min(red_button_to_base, red_button_to_portal1, red_button_to_portal2)

        max_step_diff = 4
        if red_button_distance + max_step_diff <= self.chosen_diamond_distance:
            if portals.is_closer_by_portal(player.current_position, self.red_button.position):
                self.chosen_target = portals.closest_portal
            else:
                self.chosen_target = self.red_button

class Enemies:
    enemies_list: List[GameObject]
    target_enemy: Optional[GameObject]
    target_enemy_distance: int
    try_tackle: bool

    def __init__(self, bots_list: List[GameObject], player_bot: GameObject):
        self.enemies_list = [bot for bot in bots_list if bot.id != player_bot.id]
        self.target_enemy = None
        self.target_enemy_distance = float('inf')
        self.try_tackle = False

    def check_nearby_enemy(self, diamonds: Diamonds, player: Player, portals: Portals, has_tried_tackle: bool):
        for enemy in self.enemies_list:
            enemy_distance = count_steps(player.current_position, enemy.position)
            if enemy_distance < self.target_enemy_distance:
                self.target_enemy = enemy
                self.target_enemy_distance = enemy_distance

        if (self.target_enemy_distance == 2 and not has_tried_tackle and
           (player.current_position.x != self.target_enemy.position.x and player.current_position.y != self.target_enemy.position.y)):
            player.next_move = get_direction_v2(player.current_position.x, player.current_position.y,
                                               self.target_enemy.position.x, self.target_enemy.position.y)
            self.try_tackle = True
        elif self.target_enemy_distance == 3:
            self.avoid_enemy(player, diamonds, portals)

    def avoid_enemy(self, player: Player, diamonds: Diamonds, portals: Portals):
        diamonds.filter_diamond(player.current_position, self.target_enemy.position)
        diamonds.choose_diamond(player, portals)
        if not same_direction(player.current_position, self.target_enemy.position, diamonds.red_button.position):
            diamonds.check_red_button(player, portals)

class GameState:
    board: Board
    player_bot: GameObject

    def __init__(self, board_bot: GameObject, board: Board):
        self.board = board
        self.player_bot = board_bot

    def initialize(self):
        list_of_diamonds = []
        list_of_portals = []
        list_of_bots = []
        red_button = None

        for obj in self.board.game_objects:
            if obj.type == "DiamondGameObject":
                list_of_diamonds.append(obj)
            elif obj.type == "DiamondButtonGameObject":
                red_button = obj
            elif obj.type == "TeleportGameObject":
                list_of_portals.append(obj)
            elif obj.type == "BotGameObject":
                list_of_bots.append(obj)

        return (Player(self.player_bot.position, self.player_bot.properties),
                Diamonds(list_of_diamonds, red_button, self.player_bot.properties.diamonds),
                Portals(list_of_portals, self.player_bot.position),
                Enemies(list_of_bots, self.player_bot))

    def no_time_left(self, current_position: Position, base_position: Position) -> bool:
        if count_steps(current_position, base_position) == 0:
            return False
        return self.player_bot.properties.milliseconds_left / count_steps(current_position, base_position) <= 1300

class NotUnderstand(BaseLogic):
    def __init__(self):
        self.back_to_base = False
        self.is_avoiding_portal = False
        self.tackle = False

    def next_move(self, board_bot: GameObject, board: Board) -> Tuple[int, int]:
        game_state = GameState(board_bot, board)
        player, diamonds, portals, enemies = game_state.initialize()

        if position_equals(player.current_position, player.base_position):
            self.back_to_base = False
        elif position_equals(player.current_position, portals.closest_portal.position):
            player.is_inside_portal = True
        else:
            player.is_inside_portal = False

        if self.back_to_base or player.is_inventory_full() or game_state.no_time_left(player.current_position, player.base_position):
            player.set_target_position(player.base_position)
            self.back_to_base = True

            if (not player.is_inside_portal and
                (not game_state.no_time_left(player.current_position, player.base_position) or
                 count_steps(player.current_position, portals.closest_portal.position) == 1) and
                portals.is_closer_by_portal(player.current_position, player.base_position)):
                player.set_target(portals.closest_portal)
        else:
            diamonds.choose_diamond(player, portals)
            if diamonds.chosen_target:
                diamonds.check_red_button(player, portals)
                player.set_target(diamonds.chosen_target)
            else:
                player.set_target_position(player.base_position)
                self.back_to_base = True

        if not game_state.no_time_left(player.current_position, player.base_position):
            enemies.check_nearby_enemy(diamonds, player, portals, self.tackle)
            self.tackle = enemies.try_tackle

        if not enemies.try_tackle:
            player.avoid_obstacles(portals, self.is_avoiding_portal, board)
            self.is_avoiding_portal = player.is_avoiding_portal

        if player.next_move == (0, 0):
            directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]
            curr_dir = random.choice(directions)
            player.next_move = curr_dir

        return player.next_move
