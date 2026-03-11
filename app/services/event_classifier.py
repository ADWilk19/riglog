from datetime import datetime, time

def classify_meal_event(dt: datetime) -> str:
    t = dt.time()

    if time(6, 30) <= t <= time(8, 29):
        return "pre_breakfast"
    elif time(8, 30) <= t <= time(11, 29):
        return "post_breakfast"
    elif time(11, 30) <= t <= time(13, 29):
        return "pre_lunch"
    elif time(13, 30) <= t <= time(16, 29):
        return "post_lunch"
    elif time(16, 30) <= t <= time(18, 29):
        return "pre_dinner"
    elif time(18, 30) <= t <= time(21, 29):
        return "post_dinner"
    elif time(21, 30) <= t <= time(23, 0):
        return "before_bed"
    else:
        return "night"
