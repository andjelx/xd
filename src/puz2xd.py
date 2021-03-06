#!/usr/bin/env python
# -*- coding: utf-8 

# pip install crossword puzpy

import string
import puz
import crossword
import xdfile

hdr_order = [ "title", "creator", "editor", "rights", "publisher", "category", "description", "date" ]

import urllib

def reparse_date(s):
    import time
    tm = time.strptime(s, "%B %d, %Y")
    return time.strftime("%Y-%m-%d", tm)

def decode(s):
    s = s.replace(u'\x92', "'")
    s = s.replace(u'\x93', '"')
    s = s.replace(u'\x94', '"')
    s = s.replace(u'\x85', '...')
    s = urllib.unquote(s)
    return s

def is_block(puz, x, y):
    return x < 0 or y < 0 or x >= puz.width or y >= puz.height or puz[x, y].solution == '.'

def parse_puz(contents, filename):
    rebus_shorthands = list(u"♚♛♜♝♞♟⚅⚄⚃⚂⚁⚀♣♦♥♠Фθиλπφя+&%$@?*zyxwvutsrqponmlkjihgfedcba0987654321")

    if not filename.lower().endswith('.puz'):
        return
    puz_object = puz.load(contents)
    puzzle = crossword.from_puz(puz_object)

    grid_dict = dict(zip(string.uppercase, string.uppercase))

    xd = xdfile.xdfile()

    md = dict([ (k.lower(), v) for k, v in puzzle.meta() if v ])
    author = md.get("creator", "")
    if " / " in author:
        author, editor = author.split(" / ")
    else:
        editor = ""

    author = author.strip()
    editor = editor.strip()

    for editsep in [ "edited by ", "ed. " ]:
      try:
        i = author.lower().index(editsep)
        if i == 0:
            editor = author[len(editsep):]
            author = editor.split(",")[1]
        elif i > 0:
            assert not editor
            editor = author[i+len(editsep):]
            author = author[:i]
      except:
        pass

    author = author.strip()
    editor = editor.strip()

    while author.lower().startswith("by "):
        author = author[3:]

    if author and author[-1] in ",.":
        author = author[:-1]

    md["creator"] = author
    md["editor"] = editor

    for k, v in sorted(md.items(), key=lambda x: hdr_order.index(x[0])):
        if v:
            k = k[0].upper() + k[1:].lower()
            v = decode(v.strip())
            v = v.replace(u"©", "(c)")
            xd.headers.append((k, v))

    answers = { }
    clue_num = 1

    for r, row in enumerate(puzzle):
        rowstr = ""
        for c, cell in enumerate(row):
            if puzzle.block is None and cell.solution == '.':
                rowstr += xdfile.BLOCK_CHAR
            elif puzzle.block == cell.solution:
                rowstr += xdfile.BLOCK_CHAR
            elif cell == puzzle.empty:
                rowstr += "."
            else:
                if cell.solution not in grid_dict:
                    grid_dict[cell.solution] = rebus_shorthands.pop()

                rowstr += grid_dict[cell.solution]

                # compute number shown in box
                new_clue = False
                if is_block(puzzle, c-1, r):  # across clue start
                    j = 0
                    answer = ""
                    while not is_block(puzzle, c+j, r):
                        answer += puzzle[c+j, r].solution
                        j += 1

                    if len(answer) > 1:
                        new_clue = True
                        answers["A"+str(clue_num)] = answer

                if is_block(puzzle, c, r-1):  # down clue start
                    j = 0
                    answer = ""
                    while not is_block(puzzle, c, r+j):
                        answer += puzzle[c, r+j].solution
                        j += 1

                    if len(answer) > 1:
                        new_clue = True
                        answers["D"+str(clue_num)] = answer

                if new_clue:
                    clue_num += 1
        xd.grid.append(rowstr)

    for number, clue in puzzle.clues.across():
        xd.clues.append((("A", number), decode(clue), answers["A"+str(number)]))

    for number, clue in puzzle.clues.down():
        xd.clues.append((("D", number), decode(clue), answers["D"+str(number)]))

    return xd

if __name__ == "__main__":
    xdfile.main_parse(parse_puz)

