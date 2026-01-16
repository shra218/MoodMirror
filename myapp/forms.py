from django import forms
from .models import Mood

class MoodForm(forms.ModelForm):
    MOOD_CHOICES = [
        ('happy', '😊 Happy'),
        ('sad', '😔 Sad'),
        ('anxious', '😰 Anxious'),
        ('angry', '😡 Angry'),
        ('calm', '😌 Calm'),
        ('tired', '😴 Tired'),
    ]

    mood_type = forms.ChoiceField(
        choices=MOOD_CHOICES,
        widget=forms.Select(attrs={'class': 'journal-select'}),
        label=""
    )

    note = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'journal-textarea',
            'placeholder': 'Write your thoughts here...',
            'rows': 4
        }),
        label=""
    )

    class Meta:
        model = Mood
        fields = ['mood_type', 'note']