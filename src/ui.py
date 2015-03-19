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

def input_bool(query):
    bool_query = query + '? (y/n)> '

    while True:
        v = input(bool_query)
        if v in ('', 'y', 'n'):
            break

        print('ERROR: please type y, n, or leave the line empty')

    return v == 'y'


def input_number(query, minimum=None, maximum=None):
    number_query = query + '> '
    while True:
        v = input(number_query)
        try:
            v = int(v)
            if ((minimum is None or minimum <= v)
                    and (maximum is None or maximum >= v)):
                return v
            else:
                print('ERROR: invalid number provided')

        except ValueError:
            print('ERROR: please enter a number')


def _is_int(v):
    try:
        int(v)
        return True
    except ValueError:
        return False


def input_multi_options(title, options):
    print(title)
    selected = set([o for o in options if input_bool('  ' + o)])
    return selected


def input_single_option(title, options):
    while True:
        print(title)
        for i, o in enumerate(options):
            print('  {0}. {1}'.format(i + 1, o))

        v = input_number('pick one')
        if 1 <= v <= len(options):
            return options[v - 1]

        print('ERROR: you must pick one of the options')


EMAIL_REGEX = '^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,6}$'

def input_email():
    while True:
        v = input('email address> ')
        if re.match(EMAIL_REGEX, v, re.IGNORECASE):
            return v

        print('ERROR: please enter a valid email address')


def input_string(query, allow_empty=False):
    while True:
        v = input(query + '> ').strip()
        if allow_empty or v:
            return v

        print('ERROR: cannot be left empty')


def pause(message='Press ENTER to continue...'):
    input(message)


def clear_screen():
    os.system('clear')
