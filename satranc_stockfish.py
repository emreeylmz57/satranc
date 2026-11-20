import pygame
import chess
import time
from stockfish import Stockfish

# --- AYARLAR VE SABİTLER ---
TAHTA_BOYUTU = 640
PANEL_GENISLIGI = 260
GENISLIK = TAHTA_BOYUTU + PANEL_GENISLIGI
YUKSEKLIK = TAHTA_BOYUTU
KARE_BOYUTU = TAHTA_BOYUTU // 8

# Renkler (RGB)
ACIK_KARE = (238, 238, 210)
KOYU_KARE = (118, 150, 86)
SECILI_RENK = (186, 202, 68)
SON_HAMLE_RENK = (246, 246, 105)
SAH_UYARI_RENK = (235, 64, 52)     # Şah çekildiğinde geçici kızarma rengi
IPUCU_BASLANGIC = (52, 152, 219)   # Stockfish ipucu başlangıç karesi
IPUCU_BITIS = (46, 204, 113)       # Stockfish ipucu hedef karesi
PANEL_ARKA_PLAN = (40, 44, 52)
BUTON_RENK = (70, 130, 180)
BUTON_PASIF = (100, 100, 100)
BEYAZ = (255, 255, 255)
SIYAH = (20, 20, 20)

# Stockfish yürütülebilir dosya yolu (Kendi bilgisayarındaki yola göre güncelle!)
STOCKFISH_YOLU = "stockfish.exe"  # Örn: r"C:\stockfish\stockfish-windows-x86-64-avx2.exe"

# Unicode Satranç Taşları
TAS_SEMBOLLERI = {
    'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
    'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚'
}

class SatrancUygulamasi:
    def __init__(self):
        pygame.init()
        self.ekran = pygame.display.set_mode((GENISLIK, YUKSEKLIK))
        pygame.display.set_caption("Stockfish Destekli Satranç")
        self.saat = pygame.time.Clock()

        # Yazı tipleri (Sistemdeki Unicode destekli fontu kullanır)
        self.tas_font = pygame.font.SysFont("segoeuisymbol", 56)
        self.baslik_font = pygame.font.SysFont("arial", 22, bold=True)
        self.metin_font = pygame.font.SysFont("arial", 18)
        self.sonuc_font = pygame.font.SysFont("arial", 28, bold=True)

        # Stockfish Motorunu Başlat
        try:
            self.stockfish = Stockfish(path=STOCKFISH_YOLU, depth=15)
        except Exception as e:
            print(f"HATA: Stockfish başlatılamadı. Dosya yolunu kontrol edin: {e}")
            self.stockfish = None

        self.oyunu_sifirla()

    def oyunu_sifirla(self):
        self.tahta = chess.Board()
        self.secili_kare = None
        self.yasal_hedefler = []
        self.ipucu_haklari = {chess.WHITE: 5, chess.BLACK: 5}
        self.aktif_ipucu = None  # (baslangic_karesi, bitis_karesi)
        self.sah_uyari_zamani = 0
        self.sah_cekilen_kare = None
        self.oyun_bitti = False
        self.sonuc_mesaji = ""

    def koordinattan_kareye(self, x, y):
        if x >= TAHTA_BOYUTU or y >= YUKSEKLIK:
            return None
        sutun = x // KARE_BOYUTU
        satir = 7 - (y // KARE_BOYUTU)
        return chess.square(sutun, satir)

    def kareden_koordinata(self, kare):
        sutun = chess.square_file(kare)
        satir = 7 - chess.square_rank(kare)
        return sutun * KARE_BOYUTU, satir * KARE_BOYUTU

    def ipucu_al(self):
        if self.oyun_bitti or not self.stockfish:
            return
        sira = self.tahta.turn
        if self.ipucu_haklari[sira] <= 0:
            return

        # Mevcut konumu Stockfish'e gönder ve en iyi hamleyi al
        self.stockfish.set_fen_position(self.tahta.fen())
        en_iyi_hamle_uci = self.stockfish.get_best_move()

        if en_iyi_hamle_uci:
            hamle = chess.Move.from_uci(en_iyi_hamle_uci)
            self.aktif_ipucu = (hamle.from_square, hamle.to_square)
            self.ipucu_haklari[sira] -= 1

    def hamle_yap(self, kaynak, hedef):
        # Piyon terfisi kontrolü (Otomatik Vezir'e terfi eder)
        tas = self.tahta.piece_at(kaynak)
        terfi = None
        if tas and tas.piece_type == chess.PAWN:
            if (tas.color == chess.WHITE and chess.square_rank(hedef) == 7) or \
               (tas.color == chess.BLACK and chess.square_rank(hedef) == 0):
                terfi = chess.QUEEN

        hamle = chess.Move(kaynak, hedef, promotion=terfi)

        if hamle in self.tahta.legal_moves:
            self.tahta.push(hamle)
            self.aktif_ipucu = None  # Hamle yapılınca ipucu vurgusunu temizle

            # Şah çekildi mi kontrol et (Geçici kızartma tetiklemesi)
            if self.tahta.is_check():
                self.sah_cekilen_kare = self.tahta.king(self.tahta.turn)
                self.sah_uyari_zamani = time.time()

            # Oyun sonu (Mat / Beraberlik) kontrolü
            if self.tahta.is_game_over():
                self.oyun_bitti = True
                if self.tahta.is_checkmate():
                    kazanan = "BEYAZ" if self.tahta.turn == chess.BLACK else "SIYAH"
                    self.sonuc_mesaji = f"Oyun Bitti! Kazanan: {kazanan}"
                else:
                    self.sonuc_mesaji = "Oyun Bitti! Berabere"

    def tahtayi_ciz(self):
        # 1. Kareleri Çiz
        for satir in range(8):
            for sutun in range(8):
                kare = chess.square(sutun, 7 - satir)
                x, y = sutun * KARE_BOYUTU, satir * KARE_BOYUTU
                renk = ACIK_KARE if (satir + sutun) % 2 == 0 else KOYU_KARE

                # Son hamle vurgusu
                if self.tahta.move_stack:
                    son_hamle = self.tahta.peek()
                    if kare in (son_hamle.from_square, son_hamle.to_square):
                        renk = SON_HAMLE_RENK

                # Seçili kare vurgusu
                if kare == self.secili_kare:
                    renk = SECILI_RENK

                # Stockfish İpucu vurgusu
                if self.aktif_ipucu:
                    if kare == self.aktif_ipucu[0]:
                        renk = IPUCU_BASLANGIC
                    elif kare == self.aktif_ipucu[1]:
                        renk = IPUCU_BITIS

                # Geçici Şah Çekme Kızartması (1.5 saniye sürer)
                if self.sah_cekilen_kare == kare and (time.time() - self.sah_uyari_zamani < 1.5):
                    renk = SAH_UYARI_RENK

                pygame.draw.rect(self.ekran, renk, (x, y, KARE_BOYUTU, KARE_BOYUTU))

                # Yasal hamle noktaları
                if kare in self.yasal_hedefler:
                    merkez = (x + KARE_BOYUTU // 2, y + KARE_BOYUTU // 2)
                    pygame.draw.circle(self.ekran, (80, 80, 80), merkez, 10)

                # Taşları Çiz
                tas = self.tahta.piece_at(kare)
                if tas:
                    sembol = TAS_SEMBOLLERI[tas.symbol()]
                    yazi_rengi = BEYAZ if tas.color == chess.WHITE else SIYAH
                    # Beyaz taşların okunabilirliği için koyu dış kontur efekti
                    if tas.color == chess.WHITE:
                        golge = self.tas_font.render(sembol, True, SIYAH)
                        golge_rect = golge.get_rect(center=(x + KARE_BOYUTU // 2 + 2, y + KARE_BOYUTU // 2 + 2))
                        self.ekran.blit(golge, golge_rect)

                    metin = self.tas_font.render(sembol, True, yazi_rengi)
                    rect = metin.get_rect(center=(x + KARE_BOYUTU // 2, y + KARE_BOYUTU // 2))
                    self.ekran.blit(metin, rect)

    def paneli_ciz(self):
        pygame.draw.rect(self.ekran, PANEL_ARKA_PLAN, (TAHTA_BOYUTU, 0, PANEL_GENISLIGI, YUKSEKLIK))

        # Sıra Bilgisi
        sira_metni = "Sıra: BEYAZ" if self.tahta.turn == chess.WHITE else "Sıra: SİYAH"
        sira_yuzey = self.baslik_font.render(sira_metni, True, BEYAZ)
        self.ekran.blit(sira_yuzey, (TAHTA_BOYUTU + 25, 30))

        # İpucu Hakları
        beyaz_hak = self.metin_font.render(f"Beyaz İpucu Hakkı: {self.ipucu_haklari[chess.WHITE]}/5", True, BEYAZ)
        siyah_hak = self.metin_font.render(f"Siyah İpucu Hakkı: {self.ipucu_haklari[chess.BLACK]}/5", True, BEYAZ)
        self.ekran.blit(beyaz_hak, (TAHTA_BOYUTU + 25, 80))
        self.ekran.blit(siyah_hak, (TAHTA_BOYUTU + 25, 110))

        # İpucu Al Butonu
        aktif_hak = self.ipucu_haklari[self.tahta.turn]
        buton_aktif = aktif_hak > 0 and not self.oyun_bitti and self.stockfish is not None
        self.ipucu_buton_rect = pygame.Rect(TAHTA_BOYUTU + 25, 160, 210, 45)
        pygame.draw.rect(self.ekran, BUTON_RENK if buton_aktif else BUTON_PASIF, self.ipucu_buton_rect, border_radius=8)

        buton_yazi = self.baslik_font.render("İpucu Al (Stockfish)", True, BEYAZ)
        self.ekran.blit(buton_yazi, buton_yazi.get_rect(center=self.ipucu_buton_rect.center))

        # İpucu Açıklaması
        if self.aktif_ipucu:
            kaynak_ad = chess.square_name(self.aktif_ipucu[0]).upper()
            hedef_ad = chess.square_name(self.aktif_ipucu[1]).upper()
            ipucu_bilgi = self.metin_font.render(f"Öneri: {kaynak_ad} -> {hedef_ad}", True, IPUCU_BITIS)
            self.ekran.blit(ipucu_bilgi, (TAHTA_BOYUTU + 25, 225))

        # Yeniden Başlat Butonu
        self.reset_buton_rect = pygame.Rect(TAHTA_BOYUTU + 25, YUKSEKLIK - 75, 210, 45)
        pygame.draw.rect(self.ekran, (192, 57, 43), self.reset_buton_rect, border_radius=8)
        reset_yazi = self.baslik_font.render("Yeni Oyun", True, BEYAZ)
        self.ekran.blit(reset_yazi, reset_yazi.get_rect(center=self.reset_buton_rect.center))

    def oyun_sonu_ekrani_ciz(self):
        if not self.oyun_bitti:
            return
        # Tahta üzerine yarı saydam sonuç kutusu
        overlay = pygame.Surface((TAHTA_BOYUTU, 140))
        overlay.set_alpha(220)
        overlay.fill((20, 20, 20))
        self.ekran.blit(overlay, (0, TAHTA_BOYUTU // 2 - 70))

        sonuc_yuzey = self.sonuc_font.render(self.sonuc_mesaji, True, (255, 215, 0))
        self.ekran.blit(sonuc_yuzey, sonuc_yuzey.get_rect(center=(TAHTA_BOYUTU // 2, TAHTA_BOYUTU // 2)))

    def calistir(self):
        calisiyor = True
        while calisiyor:
            for etkinlik in pygame.event.get():
                if etkinlik.type == pygame.QUIT:
                    calisiyor = False

                elif etkinlik.type == pygame.MOUSEBUTTONDOWN and etkinlik.button == 1:
                    mx, my = etkinlik.pos

                    # Yeniden başlat butonu
                    if self.reset_buton_rect.collidepoint(mx, my):
                        self.oyunu_sifirla()
                        continue

                    # İpucu butonu
                    if self.ipucu_buton_rect.collidepoint(mx, my):
                        self.ipucu_al()
                        continue

                    # Tahta tıklaması
                    if not self.oyun_bitti and mx < TAHTA_BOYUTU:
                        tiklanan_kare = self.koordinattan_kareye(mx, my)
                        if tiklanan_kare is not None:
                            # Eğer zaten bir taş seçiliyse ve yasal hedefe tıklandıysa hamleyi yap
                            if self.secili_kare is not None and tiklanan_kare in self.yasal_hedefler:
                                self.hamle_yap(self.secili_kare, tiklanan_kare)
                                self.secili_kare = None
                                self.yasal_hedefler = []
                            else:
                                # Kendi taşını seçme
                                tas = self.tahta.piece_at(tiklanan_kare)
                                if tas and tas.color == self.tahta.turn:
                                    self.secili_kare = tiklanan_kare
                                    self.yasal_hedefler = [
                                        m.to_square for m in self.tahta.legal_moves if m.from_square == tiklanan_kare
                                    ]
                                else:
                                    self.secili_kare = None
                                    self.yasal_hedefler = []

            self.tahtayi_ciz()
            self.paneli_ciz()
            self.oyun_sonu_ekrani_ciz()
            pygame.display.flip()
            self.saat.tick(30)

        pygame.quit()

if __name__ == "__main__":
    uygulama = SatrancUygulamasi()
    uygulama.calistir()