"""The OFAC copy script turns the Treasury's sdn.csv, alt.csv and add.csv into one compact JSON (fictitious rows)."""

import importlib.util
import json
from datetime import date
from pathlib import Path
from types import ModuleType

from custodio.engine.sanctions import SanctionsList

SCRIPT = Path(__file__).parents[2] / "scripts" / "update_ofac.py"
SDN = (
    '990001,"QUIMERA FICTICIA TRADING LLC",-0- ,"SDGT] [PRUEBA",-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,-0- \n'
    '990002,"PEREZ INVENTADO, Fulano",individual,"PRUEBA",-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,"DOB 1970."\n'
    "\x1a\n"
)
ALT = '990001,1,"aka","QUIMERA TRADING",-0- \n990001,2,"fka","QFT TEST",-0- \n'
ADD = '990001,10,-0- ,"Ciudad Ficticia","Utopia",-0- \n990001,11,-0- ,-0- ,"Utopia",-0- \n990002,12,-0- ,-0- ,-0- ,-0- \n'


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("update_ofac", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_entries_carry_name_aliases_countries_programs_and_uid() -> None:
    entries = load_script().parse_entries(SDN, ALT, ADD)
    assert entries == [
        {
            "uid": 990001,
            "name": "QUIMERA FICTICIA TRADING LLC",
            "aliases": ["QUIMERA TRADING", "QFT TEST"],
            "countries": ["Utopia"],
            "programs": ["SDGT", "PRUEBA"],
            "type": None,
        },
        {
            "uid": 990002,
            "name": "PEREZ INVENTADO, Fulano",
            "aliases": [],
            "countries": [],
            "programs": ["PRUEBA"],
            "type": "individual",
        },
    ]


def test_the_copy_is_dated_and_loads_as_a_sanctions_list() -> None:
    script = load_script()
    copy = script.build_copy(
        script.parse_entries(SDN, ALT, ADD),
        published_on=date(2026, 10, 15),
        downloaded_on=date(2026, 10, 17),
        source="prueba",
    )
    screened = SanctionsList.from_json(json.dumps(copy))
    assert screened.published_on == date(2026, 10, 15)
    assert screened.size == 2
    hit = screened.screen("QFT Test")
    assert hit is not None and hit.entry.uid == 990001
