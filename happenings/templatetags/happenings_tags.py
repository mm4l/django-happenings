from __future__ import unicode_literals

import heapq

from django.template import Library
from django.conf import settings
from django.utils import timezone

from happenings.utils.upcoming import UpcomingEvents
from happenings.models import Event
from happenings.utils.displays import month_display
from happenings.utils.common import (
    get_net_category_tag,
    get_qs,
    clean_year_month,
    now
)

register = Library()
start_day = getattr(settings, "CALENDAR_START_DAY", 0)


@register.simple_tag
def show_calendar(req, mini=False):
    net, category, tag = get_net_category_tag(req)
    year = now.year
    month = now.month + net
    year, month, error = clean_year_month(year, month, None)

    prefetch = {'loc': True, 'cncl': True}
    if mini:
        prefetch['loc'] = False  # locations aren't displayed on mini calendar

    all_month_events = list(Event.objects.all_month_events(
        year, month, category, tag, **prefetch
    ))
    all_month_events.sort(key=lambda x: x.l_start_date.hour)
    qs = req.META['QUERY_STRING']
    if qs:  # get any querystrings that are not next/prev
        qs = get_qs(qs)
    return month_display(
        year, month, all_month_events, start_day, net, qs, mini=mini
    )


@register.inclusion_tag('happenings/partials/upcoming_events.html')
def upcoming_events(now=timezone.localtime(timezone.now()), finish=90, num=5):
    return {
        'upcoming_events': _get_the_events(now, finish, num, happenings=False)
    }


@register.inclusion_tag('happenings/partials/happening_events.html')
def current_happenings(now=timezone.localtime(timezone.now())):
    temp = now
    drepl = lambda x: temp.replace(  # replace hr, min, sec, msec of 'now'
        hour=x.l_start_date.hour,
        minute=x.l_start_date.minute,
        second=x.l_start_date.second,
        microsecond=x.l_start_date.microsecond
    )
    the_haps = (
        (drepl(x), x) for x in Event.objects.live(now) if x.is_happening(now)
    )
    return {'upcoming_events': the_haps}


def _get_the_events(now, finish, num, happenings):
    if finish is not 0:
        finish = now + timezone.timedelta(days=finish)
        finish = finish.replace(hour=23, minute=59, second=59, microsecond=999)
    else:
        happenings = True
    all_upcoming = (
        UpcomingEvents(
            x, now, finish, num, happenings=happenings
        ).get_upcoming_events() for x in Event.objects.live(now)
    )  # list comp
    the_events = heapq.nsmallest(
        num,
        (item for sublist in all_upcoming for item in sublist),
        key=lambda x: x[0]
    )
    return the_events
