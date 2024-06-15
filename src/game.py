import functools
import tkinter as tk
import engine

GAME_WIDTH = 20
GAME_HEIGHT = 15
GAME_MINE_RATIO = 0.25
CELL_WIDTH = 1
CELL_HEIGHT = 1

CELL_COLORS = {
    engine.CellValue.EMPTY: 'black',
    engine.CellValue.ONE: 'blue',
    engine.CellValue.TWO: 'green',
    engine.CellValue.THREE: 'red',
    engine.CellValue.FOUR: 'navy',
    engine.CellValue.FIVE: 'brown',
    engine.CellValue.SIX: 'red3',
    engine.CellValue.SEVEN: 'tomato',
    engine.CellValue.EIGHT: 'grey17',
    engine.CellValue.MINE: 'black',
    engine.CellValue.HIDDEN: 'black',
    engine.CellValue.FLAG: 'red',
    engine.CellValue.EXPLOSION: 'red',
}

CELL_STR = engine.CELL_STR.copy()
CELL_STR[engine.CellValue.HIDDEN] = " "

class MinesweeperGUI(tk.Tk):
    def __init__(self, width, height, num_mines):
        super().__init__()
        self.title("Minesweeper")
        self.eng = engine.MinesweeperEngine(width=width, height=height, num_mines=num_mines)
        self.top_frame = tk.Frame(self)
        self.restart_button = tk.Button(self.top_frame, text="Restart", command=self.Restart)
        self.restart_button.pack(anchor="center")
        self.top_frame.pack(side="top")
        self.game_field_frame = tk.Frame(self)
        self.game_field_frame.pack(side="bottom")
        self.cells = []
        for y in range(height):
            row = []
            for x in range(width):
                cell = tk.Button(self.game_field_frame, text=" ", command=functools.partial(self.OpenClick, x, y), height=CELL_HEIGHT, width=CELL_WIDTH)

                # From the documentation is not clear which <Button-N> represents the right mouse button.
                cell.bind("<Button-2>", functools.partial(self.ToggleFlag, x=x, y=y))
                cell.bind("<Button-3>", functools.partial(self.ToggleFlag, x=x, y=y))

                cell.grid(row=y, column=x)
                row.append(cell)
            self.cells.append(row)
        self.Redraw()

    def Redraw(self):
        for y, row in enumerate(self.eng.view_mask):
            for x, val in enumerate(row):
                cell = self.cells[y][x]
                state = tk.NORMAL
                relief = tk.RAISED
                if val not in (engine.CellValue.HIDDEN, engine.CellValue.FLAG):
                    state = tk.DISABLED
                    relief = tk.FLAT
                color = CELL_COLORS[val]
                cell.configure(text=CELL_STR[val], disabledforeground=color, fg=color, state=state, relief=relief)

    def OpenClick(self, x, y):
        self.eng.open_cell(x, y)
        self.Redraw()

    def ToggleFlag(self, event, x, y):
        self.eng.toggle_flag(x, y)
        self.Redraw()

    def Restart(self):
        self.eng = engine.MinesweeperEngine(width=self.eng.width, height=self.eng.height, num_mines=self.eng.num_mines)
        self.Redraw()

if __name__ == "__main__":
    gui = MinesweeperGUI(
        width=GAME_WIDTH,
        height=GAME_HEIGHT,
        num_mines=int(GAME_HEIGHT*GAME_HEIGHT*GAME_MINE_RATIO))
    gui.mainloop()
