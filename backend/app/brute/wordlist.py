import pathlib

_WORDLIST_PATH = pathlib.Path(__file__).parent / "default_wordlist.txt"


def load_words(content: str | None) -> list[str]:
    if content:
        words = [line.strip() for line in content.splitlines() if line.strip()]
        return list(dict.fromkeys(words))
    with open(_WORDLIST_PATH) as f:
        return [line.strip() for line in f if line.strip()]
