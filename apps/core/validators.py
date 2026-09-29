import re

from django import forms

PHONE_RE = re.compile(r"^(?:\+?38)?(0\d{9})$")


def normalize_phone(value: str) -> str:
    """Accept 0991112233, 380991112233 or +38 (099) 111-22-33 and return +380991112233."""
    match = PHONE_RE.match(re.sub(r"[\s()\-]", "", value))
    if not match:
        raise forms.ValidationError("Введіть український номер, наприклад +380991112233.")
    return f"+38{match.group(1)}"
