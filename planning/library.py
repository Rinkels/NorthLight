"""Starting-point samples for the hardest blank boxes in the product.

A North Light is directional and personal; a blank textarea is the worst way
to begin one. Each default area gets a few sample (North Light, Why) pairs the
user can start from and then edit. Custom areas get the general set. Samples
are suggestions only: nothing here is ever written without the user choosing it.
"""
from __future__ import annotations

GENERAL_KEY = ""

NORTH_LIGHT_SAMPLES: dict[str, list[tuple[str, str]]] = {
    "health": [
        ("Remain healthy, capable and energetic enough that age does not unnecessarily restrict what I can do.",
         "Freedom and independence."),
        ("Feel strong and rested most days, with energy left over for the people and things I care about.",
         "Everything else in my life runs on this."),
        ("Treat my body as something to look after for the long run, not something to fix in bursts.",
         "I want to still be doing the things I love at 80."),
    ],
    "relationships": [
        ("Stay genuinely close to the people who matter most.",
         "Connection with people who matter."),
        ("Be present and reliable for my partner and family, in ordinary weeks and not only on big occasions.",
         "These relationships are what I will remember."),
        ("Keep a home where people feel safe, heard and welcome.",
         "Belonging matters more to me than achievement."),
    ],
    "friends": [
        ("Have a small circle of friends I see regularly and can call on without hesitation.",
         "Friendship needs tending or it quietly fades."),
        ("Be part of a community where I contribute and am known.",
         "I want to belong somewhere beyond work and family."),
        ("Keep old friendships alive across distance, and stay open to new ones.",
         "Good company makes a good life."),
    ],
    "work": [
        ("Do interesting, useful and intellectually challenging work with considerable autonomy.",
         "Autonomy and mastery."),
        ("Be excellent at something that matters, and be recognised for it by people I respect.",
         "Craft and contribution give my work meaning."),
        ("Work in a way that leaves room for the rest of my life.",
         "Work should serve my life, not the other way around."),
    ],
    "finance": [
        ("Build enough financial independence that paid work increasingly becomes a choice rather than a requirement.",
         "Choice and control over my time."),
        ("Live comfortably within my means, with a buffer that means a surprise is an inconvenience, not a crisis.",
         "Security lets me make decisions calmly."),
        ("Be deliberate about money: know where it goes and let it fund what I actually value.",
         "Money is a tool for the life I want, not a scoreboard."),
    ],
    "time": [
        ("Have real control over my calendar, with unhurried time most weeks.",
         "Time is the one resource I cannot earn back."),
        ("Keep enough slack in my life that I can say yes to what matters and no to what does not.",
         "A full diary is not the same as a full life."),
        ("Protect regular blocks of time that are mine, for thinking, rest and play.",
         "I do my best living and thinking when I am not rushed."),
    ],
    "learning": [
        ("Keep learning deliberately, so I am more capable and more curious each year than the last.",
         "Growth keeps life interesting."),
        ("Go deep in a few subjects rather than shallow in many.",
         "Mastery is more satisfying than familiarity."),
        ("Stay a beginner at something, always.",
         "Humility and curiosity keep me open."),
    ],
    "creating": [
        ("Regularly turn ideas into real things.",
         "Expression, curiosity and the enjoyment of building."),
        ("Finish what I start, and ship work I am proud of into the world.",
         "Making things is how I think and how I leave a mark."),
        ("Keep a creative practice that is mine, separate from work and its demands.",
         "Creating for its own sake keeps me whole."),
    ],
    "fun": [
        ("Have genuinely memorable experiences every year, not just a busy year.",
         "I want a life I can look back on with delight."),
        ("Keep play, humour and adventure in ordinary weeks, not only on holiday.",
         "Joy is a habit, not an event."),
        ("Explore new places and try new things while I can.",
         "Novelty keeps me alive and grateful."),
    ],
    "purpose": [
        ("Contribute to something larger than myself in a way that uses what I am good at.",
         "Meaning comes from being useful to others."),
        ("Live in line with my values, so that what I do and what I believe match.",
         "Integrity is the foundation of a life I respect."),
        ("Leave the people and places I touch a little better than I found them.",
         "This is what I want to be remembered for."),
    ],
    GENERAL_KEY: [
        ("Have this part of my life feel settled, healthy and genuinely mine.",
         "It matters to me, and I want to give it deliberate attention."),
        ("Reach a point here where I feel quietly proud rather than anxious.",
         "Peace of mind is worth more than a perfect score."),
        ("Keep what already works here, and improve one thing at a time.",
         "Steady attention beats occasional heroics."),
    ],
}


def samples_for(template_key: str) -> list[tuple[str, str]]:
    return NORTH_LIGHT_SAMPLES.get(template_key) or NORTH_LIGHT_SAMPLES[GENERAL_KEY]


# --------------------------------------------------------------------------- #
# Goal suggestions — offered only for areas the user has marked Improve.
# Baseline and target are deliberately absent: the user must make them concrete.
# --------------------------------------------------------------------------- #

GOAL_SAMPLES: dict[str, list[dict]] = {
    "health": [
        {"title": "Reach and hold a healthy weight", "goal_type": "outcome", "target_unit": "kg",
         "description": "Set a baseline from today's weight and a target you can hold, not a crash number."},
        {"title": "Train consistently every week", "goal_type": "process", "target_unit": "sessions per week",
         "description": "The behaviour you control. Pair it with a habit."},
        {"title": "Complete a health check-up and act on it", "goal_type": "milestone", "target_unit": "",
         "description": "One discrete event that removes uncertainty."},
    ],
    "relationships": [
        {"title": "Regular one-to-one time with each person who matters", "goal_type": "process", "target_unit": "times per month",
         "description": "Ordinary weeks, not just occasions."},
        {"title": "A shared trip or experience together", "goal_type": "experience", "target_unit": "",
         "description": "Something you will still talk about in ten years."},
        {"title": "Keep the weekly family ritual intact", "goal_type": "maintenance", "target_unit": "",
         "description": "Protecting what already works is a legitimate goal."},
    ],
    "friends": [
        {"title": "See close friends in person regularly", "goal_type": "process", "target_unit": "meet-ups per month",
         "description": "Frequency matters more than grand plans."},
        {"title": "Join or re-join a community and show up", "goal_type": "milestone", "target_unit": "",
         "description": "A club, a team, a group that meets."},
        {"title": "Host people at home", "goal_type": "process", "target_unit": "times this year",
         "description": "Being the one who invites."},
    ],
    "work": [
        {"title": "Reach the next level of role, responsibility or income", "goal_type": "outcome", "target_unit": "",
         "description": "Name the specific step and what would prove it."},
        {"title": "Ship one piece of work you are genuinely proud of", "goal_type": "milestone", "target_unit": "",
         "description": "Finished, visible, yours."},
        {"title": "Protect deep-work time every week", "goal_type": "process", "target_unit": "hours per week",
         "description": "Blocks in the calendar that survive the week."},
    ],
    "finance": [
        {"title": "Grow savings or investments to a target", "goal_type": "outcome", "target_unit": "$",
         "description": "Baseline is today's balance; the target is the number that would feel different."},
        {"title": "Invest a fixed amount every month", "goal_type": "process", "target_unit": "$ per month",
         "description": "The process goal that drives the outcome."},
        {"title": "Clear a specific debt", "goal_type": "outcome", "target_unit": "$",
         "description": "A decreasing target: baseline is what you owe now, target is zero."},
    ],
    "time": [
        {"title": "Keep one weekday evening and one weekend day free each week", "goal_type": "maintenance", "target_unit": "",
         "description": "Something to protect rather than improve."},
        {"title": "Cut recurring commitments that no longer earn their place", "goal_type": "milestone", "target_unit": "",
         "description": "One deliberate pruning pass."},
        {"title": "Take real holidays, fully offline", "goal_type": "experience", "target_unit": "weeks",
         "description": "Count the weeks, not the intentions."},
    ],
    "learning": [
        {"title": "Complete a course or qualification", "goal_type": "milestone", "target_unit": "",
         "description": "One finished thing, not five started ones."},
        {"title": "Read deliberately", "goal_type": "process", "target_unit": "books",
         "description": "Pick a number you would actually enjoy."},
        {"title": "Practise a skill every week", "goal_type": "process", "target_unit": "hours per week",
         "description": "An instrument, a language, a craft."},
    ],
    "creating": [
        {"title": "Finish and release one project", "goal_type": "milestone", "target_unit": "",
         "description": "Done and out in the world beats perfect and private."},
        {"title": "Keep a regular making practice", "goal_type": "process", "target_unit": "sessions per week",
         "description": "Small, regular, protected."},
        {"title": "Share work publicly", "goal_type": "process", "target_unit": "pieces",
         "description": "Posts, prints, performances, releases."},
    ],
    "fun": [
        {"title": "Four genuinely memorable experiences this year", "goal_type": "experience", "target_unit": "experiences",
         "description": "Decide what counts before the year starts."},
        {"title": "Try something completely new", "goal_type": "milestone", "target_unit": "",
         "description": "A sport, a place, a skill you have never tried."},
        {"title": "A weekly slot for play", "goal_type": "maintenance", "target_unit": "",
         "description": "Games, sport, music, whatever is purely for enjoyment."},
    ],
    "purpose": [
        {"title": "Give time regularly to a cause that matters", "goal_type": "process", "target_unit": "hours per month",
         "description": "Consistency over grand gestures."},
        {"title": "Write down what you stand for and revisit it", "goal_type": "milestone", "target_unit": "",
         "description": "A page, not a manifesto."},
        {"title": "Mentor or help someone specific", "goal_type": "outcome", "target_unit": "",
         "description": "Name the person and what better looks like for them."},
    ],
    GENERAL_KEY: [
        {"title": "One measurable improvement in this area", "goal_type": "outcome", "target_unit": "",
         "description": "Pick the single number or fact that would show this area is better."},
        {"title": "A weekly practice that moves this area forward", "goal_type": "process", "target_unit": "times per week",
         "description": "The behaviour you control."},
        {"title": "Keep what already works here", "goal_type": "maintenance", "target_unit": "",
         "description": "Protecting is legitimate."},
    ],
}


def goal_samples_for(template_key: str) -> list[dict]:
    return GOAL_SAMPLES.get(template_key) or GOAL_SAMPLES[GENERAL_KEY]
