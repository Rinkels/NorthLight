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
