"""
This module helps create datasets of Minesweeper games for training ML models.
Generation of Minesweeper boards can be slow. This module can save the dataset as files.
"""

import os
import random
import torch
import gzip
import time

import engine

verbose_mode = 1

def EngineToInputTensor(eng: engine.MinesweeperEngine, device: str) -> torch.Tensor:
    """Converts MinesweeperEngine view mask into a Pytorch Tensor"""
    tensor = torch.tensor(eng.view_mask, dtype=torch.long, device=device)
    return tensor

def EngineToHiddenMask(eng: engine.MinesweeperEngine, device: str) -> torch.Tensor:
    """Returns a bool tensor mask of cells that are not visible."""
    return (EngineToInputTensor(eng=eng, device=device) == engine.CellValue.HIDDEN)

def EngineToLabelsTensor(eng: engine.MinesweeperEngine, device: str) -> torch.Tensor:
    """Creates training labels.

    The resulting tensor has the following values:
        0 indicates cells without mines
        1 indicates cells with mines
        -100 is set for visible cells to avoid training on them.
    """
    field_tensor = torch.tensor(eng.field, dtype=torch.long, device=device)
    is_mine_tensor = (field_tensor > engine.CellValue.EIGHT).long().to(device)
    mask_tensor = EngineToHiddenMask(eng=eng, device=device)
    return torch.where(mask_tensor, is_mine_tensor, -100).to(device)


def _MakeFileName(file_idx: int, width=64, height=32, num_samples_per_file=100, data_dir="./data") -> str:
    return os.path.join(data_dir, f"minesweeper_{width}x{height}_per_file_{num_samples_per_file}_file_idx_{file_idx}.pt.gz")


class DatasetGenerator:
    def __init__(self, width=128, height=128, num_samples_per_file=1000, save_dir="./data", dtype=torch.int8):
        self.width = width
        self.height = height
        self.num_samples_per_file = num_samples_per_file
        self.board_size = width * height
        self.save_dir = save_dir
        self.dtype = dtype
        os.makedirs(save_dir, exist_ok=True)

    def GenerateOneFile(self, file_idx: int, override=False) -> None:
        file_name = _MakeFileName(
            file_idx=file_idx,
            width=self.width,
            height=self.height,
            num_samples_per_file=self.num_samples_per_file,
            data_dir=self.save_dir)
        if not override and os.path.isfile(file_name):
            print(f"skipping {file_name}")
            return
        start_t = time.time()
        save_dict = {}
        for sample_id in range(self.num_samples_per_file):
            idx = file_idx * self.num_samples_per_file + sample_id
            random.seed(idx)
            num_mines = random.randint(int(self.board_size*0.05), self.board_size//2)
            eng = engine.MinesweeperEngine(width=self.width, height=self.height, num_mines=num_mines)
            eng.partially_open(open_ratio=random.random() * 0.3 + 0.1)
            if verbose_mode >= 2 and sample_id % 50 == 0:
                print(f"{idx=}")
                print(eng.to_str(is_view_mask=True))
            save_dict[idx] = (EngineToInputTensor(eng, device="cpu").to(self.dtype), EngineToLabelsTensor(eng, device="cpu").to(self.dtype))
        with gzip.open(filename=file_name, mode='wb') as file_obj:
            torch.save(save_dict, file_obj)
        elapsed_t = time.time() - start_t
        if verbose_mode >= 1:
            print(f"generated {file_name} in {elapsed_t:.2f}s")

    def GenerateDataset(self, num_files: int, override=False) -> None:
        for file_idx in range(num_files):
            self.GenerateOneFile(file_idx, override=override)


class MinesweeperDataset(torch.utils.data.Dataset):
    def __init__(self, width=128, height=128, num_samples_per_file=1000, data_dir="./data"):
        super().__init__()
        self.width = width
        self.height = height
        self.num_samples_per_file = num_samples_per_file
        self.data_dir = data_dir
        self.num_samples = self.ScanDir()
        assert self.num_samples > 0, f"No matching data files in '{data_dir}'"
        self.current_file_idx: int | None = None
        self.current_file_content: dict[int, tuple[torch.Tensor, torch.Tensor]] | None = None

    def ScanDir(self) -> int:
        file_idx = 0
        while True:
            file_name = _MakeFileName(
                file_idx=file_idx,
                width=self.width,
                height=self.height,
                num_samples_per_file=self.num_samples_per_file,
                data_dir=self.data_dir)
            if os.path.isfile(file_name):
                file_idx += 1
            else:
                break
        return file_idx * self.num_samples_per_file

    def __len__(self):
        return self.num_samples

    def __getitem__(self, idx):
        assert idx < self.num_samples, (idx, self.num_samples)
        file_idx = idx // self.num_samples_per_file
        if self.current_file_idx != file_idx:
            file_name = _MakeFileName(
                file_idx=file_idx,
                width=self.width,
                height=self.height,
                num_samples_per_file=self.num_samples_per_file,
                data_dir=self.data_dir)
            start_t = time.time()
            with gzip.open(file_name, mode='rb') as f:
                self.current_file_content = torch.load(f)
            self.current_file_idx = file_idx
            elapsed_t = time.time() - start_t
            if verbose_mode >= 2:
                print(f"fetched file {file_name} in {elapsed_t:.2f}s")
        a, b = self.current_file_content[idx]
        return a.long(), b.long()


if __name__ == "__main__":
    verbose_mode = 2
    width = 64
    height = 64
    num_samples_per_file = 1000
    gen = DatasetGenerator(width=width, height=height, num_samples_per_file=num_samples_per_file, save_dir="./data")
    gen.GenerateDataset(num_files=4, override=True)
    dataset = MinesweeperDataset(width=width, height=height, num_samples_per_file=num_samples_per_file, data_dir="./data")
    for x in range(len(dataset)):
        dataset[x]