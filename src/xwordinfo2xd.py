#!/usr/bin/env python
# -*- coding: utf-8 -*-

import string
import os.path
import re

from lxml import html

import xdfile

SPLIT_REBUS_TITLES = "CRYPTOCROSSWORD TIC-TAC-TOE".split()

REBUS_LONG_HANDS = {
    'NINE': '9', 'EIGHT': '8', 'SEVEN': '7', 'SIX': '6', 'FIVE': '5', 'FOUR': '4', 'THREE': '3',
    'TWO': '2', 'ONE': '1', 'ZERO': '0', 'AUGHT': '0', 'AMPERSAND': '&', 'AND': '&', 'ASTERISK': '*',
    'PERCENT': '%', 'STAR': '*', 'AT': '@', 'DOLLAR': '$', 'PLUS': '+', 'CENT': 'c',
#    'DASH': '-',
#    'DOT': '●',
}

REBUS_SHORT_HANDS = list(u'♚♛♜♝♞♟⚅⚄⚃⚂⚁⚀♣♦♥♠Фθиλπφя+&%$@?*zyxwvutsrqponmlkjihgfedcba0987654321')

# content is unicode()
def parse_xwordinfo(content):
    content = content.replace("<b>", "{*")
    content = content.replace("</b>", "*}")
    content = content.replace("<i>", "{/")
    content = content.replace("</i>", "/}")
    content = content.replace("<em>", "{/")
    content = content.replace("</em>", "/}")
    content = content.replace("<u>", "{_")
    content = content.replace("</u>", "_}")
    content = content.replace("<strike>", "{-")
    content = content.replace("</strike>", "-}")

    root = html.fromstring(content)

    special_type = ''
    rebus = {}
    rebus_order = []
    xd = xdfile.xdfile()

    puzzle_table = root.cssselect('#CPHContent_PuzTable tr') or \
        root.cssselect('#PuzTable tr')

    for row in puzzle_table:
        row_data = u""
        for cell in row.cssselect('td'):
            # check if the cell is special - with a shade or a circle
            cell_class = cell.get('class')
            cell_type = ''
            if cell_class == 'bigshade':
                cell_type = 'shaded'
            elif cell_class == 'bigcircle':
                cell_type = 'circle'

            letter = cell.cssselect('div.letter')
            letter = (len(letter) and letter[0].text) or xdfile.BLOCK_CHAR

            # handle rebuses
            if letter == xdfile.BLOCK_CHAR:
                subst = cell.cssselect('div.subst2')
                subst = (len(subst) and subst[0].text) or ''
                if not subst:
                    subst = cell.cssselect('div.subst')
                    if subst:
                        if title in SPLIT_REBUS_TITLES:
                            subst = "/".join(list(subst[0].text))
                        else:
                            subst = subst[0].text
                    else:
                        subst = ''

                if subst:
                    if not subst in rebus:
                        if subst in REBUS_LONG_HANDS:
                            rebus_val = REBUS_LONG_HANDS[subst]
                            if rebus_val in REBUS_SHORT_HANDS:
                                REBUS_SHORT_HANDS.remove(rebus_val)
                        else:
                            rebus_val = REBUS_SHORT_HANDS.pop()
                        rebus[subst] = rebus_val
                        rebus_order.append(subst)
                    letter = rebus[subst]

            if cell_type:
                # the special cell's letter should be represented in lower case
                letter = letter.lower()
                if not special_type:
                    # hopefully there shouldn't be both shades and circles in
                    # the same puzzle - if that is the case, only the last value
                    # will be put up in the header
                    special_type = cell_type

            row_data += letter
        xd.grid.append(row_data)

    # add meta data
    title = root.cssselect('#CPHContent_TitleLabel')[0].text.strip()
    subtitle = ''
    try:
        subtitle = root.cssselect('#CPHContent_SubTitleLabel')[0].text.strip()
        subtitle = ' [%s]' %subtitle
    except:
        pass

    xd.headers.append(("Title", '%s%s' %(title, subtitle)))
    xd.headers.append(("Author", root.cssselect('#CPHContent_AuthorLabel')[0].text.strip()))
    xd.headers.append(("Editor", root.cssselect('#CPHContent_EditorLabel')[0].text.strip()))

    if len(rebus):
        rebus = ["%s=%s" %(rebus[x], x.upper()) for x in rebus_order]
        xd.headers.append(("Rebus", ','.join(rebus)))
    if special_type:
        xd.headers.append(("Special", special_type))

    # add clues
    across_clues = _fetch_clues(xd, 'A', root, '#CPHContent_AcrossClues', rebus)
    down_clues = _fetch_clues(xd, 'D', root, '#CPHContent_DownClues', rebus)

    return xd

def _fetch_clues(xd, clueprefix, root, css_identifier, rebus):
    PT_CLUE = re.compile(r'(\d+)\. (.*) :')
    text = number = solution = None
    for content in root.cssselect(css_identifier)[0].itertext():
        content = content.strip()
        if text:
            # replace rebuses with appropriate identifiers (numbers)
            for item in rebus:
                if item in content:
                    content = content.replace(item, str(index+1))

            solution = content
            xd.clues.append(((clueprefix, number), text, solution))
            text = number = solution = None
        else:
            match = re.match(PT_CLUE, content)
            number = int(match.group(1))
            text = match.group(2)

if __name__ == "__main__":
    xdfile.main_parse(parse_xwordinfo)
