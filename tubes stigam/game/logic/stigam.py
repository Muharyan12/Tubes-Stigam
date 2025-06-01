import random
from typing import Optional, List, Tuple
from game.logic.base import BaseLogic
from game.models import GameObject, Board, Position
from game.util import clamp

class Stigam(BaseLogic):
    def init(self):
        # arah pergerakan: kanan, bawah, kiri, atas
        self.directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        # posisi tujuan
        self.goal_position: Optional[Position] = None
        # arah saat ini
        self.current_direction = 0

    def distance(self, a: Position, b: Position) -> int:
        # Menghitung jarak Manhattan antar dua posisi
        return abs(a.x - b.x) + abs(a.y - b.y)

    def distance_portal(self, curr_pos: Position, transition: Position, target_pos: Position) -> int:
        # jarak dari posisi sekarang ke target melewati portal
        return (self.distance(curr_pos, transition) +
                self.distance(transition, target_pos))

    def nearest_position(self, curr_pos: Position, positions: List[Position]) -> Optional[Position]:
        # mencari posisi terdekat dari daftar posisi
        if not positions:
            return None
        return min(positions, key=lambda p: self.distance(curr_pos, p))

    def objects_in_area(self, center: Position, positions: List[Position], area: int) -> List[Position]:
        # return posisi-posisi objek dalam area tertentu
        return [p for p in positions if self.distance(center, p) <= area]

    def is_object_in_area(self, center: Position, positions: List[Position], area: int) -> bool:
        # mengecek apakah ada objek dalam area tertentu
        return any(self.distance(center, p) <= area for p in positions)

    def same_direction(self, curr_pos: Position, target1: Position, target2: Position) -> bool:
        # mengecek apakah dua target berada dalam arah yang sama dari posisi sekarang
        dx1 = target1.x - curr_pos.x
        dy1 = target1.y - curr_pos.y
        dx2 = target2.x - curr_pos.x
        dy2 = target2.y - curr_pos.y

        ndx1 = (dx1 > 0) - (dx1 < 0)
        ndy1 = (dy1 > 0) - (dy1 < 0)
        ndx2 = (dx2 > 0) - (dx2 < 0)
        ndy2 = (dy2 > 0) - (dy2 < 0)
        return ndx1 == ndx2 and ndy1 == ndy2

    def get_direction_v2(self, current_x: int, current_y: int, dest_x: int, dest_y: int) -> Tuple[int, int]:
        # menentukan langkah arah ke posisi tujuan
        delta_x = clamp(dest_x - current_x, -1, 1)
        delta_y = clamp(dest_y - current_y, -1, 1)
        if delta_x == 0 or delta_y == 0:
            return delta_x, delta_y
        else:
            # kalau x ganjil, horizontal dulu, kalau genap vertikal dulu
            if current_x % 2 == 1:
                return delta_x, 0
            else:
                return 0, delta_y

    def get_distance_with_portal_and_base(self, curr_pos: Position, near_portal: Position, far_portal: Position, target_pos: Position, base_pos: Position) -> int:
        # menghitung jarak total menggunakan teleport lalu ke base
        dist_portal = (self.distance(curr_pos, near_portal) +
                       self.distance(far_portal, target_pos) +
                       min(self.distance(target_pos, base_pos),
                           self.distance(target_pos, far_portal) + self.distance(near_portal, base_pos)))
        return dist_portal

    def dodge_teleport(self, curr_pos: Position, near_tele: Position, far_tele: Position, goal_pos: Position) -> Position:
        # menghindari teleport jika tidak dipakai
        delta_x = goal_pos.x - curr_pos.x
        delta_y = goal_pos.y - curr_pos.y

        if curr_pos.y == goal_pos.y:
            if abs(curr_pos.y + 1 - far_tele.y) == 0 or abs(curr_pos.y - 1 - far_tele.y) == 0:
                return Position(x=curr_pos.x, y=curr_pos.y + 1 if curr_pos.y + 1 == far_tele.y else curr_pos.y - 1)
            return Position(x=curr_pos.x, y=curr_pos.y + 1 if curr_pos.y + 1 < 15 else curr_pos.y - 1)

        elif curr_pos.x == goal_pos.x:
            if abs(curr_pos.x + 1 - far_tele.x) == 0 or abs(curr_pos.x - 1 - far_tele.x) == 0:
                return Position(x=curr_pos.x + 1 if curr_pos.x + 1 == far_tele.x else curr_pos.x - 1, y=curr_pos.y)
            return Position(x=curr_pos.x + 1 if curr_pos.x + 1 < 15 else curr_pos.x - 1, y=curr_pos.y)

        elif curr_pos.y == near_tele.y:
            return Position(x=curr_pos.x, y=curr_pos.y + 1 if delta_y > 0 else curr_pos.y - 1)
        elif curr_pos.x == near_tele.x:
            return Position(x=curr_pos.x + 1 if delta_x > 0 else curr_pos.x - 1, y=curr_pos.y)

        return goal_pos

    def get_nearest_diamond(self, bot_pos: Position, diamond_positions: List[Position]) -> Optional[Position]:
        # mendapatkan diamond terdekat dari posisi bot
        return self.nearest_position(bot_pos, diamond_positions)

    def get_nearest_diamond_base(self, diamonds: List[GameObject], diamond_positions: List[Position], bot_pos: Position, base_pos: Position) -> Optional[Position]:
        # mendapatkan diamond dengan melihat jarak dan nilainya
        min_distance = float('inf')
        nearest_diamond = None
        for diamond in diamond_positions:
            if len(diamond_positions) >= 3:
                other_diamonds = [d for d in diamond_positions if d != diamond]
                nearest_other = self.nearest_position(diamond, other_diamonds)

                nearest_obj = next((d for d in diamonds if d.position == nearest_other), None)
                curr_obj = next((d for d in diamonds if d.position == diamond), None)

                dist = (self.distance(bot_pos, diamond) +
                        self.distance(diamond, base_pos) +
                        self.distance(diamond, nearest_other) -
                        (nearest_obj.properties.points if nearest_obj else 0) -
                        (curr_obj.properties.points if curr_obj else 0))
            else:
                dist = self.distance(bot_pos, diamond) + self.distance(diamond, base_pos)

            if dist < min_distance:
                min_distance = dist
                nearest_diamond = diamond
        return nearest_diamond

    def diamond_process(self, base_pos: Position, diamonds: List[GameObject], diamond_positions: List[Position], bot: GameObject, red_button_pos: Position):
        # proses pemilihan tujuan berdasarkan diamond, base, dan tombol merah
        bot_pos = bot.position
        nearest_diamond_with_base = self.get_nearest_diamond_base(diamonds, diamond_positions, bot_pos, base_pos)

        if (self.distance(bot_pos, nearest_diamond_with_base) > self.distance(bot_pos, red_button_pos) and
            self.distance(bot_pos, nearest_diamond_with_base) > 2):
            self.goal_position = red_button_pos
        elif (self.distance(bot_pos, nearest_diamond_with_base) > self.distance(bot_pos, base_pos) and
              self.same_direction(bot_pos, nearest_diamond_with_base, base_pos) and
              bot.properties.diamonds > 2):
            self.goal_position = base_pos
        else:
            nearest_diamond = self.get_nearest_diamond(bot_pos, diamond_positions)
            if nearest_diamond and self.distance(bot_pos, nearest_diamond) <= 2:
                self.goal_position = nearest_diamond
            else:
                self.goal_position = nearest_diamond_with_base

    def bot_process(self, bot: GameObject, enemies_pos: List[Position], diamond_positions: List[Position], diamonds: List[GameObject], base_pos: Position) -> Optional[Position]:
        # mendapatkan diamond terdekat dengan mempertimbangkan posisi musuh
        curr_pos = bot.position
        dm_candidate = diamond_positions.copy()

        for enemy in enemies_pos:
            delta_x_en, delta_y_en = self.get_direction_v2(curr_pos.x, curr_pos.y, enemy.x, enemy.y)
            while dm_candidate:
                nearest_dm = self.get_nearest_diamond_base(diamonds, dm_candidate, curr_pos, base_pos)
                delta_x_dm, delta_y_dm = self.get_direction_v2(curr_pos.x, curr_pos.y, nearest_dm.x, nearest_dm.y)
                if delta_x_en == delta_x_dm and delta_y_en == delta_y_dm:
                    dm_candidate.remove(nearest_dm)
                else:
                    return nearest_dm

        if dm_candidate:
            return self.get_nearest_diamond_base(diamonds, dm_candidate, curr_pos, base_pos)
        return None

    def next_move(self, board_bot: GameObject, board: Board) -> Tuple[int, int]:
        # method utama untuk menentukan langkah bot
        bot = board_bot
        teleports_pos = []
        red_buttons_pos = []
        enemy_positions = []
        diamond_positions = []
        diamonds = []

        base_pos = bot.properties.base

        for obj in getattr(board, "game_objects", []):
            if obj.type == "DiamondGameObject":
                if bot.properties.diamonds >= 4 and obj.properties.points == 2:
                    continue
                diamonds.append(obj)
                diamond_positions.append(obj.position)
            elif obj.type == "TeleportGameObject":
                teleports_pos.append(obj.position)
            elif obj.type == "BotGameObject":
                if bot.properties.name != obj.properties.name:
                    enemy_positions.append(obj.position)
            elif obj.type == "DiamondButtonGameObject":
                red_buttons_pos.append(obj.position)

        if len(teleports_pos) == 2:
            dist0 = self.distance(bot.position, teleports_pos[0])
            dist1 = self.distance(bot.position, teleports_pos[1])
            if dist0 >= dist1:
                teleports_pos[0], teleports_pos[1] = teleports_pos[1], teleports_pos[0]

        time_left = getattr(bot.properties, "milliseconds_left", 20000)

        #algoritma greedynya

        #kalau waktu hampir habis dan ada diamond di inventori atau inventory penuh
        if (time_left < 10000 and bot.properties.diamonds > 0) or bot.properties.diamonds == 5:
            self.goal_position = base_pos
        #jika ada bot lawan disekitar, car diamond yang jauh dari bot lawan
        elif self.is_object_in_area(bot.position, enemy_positions, 2):
            goal_candidate = self.bot_process(bot, enemy_positions, diamond_positions, diamonds, base_pos)
            self.goal_position = goal_candidate if goal_candidate else self.goal_position
        else:
            if red_buttons_pos:
                red_button_pos = red_buttons_pos[0]
            else:
                red_button_pos = Position(-1, -1)
            #pilih diamond yang menguntungkan berdasar jarak
            self.diamond_process(base_pos, diamonds, diamond_positions, bot, red_button_pos)

        #gunakan teleport kalau  ada untungnya
        if (self.goal_position and len(teleports_pos) == 2 and
            self.get_distance_with_portal_and_base(bot.position, teleports_pos[0], teleports_pos[1], self.goal_position, base_pos) <
            self.distance(bot.position, self.goal_position) + self.distance(self.goal_position, base_pos)):
            self.goal_position = teleports_pos[0]

        #untuk menuju ke goal positionnya
        if self.goal_position and self.goal_position != Position(-1, -1):
            delta_x, delta_y = self.get_direction_v2(bot.position.x, bot.position.y, self.goal_position.x, self.goal_position.y)
            #untuk menghindari teleport kalau bukal goal positionny
            current_plus_portal = Position(bot.position.x + delta_x, bot.position.y + delta_y)
            if (len(teleports_pos) == 2 and
                self.goal_position != teleports_pos[0] and
                current_plus_portal == teleports_pos[0]):
                self.goal_position = self.dodge_teleport(bot.position, teleports_pos[0], teleports_pos[1], self.goal_position)
                delta_x, delta_y = self.get_direction_v2(bot.position.x, bot.position.y, self.goal_position.x, self.goal_position.y)
        else:
            #kalau nggk punya tujuan, jalan random
            delta = self.directions[self.current_direction]
            delta_x, delta_y = delta[0], delta[1]
            if random.random() > 0.6:
                self.current_direction = (self.current_direction + 1) % len(self.directions)

        return delta_x, delta_y