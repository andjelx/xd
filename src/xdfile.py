#!/usr/bin/python

import sys
import os
import os.path
import stat
import string
import zipfile

BLOCK_CHAR = '#'
EOL = '\n'

publishers = {
    'unk': 'unknown',
    'che': 'chronicle',
    'ch': 'chicago',
    'cs': 'crossynergy',
    'pp': 'wapost',
    'wsj': 'wsj',
    'rnr': 'rocknroll',
    'nw': 'newsday',
    'nyt': 'nytimes',
    'tech': 'nytimes',
    'tm': "time",
    'nfl': "cbs",
    'cn': "crosswordnation",
    'vwl': 'nytimes',
    'nyk': 'nytimes',
    'la': 'latimes',
    'nys': 'nysun',
    'pzz': 'puzzazz',
    'nyh': 'nyherald',
    'lt': 'london',
    'pa': 'nytimes',
    'pk': 'king',
    'nym': 'nymag',
    'db': 'dailybeast',
    'awm': 'threeacross',
    'rp': 'rexparker',
    'wp': 'wapost',
    'nl': 'lampoon',
    'tmdcr': 'tribune',
    'kc': 'kcstar',
    'mg': 'mygen',
    'atc': 'crossroads',
    'onion': 'onion',
    'mm': 'aarp',
    'ue': 'universal',
    'ut': 'universal',
    'up': 'universal',
    'us': 'universal',
    'um': 'universal',
    'ub': 'universal',
    'ss': 'simonschuster',
    'sl': 'slate',
    'ana': 'nytimes',
}

unknownpubs = { }
all_files = { }


class xdfile:
    def __init__(self, xd_contents=None, filename=None):
        self.filename = filename
        self.headers = [ ]
        self.grid = [ ]
        self.clues = [ ] # list of (("A", 21), "{*Bold*}, {/italic/}, {_underscore_}, or {-overstrike-}", "MARKUP")
        self.notes = ""
        self.orig_contents = xd_contents

        if xd_contents:
            self.parse_xd(xd_contents.decode("utf-8"))

    def __str__(self):
        return self.filename

    def get_header(self, fieldname):
        vals = [ v for k, v in self.headers if k == fieldname ]
        if vals:
            assert len(vals) == 1, vals
            return vals[0]

    def parse_xd(self, xd_contents):
        # placeholders, actual numbering starts at 1
        section = 0
        subsection = 0

        # fake blank line at top to allow leading actual blank lines before headers
        nblanklines = 2

        for line in xd_contents.splitlines():
            # leading whitespace is decorative
            line = line.strip()

            # collapse consecutive lines of whitespace into one line and start next group
            if not line:
                nblanklines += 1
                continue
            else:
                if nblanklines >= 2:
                    section += 1
                    subsection = 1
                    nblanklines = 0
                elif nblanklines == 1:
                    subsection += 1
                    nblanklines = 0

            if section == 1:
                # headers first
                if ":" in line:
                    k, v = line.split(":", 1)
                    k, v = k.strip(), v.strip()

                    self.headers.append((k, v))
                else:
                    self.headers.append(("", line))  # be permissive
            elif section == 2:
                # grid second
                self.grid.append(line)
            elif section == 3:
                # across or down clues
                answer_idx = line.rfind("~")
                if answer_idx > 0:
                    clue = line[:answer_idx]
                    answer = line[answer_idx+1:]
                else:
                    clue, answer = line, ""

                clue_idx = clue.find(".")

                assert clue_idx > 0, "no clue number: " + clue
                pos = clue[:clue_idx].strip()
                clue = clue[clue_idx+1:]

                if pos[0] in string.uppercase:
                    cluedir = pos[0]
                    cluenum = pos[1:]
                else:
                    cluedir = ""
                    cluenum = pos

                self.clues.append(((cluedir, cluenum), clue.strip(), answer.strip()))
            else: # anything remaining
                if line:
                    self.notes += line + EOL

    def to_unicode(self):
        # headers (section 1)

        r = u"" 
        for k, v in self.headers:
            if v:
                r += "%s: %s" % (k or "Header", v)
            r += EOL

        r += EOL + EOL

        # grid (section 2)
        r += EOL.join(self.grid)
        r += EOL + EOL

        # clues (section 3)
        prevdir = None
        for pos, clue, answer in self.clues:
            cluedir, cluenum = pos
            if cluedir != prevdir:
                r += EOL
            prevdir = cluedir

            r += u"%s%s. %s ~ %s" % (cluedir, cluenum, clue.strip(), answer)
            r += EOL

        if self.notes:
            r += EOL + EOL
            r += self.notes

        r += EOL

        # some Postscript CE encodings can be caught here
        r = r.replace(u'\x91', "'")
        r = r.replace(u'\x92', "'")
        r = r.replace(u'\x93', '"')
        r = r.replace(u'\x94', '"')
        r = r.replace(u'\x85', '...')

        # these are always supposed to be double-quotes
        r = r.replace("''", '"')

        return r

def get_base_filename(fn):
    path, b = os.path.split(fn)
    b, ext = os.path.splitext(b)

    return b


def find_files(*paths):
    for path in paths:
        if stat.S_ISDIR(os.stat(path).st_mode):
            for thisdir, subdirs, files in os.walk(path):
                for fn in files:
                    if fn[0] == ".":
                        continue
                    for f, c in find_files(os.path.join(thisdir, fn)):
                        yield f, c
        elif path.endswith(".zip"):
            import zipfile
            with zipfile.ZipFile(path, 'r') as zf:
                for f in zf.infolist():
                    fullfn = f.filename
                    contents = zf.read(f)
                    yield fullfn, contents
        else:
            fullfn = path
            contents = file(path).read()
            yield fullfn, contents
    
def load_corpus(*pathnames):
    ret = { }

    n = 0
    for fullfn, contents in find_files(*pathnames):
        if not fullfn.endswith(".xd"):
            continue

        try:
            basefn = get_base_filename(fullfn)
            n += 1
            print >>sys.stderr, "\r% 6d %s" % (n, basefn),
            xd = xdfile(contents, fullfn)

            ret[basefn] = xd
        except Exception, e:
            print >>sys.stderr, unicode(e)
            #if args.debug:
            #    raise

    print >>sys.stderr, ""

    return ret

def parse_filename(fn):
    import re
    m = re.search("([A-z]*)[_\s]?(\d{2,4})-?(\d{2})-?(\d{2})(.*)\.", fn)
    if m:
        abbr, yearstr, monstr, daystr, rest = m.groups()
        year, mon, day = int(yearstr), int(monstr), int(daystr)
        if len(yearstr) == 2:
            if year > 1900:
                pass
            elif year > 18:
                year += 1900
            else:
                year += 2000
        assert len(abbr) <= 5, fn
        assert year > 1920 and year < 2017, "bad year %s" % yearstr
        assert mon >= 1 and mon <= 12, "bad month %s" % monstr
        assert day >= 1 and day <= 31, "bad day %s" % daystr
#        print "%s %d-%02d-%02d" % (abbr, year, mon, day)
        return abbr, year, mon, day, "".join(rest.split())[:3]

def xd_filename(pubid, pubabbr, year, mon, day, unique=""):
    return "crosswords/%s/%s/%s%s-%02d-%02d%s.xd" % (pubid, year, pubabbr, year, mon, day, unique)

def main_load():
    corpus = load_corpus(*sys.argv[1:])

    if len(corpus) == 1:
        xd = corpus.values()[0]
        print xd.to_unicode().encode("utf-8")
    else:
        print "%s puzzles" % len(corpus)

    return corpus

def main_parse(parserfunc):
    import os.path
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='convert crosswords to .xd format')
    parser.add_argument('path', type=str, nargs='+', help='files, .zip, or directories to be converted')
    parser.add_argument('-o', dest='output', default=None, help='output directory (default stdout)')
    parser.add_argument('-t', dest='toplevel', default=None, help='set toplevel directory of files in .zip')
    parser.add_argument('-d', dest='debug', action='store_true', default=False, help='abort on exception')

    args = parser.parse_args()

    outf = sys.stdout

    if args.output:
        outbase, outext = os.path.splitext(args.output)
        if outext == ".zip":
            outf = zipfile.ZipFile(args.output, 'w')
        else:
            outf = None

    for fullfn, contents in sorted(find_files(*args.path)):
        print >>sys.stderr, "\r" + fullfn,
        path, fn = os.path.split(fullfn)
        base, ext = os.path.splitext(fn)
        try:
            xd = parserfunc(contents, fullfn)
            if not xd:
                print >>sys.stderr, ""
                continue
            xd.headers.append(("", ""))
            try:
                abbr, year, month, day, rest = parse_filename(fullfn.lower())
                xd.headers.append(("Date", "%d-%02d-%02d" % (year, month, day)))
                if abbr:
                    base = "%s%s-%02d-%02d%s" % (abbr, year, month, day, rest)
                    outfn = xd_filename(publishers.get(abbr, abbr), abbr, year, month, day, rest)
                else:
                    base = "%s-%02d-%02d%s" % (year, month, day, rest)
            except Exception, e:
                abbr = ""
                year, month, day = 1980, 1, 1
                outfn = "crosswords/unknown/%s.xd" % base

            xd.headers.append(("Identifier", base + ".xd"))

            xd.headers.append(("", ""))
            xd.headers.append(("Source", fullfn))


            xdstr = xd.to_unicode().encode("utf-8")
        except Exception, e:
            if args.debug:
                raise
            else:
                print >>sys.stderr, "error:", str(e), type(e)
                continue
            
        if isinstance(outf, zipfile.ZipFile):
            if args.toplevel:
                fullfn = "%s/%s/%s.xd" % (args.toplevel, "/".join(path.split("/")[1:]), base)
            else:
                base, ext = os.path.splitext(fullfn)
                fullfn = base + ".xd"

            if abbr and abbr not in publishers:
                rights = xd.get_header("Rights")
                if rights:
                    publishers[abbr] = abbr
                    if abbr not in unknownpubs:
                        unknownpubs[abbr] = set()
                    unknownpubs[abbr].add(rights.strip())

            if outfn in all_files:
                if all_files[outfn] != xdstr:
                    print >>sys.stderr, "different versions", outfn
                    outfn += ".2"
            
            all_files[outfn] = xdstr

            if year < 1980:
                year = 1980
            zi = zipfile.ZipInfo(outfn, (year, month, day, 9, 0, 0))
            zi.external_attr = 0444 << 16L
            zi.compress_type = zipfile.ZIP_DEFLATED
            outf.writestr(zi, xdstr)
        elif isinstance(outf, file):
            outf.write(xdstr)
        else:
            _, fn = os.path.split(fullfn)
            base, ext = os.path.splitext(fn)
            xdfn = "%s/%s.xd" % (args.output, base)
            file(xdfn, "w-").write(xdstr)

    print >>sys.stderr, "Done"
    for k, v in unknownpubs.items():
        print k, "\n".join(v)

if __name__ == "__main__":
    main_load()

