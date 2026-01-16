from django.db import models
from django.contrib.auth.models import User

class Mood(models.Model):
    MOOD_CHOICES = [
        ("happy", "Happy"),
        ("sad", "Sad"),
        ("anxious", "Anxious"),
        ("angry", "Angry"),
        ("calm", "Calm"),
        ("tired", "Tired"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    note = models.TextField()
    mood_type = models.CharField(max_length=20, choices=MOOD_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.mood_type}"