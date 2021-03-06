import requests
from bs4 import BeautifulSoup
import re
from libulb.tools import Slug


def parse_event(event):
    title = event.find(class_="tooltip_titre").text.strip()

    infos = event.find(class_="tooltip_info")
    infos = infos.findAll("p")

    # The first line is like "Le Mardi de 08:00 à 10:00" we need to treat it separately
    time = infos[0]
    infos = infos[1:]
    day, start, stop = map(lambda x: x.text, time.findAll('strong'))

    course = {
        'title': title,
        'day': day,
        'start': start,
        'stop': stop
    }

    # Every other line is like "Professeur(s) : Massart, Thierry" -> key: value
    for line in infos:
        key, val = line.text.split(':', 1)
        course[key.strip()] = val.strip()

    return course


def prettify_event(course):
    course['days'] = course['Date(s)'].split(', ')
    del course['Date(s)']

    course['groups'] = course['Groupe(s)'].split(', ')
    del course['Groupe(s)']

    course['weeks'] = course['Semaine(s)'].split('; ')
    del course['Semaine(s)']

    # 'title' looks like 'Programmation [INFOF101]'
    course['name'], course['slug'] = re.match(r"^(.*)\[([A-Z]{5}\d{3,4})\]$", course['title']).groups()
    del course['title']

    course['name'] = course['name'].strip()
    course['slug'] = Slug.from_gehol(course['slug'])

    return course


def get_events_for_week(week, *slugs):
    if len(slugs) > 200:
        raise ValueError("Too much slugs. GeHoL can't handle that much (max 200)")

    BASE_URL = "http://gehol.ulb.ac.be/gehol/Vue/HoraireCours.php?semaine_unif={}&cours="
    url = BASE_URL.format(week)
    gehol_slugs = map(lambda x: x.gehol, slugs)
    url = BASE_URL + '-'.join(gehol_slugs)

    txt = requests.get(url).text
    soup = BeautifulSoup(txt)

    # When a course is not given on a week or quadri, gehol redirects you internaly
    # to the current week. We want to avoid that
    possible_weeks = soup.find(id="FormSemaineUnif").findAll('option')
    possible_weeks = map(lambda x: x['value'], possible_weeks)

    if week not in possible_weeks or week == 0:
        return []

    events = soup.findAll("div", class_="activity")

    events = map(parse_event, events)
    events = map(prettify_event, events)
    return list(events)


def get_events(*slugs):
    # Get the 1st quadri (weeks 1-14) and second (21-35)
    return get_events_for_week("114", *slugs) + get_events_for_week("2135", *slugs)
