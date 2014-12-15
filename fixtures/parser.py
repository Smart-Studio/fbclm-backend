import urllib
import urllib2

from bs4 import BeautifulSoup
from django.db.transaction import atomic

from models import Season, League, Group, SubGroup


FIXTURES_URL = 'http://www.fbclm.net/dinamico/competiciones/competiciones.asp'

# Parser tags
NAME_ATTRIBUTE = 'name'
SELECTORS_HTML_TAG = 'table'
VALUE_ATTR = 'value'

# Headers
ACCEPT_ENCODING = 'Accept-Encoding'
ENCODING = 'gzip, deflate'
ACCEPT_LANGUAGE = 'Accept-Language'
LANGUAGE = 'en,en-US;q=0.8,es;q=0.6'
CACHE_CONTROL = 'Cache-Control'
CACHE = 'max-age=0'
CONNECTION = 'Connection'
KEEP_ALIVE = 'keep-alive'
CONTENT_TYPE = 'Content-Type'
X_WWW_FORM = 'application/x-www-form-urlencoded'
COOKIE = 'Cookie'
COOKIE_VALUE = 'ASPSESSIONIDQCTBBBCC=BEHNECLDNOFKEEIIPKIADEID; ASPSESSIONIDQCRCCBCB=KBEBFPHAGCGJPOBNENOGIACM'
HOST = 'Host'
HOST_VALUE = 'www.fbclm.net'
ORIGIN = 'Origin'
ORIGIN_VALUE = 'http://www.fbclm.net'
REFERER = 'Referer'

# Form parameters
LOGIN = 'login'
PASS = 'pass'
NEWS_ID = 'id_noticia'
NEWS_TYPE_ID = 'id_tipo_noticia'
MATCH_ID = 'id_partido'
ONLINE = 'online'
SEASON_ID = 'id_temporada'
LEAGUE_ID = 'agrupacion'
CATEGORY_ID = 'id_categoria'
GROUP_ID = 'id_grupo'
MATCH_DAY_ID = 'id_jornada'


def parse_fixtures():
    content = urllib2.urlopen(FIXTURES_URL).read()
    parsed_html = BeautifulSoup(content)
    selectors_html = parsed_html.find(SELECTORS_HTML_TAG)
    seasons_html = selectors_html.find(attrs={NAME_ATTRIBUTE: SEASON_ID})

    print parse_seasons(seasons_html)


@atomic
def parse_seasons(seasons_html):
    for season_html in seasons_html:
        season_id = season_html[VALUE_ATTR]
        season_name = season_html.string
        season = Season.objects.filter(season_name=season_name)

        if season.exists():
            season = season[0]
        else:
            season = Season(season_name=season_html.string)
            season.save()

        season_html = request_seasons_html(season_id=season_id)

        parse_leagues(season, season_id, season_html)

        if season.league_set.count() == 0:
            season.delete()


def parse_leagues(season, season_id, season_html):
    leagues_html = season_html.find(attrs={NAME_ATTRIBUTE: LEAGUE_ID})
    for league_html in leagues_html:
        league_name = league_html.string
        if league_name:
            league_id = league_html[VALUE_ATTR]
            league_name = unicode(league_name)
            league = League.objects.filter(name=league_name, season=season.id)

            if league.exists():
                league = league[0]
            else:
                league = season.league_set.create(name=league_name)

            if league_id:
                league_html = request_league_html(season_id=season_id, league_id=league_id)
                # print season.season_name + " " + league.name + '\n'
                parse_groups(season_id, league, league_id, league_html)


def parse_groups(season_id, league, league_id, league_html):
    groups_html = league_html.find(attrs={NAME_ATTRIBUTE: GROUP_ID})

    if len(groups_html.contents) > 1:
        create_group(season_id, league, league_id, groups_html, False)
    else:
        groups_html = league_html.find(attrs={NAME_ATTRIBUTE: CATEGORY_ID})
        create_group(season_id, league, league_id, groups_html, True)


def create_group(season_id, league, league_id, groups_html, has_subgroups):
    for group_html in groups_html.contents[1:]:
        group_id = group_html[VALUE_ATTR]
        group_name = unicode(group_html.string)

        group = Group.objects.filter(league_id=league.id, name=group_name)

        if group.exists():
            group = group[0]
        else:
            group = league.group_set.create(name=group_name)

        if has_subgroups:
            group_html = request_area_html(season_id, league_id, group_id)
            parse_subgroups(group, group_id, group_html)


def parse_subgroups(group, group_id, group_html):
    subgroups_html = group_html.find(attrs={NAME_ATTRIBUTE: GROUP_ID})
    for subgroup_html in subgroups_html.contents[1:]:
        subgroup_id = subgroup_html[VALUE_ATTR]
        subgroup_name = unicode(subgroup_html.string)

        subgroup = SubGroup.objects.filter(group_id=group_id, name=subgroup_name)

        if subgroup.exists():
            subgroup = subgroup[0]
        else:
            subgroup = group.subgroup_set.create(name=subgroup_name)


def request_seasons_html(season_id):
    return request_web_page(season_id=season_id, league_id=0, category_id=0, group_id=0)


def request_league_html(season_id, league_id):
    return request_web_page(season_id=season_id, league_id=league_id, category_id=0, group_id=0)


def request_area_html(season_id, league_id, category_id):
    return request_web_page(season_id=season_id, league_id=league_id, category_id=category_id, group_id=0)


def request_group_html(season_id, league_id, group_id):
    return request_web_page(season_id=season_id, league_id=league_id, category_id=0, group_id=group_id)


def request_web_page(season_id, league_id, category_id, group_id):
    headers = {ACCEPT_ENCODING: ENCODING,
               ACCEPT_LANGUAGE: LANGUAGE,
               CACHE_CONTROL: CACHE,
               CONNECTION: KEEP_ALIVE,
               CONTENT_TYPE: X_WWW_FORM,
               COOKIE: COOKIE_VALUE,
               HOST: HOST_VALUE,
               ORIGIN: ORIGIN_VALUE,
               REFERER: FIXTURES_URL}

    values = {LOGIN: '',
              PASS: '',
              NEWS_ID: 0,
              NEWS_TYPE_ID: 0,
              MATCH_ID: 0,
              ONLINE: 1,
              SEASON_ID: season_id,
              LEAGUE_ID: league_id,
              CATEGORY_ID: category_id,
              GROUP_ID: group_id,
              MATCH_DAY_ID: 0}

    data = urllib.urlencode(values)
    request = urllib2.Request(FIXTURES_URL, data, headers)
    response = urllib2.urlopen(request)
    return BeautifulSoup(response.read())