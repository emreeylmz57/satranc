"""
TÜRKÇE MASAÜSTÜ SATRANÇ UYGULAMASI
---------------------------------
Gerekli Python paketleri:
    pip install pygame python-chess stockfish

Ayrıca Stockfish motorunun çalıştırılabilir dosyası gerekir:
    Windows: stockfish.exe
    Linux/macOS: stockfish

Motor yolu:
    1) STOCKFISH_PATH ortam değişkenini tanımlayın veya
    2) stockfish.exe dosyasını bu Python dosyasının yanına koyun veya
    3) PATH üzerinde erişilebilir hale getirin.

Çalıştırma:
    python satranc.py

Not: Satranç kuralları ve hamle doğrulaması python-chess tarafından yapılır.
Stockfish yalnızca ipucu üretmek için kullanılır.
"""

import os
import sys
import shutil
import time
import pygame
import chess
from stockfish import Stockfish


# ---------------------------------------------------------------------
# AYARLAR
# ---------------------------------------------------------------------

GENISLIK = 1000
YUKSEKLIK = 720
TAHTA_BOYUTU = 640
KARE = TAHTA_BOYUTU // 8
TAHTA_X = 30
TAHTA_Y = 40
PANEL_X = 710
FPS = 60

ACIK_KARE = (238, 216, 181)
KOYU_KARE = (181, 136, 99)
SECILI_RENK = (246, 246, 105)
SON_HAMLE_RENK = (205, 210, 106)
YASAL_NOKTA = (45, 45, 45)
KIRMIZI = (235, 45, 45)
PANEL_RENK = (35, 39, 47)
METIN_RENK = (240, 240, 240)
YESIL = (80, 180, 110)
BUTON_RENK = (65, 105, 150)
BUTON_HOVER = (85, 130, 180)
PASIF_RENK = (90, 90, 90)

# Unicode satranç taşları. Dolu semboller (♚♛♜♝♞♟) hem beyaz hem siyah taşların
# dolgun görünmesi için kullanılıp çizim aşamasında renklendirilir.
TAS_GLYPH = {
    chess.WHITE: {
        chess.KING: "♚", chess.QUEEN: "♛", chess.ROOK: "♜",
        chess.BISHOP: "♝", chess.KNIGHT: "♞", chess.PAWN: "♟"
    },
    chess.BLACK: {
        chess.KING: "♚", chess.QUEEN: "♛", chess.ROOK: "♜",
        chess.BISHOP: "♝", chess.KNIGHT: "♞", chess.PAWN: "♟"
    }
}


# ---------------------------------------------------------------------
# STOCKFISH MOTORUNU BULMA VE BAŞLATMA
# ---------------------------------------------------------------------

def stockfish_yolunu_bul():
    klasor = os.path.dirname(os.path.abspath(__file__))

    adaylar = [
        os.environ.get("STOCKFISH_PATH"),
        os.path.join(
            klasor,
            "stockfish",
            "stockfish-windows-x86-64-universal.exe"
        ),
        shutil.which("stockfish"),
        shutil.which("stockfish.exe"),
    ]

    for yol in adaylar:
        if yol and os.path.isfile(yol):
            return os.path.abspath(yol)

    return None


def motoru_baslat():
    yol = stockfish_yolunu_bul()

    if not yol:
        return None, "Stockfish EXE bulunamadı!"

    try:
        motor = Stockfish(path=yol, depth=15)
        motor.update_engine_parameters({
            "Threads": 2,
            "Minimum Thinking Time": 30
        })

        return motor, None

    except Exception as hata:
        return None, f"Stockfish hatası: {hata}"


# ---------------------------------------------------------------------
# ARAYÜZÜN KÜÇÜK YARDIMCI FONKSİYONLARI
# ---------------------------------------------------------------------

def metin_yaz(ekran, yazi, x, y, font, renk=METIN_RENK):
    yuzey = font.render(str(yazi), True, renk)
    ekran.blit(yuzey, (x, y))
    return yuzey.get_rect(topleft=(x, y))


def satir_satir_yaz(ekran, yazi, x, y, font, renk=METIN_RENK, aralik=23):
    """Uzun uyarıları panelde satırlara bölerek gösterir."""
    for i, satir in enumerate(yazi.splitlines()):
        metin_yaz(ekran, satir, x, y + i * aralik, font, renk)


def buton_ciz(ekran, rect, yazi, font, etkin=True, fare=None):
    renk = PASIF_RENK if not etkin else BUTON_RENK
    if etkin and fare and rect.collidepoint(fare):
        renk = BUTON_HOVER
    pygame.draw.rect(ekran, renk, rect, border_radius=8)
    pygame.draw.rect(ekran, (210, 210, 210), rect, 1, border_radius=8)
    etiket = font.render(yazi, True, METIN_RENK)
    ekran.blit(etiket, etiket.get_rect(center=rect.center))


def kare_merkezi(kare, ters=False):
    """python-chess kare numarasını ekran koordinatına çevirir."""
    sutun = 7 - chess.square_file(kare) if ters else chess.square_file(kare)
    satir = chess.square_rank(kare) if ters else 7 - chess.square_rank(kare)
    return (
        TAHTA_X + sutun * KARE + KARE // 2,
        TAHTA_Y + satir * KARE + KARE // 2
    )


def ekran_kare_bul(pos, ters=False):
    """Fare konumundan tahta karesini bulur; tahta dışındaysa None döndürür."""
    x, y = pos
    if not (TAHTA_X <= x < TAHTA_X + TAHTA_BOYUTU):
        return None
    if not (TAHTA_Y <= y < TAHTA_Y + TAHTA_BOYUTU):
        return None
    sutun = (x - TAHTA_X) // KARE
    satir = (y - TAHTA_Y) // KARE
    gercek_sutun = 7 - sutun if ters else sutun
    gercek_satir = satir if ters else 7 - satir
    return chess.square(gercek_sutun, gercek_satir)


# ---------------------------------------------------------------------
# SATRANÇ TAHTASI ÇİZİMİ
# ---------------------------------------------------------------------

def tahta_ciz(ekran, font_tas, font_kucuk, tahta, secili, son_hamle,
              ipucu_hamlesi, sah_uyari_baslangici, ters=False):
    """Tahtayı, taşları, yasal hedefleri, son hamleyi ve şah uyarısını çizer."""
    simdi = time.time()

    for satir in range(8):
        for sutun in range(8):
            x = TAHTA_X + sutun * KARE
            y = TAHTA_Y + satir * KARE
            gercek_sutun = 7 - sutun if ters else sutun
            gercek_satir = satir if ters else 7 - satir
            kare = chess.square(gercek_sutun, gercek_satir)

            renk = ACIK_KARE if (satir + sutun) % 2 == 0 else KOYU_KARE

            # Son hamlenin başlangıç ve bitiş karelerini vurgula.
            if son_hamle and kare in (son_hamle.from_square, son_hamle.to_square):
                renk = SON_HAMLE_RENK

            # Seçili taşı vurgula.
            if secili == kare:
                renk = SECILI_RENK

            # Şah çekilmişse şahın karesini 1,5 saniye kırmızı yanıp söndür.
            if sah_uyari_baslangici is not None and simdi - sah_uyari_baslangici < 1.5:
                if tahta.is_check():
                    sah_kare = tahta.king(tahta.turn)
                    if kare == sah_kare and int((simdi - sah_uyari_baslangici) * 8) % 2 == 0:
                        renk = KIRMIZI

            pygame.draw.rect(ekran, renk, (x, y, KARE, KARE))

            tas = tahta.piece_at(kare)
            if tas:
                sembol = TAS_GLYPH[tas.color][tas.piece_type]
                # Beyaz taşlar (tas.color == True) beyaz, siyah taşlar siyah çizilir.
                tas_rengi = (250, 250, 250) if tas.color == chess.WHITE else (25, 25, 25)
                if tas.color == chess.WHITE:
                    golge = font_tas.render(sembol, True, (40, 40, 40))
                    ekran.blit(golge, golge.get_rect(center=(x + KARE // 2 + 1, y + KARE // 2 + 1)))
                tas_yuzey = font_tas.render(sembol, True, tas_rengi)
                ekran.blit(tas_yuzey, tas_yuzey.get_rect(center=(x + KARE // 2, y + KARE // 2)))

    # Yasal hamle hedeflerini küçük noktalarla göster.
    if secili is not None:
        for hamle in tahta.legal_moves:
            if hamle.from_square == secili:
                cx, cy = kare_merkezi(hamle.to_square, ters)
                hedefte_tas = tahta.piece_at(hamle.to_square)
                if hedefte_tas:
                    pygame.draw.circle(ekran, YASAL_NOKTA, (cx, cy), 25, 4)
                else:
                    pygame.draw.circle(ekran, YASAL_NOKTA, (cx, cy), 8)

    # Stockfish ipucu: önerilen hamlenin başlangıç ve bitiş karesini işaretle.
    if ipucu_hamlesi:
        bas = kare_merkezi(ipucu_hamlesi.from_square, ters)
        bit = kare_merkezi(ipucu_hamlesi.to_square, ters)
        pygame.draw.circle(ekran, (30, 190, 90), bas, 27, 4)
        pygame.draw.circle(ekran, (30, 190, 90), bit, 27, 5)
        pygame.draw.line(ekran, (30, 190, 90), bas, bit, 5)

    # Tahta koordinatları.
    for i in range(8):
        harf_indeks = 7 - i if ters else i
        sayi_deger = i + 1 if ters else 8 - i
        harf = font_kucuk.render(chess.FILE_NAMES[harf_indeks], True, (35, 35, 35))
        ekran.blit(harf, (TAHTA_X + i * KARE + KARE - 15, TAHTA_Y + TAHTA_BOYUTU + 2))
        sayi = font_kucuk.render(str(sayi_deger), True, (35, 35, 35))
        ekran.blit(sayi, (TAHTA_X - 18, TAHTA_Y + i * KARE + 3))


# ---------------------------------------------------------------------
# OYUN DURUMU VE HAMLE İŞLEMLERİ
# ---------------------------------------------------------------------

def oyun_sonucu(tahta):
    """Oyunun resmi bitiş durumunu Türkçe metne dönüştürür."""
    if not tahta.is_game_over(claim_draw=True):
        return None

    if tahta.is_checkmate():
        kazanan = "Beyaz" if tahta.turn == chess.BLACK else "Siyah"
        return f"Oyun Bitti! Kazanan: {kazanan}"

    sonuc = tahta.result(claim_draw=True)
    neden = {
        "1/2-1/2": "Beraberlik",
        "1-0": "Beyaz kazandı",
        "0-1": "Siyah kazandı",
    }.get(sonuc, "Beraberlik")

    if tahta.is_stalemate():
        neden = "Beraberlik: Pat"
    elif tahta.is_insufficient_material():
        neden = "Beraberlik: Yetersiz materyal"
    elif tahta.is_fifty_moves():
        neden = "Beraberlik: 50 hamle kuralı"
    elif tahta.is_repetition(3):
        neden = "Beraberlik: Üç kez tekrar"
    return f"Oyun Bitti! {neden}"


def terfi_secimi(ekran, font, saat):
    """Terfi eden piyon için kullanıcıdan taş seçmesini ister."""
    secenekler = [
        (chess.QUEEN, "Vezir"),
        (chess.ROOK, "Kale"),
        (chess.BISHOP, "Fil"),
        (chess.KNIGHT, "At"),
    ]
    rects = []
    panel = pygame.Rect(250, 280, 500, 160)
    pygame.draw.rect(ekran, (30, 34, 42), panel, border_radius=12)
    pygame.draw.rect(ekran, (230, 230, 230), panel, 2, border_radius=12)
    baslik = font.render("Piyon terfisi: Taş seçin", True, METIN_RENK)
    ekran.blit(baslik, baslik.get_rect(center=(500, 310)))

    for i, (tas_turu, ad) in enumerate(secenekler):
        rect = pygame.Rect(275 + i * 115, 345, 100, 55)
        pygame.draw.rect(ekran, BUTON_RENK, rect, border_radius=7)
        yazi = font.render(ad, True, METIN_RENK)
        ekran.blit(yazi, yazi.get_rect(center=rect.center))
        rects.append((rect, tas_turu))

    pygame.display.flip()
    while True:
        for olay in pygame.event.get():
            if olay.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if olay.type == pygame.MOUSEBUTTONDOWN and olay.button == 1:
                for rect, tas_turu in rects:
                    if rect.collidepoint(olay.pos):
                        return tas_turu
        saat.tick(FPS)


# ---------------------------------------------------------------------
# ANA UYGULAMA
# ---------------------------------------------------------------------

def main():
    pygame.init()
    pygame.display.set_caption("Python Satranç - Stockfish İpuçlu")
    ekran = pygame.display.set_mode((GENISLIK, YUKSEKLIK))
    saat = pygame.time.Clock()

    # Taş fontu Unicode satranç karakterlerini destekleyen sistem fontundan seçilir.
    font_tas = pygame.font.SysFont("segoeuisymbol", 58)
    if not font_tas:
        font_tas = pygame.font.SysFont("dejavusans", 58)
    font = pygame.font.SysFont("arial", 22)
    font_kucuk = pygame.font.SysFont("arial", 16)
    font_buyuk = pygame.font.SysFont("arial", 28, bold=True)

    tahta = chess.Board()
    motor, motor_hatasi = motoru_baslat()

    # Her renk için ayrı ipucu hakkı.
    ipucu_haklari = {chess.WHITE: 150, chess.BLACK: 150}

    secili = None
    son_hamle = None
    ipucu_hamlesi = None
    ipucu_mesaji = "İpucu almak için butona basın."
    sah_uyari_baslangici = None
    bitis_mesaji = None
    tahta_ters = False

    ipucu_buton = pygame.Rect(PANEL_X, 275, 250, 48)
    dondur_buton = pygame.Rect(PANEL_X, 475, 250, 46)
    geri_al_buton = pygame.Rect(PANEL_X, 535, 250, 46)
    yeniden_buton = pygame.Rect(PANEL_X, 595, 250, 46)

    calisiyor = True
    while calisiyor:
        saat.tick(FPS)
        fare = pygame.mouse.get_pos()

        for olay in pygame.event.get():
            if olay.type == pygame.QUIT:
                calisiyor = False

            elif olay.type == pygame.MOUSEBUTTONDOWN and olay.button == 1:
                # Tahtayı Döndür butonu (her zaman aktif).
                if dondur_buton.collidepoint(olay.pos):
                    tahta_ters = not tahta_ters
                    continue

                # Hamleyi Geri Al butonu (oyun bittiyse de son hamleyi geri almaya izin verir).
                if geri_al_buton.collidepoint(olay.pos) and len(tahta.move_stack) > 0:
                    tahta.pop()
                    son_hamle = tahta.peek() if len(tahta.move_stack) > 0 else None
                    secili = None
                    ipucu_hamlesi = None
                    bitis_mesaji = None
                    ipucu_mesaji = "Son hamle geri alındı."
                    sah_uyari_baslangici = time.time() if tahta.is_check() else None
                    continue

                # Oyun bittiyse yalnızca yeniden başlatma seçeneği aktiftir.
                if bitis_mesaji:
                    if yeniden_buton.collidepoint(olay.pos):
                        tahta = chess.Board()
                        ipucu_haklari = {chess.WHITE: 150, chess.BLACK: 150}
                        secili = None
                        son_hamle = None
                        ipucu_hamlesi = None
                        ipucu_mesaji = "İpucu almak için butona basın."
                        sah_uyari_baslangici = None
                        bitis_mesaji = None
                    continue

                # İpucu butonu.
                if ipucu_buton.collidepoint(olay.pos):
                    renk = tahta.turn
                    if ipucu_haklari[renk] <= 0:
                        ipucu_mesaji = "Bu oyuncunun ipucu hakkı kalmadı."
                    elif motor is None:
                        ipucu_mesaji = "Stockfish kullanılamıyor. Motor yolunu kontrol edin."
                    else:
                        try:
                            # İstenen konum FEN olarak Stockfish motoruna gönderilir.
                            motor.set_fen_position(tahta.fen())
                            en_iyi = motor.get_best_move()
                            if en_iyi:
                                hamle = chess.Move.from_uci(en_iyi)
                                if hamle in tahta.legal_moves:
                                    ipucu_haklari[renk] -= 1
                                    ipucu_hamlesi = hamle
                                    ipucu_mesaji = (
                                        f"Öneri: {tahta.san(hamle)} ({en_iyi})"
                                    )
                                else:
                                    ipucu_mesaji = "Motor geçerli bir hamle döndürmedi."
                            else:
                                ipucu_mesaji = "Motor bu konum için hamle önermedi."
                        except Exception as hata:
                            ipucu_mesaji = f"Motor hatası: {hata}"
                    continue

                # Tahta üzerinde tıklama.
                kare = ekran_kare_bul(olay.pos, tahta_ters)
                if kare is None:
                    continue

                if secili is None:
                    tas = tahta.piece_at(kare)
                    if tas and tas.color == tahta.turn:
                        secili = kare
                        ipucu_hamlesi = None
                else:
                    # Aynı renkte başka taşa tıklanırsa seçim değişir.
                    tiklanan_tas = tahta.piece_at(kare)
                    if tiklanan_tas and tiklanan_tas.color == tahta.turn:
                        secili = kare
                    else:
                        adaylar = [
                            h for h in tahta.legal_moves
                            if h.from_square == secili and h.to_square == kare
                        ]
                        if adaylar:
                            hamle = adaylar[0]

                            # Son sıraya ulaşan piyon için otomatik vezir yerine seçim sun.
                            if tahta.piece_at(secili).piece_type == chess.PAWN:
                                hedef_sira = chess.square_rank(kare)
                                if hedef_sira in (0, 7):
                                    terfi = terfi_secimi(ekran, font, saat)
                                    hamle = chess.Move(
                                        secili, kare, promotion=terfi
                                    )

                            if hamle in tahta.legal_moves:
                                tahta.push(hamle)
                                son_hamle = hamle
                                secili = None
                                ipucu_hamlesi = None
                                if tahta.is_check():
                                    sah_uyari_baslangici = time.time()
                                else:
                                    sah_uyari_baslangici = None
                                bitis_mesaji = oyun_sonucu(tahta)
                            else:
                                secili = None
                        else:
                            secili = None

        # -------------------------------------------------------------
        # EKRANI ÇİZ
        # -------------------------------------------------------------
        ekran.fill((225, 225, 225))
        tahta_ciz(
            ekran, font_tas, font_kucuk, tahta, secili,
            son_hamle, ipucu_hamlesi, sah_uyari_baslangici, tahta_ters
        )

        # Sağ bilgi paneli.
        panel = pygame.Rect(690, 20, 290, 670)
        pygame.draw.rect(ekran, PANEL_RENK, panel, border_radius=12)

        metin_yaz(ekran, "SAT RANÇ", PANEL_X, 42, font_buyuk)
        metin_yaz(ekran, "Sıra:", PANEL_X, 100, font)
        sira = "Beyaz" if tahta.turn == chess.WHITE else "Siyah"
        metin_yaz(ekran, sira, PANEL_X + 85, 100, font, YESIL)

        metin_yaz(ekran, "Beyaz ipucu: " + str(ipucu_haklari[chess.WHITE]),
                  PANEL_X, 150, font)
        metin_yaz(ekran, "Siyah ipucu: " + str(ipucu_haklari[chess.BLACK]),
                  PANEL_X, 185, font)

        buton_etkin = (
            bitis_mesaji is None
            and ipucu_haklari[tahta.turn] > 0
            and motor is not None
        )
        buton_ciz(ekran, ipucu_buton, "İpucu Al", font, buton_etkin, fare)

        satir_satir_yaz(ekran, ipucu_mesaji, PANEL_X, 335, font_kucuk,
                        (170, 225, 180), 21)

        if motor_hatasi:
            satir_satir_yaz(ekran, motor_hatasi, PANEL_X, 390,
                            font_kucuk, (255, 170, 150), 19)
        elif motor:
            metin_yaz(ekran, "Stockfish hazır", PANEL_X, 405, font_kucuk, YESIL)

        # Konum ve oyun durumu.
        metin_yaz(ekran, "Hamle sayısı: " + str(tahta.fullmove_number),
                  PANEL_X, 435, font_kucuk)

        # Tahtayı Döndür butonu.
        buton_ciz(ekran, dondur_buton, "Tahtayı Döndür", font, True, fare)

        # Hamleyi Geri Al butonu (tahtada en az 1 hamle varsa aktif).
        buton_ciz(ekran, geri_al_buton, "Hamleyi Geri Al", font,
                  len(tahta.move_stack) > 0, fare)

        if bitis_mesaji:
            pygame.draw.rect(ekran, (20, 25, 32), (TAHTA_X + 35, 280, 570, 130),
                             border_radius=12)
            pygame.draw.rect(ekran, (245, 220, 120),
                             (TAHTA_X + 35, 280, 570, 130), 3,
                             border_radius=12)
            yazi = font_buyuk.render(bitis_mesaji, True, (255, 240, 180))
            ekran.blit(yazi, yazi.get_rect(center=(TAHTA_X + 320, 330)))
            buton_ciz(ekran, yeniden_buton, "Yeniden Başlat", font, True, fare)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()