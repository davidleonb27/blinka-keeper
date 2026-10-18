"""The demo XML files are the generator's output, byte for byte, and only use fictitious data."""

from pathlib import Path

import pytest

from custodio.dataset.einvoices import DEMO_DIRECTORY, DEMO_FILES

WEB_COPY = Path(__file__).parents[3] / "web" / "public" / "demo" / "facturas"


@pytest.mark.parametrize("directory", [DEMO_DIRECTORY, WEB_COPY], ids=["dataset", "web"])
@pytest.mark.parametrize("name", sorted(DEMO_FILES))
def test_the_committed_demo_file_matches_its_generator(directory: Path, name: str) -> None:
    assert (directory / name).read_text(encoding="utf-8") == DEMO_FILES[name], (
        "regenerate with: uv run python -m custodio.dataset.einvoices custodio/dataset/einvoices "
        "../web/public/demo/facturas"
    )
