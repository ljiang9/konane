#!/usr/bin/env python3
"""Konane（夏威夷跳棋）极简版。

规则（简化自传统 Konane）：
- 8x8 棋盘，黑白棋子交错摆放（黑 32 / 白 32）。
- 开局：黑方先从中央 4 格中取走一枚黑子；白方取走与空格正交相邻的一枚白子。
- 行棋：正交方向（上下左右，不可斜向）跳过一枚相邻的对方棋子，
  落到其后紧邻的空格，被跳过的棋子移除。一回合内可连跳（可转向），
  也可提前停下。
- 无棋可跳的一方判负。

纯标准库，Python 3.10+。
"""

import argparse
import random
import sys

EMPTY, BLACK, WHITE = 0, 1, 2
DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
NAMES = {BLACK: "黑方", WHITE: "白方"}
GLYPH = {EMPTY: "·", BLACK: "●", WHITE: "○"}


def opp(player):
    return WHITE if player == BLACK else BLACK


class Konane:
    def __init__(self):
        # (r+c) 为偶数 -> 黑子
        self.board = [
            [BLACK if (r + c) % 2 == 0 else WHITE for c in range(8)]
            for r in range(8)
        ]
        self.phase = "open_black"  # open_black -> open_white -> play
        self.turn = BLACK

    # ---------- 开局 ----------

    CENTER_BLACK = [(3, 3), (4, 4)]

    def legal_opening_removals(self, player):
        """开局取子合法位置。"""
        if player == BLACK and self.phase == "open_black":
            return [p for p in self.CENTER_BLACK if self.board[p[0]][p[1]] == BLACK]
        if player == WHITE and self.phase == "open_white":
            empt = self.empty_square()
            out = []
            for dr, dc in DIRS:
                r, c = empt[0] + dr, empt[1] + dc
                if 0 <= r < 8 and 0 <= c < 8 and self.board[r][c] == WHITE:
                    out.append((r, c))
            return out
        return []

    def empty_square(self):
        for r in range(8):
            for c in range(8):
                if self.board[r][c] == EMPTY:
                    return (r, c)
        return None

    def opening_remove(self, player, pos):
        if pos not in self.legal_opening_removals(player):
            raise ValueError(f"非法开局取子: {pos}")
        self.board[pos[0]][pos[1]] = EMPTY
        if self.phase == "open_black":
            self.phase = "open_white"
            self.turn = WHITE
        else:
            self.phase = "play"
            self.turn = BLACK

    # ---------- 跳吃 ----------

    def _jumps_from(self, board, r, c, player, path, out):
        op = opp(player)
        for dr, dc in DIRS:
            r1, c1, r2, c2 = r + dr, c + dc, r + 2 * dr, c + 2 * dc
            if (
                0 <= r2 < 8
                and 0 <= c2 < 8
                and board[r1][c1] == op
                and board[r2][c2] == EMPTY
            ):
                board[r][c] = EMPTY
                board[r1][c1] = EMPTY
                board[r2][c2] = player
                new_path = path + [(r2, c2)]
                out.append(new_path)
                self._jumps_from(board, r2, c2, player, new_path, out)
                board[r][c] = player
                board[r1][c1] = op
                board[r2][c2] = EMPTY

    def legal_moves(self, player):
        """全部合法走法：每条为位置路径 [(r0,c0), (r1,c1), ...]，含可提前停下的前缀。"""
        if self.phase != "play":
            return []
        moves = []
        for r in range(8):
            for c in range(8):
                if self.board[r][c] == player:
                    self._jumps_from(self.board, r, c, player, [(r, c)], moves)
        return moves

    def apply_move(self, player, path):
        if self.phase != "play":
            raise ValueError("开局尚未完成")
        if player != self.turn:
            raise ValueError("未轮到该方行棋")
        if path not in self.legal_moves(player):
            raise ValueError(f"非法走法: {path}")
        r0, c0 = path[0]
        self.board[r0][c0] = EMPTY
        for (ra, ca), (rb, cb) in zip(path, path[1:]):
            self.board[(ra + rb) // 2][(ca + cb) // 2] = EMPTY
        re_, ce = path[-1]
        self.board[re_][ce] = player
        self.turn = opp(player)

    def loser(self):
        """无棋可走的一方判负，返回输家；对局未结束返回 None。"""
        if self.phase != "play":
            return None
        if not self.legal_moves(self.turn):
            return self.turn
        return None

    def count(self):
        b = sum(row.count(BLACK) for row in self.board)
        w = sum(row.count(WHITE) for row in self.board)
        return b, w


# ---------- AI ----------

def ai_opening(g, rng):
    player = g.turn
    choices = g.legal_opening_removals(player)
    g.opening_remove(player, rng.choice(choices))


def ai_move(g, rng):
    """贪心：吃子最多者胜出，平局随机。"""
    moves = g.legal_moves(g.turn)
    if not moves:
        return None
    best = max(len(p) - 1 for p in moves)
    cands = [p for p in moves if len(p) - 1 == best]
    path = rng.choice(cands)
    g.apply_move(g.turn, path)
    return path


# ---------- 文本界面 ----------

def coord(pos):
    r, c = pos
    return f"{'abcdefgh'[c]}{r + 1}"


def fmt_path(path):
    return "-".join(coord(p) for p in path)


def render(g):
    lines = ["  a b c d e f g h"]
    for r in range(8):
        lines.append(f"{r + 1} " + " ".join(GLYPH[g.board[r][c]] for c in range(8)))
    b, w = g.count()
    lines.append(f"黑 ●{b}  白 ○{w}  轮到{NAMES[g.turn]}")
    return "\n".join(lines)


def play_auto(games, seed):
    rng = random.Random(seed)
    black_wins = white_wins = 0
    for i in range(games):
        g = Konane()
        ai_opening(g, rng)
        ai_opening(g, rng)
        while g.loser() is None:
            ai_move(g, rng)
        if g.loser() == WHITE:
            black_wins += 1
        else:
            white_wins += 1
    print(f"共 {games} 局：黑方胜 {black_wins}，白方胜 {white_wins}")
    return black_wins, white_wins


def play_interactive(seed):
    if not sys.stdin.isatty():
        print("交互模式需要终端；无头演示请用 --auto", file=sys.stderr)
        return 2
    rng = random.Random(seed)
    g = Konane()
    print("你是黑方（先手）。开局由 AI 代下。")
    ai_opening(g, rng)
    ai_opening(g, rng)
    human = BLACK
    while True:
        print()
        print(render(g))
        loser = g.loser()
        if loser is not None:
            print(f"{NAMES[loser]}无棋可走，{NAMES[opp(loser)]}获胜！")
            return 0
        if g.turn == human:
            moves = g.legal_moves(human)
            for i, m in enumerate(moves):
                print(f"  {i}: {fmt_path(m)}（吃 {len(m) - 1} 子）")
            raw = input("走法编号（q 退出）> ").strip()
            if raw.lower() == "q":
                return 0
            try:
                g.apply_move(human, moves[int(raw)])
            except (ValueError, IndexError):
                print("非法输入，请重输。")
        else:
            path = ai_move(g, rng)
            print(f"AI（白方）走：{fmt_path(path)}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Konane（夏威夷跳棋）极简版")
    ap.add_argument("--auto", action="store_true", help="AI 对 AI 自动演示")
    ap.add_argument("--games", type=int, default=10, help="自动演示局数")
    ap.add_argument("--seed", type=int, default=42, help="随机种子")
    args = ap.parse_args(argv)
    if args.auto:
        play_auto(args.games, args.seed)
        return 0
    return play_interactive(args.seed)


if __name__ == "__main__":
    sys.exit(main())
