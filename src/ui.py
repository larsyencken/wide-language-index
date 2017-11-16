# -*- coding: utf-8 -*-
#
#  ui.py
#  wide-language-index
#

"""
Helpers for writing interactive console scripts.
"""

import re
import os
from typing import List, Set, Optional


def input_bool(query: str) -> bool:
    bool_query = query + '? (y/n)> '

    while True:
        v = input(bool_query)
        if v in ('', 'y', 'n'):
            break

        print('ERROR: please type y, n, or leave the line empty')

    return v == 'y'


def input_number(query: str, minimum: Optional[int]=None, maximum: Optional[int]=None) -> int:
    number_query = query + '> '
    while True:
        r = input(number_query)
        try:
            v = int(r)
            if ((minimum is None or minimum <= v)
                    and (maximum is None or maximum >= v)):
                return v
            else:
                print('ERROR: invalid number provided')

        except ValueError:
            print('ERROR: please enter a number')


def input_multi_options(title: str, options: List[str]) -> Set[str]:
    print(title)
    selected = set([o for o in options if input_bool('  ' + o)])
    return selected


def input_single_option(title: str, options: List[str]) -> str:
    print(title)
    for i, o in enumerate(options):
        print('  {0}. {1}'.format(i + 1, o))

    v = input_number('pick one', minimum=1, maximum=len(options))

    return options[v - 1]


EMAIL_REGEX = '^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,6}$'


def input_email() -> str:
    while True:
        v = input('email address> ')
        if re.match(EMAIL_REGEX, v, re.IGNORECASE):
            return v

        print('ERROR: please enter a valid email address')


def input_string(query: str, allow_empty: bool=False) -> str:
    while True:
        v = input(query + '> ').strip()
        if allow_empty or v:
            return v

        print('ERROR: cannot be left empty')


def pause(message: str='Press ENTER to continue...') -> None:
    input(message)


def clear_screen() -> None:
    os.system('clear')
