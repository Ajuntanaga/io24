"""DLL-free native EQ parity against the pinned instruction oracle."""
import json
from pathlib import Path
import struct
import subprocess
import sys

import pytest
import io24_eq_native as native

CASES = json.loads((Path(__file__).parent / 'fixtures' /
                    'native_eq_coefficients.json').read_text())['cases']


@pytest.mark.parametrize('case', CASES)
def test_reference_coefficients_are_byte_exact(case):
    result = getattr(native, case['kind'])(*case['args'])
    assert struct.pack('<%df' % len(result), *result).hex() == case['hex']


def test_enabled_models_work_without_vendor_or_disassembler():
    subprocess.run([sys.executable, '-c', '''
import sys
sys.modules['capstone'] = None
sys.modules['io24_uc472_vintage_eq'] = None
sys.modules['io24_uc472_passive_eq'] = None
import io24_alt_eq as eq
assert eq.designer_status('/missing.dll')[0]
for model in ('passive', 'vintage'):
    state = eq.default_eq(model, on=True)
    sections = eq.design_live_sections(state, dll_path='/missing.dll')
    assert len(sections) == 4
    tables = eq.design_native_coefficients(state, dll_path='/missing.dll')
    assert len(tables) == 4
    for field in state:
        if field not in ('__classid', 'eqallon'):
            assert eq.design_changed_live_sections(state, field, sections) == sections
'''], check=True)
