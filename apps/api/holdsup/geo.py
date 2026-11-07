"""Place codes: the claim spec's codes (ISO 3166-1 alpha-2 plus EU, EA, WORLD) and the codes
each data source writes.

Sources disagree: Eurostat writes EL for Greece and EU27_2020 for the EU, the World Bank
answers 1W for the world, OWID uses ISO3 and OWID_WRL. The fetch step maps the claim's codes
to the source's before asking, and maps the source's codes back before planning, so the plan
and the receipt only ever see the claim's codes.
"""

from collections.abc import Iterable

from holdsup.adapters.base import Observation
from holdsup.catalog.schema import Source

# ISO 3166-1 alpha-2 -> alpha-3, every officially assigned code (249), plus Kosovo (XK),
# which the World Bank and OWID both use.
# fmt: off
ISO3: dict[str, str] = {
    "AD": "AND", "AE": "ARE", "AF": "AFG", "AG": "ATG", "AI": "AIA", "AL": "ALB", "AM": "ARM",
    "AO": "AGO", "AQ": "ATA", "AR": "ARG", "AS": "ASM", "AT": "AUT", "AU": "AUS", "AW": "ABW",
    "AX": "ALA", "AZ": "AZE", "BA": "BIH", "BB": "BRB", "BD": "BGD", "BE": "BEL", "BF": "BFA",
    "BG": "BGR", "BH": "BHR", "BI": "BDI", "BJ": "BEN", "BL": "BLM", "BM": "BMU", "BN": "BRN",
    "BO": "BOL", "BQ": "BES", "BR": "BRA", "BS": "BHS", "BT": "BTN", "BV": "BVT", "BW": "BWA",
    "BY": "BLR", "BZ": "BLZ", "CA": "CAN", "CC": "CCK", "CD": "COD", "CF": "CAF", "CG": "COG",
    "CH": "CHE", "CI": "CIV", "CK": "COK", "CL": "CHL", "CM": "CMR", "CN": "CHN", "CO": "COL",
    "CR": "CRI", "CU": "CUB", "CV": "CPV", "CW": "CUW", "CX": "CXR", "CY": "CYP", "CZ": "CZE",
    "DE": "DEU", "DJ": "DJI", "DK": "DNK", "DM": "DMA", "DO": "DOM", "DZ": "DZA", "EC": "ECU",
    "EE": "EST", "EG": "EGY", "EH": "ESH", "ER": "ERI", "ES": "ESP", "ET": "ETH", "FI": "FIN",
    "FJ": "FJI", "FK": "FLK", "FM": "FSM", "FO": "FRO", "FR": "FRA", "GA": "GAB", "GB": "GBR",
    "GD": "GRD", "GE": "GEO", "GF": "GUF", "GG": "GGY", "GH": "GHA", "GI": "GIB", "GL": "GRL",
    "GM": "GMB", "GN": "GIN", "GP": "GLP", "GQ": "GNQ", "GR": "GRC", "GS": "SGS", "GT": "GTM",
    "GU": "GUM", "GW": "GNB", "GY": "GUY", "HK": "HKG", "HM": "HMD", "HN": "HND", "HR": "HRV",
    "HT": "HTI", "HU": "HUN", "ID": "IDN", "IE": "IRL", "IL": "ISR", "IM": "IMN", "IN": "IND",
    "IO": "IOT", "IQ": "IRQ", "IR": "IRN", "IS": "ISL", "IT": "ITA", "JE": "JEY", "JM": "JAM",
    "JO": "JOR", "JP": "JPN", "KE": "KEN", "KG": "KGZ", "KH": "KHM", "KI": "KIR", "KM": "COM",
    "KN": "KNA", "KP": "PRK", "KR": "KOR", "KW": "KWT", "KY": "CYM", "KZ": "KAZ", "LA": "LAO",
    "LB": "LBN", "LC": "LCA", "LI": "LIE", "LK": "LKA", "LR": "LBR", "LS": "LSO", "LT": "LTU",
    "LU": "LUX", "LV": "LVA", "LY": "LBY", "MA": "MAR", "MC": "MCO", "MD": "MDA", "ME": "MNE",
    "MF": "MAF", "MG": "MDG", "MH": "MHL", "MK": "MKD", "ML": "MLI", "MM": "MMR", "MN": "MNG",
    "MO": "MAC", "MP": "MNP", "MQ": "MTQ", "MR": "MRT", "MS": "MSR", "MT": "MLT", "MU": "MUS",
    "MV": "MDV", "MW": "MWI", "MX": "MEX", "MY": "MYS", "MZ": "MOZ", "NA": "NAM", "NC": "NCL",
    "NE": "NER", "NF": "NFK", "NG": "NGA", "NI": "NIC", "NL": "NLD", "NO": "NOR", "NP": "NPL",
    "NR": "NRU", "NU": "NIU", "NZ": "NZL", "OM": "OMN", "PA": "PAN", "PE": "PER", "PF": "PYF",
    "PG": "PNG", "PH": "PHL", "PK": "PAK", "PL": "POL", "PM": "SPM", "PN": "PCN", "PR": "PRI",
    "PS": "PSE", "PT": "PRT", "PW": "PLW", "PY": "PRY", "QA": "QAT", "RE": "REU", "RO": "ROU",
    "RS": "SRB", "RU": "RUS", "RW": "RWA", "SA": "SAU", "SB": "SLB", "SC": "SYC", "SD": "SDN",
    "SE": "SWE", "SG": "SGP", "SH": "SHN", "SI": "SVN", "SJ": "SJM", "SK": "SVK", "SL": "SLE",
    "SM": "SMR", "SN": "SEN", "SO": "SOM", "SR": "SUR", "SS": "SSD", "ST": "STP", "SV": "SLV",
    "SX": "SXM", "SY": "SYR", "SZ": "SWZ", "TC": "TCA", "TD": "TCD", "TF": "ATF", "TG": "TGO",
    "TH": "THA", "TJ": "TJK", "TK": "TKL", "TL": "TLS", "TM": "TKM", "TN": "TUN", "TO": "TON",
    "TR": "TUR", "TT": "TTO", "TV": "TUV", "TW": "TWN", "TZ": "TZA", "UA": "UKR", "UG": "UGA",
    "UM": "UMI", "US": "USA", "UY": "URY", "UZ": "UZB", "VA": "VAT", "VC": "VCT", "VE": "VEN",
    "VG": "VGB", "VI": "VIR", "VN": "VNM", "VU": "VUT", "WF": "WLF", "WS": "WSM", "YE": "YEM",
    "YT": "MYT", "ZA": "ZAF", "ZM": "ZMB", "ZW": "ZWE",
    "XK": "XKX",
}
# fmt: on
ISO2 = {v: k for k, v in ISO3.items()}

# Claim code -> the source's code, where it differs from the default (ISO2, or ISO3 for OWID).
_TO_SOURCE: dict[Source, dict[str, str]] = {
    Source.EUROSTAT: {"GR": "EL", "GB": "UK", "EU": "EU27_2020", "EA": "EA20"},
    Source.WORLDBANK: {"EU": "EUU", "EA": "EMU", "WORLD": "WLD"},
    Source.OWID: {"WORLD": "OWID_WRL", "EU": "OWID_EU27", "XK": "OWID_KOS"},
}
# The source's code -> claim code, for what comes back.
_FROM_SOURCE: dict[Source, dict[str, str]] = {
    Source.EUROSTAT: {"EL": "GR", "UK": "GB", "EU27_2020": "EU", "EA20": "EA"},
    # World Bank observations are read by their ISO3 dimension (country.id is "1W" for WLD).
    Source.WORLDBANK: {"EUU": "EU", "EMU": "EA", "WLD": "WORLD", "XKX": "XK"},
    Source.OWID: {"OWID_WRL": "WORLD", "OWID_EU27": "EU", "OWID_KOS": "XK"},
}
# The adapter's filter key for places.
GEO_FILTER = {Source.EUROSTAT: "geo", Source.WORLDBANK: "country", Source.OWID: "country"}


class UnknownPlace(ValueError):
    """The source has no code for this place (e.g. G7 on Eurostat)."""


def to_source(source: Source, code: str) -> str:
    """The source's code for a claim code."""
    special = _TO_SOURCE.get(source, {})
    if code in special:
        return special[code]
    if code not in ISO3:
        raise UnknownPlace(f"{source} has no code for {code}")
    return ISO3[code] if source is Source.OWID else code


def geo_filter(source: Source, codes: Iterable[str]) -> dict[str, str | list[str]]:
    """The adapter filter asking for these claim codes (deduplicated, order kept)."""
    if source not in GEO_FILTER:
        raise UnknownPlace(f"no adapter for source {source}")
    wanted = list(dict.fromkeys(to_source(source, c) for c in codes))
    if not wanted:
        raise UnknownPlace("the claim names no place")
    return {GEO_FILTER[source]: wanted[0] if len(wanted) == 1 else wanted}


def from_source(source: Source, observation: Observation) -> str:
    """The claim code for a fetched observation; the source's own code if none is known."""
    raw = observation.geo
    if source is Source.WORLDBANK:
        raw = observation.dims.get("iso3") or raw
    special = _FROM_SOURCE.get(source, {})
    if raw in special:
        return special[raw]
    if source is not Source.EUROSTAT and raw in ISO2:
        return ISO2[raw]
    return raw


def to_claim_codes(source: Source, observations: Iterable[Observation]) -> list[Observation]:
    """The observations with their places rewritten as claim codes."""
    out = []
    for o in observations:
        code = from_source(source, o)
        out.append(o if code == o.geo else Observation(code, o.period, o.value, o.status, o.dims))
    return out
