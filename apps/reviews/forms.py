from django import forms

from .models import Review

RATING_CHOICES = [(value, str(value)) for value in range(1, 6)]


class ReviewForm(forms.ModelForm):
    """Відгук про товар: оцінка 1–5 та коментар."""

    rating = forms.TypedChoiceField(
        choices=RATING_CHOICES,
        coerce=int,
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Review
        fields = ("rating", "comment")
