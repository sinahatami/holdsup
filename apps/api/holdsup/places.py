"""Place names to the codes a claim spec uses.

The extraction model is told to answer with a code, but sometimes writes the name ("Italy"),
a demonym ("Italian") or a common short form ("the UK", "America"). Code reads those instead
of dropping the claim for naming no place. A name that fits two places (Korea, Congo, Georgia)
is left out on purpose: no place beats a wrong one.
"""

import re
import unicodedata

from holdsup.geo import ISO2, ISO3

# Codes that are not countries (the claim spec's groups).
GEO_GROUPS = frozenset({"EU", "EA", "WORLD", "G7", "G20", "OECD"})
# Other spellings of a code.
GEO_ALIASES = {
    "UK": "GB",
    "EL": "GR",
    "EU27": "EU",
    "EU27_2020": "EU",
    "EZ": "EA",
    "EA19": "EA",
    "EA20": "EA",
    "WLD": "WORLD",
}

# code: the names people use for the place, its demonyms and short forms. Written plainly;
# `_key` folds case, accents, punctuation and a leading "the" when they are looked up.
_NAMES: dict[str, tuple[str, ...]] = {
    "AL": ("Albania", "Albanian"),
    "AM": ("Armenia", "Armenian"),
    "AR": ("Argentina", "Argentine", "Argentinian"),
    "AT": ("Austria", "Austrian"),
    "AU": ("Australia", "Australian"),
    "AZ": ("Azerbaijan", "Azerbaijani"),
    "BA": ("Bosnia", "Bosnia and Herzegovina", "Bosnian"),
    "BD": ("Bangladesh", "Bangladeshi"),
    "BE": ("Belgium", "Belgian"),
    "BG": ("Bulgaria", "Bulgarian"),
    "BO": ("Bolivia", "Bolivian"),
    "BR": ("Brazil", "Brazilian"),
    "BY": ("Belarus", "Belarusian"),
    "CA": ("Canada", "Canadian"),
    "CH": ("Switzerland", "Swiss"),
    "CL": ("Chile", "Chilean"),
    "CM": ("Cameroon", "Cameroonian"),
    "CN": ("China", "Chinese", "People's Republic of China", "PRC"),
    "CO": ("Colombia", "Colombian"),
    "CR": ("Costa Rica", "Costa Rican"),
    "CU": ("Cuba", "Cuban"),
    "CY": ("Cyprus", "Cypriot"),
    "CZ": ("Czechia", "Czech Republic", "Czech"),
    "DE": ("Germany", "German"),
    "DK": ("Denmark", "Danish", "Dane"),
    "DO": ("Dominican Republic", "Dominican"),
    "DZ": ("Algeria", "Algerian"),
    "EC": ("Ecuador", "Ecuadorian"),
    "EE": ("Estonia", "Estonian"),
    "EG": ("Egypt", "Egyptian"),
    "ES": ("Spain", "Spanish"),
    "ET": ("Ethiopia", "Ethiopian"),
    "FI": ("Finland", "Finnish"),
    "FR": ("France", "French"),
    "GB": ("United Kingdom", "Great Britain", "Britain", "British", "UK", "U.K."),
    "GH": ("Ghana", "Ghanaian"),
    "GR": ("Greece", "Greek"),
    "GT": ("Guatemala", "Guatemalan"),
    "HK": ("Hong Kong",),
    "HN": ("Honduras", "Honduran"),
    "HR": ("Croatia", "Croatian"),
    "HU": ("Hungary", "Hungarian"),
    "ID": ("Indonesia", "Indonesian"),
    "IE": ("Ireland", "Irish", "Republic of Ireland"),
    "IL": ("Israel", "Israeli"),
    "IN": ("India", "Indian"),
    "IQ": ("Iraq", "Iraqi"),
    "IR": ("Iran", "Iranian"),
    "IS": ("Iceland", "Icelandic"),
    "IT": ("Italy", "Italian"),
    "JM": ("Jamaica", "Jamaican"),
    "JO": ("Jordan", "Jordanian"),
    "JP": ("Japan", "Japanese"),
    "KE": ("Kenya", "Kenyan"),
    "KH": ("Cambodia", "Cambodian"),
    "KR": ("South Korea", "South Korean", "Republic of Korea"),
    "KP": ("North Korea", "North Korean"),
    "KW": ("Kuwait", "Kuwaiti"),
    "KZ": ("Kazakhstan", "Kazakh"),
    "LB": ("Lebanon", "Lebanese"),
    "LK": ("Sri Lanka", "Sri Lankan"),
    "LT": ("Lithuania", "Lithuanian"),
    "LU": ("Luxembourg", "Luxembourger"),
    "LV": ("Latvia", "Latvian"),
    "LY": ("Libya", "Libyan"),
    "MA": ("Morocco", "Moroccan"),
    "MD": ("Moldova", "Moldovan"),
    "ME": ("Montenegro", "Montenegrin"),
    "MK": ("North Macedonia", "Macedonia", "Macedonian"),
    "MM": ("Myanmar", "Burma", "Burmese"),
    "MT": ("Malta", "Maltese"),
    "MX": ("Mexico", "Mexican"),
    "MY": ("Malaysia", "Malaysian"),
    "MZ": ("Mozambique", "Mozambican"),
    "NA": ("Namibia", "Namibian"),
    "NG": ("Nigeria", "Nigerian"),
    "NL": ("Netherlands", "Dutch", "Holland", "Netherlander"),
    "NO": ("Norway", "Norwegian"),
    "NP": ("Nepal", "Nepali", "Nepalese"),
    "NZ": ("New Zealand", "New Zealander"),
    "PA": ("Panama", "Panamanian"),
    "PE": ("Peru", "Peruvian"),
    "PH": ("Philippines", "Filipino", "Philippine"),
    "PK": ("Pakistan", "Pakistani"),
    "PL": ("Poland", "Polish", "Pole"),
    "PT": ("Portugal", "Portuguese"),
    "PY": ("Paraguay", "Paraguayan"),
    "QA": ("Qatar", "Qatari"),
    "RO": ("Romania", "Romanian"),
    "RS": ("Serbia", "Serbian"),
    "RU": ("Russia", "Russian", "Russian Federation"),
    "RW": ("Rwanda", "Rwandan"),
    "SA": ("Saudi Arabia", "Saudi"),
    "SE": ("Sweden", "Swedish", "Swede"),
    "SG": ("Singapore", "Singaporean"),
    "SI": ("Slovenia", "Slovenian", "Slovene"),
    "SK": ("Slovakia", "Slovak"),
    "SN": ("Senegal", "Senegalese"),
    "SV": ("El Salvador", "Salvadoran"),
    "SY": ("Syria", "Syrian"),
    "TH": ("Thailand", "Thai"),
    "TN": ("Tunisia", "Tunisian"),
    "TR": ("Turkey", "Türkiye", "Turkiye", "Turkish"),
    "TW": ("Taiwan", "Taiwanese"),
    "TZ": ("Tanzania", "Tanzanian"),
    "UA": ("Ukraine", "Ukrainian"),
    "UG": ("Uganda", "Ugandan"),
    "US": ("United States", "United States of America", "USA", "U.S.A.", "America", "American",
           "U.S."),
    "UY": ("Uruguay", "Uruguayan"),
    "UZ": ("Uzbekistan", "Uzbek"),
    "VE": ("Venezuela", "Venezuelan"),
    "VN": ("Vietnam", "Viet Nam", "Vietnamese"),
    "YE": ("Yemen", "Yemeni"),
    "ZA": ("South Africa", "South African"),
    "ZM": ("Zambia", "Zambian"),
    "ZW": ("Zimbabwe", "Zimbabwean"),
    # Groups.
    "EU": ("European Union", "the EU", "EU member states"),
    "EA": ("euro area", "euro zone", "eurozone", "euro-area", "the euro area"),
    "WORLD": ("world", "the world", "global", "worldwide", "the globe"),
    "G7": ("G7", "G-7", "Group of Seven"),
    "G20": ("G20", "G-20", "Group of Twenty"),
    "OECD": ("OECD",),
}  # fmt: skip


def _key(text: str) -> str:
    """Case, accents, punctuation and a leading "the" folded away: "The U.K." → "uk"."""
    plain = unicodedata.normalize("NFKD", text)
    plain = "".join(ch for ch in plain if not unicodedata.combining(ch)).casefold()
    plain = re.sub(r"[.'’]", "", plain)  # U.K., People's
    plain = re.sub(r"[-_,]", " ", plain)
    words = plain.split()
    if words[:1] == ["the"] and len(words) > 1:
        words = words[1:]
    return " ".join(words)


BY_NAME: dict[str, str] = {_key(name): code for code, names in _NAMES.items() for name in names}


def is_name(text: str) -> bool:
    """True if `text` is a place written as a name, not as a code (so the reading is worth a note)."""
    raw = text.strip().upper()
    raw = GEO_ALIASES.get(raw, raw)
    return not (raw in ISO3 or raw in GEO_GROUPS or raw in ISO2)


def place_code(text: str | None) -> str | None:
    """The claim code for a code, name, demonym or short form; None if the place is unknown."""
    if text is None or not text.strip():
        return None
    raw = text.strip().upper()
    raw = GEO_ALIASES.get(raw, raw)
    if raw in ISO3 or raw in GEO_GROUPS:
        return raw
    if raw in ISO2:  # an ISO3 code: ITA
        return ISO2[raw]
    key = _key(text)
    code = BY_NAME.get(key)
    if code is None and key.endswith("s") and len(key) > 3:
        code = BY_NAME.get(key[:-1])  # "the Italians", "Greeks"
    return code
