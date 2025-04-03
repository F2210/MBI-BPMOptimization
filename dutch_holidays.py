def check_if_holiday(hour):
    # Holidays derived from https://www.officeholidays.com/countries/netherlands/2018

    # Monday January 1st: New Year's Day
    if hour >= 0 and hour < 24:
        return True

    # Friday March 30st: Good Friday
    if hour >= 2112 and hour < 2112 + 24:
        return True

    # Sunday April 1st: Easter Day
    if hour >= 2160 and hour < 2160 + 24:
        return True

    # Monday April 2nd: Easter Monday
    if hour >= 2184 and hour < 2184 + 24:
        return True

    # Friday April 27th: Kingsday
    if hour >= 2784 and hour < 2784 + 24:
        return True

    # Saturday May 5th: Liberation Day
    if hour >= 2976 and hour < 2975 + 24:
        return True

    # Thursday May 10: Ascension Day
    if hour >= 3096 and hour < 3096 + 24:
        return True

    # Sunday May 20: Pentecost Sunday
    if hour >= 3336 and hour < 3336 + 24:
        return True

    # Monday May 21: Whit Monday
    if hour >= 3360 and hour < 3360 + 24:
        return True

    # Tuesday December 25th: Christmas Day 1
    if hour >= 8592 and hour < 8592 + 24:
        return True

    # Thursday December 26th: Christmas Day 2
    if hour >= 8616 and hour < 8616 + 24:
        return True

    return False
