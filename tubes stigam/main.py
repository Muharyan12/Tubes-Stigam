# Import library standar dan eksternal
import argparse  # Untuk membaca argumen dari command line
from time import sleep  # Untuk membuat jeda (delay) antar iterasi loop

# Import untuk menampilkan warna di terminal (agar output lebih menarik)
from colorama import Back, Fore, Style, init

# Import modul internal dari folder 'game'
from game.api import Api  # Untuk komunikasi dengan server game (backend API)
from game.board_handler import BoardHandler  # Menangani dan menampilkan papan permainan
from game.bot_handler import BotHandler  # Menangani interaksi bot (mengambil status, kirim langkah)
from game.logic.random import RandomLogic  # Bot logic acak (tidak digunakan langsung di sini)
from game.util import *  # Fungsi utilitas umum
from game.logic.base import BaseLogic  # Kelas dasar logika bot
from game.logic.stigam import Stigam  # Bot dengan strategi khusus bernama Stigam

# Inisialisasi Colorama agar bisa menggunakan warna di terminal
init()

# URL server backend tempat game dijalankan
BASE_URL = "http://localhost:3000/api"

# ID papan default
DEFAULT_BOARD_ID = 1

# Dictionary yang berisi daftar bot logic yang tersedia
# Bisa ditambahkan bot lain di sini jika dikembangkan
CONTROLLERS = {
    "Stigam": Stigam  # Menggunakan logika bot dari class Stigam
}

# ============================================================================
# Bagian ini untuk parsing (membaca) argumen dari terminal/command line
# ============================================================================

parser = argparse.ArgumentParser(description="Diamonds example bot")

# Menentukan dua argumen yang saling eksklusif: menggunakan token ATAU registrasi dengan nama baru
group = parser.add_mutually_exclusive_group()
group.add_argument(
    "--token",  # Token digunakan jika bot sudah pernah terdaftar
    help="Token bot yang sudah terdaftar",
    action="store",
)
group.add_argument(
    "--name",  # Nama digunakan untuk registrasi bot baru
    help="Nama bot baru untuk registrasi",
    action="store"
)

# Argumen tambahan
parser.add_argument("--email", help="Email untuk registrasi bot", action="store")
parser.add_argument("--board", help="ID papan permainan", type=int, default=DEFAULT_BOARD_ID)
parser.add_argument("--controller", help="Nama controller (bot logic) yang digunakan", default="Stigam")

# Eksekusi parsing argumen
args = parser.parse_args()

# ============================================================================
# Inisialisasi koneksi ke API dan login/registrasi bot
# ============================================================================

# Membuat objek API dengan base URL
api = Api(BASE_URL)

# Menentukan token bot
if args.token:
    # Jika token diberikan, gunakan token tersebut
    token = args.token
else:
    # Jika tidak, maka lakukan registrasi bot baru
    bot = api.register_bot(args.name, args.email)
    token = bot["token"]

# ============================================================================
# Menjalankan game (looping)
# ============================================================================

# Ambil class controller (logika bot) dari dictionary CONTROLLERS
controller_class = CONTROLLERS[args.controller]
controller = controller_class()  # Buat objek controller

# Inisialisasi handler papan dan handler bot
board_handler = BoardHandler()
bot_handler = BotHandler(api, token, args.board)

# Tampilkan informasi koneksi bot
print(Fore.GREEN + f"Bot berhasil terhubung ke papan {args.board}" + Style.RESET_ALL)

# Mulai game loop
while True:
    # Ambil status game terbaru dari API
    game = bot_handler.get_game_status()

    # Tampilkan papan ke terminal
    board_handler.display(game)

    # Jika giliran bot untuk bermain
    if bot_handler.should_move(game):
        # Tentukan langkah berdasarkan logic dari controller (AI bot)
        move = controller.move(game)

        # Kirim langkah ke server (API)
        bot_handler.send_move(move)

    # Jeda 1 detik sebelum iterasi berikutnya
    sleep(1)


###############################################################################
#
# Game over!
#
###############################################################################
print(Fore.BLUE + Style.BRIGHT + "Game over!" + Style.RESET_ALL)
