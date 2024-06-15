"""
This is the logic of the game.
It is a library, it is not expected to be executed directly.
"""
from enum import IntEnum
import random

class CellValue(IntEnum):
    EMPTY = 0
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8

    # Some code below assumes that those values are greater than 8
    MINE = 9
    HIDDEN = 10
    FLAG = 11
    EXPLOSION = 12

CELL_STR = {
    CellValue.EMPTY: ' ',
    CellValue.ONE: '1',
    CellValue.TWO: '2',
    CellValue.THREE: '3',
    CellValue.FOUR: '4',
    CellValue.FIVE: '5',
    CellValue.SIX: '6',
    CellValue.SEVEN: '7',
    CellValue.EIGHT: '8',
    CellValue.MINE: '*',
    CellValue.HIDDEN: '☐',
    CellValue.FLAG: '⚐',
    CellValue.EXPLOSION: 'X',
}

class MinesweeperEngine:
    def __init__(self, width: int, height:int, num_mines: int):
        assert 0 < width
        assert 0 < height
        assert 0 < num_mines < width * height
        self.width = width
        self.height = height
        self.num_mines = num_mines
        self.is_game_over = False
        self.field, self.view_mask = self.GenerateField()

    def GenerateField(self) -> tuple[list[list[CellValue]], list[list[CellValue]]]:
        field = []
        view_mask = []
        for _ in range(self.height):
            field.append([CellValue.EMPTY] * self.width)
            view_mask.append([CellValue.HIDDEN] * self.width)

        mine_positions = random.sample(
            range(self.height * self.width),
            k = self.num_mines)
        for pos in mine_positions:
            y = (pos // self.width)
            x = (pos % self.width)
            assert field[y][x] <= CellValue.EIGHT
            field[y][x] = CellValue.MINE

            for i in range(max(y-1, 0), min(y+2, self.height)):
                for j in range(max(x-1, 0), min(x+2, self.width)):
                    if field[i][j] < CellValue.EIGHT:
                        field[i][j] += 1

        return field, view_mask

    def toggle_flag(self, x, y):
        if self.is_game_over:
            return
        match self.view_mask[y][x]:
            case CellValue.HIDDEN:
                self.view_mask[y][x] = CellValue.FLAG
            case CellValue.FLAG:
                self.view_mask[y][x] = CellValue.HIDDEN

    def open_cell(self, x, y):
        if self.is_game_over:
            return
        if self.view_mask[y][x] != CellValue.HIDDEN:
            return
        match self.field[y][x]:
            case CellValue.MINE:
                for i, row in enumerate(self.field):
                    for j, val in enumerate(row):
                        self.view_mask[i][j] = val
                self.view_mask[y][x] = CellValue.EXPLOSION
                self.is_game_over = True
            case CellValue.EMPTY:
                # BFS to open the field
                stack = [(x, y)]
                while stack:
                    tmp_x, tmp_y = stack.pop()
                    self.view_mask[tmp_y][tmp_x] = self.field[tmp_y][tmp_x]
                    if self.field[tmp_y][tmp_x] == CellValue.EMPTY:
                        for i in range(max(0, tmp_y-1), min(self.height, tmp_y+2)):
                            for j in range(max(0, tmp_x-1), min(self.width, tmp_x+2)):
                                if self.view_mask[i][j] == CellValue.HIDDEN:
                                    stack.append((j, i))
            case _:
                self.view_mask[y][x] = self.field[y][x]

        if self.num_mines == self.count_not_open():
            for i, row in enumerate(self.view_mask):
                for j, val in enumerate(row):
                    if val == CellValue.HIDDEN:
                        self.view_mask[i][j] = CellValue.FLAG
            self.is_game_over = True

    def count_not_open(self):
        count_not_open = 0
        for row in self.view_mask:
            for val in row:
                if val in (CellValue.HIDDEN, CellValue.FLAG):
                    count_not_open += 1
        return count_not_open

    def to_str(self, is_view_mask=False):
        source = self.view_mask if is_view_mask else self.field
        row_strs = []
        for row in source:
            row_strs.append(" ".join((CELL_STR[x] for x in row)))
        return "\n".join(row_strs)

    def partially_open(self, open_ratio = 0.2):
        while not self.is_game_over and self.open_ratio() < open_ratio:
            x, y = random.randint(0, self.width-1), random.randint(0, self.height-1)
            if self.view_mask[y][x] == CellValue.HIDDEN and self.field[y][x] != CellValue.MINE:
                self.open_cell(x, y)

    def open_ratio(self):
        return 1 - (self.count_not_open() / (self.width*self.height))

    def __str__(self):
        return self.to_str(False)


if __name__ == '__main__':
    engine = MinesweeperEngine(40, 10, 100)
    print(engine)
    print(engine.to_str(True))
