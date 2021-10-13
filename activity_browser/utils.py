from pathlib import Path


def get_base_path() -> Path:
    return Path(__file__).resolve().parents[0]


def read_file_text(file_dir: str) -> str:
    if not file_dir:
        raise ValueError('File path passed is empty')
    file = open(file_dir, mode="r", encoding='UTF-8')
    if not file:
        raise ValueError('File does not exist in the passed path:', file_dir)
    text = file.read()
    file.close()
    return text
