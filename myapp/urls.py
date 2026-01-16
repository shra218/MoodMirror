from django.urls import path
from . import views
from .views import login_view, logout_view, wisdom_view, wellness_analytics, mindful_challenges, wellness_insights, personalized_playlist, mood_playlists, mood_history

urlpatterns = [
    path('', views.landing, name='landing'),
    path('home/', views.home, name='home'),
    path("login/", login_view, name='login'),
    path("logout/", logout_view, name='logout'),
    path('wisdom/', wisdom_view, name='wisdom'),
    path("journaling-success/", login_view, name='journaling_success'),
    path('signup/', views.signup, name='signup'),
    path('signup-success/', views.signup_success,name='signup_success'),
    path('monthly-analysis/', views.monthly_analysis,name='monthly_analysis'),
    path('entry/', views.mood_entry, name='mood_entry'),
    path('history/', mood_history, name='mood_history'),
    path('reflection/', views.mood_entry,name='reflection'),
    path('suggestion/', views.suggestion,name='suggestion'),
    path('analytics/', views.analytics, name='analytics'),
    path('wellness-analytics/', wellness_analytics, name='wellness_analytics'),
    path('wellness-insights/', wellness_insights, name='wellness_insights'),
    path('mindful-challenges/', mindful_challenges, name='mindful_challenges'),
    path('personalized-playlist/', personalized_playlist, name='personalized_playlist'),
    path('mood-playlists/', mood_playlists, name='mood_playlists'),
    path('thankyou/', views.thank_you, name='thank_you'),
]