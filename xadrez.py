#!/usr/bin/env python3

import random

PECAS_UNICODE = {
    "K": "♔", "Q": "♕", "R": "♖", "B": "♗", "N": "♘", "P": "♙",
    "k": "♚", "q": "♛", "r": "♜", "b": "♝", "n": "♞", "p": "♟",
}

VALORES = {"p": 100, "n": 320, "b": 330, "r": 500, "q": 900, "k": 0}

DIRECOES_TORRE = [(-1, 0), (1, 0), (0, -1), (0, 1)]
DIRECOES_BISPO = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
SALTOS_CAVALO = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                 (1, -2), (1, 2), (2, -1), (2, 1)]

FEN_INICIAL = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def dentro(r, c):
    return 0 <= r < 8 and 0 <= c < 8


def branca(p):
    return p.isupper()


def nome_casa(r, c):
    return "abcdefgh"[c] + str(8 - r)


def casa_de_nome(s):
    if len(s) != 2 or s[0] not in "abcdefgh" or s[1] not in "12345678":
        return None
    return 8 - int(s[1]), "abcdefgh".index(s[0])


class Posicao:
    """Estado completo de uma posição. Linha 0 = 8ª fileira (pretas)."""

    def __init__(self, fen=FEN_INICIAL):
        partes = fen.split()
        self.tabuleiro = []
        for linha in partes[0].split("/"):
            l = []
            for ch in linha:
                if ch.isdigit():
                    l.extend(["."] * int(ch))
                else:
                    l.append(ch)
            self.tabuleiro.append(l)
        self.vez_branca = partes[1] == "w"
        self.roques = "" if partes[2] == "-" else partes[2]
        self.en_passant = None if partes[3] == "-" else casa_de_nome(partes[3])
        self.meio_lance = int(partes[4]) if len(partes) > 4 else 0
        self._legais = None

    # ---------- utilidades ----------
    def copia(self):
        n = Posicao.__new__(Posicao)
        n.tabuleiro = [l[:] for l in self.tabuleiro]
        n.vez_branca = self.vez_branca
        n.roques = self.roques
        n.en_passant = self.en_passant
        n.meio_lance = self.meio_lance
        n._legais = None
        return n

    def chave(self):
        """Identifica a posição (para repetição tripla)."""
        return ("".join("".join(l) for l in self.tabuleiro),
                self.vez_branca, self.roques, self.en_passant)

    # ---------- ataques ----------
    def atacada(self, r, c, por_brancas):
        t = self.tabuleiro
        # peões
        pr = r + 1 if por_brancas else r - 1
        peao = "P" if por_brancas else "p"
        for dc in (-1, 1):
            if dentro(pr, c + dc) and t[pr][c + dc] == peao:
                return True
        # cavalos
        cav = "N" if por_brancas else "n"
        for dr, dc in SALTOS_CAVALO:
            if dentro(r + dr, c + dc) and t[r + dr][c + dc] == cav:
                return True
        # rei
        rei = "K" if por_brancas else "k"
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if (dr or dc) and dentro(r + dr, c + dc) and t[r + dr][c + dc] == rei:
                    return True
        # peças deslizantes
        for direcoes, alvos in ((DIRECOES_TORRE, "RQ"), (DIRECOES_BISPO, "BQ")):
            for dr, dc in direcoes:
                rr, cc = r + dr, c + dc
                while dentro(rr, cc):
                    p = t[rr][cc]
                    if p != ".":
                        if branca(p) == por_brancas and p.upper() in alvos:
                            return True
                        break
                    rr += dr
                    cc += dc
        return False

    def em_xeque(self, brancas=None):
        if brancas is None:
            brancas = self.vez_branca
        rei = "K" if brancas else "k"
        for r in range(8):
            for c in range(8):
                if self.tabuleiro[r][c] == rei:
                    return self.atacada(r, c, not brancas)
        return False

    # ---------- geração de movimentos ----------
    def pseudo_movimentos(self):
        t = self.tabuleiro
        movs = []
        for r in range(8):
            for c in range(8):
                p = t[r][c]
                if p == "." or branca(p) != self.vez_branca:
                    continue
                tipo = p.upper()
                if tipo == "P":
                    self._peao(r, c, movs)
                elif tipo == "N":
                    for dr, dc in SALTOS_CAVALO:
                        self._tenta(r, c, r + dr, c + dc, movs)
                elif tipo == "K":
                    for dr in (-1, 0, 1):
                        for dc in (-1, 0, 1):
                            if dr or dc:
                                self._tenta(r, c, r + dr, c + dc, movs)
                    self._roques(r, c, movs)
                else:
                    dirs = []
                    if tipo in "RQ":
                        dirs += DIRECOES_TORRE
                    if tipo in "BQ":
                        dirs += DIRECOES_BISPO
                    for dr, dc in dirs:
                        rr, cc = r + dr, c + dc
                        while dentro(rr, cc):
                            alvo = t[rr][cc]
                            if alvo == ".":
                                movs.append((r, c, rr, cc, ""))
                            else:
                                if branca(alvo) != self.vez_branca:
                                    movs.append((r, c, rr, cc, ""))
                                break
                            rr += dr
                            cc += dc
        return movs

    def _tenta(self, r, c, rr, cc, movs):
        if not dentro(rr, cc):
            return
        alvo = self.tabuleiro[rr][cc]
        if alvo == "." or branca(alvo) != self.vez_branca:
            movs.append((r, c, rr, cc, ""))

    def _peao(self, r, c, movs):
        t = self.tabuleiro
        d = -1 if self.vez_branca else 1
        inicio = 6 if self.vez_branca else 1
        ultima = 0 if self.vez_branca else 7

        def adiciona(rr, cc):
            if rr == ultima:
                for promo in "qrbn":
                    movs.append((r, c, rr, cc, promo))
            else:
                movs.append((r, c, rr, cc, ""))

        if dentro(r + d, c) and t[r + d][c] == ".":
            adiciona(r + d, c)
            if r == inicio and t[r + 2 * d][c] == ".":
                movs.append((r, c, r + 2 * d, c, ""))
        for dc in (-1, 1):
            rr, cc = r + d, c + dc
            if not dentro(rr, cc):
                continue
            alvo = t[rr][cc]
            if alvo != "." and branca(alvo) != self.vez_branca:
                adiciona(rr, cc)
            elif (rr, cc) == self.en_passant:
                movs.append((r, c, rr, cc, ""))

    def _roques(self, r, c, movs):
        t = self.tabuleiro
        if self.vez_branca:
            if (r, c) != (7, 4):
                return
            lado_curto, lado_longo, torre, linha = "K", "Q", "R", 7
        else:
            if (r, c) != (0, 4):
                return
            lado_curto, lado_longo, torre, linha = "k", "q", "r", 0
        inimigo = not self.vez_branca
        if self.atacada(linha, 4, inimigo):
            return
        if (lado_curto in self.roques and t[linha][7] == torre
                and t[linha][5] == "." and t[linha][6] == "."
                and not self.atacada(linha, 5, inimigo)
                and not self.atacada(linha, 6, inimigo)):
            movs.append((r, c, linha, 6, ""))
        if (lado_longo in self.roques and t[linha][0] == torre
                and t[linha][1] == "." and t[linha][2] == "." and t[linha][3] == "."
                and not self.atacada(linha, 3, inimigo)
                and not self.atacada(linha, 2, inimigo)):
            movs.append((r, c, linha, 2, ""))

    def movimentos_legais(self):
        if self._legais is None:
            self._legais = [m for m in self.pseudo_movimentos()
                            if not self.aplica(m).em_xeque(self.vez_branca)]
        return self._legais

    # ---------- executar movimento ----------
    def aplica(self, m):
        fr, fc, tr, tc, promo = m
        n = self.copia()
        t = n.tabuleiro
        p = t[fr][fc]
        capturada = t[tr][tc]
        t[fr][fc] = "."
        t[tr][tc] = p

        # en passant
        if p.upper() == "P" and (tr, tc) == self.en_passant:
            t[fr][tc] = "."
            capturada = "p"
        # roque: mover a torre
        if p.upper() == "K" and abs(tc - fc) == 2:
            if tc == 6:
                t[tr][5], t[tr][7] = t[tr][7], "."
            else:
                t[tr][3], t[tr][0] = t[tr][0], "."
        # promoção
        if promo:
            t[tr][tc] = promo.upper() if branca(p) else promo.lower()

        # direitos de roque
        if p == "K":
            n.roques = n.roques.replace("K", "").replace("Q", "")
        elif p == "k":
            n.roques = n.roques.replace("k", "").replace("q", "")
        cantos = {(7, 7): "K", (7, 0): "Q", (0, 7): "k", (0, 0): "q"}
        for casa in ((fr, fc), (tr, tc)):
            if casa in cantos:
                n.roques = n.roques.replace(cantos[casa], "")

        # en passant possível no próximo lance
        n.en_passant = ((fr + tr) // 2, fc) if p.upper() == "P" and abs(tr - fr) == 2 else None
        n.meio_lance = 0 if (p.upper() == "P" or capturada != ".") else self.meio_lance + 1
        n.vez_branca = not self.vez_branca
        return n

    # ---------- fim de jogo ----------
    def material_insuficiente(self):
        pecas = [p.upper() for l in self.tabuleiro for p in l if p not in ".kK"]
        return len(pecas) == 0 or (len(pecas) == 1 and pecas[0] in "NB")

    def resultado(self, historico):
        """Retorna None se o jogo continua, senão uma mensagem."""
        if not self.movimentos_legais():
            if self.em_xeque():
                vencedor = "Pretas" if self.vez_branca else "Brancas"
                return f"XEQUE-MATE! {vencedor} vencem."
            return "Empate por afogamento (stalemate)."
        if self.material_insuficiente():
            return "Empate por material insuficiente."
        if self.meio_lance >= 100:
            return "Empate pela regra dos 50 lances."
        if sum(1 for p in historico if p.chave() == self.chave()) >= 3:
            return "Empate por repetição tripla."
        return None

    # ---------- exibição ----------
    def mostra(self, ultimo=None):
        print()
        print("    a  b  c  d  e  f  g  h")
        for r in range(8):
            linha = f" {8 - r} "
            for c in range(8):
                p = self.tabuleiro[r][c]
                simbolo = PECAS_UNICODE.get(p, "·" if (r + c) % 2 == 0 else " ")
                linha += f" {simbolo} "
            print(linha + f" {8 - r}")
        print("    a  b  c  d  e  f  g  h")
        if ultimo:
            print(f"\n  Último lance: {ultimo}")
        print()


# ---------- computador ----------
def avalia(pos):
    """Pontuação do ponto de vista das brancas (material + centro)."""
    total = 0
    for r in range(8):
        for c in range(8):
            p = pos.tabuleiro[r][c]
            if p == ".":
                continue
            v = VALORES[p.lower()]
            centro = 10 - 3 * (abs(r - 3.5) + abs(c - 3.5)) / 1.0
            if p.lower() in "pnb":
                v += centro
            total += v if branca(p) else -v
    return total


def ordena(pos, movs):
    def pontos(m):
        alvo = pos.tabuleiro[m[2]][m[3]]
        s = VALORES[alvo.lower()] if alvo != "." else 0
        return s + (800 if m[4] == "q" else 0)
    return sorted(movs, key=pontos, reverse=True)


def minimax(pos, prof, alfa, beta):
    movs = pos.movimentos_legais()
    if not movs:
        if pos.em_xeque():
            return (-100000 - prof) if pos.vez_branca else (100000 + prof)
        return 0
    if prof == 0:
        return avalia(pos)
    if pos.vez_branca:
        melhor = -10**9
        for m in ordena(pos, movs):
            melhor = max(melhor, minimax(pos.aplica(m), prof - 1, alfa, beta))
            alfa = max(alfa, melhor)
            if alfa >= beta:
                break
        return melhor
    melhor = 10**9
    for m in ordena(pos, movs):
        melhor = min(melhor, minimax(pos.aplica(m), prof - 1, alfa, beta))
        beta = min(beta, melhor)
        if alfa >= beta:
            break
    return melhor


def melhor_lance(pos, prof):
    movs = pos.movimentos_legais()
    random.shuffle(movs)
    melhor, escolhido = None, None
    for m in ordena(pos, movs):
        v = minimax(pos.aplica(m), prof - 1, -10**9, 10**9)
        if (melhor is None or (pos.vez_branca and v > melhor)
                or (not pos.vez_branca and v < melhor)):
            melhor, escolhido = v, m
    return escolhido


# ---------- entrada/saída ----------
def formata(m):
    return nome_casa(m[0], m[1]) + nome_casa(m[2], m[3]) + m[4]


def interpreta(texto, pos):
    """Converte texto como 'e2e4' ou 'e7e8q' em um lance legal."""
    s = texto.lower().replace(" ", "").replace("-", "")
    if len(s) not in (4, 5):
        return None
    origem, destino = casa_de_nome(s[:2]), casa_de_nome(s[2:4])
    if not origem or not destino:
        return None
    promo = s[4] if len(s) == 5 else ""
    if promo and promo not in "qrbn":
        return None
    candidatos = [m for m in pos.movimentos_legais()
                  if (m[0], m[1]) == origem and (m[2], m[3]) == destino]
    if not candidatos:
        return None
    if candidatos[0][4]:  # é promoção
        return next((m for m in candidatos if m[4] == (promo or "q")), None)
    return candidatos[0] if not promo else None


AJUDA = """
Comandos:
  e2e4        mover peça de e2 para e4 (notação de coordenadas)
  e7e8q       promoção (q=dama, r=torre, b=bispo, n=cavalo; padrão: dama)
  e1g1        roque curto (mova o rei duas casas)
  movimentos  lista todos os lances legais
  desfazer    desfaz o último lance (ou o par de lances contra o computador)
  ajuda       mostra esta mensagem
  sair        encerra o jogo
"""


def pergunta(msg, validas):
    while True:
        r = input(msg).strip().lower()
        if r in validas:
            return r
        print("  Opção inválida.")


def main():
    print("=" * 40)
    print("        JOGO DE XADREZ EM PYTHON")
    print("=" * 40)
    print("1) Humano x Humano")
    print("2) Humano x Computador")
    modo = pergunta("Escolha o modo [1/2]: ", ("1", "2"))

    humano_branco = True
    prof = 2
    if modo == "2":
        cor = pergunta("Você joga de (b)rancas ou (p)retas? [b/p]: ", ("b", "p"))
        humano_branco = cor == "b"
        nivel = pergunta("Dificuldade: 1) fácil  2) médio  3) difícil [1/2/3]: ",
                         ("1", "2", "3"))
        prof = int(nivel)

    pos = Posicao()
    historico = [pos]
    lances = []
    print(AJUDA)

    while True:
        pos.mostra(lances[-1] if lances else None)
        fim = pos.resultado(historico)
        if fim:
            print(f"  >>> {fim}")
            break
        if pos.em_xeque():
            print("  ** XEQUE! **")

        vez = "Brancas" if pos.vez_branca else "Pretas"
        eh_computador = modo == "2" and pos.vez_branca != humano_branco

        if eh_computador:
            print(f"  Computador ({vez}) está pensando...")
            m = melhor_lance(pos, prof)
            lances.append(formata(m))
            pos = pos.aplica(m)
            historico.append(pos)
            continue

        entrada = input(f"  {vez}, seu lance: ").strip().lower()
        if entrada in ("sair", "exit", "quit"):
            print("  Até a próxima!")
            break
        if entrada == "ajuda":
            print(AJUDA)
            continue
        if entrada == "movimentos":
            print("  " + " ".join(sorted(formata(m) for m in pos.movimentos_legais())))
            continue
        if entrada == "desfazer":
            passos = 2 if modo == "2" else 1
            if len(historico) <= passos:
                print("  Nada para desfazer.")
                continue
            for _ in range(passos):
                historico.pop()
                lances.pop()
            pos = historico[-1]
            continue

        m = interpreta(entrada, pos)
        if m is None:
            print("  Lance inválido. Digite 'movimentos' para ver as opções.")
            continue
        lances.append(formata(m))
        pos = pos.aplica(m)
        historico.append(pos)


if __name__ == "__main__":
    main()
