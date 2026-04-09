from __future__ import annotations

ELEMENTS = [
    None,
    'H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne',
    'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca',
    'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn',
    'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr', 'Rb', 'Sr', 'Y', 'Zr',
    'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn',
    'Sb', 'Te', 'I', 'Xe', 'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd',
    'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb',
    'Lu', 'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg',
    'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn', 'Fr', 'Ra', 'Ac', 'Th',
    'Pa', 'U', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm',
    'Md', 'No', 'Lr', 'Rf', 'Db', 'Sg', 'Bh', 'Hs', 'Mt', 'Ds',
    'Rg', 'Cn', 'Nh', 'Fl', 'Mc', 'Lv', 'Ts', 'Og'
]

ATOMIC_NUMBER = {symbol: i for i, symbol in enumerate(ELEMENTS) if symbol}

# 按 Aufbau 顺序排列到 7p，可覆盖 Z=1~118
ORBITALS = [
    ('1s', 1, 0, 2),
    ('2s', 2, 0, 2), ('2p', 2, 1, 6),
    ('3s', 3, 0, 2), ('3p', 3, 1, 6),
    ('4s', 4, 0, 2), ('3d', 3, 2, 10), ('4p', 4, 1, 6),
    ('5s', 5, 0, 2), ('4d', 4, 2, 10), ('5p', 5, 1, 6),
    ('6s', 6, 0, 2), ('4f', 4, 3, 14), ('5d', 5, 2, 10), ('6p', 6, 1, 6),
    ('7s', 7, 0, 2), ('5f', 5, 3, 14), ('6d', 6, 2, 10), ('7p', 7, 1, 6),
]

ORBITAL_INFO = {
    name: {'n': n, 'l': l, 'cap': cap, 'deg': 2 * l + 1, 'index': i}
    for i, (name, n, l, cap) in enumerate(ORBITALS)
}

NEUTRAL_EXCEPTIONS = {
    24: {'4s': 1, '3d': 5},
    29: {'4s': 1, '3d': 10},
    41: {'5s': 1, '4d': 4},
    42: {'5s': 1, '4d': 5},
    44: {'5s': 1, '4d': 7},
    45: {'5s': 1, '4d': 8},
    46: {'5s': 0, '4d': 10},
    47: {'5s': 1, '4d': 10},
    57: {'4f': 0, '5d': 1, '6s': 2},
    58: {'4f': 1, '5d': 1, '6s': 2},
    64: {'4f': 7, '5d': 1, '6s': 2},
    78: {'4f': 14, '5d': 9, '6s': 1},
    79: {'4f': 14, '5d': 10, '6s': 1},
    89: {'5f': 0, '6d': 1, '7s': 2},
    90: {'5f': 0, '6d': 2, '7s': 2},
    91: {'5f': 2, '6d': 1, '7s': 2},
    92: {'5f': 3, '6d': 1, '7s': 2},
    93: {'5f': 4, '6d': 1, '7s': 2},
    96: {'5f': 7, '6d': 1, '7s': 2},
    103: {'5f': 14, '6d': 0, '7s': 2, '7p': 1},
}

HARTREE_TO_EV = 27.211386245988
