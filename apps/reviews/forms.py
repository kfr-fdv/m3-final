from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        label="Оцінка",
        choices=[(value, value) for value in range(5, 0, -1)],
        coerce=int,
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Review
        fields = ("rating", "comment")
        labels = {"comment": "Коментар"}
