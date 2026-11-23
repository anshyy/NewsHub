"""Keyword-based automatic classification. Each category/sub-category has a keyword set; an article
scores +3 per title hit, +1 per description hit (+2 for the feed's category hint). The highest
score wins. Time: O(T + C*K) per article (T tokens, C categories, K keywords via set lookups)."""
from algorithms import tokenize

CATEGORY_COLORS = {"Technology": "#0D9488", "Business": "#F59E0B", "Sports": "#16A34A", "Politics": "#DC2626",
                   "Science": "#8B5CF6", "Entertainment": "#EC4899", "Health": "#0EA5E9", "World": "#3B82F6"}

_K = lambda s: set(s.split())
KEYWORDS = {
 "Technology": _K("ai tech technology software app apps google apple microsoft meta amazon openai chatgpt chip chips semiconductor nvidia startup startups cyber hackers hacker data internet smartphone iphone android robot robots algorithm cloud computing computer digital online tiktok facebook instagram youtube gadget laptop battery tesla quantum crypto bitcoin blockchain gaming xbox playstation"),
 "Business": _K("business economy economic market markets stocks shares stock investors investor bank banks banking inflation profit profits revenue sales company companies ceo trade tariff tariffs tax finance financial gdp rupee dollar oil prices price jobs unemployment merger acquisition retail growth earnings fund funding billion"),
 "Sports": _K("sport sports football cricket tennis match cup league goal goals team coach player players olympic olympics fifa nba nfl ipl champion championship tournament beat defeat striker race f1 formula golf rugby boxing athlete medal final batting bowler wicket innings premier"),
 "Politics": _K("election elections vote voters voting president minister government parliament congress senate trump biden modi party parties democrat republican opposition campaign policy bill lawmakers mp mps legislation labour tory conservative cabinet prime political politics governor mayor court supreme judge ruling"),
 "Science": _K("science scientists scientist research study researchers space nasa planet climate species earth astronomy physics chemistry biology discovery telescope moon mars fossil dinosaur ocean energy environment carbon warming emissions mission satellite rocket asteroid experiment"),
 "Entertainment": _K("film films movie movies actor actress celebrity music album singer song concert festival oscar oscars bollywood hollywood netflix series show tv television star stars director box office theatre award awards band musician drama comedy trailer"),
 "Health": _K("health hospital hospitals doctor doctors disease cancer virus vaccine patients patient nhs medical medicine treatment drug drugs mental covid diet obesity surgery cure symptoms clinic outbreak pandemic wellbeing fitness"),
 "World": _K("war ukraine russia gaza israel china nations un conflict ceasefire troops military refugees border embassy diplomat summit global international attack killed sanctions europe africa asia"),
}

SUBCATEGORIES = {
 "Technology": {"AI": "ai openai chatgpt chatbot model models learning llm", "Cybersecurity": "cyber hack hacker hackers breach security ransomware privacy malware",
                "Gadgets": "iphone android smartphone phone laptop device gadget battery chip chips", "Software & Internet": "software app apps internet online platform social tiktok facebook instagram google microsoft"},
 "Business": {"Markets": "market markets stocks shares stock investors index bitcoin crypto", "Companies": "company companies ceo merger acquisition startup startups profit revenue",
              "Economy": "economy inflation gdp trade tariff tariffs jobs unemployment bank rates tax"},
 "Sports": {"Cricket": "cricket ipl wicket batting bowler innings test odi", "Football": "football fifa premier league striker goal goals club",
            "Tennis": "tennis wimbledon slam atp wta", "Other Sports": "olympic olympics f1 formula golf rugby boxing nba nfl athlete medal"},
 "Politics": {"Elections": "election elections vote voters voting poll polls campaign ballot candidate", "Government": "government minister parliament cabinet president congress senate policy bill",
              "Law & Courts": "court judge supreme ruling law legal trial"},
 "Science": {"Space": "space nasa planet moon mars telescope rocket satellite asteroid astronomy", "Environment": "climate environment carbon warming emissions ocean species energy",
             "Research": "study research researchers scientists discovery experiment physics biology"},
 "Entertainment": {"Movies": "film films movie movies actor actress oscar oscars bollywood hollywood director box office trailer", "Music": "music album singer song concert band musician festival",
                   "Television": "tv television series show netflix drama streaming"},
 "Health": {"Medicine": "doctor doctors disease cancer drug drugs treatment surgery patients hospital vaccine", "Wellness": "diet fitness mental wellbeing sleep obesity exercise",
            "Public Health": "nhs outbreak virus pandemic covid health public"},
 "World": {"Asia": "china india japan korea pakistan asia taiwan delhi beijing", "Europe": "europe eu uk britain france germany ukraine russia london",
           "Middle East": "israel gaza iran iraq syria lebanon saudi yemen middle", "Americas": "american americans canada mexico brazil washington argentina",
           "Africa": "africa nigeria kenya sudan egypt ethiopia"},
}
SUBCATEGORIES = {c: {s: _K(k) for s, k in d.items()} for c, d in SUBCATEGORIES.items()}
HIERARCHY = {c: list(d) for c, d in SUBCATEGORIES.items()}

def _score(kw, title_t, desc_t):
    return sum(3 for w in title_t if w in kw) + sum(1 for w in desc_t if w in kw)

def classify(title, desc="", hint=None):
    """Return (category, subcategory)."""
    tt, dt = tokenize(title), tokenize(desc)
    scores = {c: _score(k, tt, dt) + (2 if c == hint else 0) for c, k in KEYWORDS.items()}
    cat = max(scores, key=scores.get)
    if scores[cat] == 0:
        cat = hint if hint in KEYWORDS else "World"
    subs = {s: _score(k, tt, dt) for s, k in SUBCATEGORIES[cat].items()}
    sub = max(subs, key=subs.get)
    return cat, (sub if subs[sub] > 0 else "General")
