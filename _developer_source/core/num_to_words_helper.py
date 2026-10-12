"""
Currency to Words Helper
Converts numerical AED invoice totals into standard UAE corporate invoice format:
e.g. "AED SIX THOUSAND FIVE HUNDRED TEN & ZERO FILS ONLY"
"""
import math
from num2words import num2words


def amount_to_aed_words(amount: float) -> str:
    """
    Converts float amount to AED uppercase words string.
    Example:
        6510.00 -> 'AED SIX THOUSAND FIVE HUNDRED TEN & ZERO FILS ONLY'
        6510.50 -> 'AED SIX THOUSAND FIVE HUNDRED TEN & FIFTY FILS ONLY'
        0.00    -> 'AED ZERO & ZERO FILS ONLY'
    """
    try:
        amount = round(float(amount), 2)
    except (ValueError, TypeError):
        return "AED ZERO & ZERO FILS ONLY"

    if amount < 0:
        amount = 0.0

    dirhams = int(math.floor(amount))
    fils = int(round((amount - dirhams) * 100))

    if fils >= 100:
        dirhams += 1
        fils = 0

    if dirhams == 0:
        dirhams_word = "ZERO"
    else:
        d_raw = num2words(dirhams, lang='en')
        dirhams_word = d_raw.replace(',', '').replace('-', ' ').upper()
        parts = dirhams_word.split()
        cleaned_parts = [p for p in parts if p != "AND"]
        dirhams_word = " ".join(cleaned_parts)

    if fils == 0:
        fils_word = "ZERO"
    else:
        f_raw = num2words(fils, lang='en')
        fils_word = f_raw.replace(',', '').replace('-', ' ').upper()
        f_parts = fils_word.split()
        fils_word = " ".join([p for p in f_parts if p != "AND"])

    return f"AED {dirhams_word} & {fils_word} FILS ONLY"


if __name__ == "__main__":
    print(amount_to_aed_words(6510.00))
    print(amount_to_aed_words(6510.50))
    print(amount_to_aed_words(200.00))
    print(amount_to_aed_words(0.00))
    print(amount_to_aed_words(1234567.89))
