"""
This module helps create datasets of Minesweeper games for training ML models.
Generation of Minesweeper boards can be slow. This module saves the dataset as files.
The dataset defined here reuses each sample multiple times using flip and rotation operations.
When square samples can produce 2x more augmentations, because we can also use their transposes.
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
        save_list = []
        for sample_id in range(self.num_samples_per_file):
            idx = file_idx * self.num_samples_per_file + sample_id
            random.seed(idx)
            num_mines = random.randint(int(self.board_size*0.05), self.board_size//2)
            eng = engine.MinesweeperEngine(width=self.width, height=self.height, num_mines=num_mines)
            eng.partially_open(open_ratio=random.random() * 0.3 + 0.1)
            if verbose_mode >= 2 and sample_id % 50 == 0:
                print(f"{idx=}")
                print(eng.to_str(is_view_mask=True))
            save_list.append((
                EngineToInputTensor(eng, device="cpu").to(self.dtype),
                EngineToLabelsTensor(eng, device="cpu").to(self.dtype)))
        with gzip.open(filename=file_name, mode='wb') as file_obj:
            torch.save(save_list, file_obj)
        elapsed_t = time.time() - start_t
        if verbose_mode >= 1:
            print(f"generated {file_name} in {elapsed_t:.2f}s")

    def GenerateDataset(self, num_files: int, override=False) -> None:
        for file_idx in range(num_files):
            self.GenerateOneFile(file_idx, override=override)


class MinesweeperDataset(torch.utils.data.Dataset):
    def __init__(self, width=128, height=128, num_samples_per_file=1000, data_dir="./data", shuffle=False):
        super().__init__()
        self.width = width
        self.height = height
        self.num_samples_per_file = num_samples_per_file
        self.data_dir = data_dir
        self.num_files, self.num_samples = self.ScanDir()
        self.shuffle = shuffle
        self.file_indicies = list(range(self.num_files))
        self.num_augmentations = 4
        if width == height:
            self.num_augmentations *= 2
        if self.shuffle:
            random.shuffle(self.file_indicies)
        assert self.num_samples > 0, f"No matching data files in '{data_dir}'"
        self.current_file_idx: int | None = None
        self.current_file_content: list[tuple[torch.Tensor, torch.Tensor]] | None = None

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
        return file_idx, file_idx * self.num_samples_per_file

    def __len__(self):
        return self.num_samples * self.num_augmentations

    def AugmentSample(self, record_idx, augmentation_idx):
        a, b = self.current_file_content[record_idx]
        assert a.shape == (self.height, self.width), a.shape
        assert b.shape == (self.height, self.width), b.shape
        if augmentation_idx // 4 == 1:
            assert self.height == self.width
            a = a.T
            b = b.T
        match augmentation_idx % 4:
            case 0:
                ...
            case 1:
                a = a.fliplr()
                b = b.fliplr()
            case 2:
                a = a.flipud()
                b = b.flipud()
            case 3:
                a = a.rot90(k=2)
                b = b.rot90(k=2)
        return a.long(), b.long()

    def __getitem__(self, idx):
        assert idx < len(self), (idx, len(self))
        augmentation_idx = idx // self.num_samples
        file_idx = self.file_indicies[(idx % self.num_samples) // self.num_samples_per_file]
        record_idx = idx % self.num_samples_per_file
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
                if self.shuffle:
                    random.shuffle(self.current_file_content)
            self.current_file_idx = file_idx
            elapsed_t = time.time() - start_t
            if verbose_mode >= 2:
                print(f"fetched file {file_name} in {elapsed_t:.2f}s")
        return self.AugmentSample(record_idx=record_idx, augmentation_idx=augmentation_idx)

if __name__ == "__main__":
    # This module is meant to be used as a library and not as a stand-alone executable.
    # Code below is simply for testing the functionality.
    verbose_mode = 2
    width = 10
    height = 10
    num_samples_per_file = 3
    gen = DatasetGenerator(width=width, height=height, num_samples_per_file=num_samples_per_file, save_dir="./data")
    gen.GenerateDataset(num_files=4, override=True)
    gen.GenerateDataset(num_files=5, override=False)
    dataset = MinesweeperDataset(width=width, height=height, num_samples_per_file=num_samples_per_file, data_dir="./data", shuffle=True)
    seen_samples = {}
    for idx in range(len(dataset)):
        a, b = dataset[idx]
        hash_val = hash((tuple(a.reshape((-1,)).tolist()), tuple(b.reshape((-1,)).tolist())))
        assert hash_val not in seen_samples, (seen_samples[hash_val], idx, hash_val)
        seen_samples[hash_val] = idx
    print(f"Produced {len(seen_samples)} unique tensors")