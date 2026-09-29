from django import forms

from apps.catalog.models import Category, Product


class ProductForm(forms.ModelForm):
    # Tags on the page, as in the design: products belong to the lowest-level categories.
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(children__isnull=True).order_by("parent__name", "name"),
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Product
        fields = ("name", "description", "price", "stock", "category", "image")
