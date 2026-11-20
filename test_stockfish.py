from stockfish import Stockfish
import os

yol = r"C:\Studio Code\bootsrap\görüntüişleme\satranc\stockfish\stockfish-windows-x86-64-universal.exe"

print("Dosya mevcut:", os.path.isfile(yol))

try:
    motor = Stockfish(path=yol, depth=10)

    print("Motor bağlantısı başarılı!")

    motor.set_fen_position(
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    )

    print("Önerilen hamle:", motor.get_best_move())

except Exception as hata:
    print("BAĞLANTI HATASI:")
    print(repr(hata))