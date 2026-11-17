"""Pay stated in an advert: a currency amount or range that sits next to a pay word. Anything else is not stated."""

import re

CURRENCY = r"(?:€|\$|£|\b(?:EUR|USD|GBP|CHF|Euro)\b)"
NUMBER = r"(?:\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)"
AMOUNT = rf"(?:{CURRENCY}\s?)?{NUMBER}(?:\s?k\b)?(?:\s?{CURRENCY})?"
RANGE = re.compile(
    rf"(?<![\w.,]){AMOUNT}(?:\s*(?:[-–—]|to|bis|und|and)\s*{AMOUNT})?"
    r"(?![\w])(?!\s?(?:million|billion|mio|mrd|bn)\b)", re.I)
UNIT = re.compile(r"\s*(?:(?:/|per\s+|pro\s+)(?:year|annum|hour|month|jahr|stunde|monat)\b"
                  r"|p\.\s?a\.|\s+annually\b)", re.I)
PAY_WORD = re.compile(
    r"\b(?:salary|salaries|compensation|remuneration|wages?|pay|ote|gross|hourly|per\s+hour|"
    r"gehalt\w*|jahresgehalt|verg[üu]tung|bezahlung|brutto|lohn|stundenlohn|verdienst|stundensatz|"
    r"pro\s+stunde|je\s+stunde|st[üu]ndlich)\b", re.I)
NOT_PAY = re.compile(r"\b(?:budget|bonus|allowance|referral|relocation|discount|funding|raised|revenue|umsatz|"
                     r"voucher|gutschein|zuschuss|pr[äa]mie|equipment)\b", re.I)
WINDOW = 60


def extract_salary(text):
    if not text:
        return None
    for found in RANGE.finditer(text):
        if not re.search(CURRENCY, found.group(), re.I):
            continue
        start = text.rfind("\n", 0, found.start()) + 1
        end = text.find("\n", found.end())
        end = len(text) if end < 0 else end
        around = text[max(start, found.start() - WINDOW):min(end, found.end() + WINDOW)]
        if PAY_WORD.search(around) and not NOT_PAY.search(around):
            unit = UNIT.match(text, found.end())
            return re.sub(r"\s+", " ", text[found.start():unit.end() if unit else found.end()]).strip()
    return None
