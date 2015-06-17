#!/usr/bin/env python
# coding: utf-8

from libulb import Client
from math import sqrt, floor, ceil
from itertools import chain
from datetime import datetime
import config

class options:
    color = True
    red = 10
    green = 12
    sepcolumns = "-+-"
    seplines = "-"
    columns = " | "

def colorize_text(color, text):
    if not options.color:
        return text
    return "\033[%dm%s\033[0m" % (color, text)

red = lambda txt: colorize_text(31, txt)
green = lambda txt: colorize_text(32, txt)
yellow = lambda txt: colorize_text(33, txt)
blue = lambda txt: colorize_text(34, txt)
magenta = lambda txt: colorize_text(35, txt)
hilight = lambda txt: colorize_text(1, txt)

class Course:
    separator = options.sepcolumns.join((
        options.seplines*10, options.seplines*4, options.seplines*2, 
        options.seplines*20, options.seplines*52))

    @classmethod
    def titles(klass):
        return options.columns.join(map(hilight, (
            "Mnemonique", "Note", "Cr", "Histogramme".ljust(20), "Nom du cours")))

    def __init__(self, mnemonic, name, ects, note=None, lower_note=0, upper_note=None):
        self.mnemonic = mnemonic
        self.name = name
        self.ects = ects
        self.note = note
        self.lower_note = lower_note
        self.upper_note = note if upper_note is None else upper_note

    def __unicode__(self):
        ects_txt = blue("%2d" % int(self.ects))
        return options.columns.join((
            self.colorize_mnemonic(), 
            self.colorize_note(), 
            self.colorize_ects(),
            self.bar(),
            self.name))

    @classmethod
    def from_ulb_api(klass, api_dict):
        return klass(
            mnemonic=api_dict['mnemonique'],
            name=api_dict['course_title'],
            ects=int(api_dict['credits']),
            note=api_dict.get('quality_points', None))

    def default_note(self, note):
        return note if self.note is None else self.note

    ### FORMATTERS ###
    def colorize_mnemonic(self):
        as_str = self.mnemonic.rjust(10)
        if self.note is not None:
            return hilight(yellow(as_str))
        return as_str

    def colorize_note(self):
        if self.note is None:
            return '----'
        n = round(self.note, 1)
        formatted = "%4s" % n
        if n < options.red:
            return red(formatted)
        elif n < options.green:
            return yellow(formatted)
        else:
            return green(formatted)

    def colorize_ects(self):
        as_str = "%2d" % int(self.ects)
        if self.note is not None:
            if self.note < 10:
                return red(as_str)
            else:
                return green(as_str)
        return blue(as_str)

    def bar(self):
        if self.note is None:
            return '.'*20

        lower, upper = int(round(self.lower_note)), int(round(self.upper_note))
        if lower > 0:
            lower -= 1

        res = ' '*int(round(lower))
        for i in range((lower), (upper)):
            cur = hilight('*') if i+1 == round(self.note) else '*'

            if i+1 < options.red:
                res += red(cur)
            elif i+1 < options.green:
                res += yellow(cur)
            else:
                res += green(cur)

        res += ' '*(20-int(round(upper)))
        return res

def print_notes(api_client, inscription):
    courses = map(Course.from_ulb_api, api_client.notes(inscription))
    
    print hilight("%s - %s (session %d)" % (
        inscription['area'], inscription['term_desc'], inscription['session_num']))
    print Course.titles()
    print Course.separator
    print '\n'.join(map(unicode, courses))

    evaluated = filter(lambda c: c.note is not None, courses)
    if evaluated:
        ects = sum(x.ects for x in evaluated)
        mu = sum(x.note*x.ects for x in evaluated)/ects
        all_ects = sum(x.ects for x in courses)
        all_0 = round(sum(c.default_note(0)*c.ects for c in courses)/all_ects, 1)
        all_20 = round(sum(c.default_note(20)*c.ects for c in courses)/all_ects, 1)
        description = "Note finale"
        if all_ects != ects:
            description += " entre %s et %s" % (str(all_0), str(all_20))
        avg_course = Course(
            mnemonic="Moyenne",
            name=description,
            ects=ects, note=mu,
            lower_note=all_0,
            upper_note=all_20)
        if evaluated == courses:
            print hilight(blue(Course.separator))
        else:
            print Course.separator
        print unicode(avg_course)

    passed = filter(lambda c: c.note and c.note >= 10, courses)
    if passed:
        ects = sum(x.ects for x in passed)
        mu = sum(x.note*x.ects for x in passed)/ects
        avg_course = Course(
            mnemonic="Reussis",
            name="Cours dont la note est >= 10/20",
            ects=ects, note=mu, lower_note=mu)
        print unicode(avg_course)

    print


def main(netid, passwd):
    session = Client.auth(netid, passwd)
    this_year = datetime.now().year if datetime.now().month >= 9 else datetime.now().year-1
    this_year_str = '%d%d' % (this_year, (this_year+1)%100)
    for inscr in filter(lambda inscr: inscr['term_code'] == this_year_str, session.inscriptions()):
        print_notes(session, inscr)

if __name__ == "__main__":
    import argparse
    from getpass import getpass

    optparser = argparse.ArgumentParser(description=u"Points des cours à l'ULB")
    optparser.add_argument(
        "--netid", "-n", action='store',
        type=str, dest='netid', default=config.NETID,
        help=u"Affiche les points pour ce netid ('%s' par defaut)" % (config.NETID))
    optparser.add_argument(
        "--no-color", "-C", action='store_false',
        dest='color', default=True,
        help=u"N'affiche pas les résultats en couleur")
    clargs = optparser.parse_args()

    options.color = clargs.color
    while not clargs.netid:
        clargs.netid = raw_input("NetID ? ")

    passwd = config.PASSWD
    while not passwd:
        passwd = getpass()

    main(clargs.netid, passwd)
