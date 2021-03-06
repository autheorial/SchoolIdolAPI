# -*- coding: utf-8 -*-
import sys, datetime, operator
from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group
from django.db.models import Count, Q
from django.utils.formats import date_format
from django.utils import timezone
from api import models

def birthdays_within(days_after, days_before=0, field_name='birthday'):
    now = timezone.now()
    after = now - datetime.timedelta(days=days_before)
    before = now + datetime.timedelta(days=days_after)

    monthdays = [(now.month, now.day)]
    while after <= before:
        monthdays.append((after.month, after.day))
        after += datetime.timedelta(days=1)

    # Tranform each into queryset keyword args.
    monthdays = (dict(zip((
        u'{}__month'.format(field_name),
        u'{}__day'.format(field_name),
    ), t)) for t in monthdays)

    # Compose the djano.db.models.Q objects together for a single query.
    return reduce(operator.or_, (Q(**d) for d in monthdays))

def get_next_birthday(birthday):
    today = datetime.date.today()

    is_feb29 = False
    if birthday.month == 2 and birthday.day == 29:
        is_feb29 = True
        birthday = birthday.replace(
            month=user.preferences.birthdate.month + 1,
            day=1,
        )

    birthday = birthday.replace(year=today.year)
    if birthday < today:
        birthday = birthday.replace(year=today.year + 1)

    if is_feb29:
        try: birthday = birthday.replace(month=2, day=29)
        except ValueError: pass

    return birthday

def print_top(hashtag, winners, id, print_message_between=False):
    activities = models.Activity.objects.filter(id__gt=id, message_data__icontains=hashtag).annotate(total_likes=Count('likes')).select_related('account', 'account__owner').order_by('-total_likes')
    top = 0
    prev = -1
    has_printed = False
    to_print_at_the_end_for_form = []
    for activity in activities:
        if activity.total_likes != prev:
            top += 1
            prev = activity.total_likes
        if top > winners:
            if print_message_between and not has_printed:
                print '***'
                print ''
                print '**Don\'t see your name?** Don\'t worry, our staff team will go through all the activities and pick 1 more winner based on creativity, originality, effort and passion.'
                print ''
                print '***'
                print ''
                print 'Participants:'
                print ''
                has_printed = True
            if print_message_between:
                to_print_at_the_end_for_form.append(activity)
                sys.stdout.write(u'[{}](http://schoolido.lu/activities/{}/), '.format(activity.account.owner.username, activity.id))
            else:
                print u'{} - http://schoolido.lu/activities/{}/'.format(activity.account.owner.username, activity.id)
            continue
        print '### #{} [{}](http://schoolido.lu/user/{}/)'.format(
            top,
            activity.account.owner.username,
            activity.account.owner.username,
        )
        print ''
        print '    {} likes'.format(activity.total_likes + 1)
        print ''
        print '[See original activity](http://schoolido.lu/activities/{}/)'.format(
            activity.id
        )
        try:
            print ''
            print u'![{})'.format(activity.message_data.split('![')[1].split(')')[0])
            print ''
        except IndexError:
            pass
        print ''

    if print_message_between:
        sys.stdout.flush()

        print ''
        print ''
        print '***'
        print ''
        print '# **Support our giveaways!**'
        print ''
        print 'These giveaways are made possible thanks to the support of our warm-hearted donators. If you wish to support School Idol Tomodachi for both our future giveaways and to cover the cost of our expensive servers in which our site run, please consider [donating on Patreon](http://patreon.com/db0company).'
        print ''
        print '[![Support us on Patreon](https://i.imgur.com/YYwkEhP.png)](http://patreon.com/db0company)'
        print ''
        print '***'
        print ''

        print '# FAQ'
        print ''
        print '- **I won and I didn\'t hear from you?**'
        print '    - Check [private messages from db0](https://schoolido.lu/user/db0/messages/). You may have to wait up to 24 hours after announcement.'
        print '- **Do I have to pay for shipping?**'
        print '    - No'
        print '- **When can I expect to get my prize?**'
        print '    - It can take between 2 weeks and 4 months after the announcement.'
        print '- **I didn\'t win and I\'m sad ;_;**'
        print '    - Sorry :( Regardless, the staff and the community loved your entry so your efforts didn\'t go to waste at all <3 Please join our next giveaway to try again!'
        print '- **How can  I thank you for your amazing work organizing these giveaways?**'
        print '    - We always appreciate sweet comments below, and if you want to push it a little further, we have a [Patreon](https://patreon.com/db0company/) open for donations <3'
        print ''
        print '***'
        print ''
        print '## What did you think about this contest?'
        print ''
        print 'We want to hear from you! Based on your opinion, we may or may not organize a similar contest next year.'
        print ''
        print u'→ [Take the survey!](https://goo.gl/forms/PVErf176nH0LX9go2)'
        print ''
        print u'Thank you ♥️'
        print ''
        print '***'
        print ''
        print 'We\'re looking for judges. [Learn more](https://goo.gl/forms/42sCU6SXnKbqnag23)'
        print ''
        print '***'
        print ''
        print '[See giveaway details](https://schoolido.lu/activities/{}/)'.format(id)
        print ''
        print '###### {}'.format(hashtag)
        print ''
        print '--------- END OF POST TO COPY'
        print ''
        print ''


        for activity in to_print_at_the_end_for_form:
            print u'{} - http://schoolido.lu/activities/{}/'.format(activity.account.owner.username, activity.id)


class Command(BaseCommand):
    can_import_settings = True

    def handle(self, *args, **options):

        if len(args) < 3:
            print 'Specify giveaway hashtag, number of winners and id of giveaway details'
            return
        hashtag = args[0]
        winners = int(args[1])
        id = int(args[2])
        current_giveaway = models.Activity.objects.get(id=id)

        birthday_idols = models.Idol.objects.filter(
            main=True,
        ).filter(birthdays_within(days_after=50, days_before=16))

        today = datetime.date.today()
        in_51_days = today + relativedelta(days=51)
        ended_recently = []
        still_running_giveaways = []
        coming_soon_giveaways = []

        for idol in birthday_idols:
            giveaway_tag = u'{}BirthdayGiveaway2018'.format(idol.short_name)
            if giveaway_tag == hashtag:
                # Current giveaway idol
                continue
            giveaway_posts = models.Activity.objects.filter(message_data__icontains=giveaway_tag, account_id__in=[1]).order_by('id')
            try:
                giveaway_details = giveaway_posts.filter(message_data__icontains='How to enter?')[0]
            except IndexError:
                giveaway_details = None
            try:
                giveaway_ended_post = giveaway_posts.filter(message_data__icontains='See giveaway details')[0]
                ended_recently.append((idol, giveaway_ended_post))
            except IndexError:
                giveaway_ended_post = None

            if giveaway_details and not giveaway_ended_post:
                still_running_giveaways.append((idol, giveaway_details))

            if not giveaway_details:
                coming_soon_giveaways.append(idol)

            next_birthday = get_next_birthday(idol.birthday)
            if next_birthday >= in_51_days and not giveaway_details:
                print '!! Warning:', idol.name, 'giveaway should have been organized already!'

        print_top(hashtag, winners, id)
        activities = models.Activity.objects.filter(id__gt=id, message_data__icontains=hashtag).annotate(total_likes=Count('likes'))
        for activity in activities:
            print '## Activity http://schoolido.lu/activities/{}/'.format(activity.id)
            print '  Total likes: {}'.format(activity.total_likes)
            print '  Cheat likes: ',
            sys.stdout.flush()
            total_cheat = 0
            for user in activity.likes.all().select_related('preferences'):
                total_accounts = user.accounts_set.all().count()
                if (False and (total_accounts == 0
                     or (total_accounts == 1 and user.accounts_set.all()[0].ownedcards.count() <= 1))
                    and not user.preferences.description
                    and not models.Activity.objects.filter(account__owner=user, message_type=models.ACTIVITY_TYPE_CUSTOM).count()
                    and not user.links.all().count()
                ):
                    print user.username, ', ',
                    sys.stdout.flush()
                    activity.likes.remove(user)
                    total_cheat += 1
            if total_cheat:
                activity.save()
            print ''
            print '  Total cheat likes: {}'.format(total_cheat)
            print '  Total remaining likes: {}'.format(activity.total_likes - total_cheat)

        print ''
        print '--------- START OF POST TO COPY'
        print ''

        print current_giveaway.message_data.split('\n# **Support our giveaways!**')[0]
        print '# Congratulations to our winners!'
        print ''
        print 'They will receive a prize of their choice among the {current_idol}-themed goodies we offer. You can see the list of prizes with pictures in [the original giveaway post](https://schoolido.lu/activities/{current_giveaway_id}/).'.format(
            current_idol=hashtag.split('BirthdayGiveaway')[0],
            current_giveaway_id=id,
        )
        print ''
        print 'Thanks to everyone who participated and helped make this contest a success!'
        if still_running_giveaways:
            print ''
            print 'Stay tuned for the winners of',
            print u'{} that will be announced soon!'.format(u' and '.join([
                u'[{idol_name}\'s Birthday giveaway](https://schoolido.lu/activities/{id}/)'.format(
                    idol_name=idol.name, id=giveaway.id,
                )
                for idol, giveaway in still_running_giveaways
            ]))
            print ''

        if coming_soon_giveaways:
            print ''
            print 'The birthday{} of {} {} coming soon, so look forward to that as well!'.format(
                '' if len(coming_soon_giveaways) == 1 else 's',
                ' and '.join([
                    u'{} ({})'.format(
                        idol.name,
                        date_format(idol.birthday, format='MONTH_DAY_FORMAT', use_l10n=True),
                    )
                    for idol in coming_soon_giveaways
                ]),
                'is' if len(coming_soon_giveaways) == 1 else 'are'
            )

        print ''
        print '***'
        print ''
        print '## Winners'
        print ''

        print_top(hashtag, winners, id, print_message_between=True)
