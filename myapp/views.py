from django.shortcuts import render, redirect
import google.generativeai as genai
from .forms import MoodForm
from datetime import timedelta, datetime
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
import json
from django.db.models import Count
from .models import Mood
from django.core.paginator import Paginator
from django.db.models import Q

def landing(request):
    return render(request, 'landing.html')

@login_required(login_url='/login/')
def home(request):
    """Dashboard/home page shown after login"""
    return render(request, 'home.html')

@login_required(login_url='/login/')
def logout_view(request):
    """Logout the user and redirect to landing page"""
    logout(request)
    return redirect('landing')

@login_required(login_url='/login/')
def wisdom_view(request):
    """Daily Wisdom page - Generates personalized wisdom based on user's mood"""
    username = request.user.username
    
    # Get the most recent mood from database
    # Falls back to 'calm' if user has no mood entries yet
    recent_mood_obj = Mood.objects.filter(user=request.user).order_by('-created_at').first()
    recent_mood = recent_mood_obj.mood_type if recent_mood_obj else 'calm'
    
    # Default fallback quote - ensures page is NEVER empty
    daily_wisdom = "Slow down. You are allowed to heal at your own pace."
    
    try:
        genai.configure(api_key="")
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = f"""
You are a compassionate wellness guide. Generate a short, calming, and encouraging quote for {username} who is feeling {recent_mood} today.

Requirements:
- 1–2 lines only
- Calm and soothing tone
- Encouraging and uplifting
- Mental-health friendly
- Do NOT include any explanations or extra text, just the quote itself

Example tone: "Even on quiet days, your strength is growing."

Generate only the quote:
"""
        
        response = model.generate_content(prompt)
        generated_quote = response.text.strip()
        
        # Ensure response is not empty. If empty, use default fallback
        if generated_quote:
            daily_wisdom = generated_quote
        
    except Exception as e:
        # If AI API call fails (network error, rate limit, invalid key, etc.),
        # use the default fallback wisdom to prevent page breakage
        # Page will always render with daily_wisdom set
        pass
    
    context = {
        'username': username,
        'recent_mood': recent_mood,
        'daily_wisdom': daily_wisdom,  # Always has a value
    }
    
    return render(request, 'wisdom.html', context)

@login_required(login_url='/login/')
def mood_entry(request):
    if request.method == "POST":
        form = MoodForm(request.POST)
        if form.is_valid():
            mood = form.save(commit=False)
            mood.user = request.user
            mood.save()
            return redirect('suggestion')
    else:
        form = MoodForm()

    moods = Mood.objects.filter(user=request.user).order_by('-created_at')

    # 🌸 Calculate streak
    streak = 0
    today = timezone.now().date()
    last_date = None

    for mood in moods:
        mood_date = mood.created_at.date()
        if last_date is None:
            if mood_date == today:
                streak += 1
                last_date = today
            elif mood_date == today - timedelta(days=1):
                streak += 1
                last_date = mood_date
            else:
                break
        else:
            if mood_date == last_date - timedelta(days=1):
                streak += 1
                last_date = mood_date
            else:
                break

    return render(request, 'mood_entry.html', {
        'form': form,
        'moods': moods,
        'streak': streak
    })
def mood_history(request):
    moods = Mood.objects.filter(user=request.user).order_by('-date')
    return render(request, 'mood_history.html', {'moods': moods})


def analytics(request):
    mood_data = (
        Mood.objects
        .values('mood')
        .annotate(count=Count('mood'))
    )

    return render(request, 'analytics.html', {
        'mood_data': mood_data
    })
def thank_you(request):
    return render(request, 'thank_you.html')

def signup(request):
    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        if password1 != password2:
            return render(request, 'signup.html', {
                'error': "Passwords do not match"
            })

        # create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1
        )

        login(request, user)
        return redirect('home')

    return render(request, 'signup.html')

def signup_success(request):
    return render(request, 'signup_success.html')


@login_required(login_url="/login/")
def reflection(request):
    if request.method == "POST":
        form = MoodForm(request.POST)
        if form.is_valid():
            mood_entry = form.save(commit=False)
            mood_entry.user = request.user
            mood_entry.save()

            # Store the last saved mood id in session to use in suggestion page
            request.session['last_mood_id'] = mood_entry.id

            # Redirect to suggestion page
            return redirect('suggestion')
    else:
        form = MoodForm()

    return render(request, "reflection.html", {
        "form": form,
        "moods": Mood.objects.filter(user=request.user).order_by("-created_at"),
    })


@login_required(login_url="/login/")
def suggestion(request):
    # get the latest mood of the logged-in user
    mood = Mood.objects.filter(user=request.user).order_by('-created_at').first()

    llm_suggestion = None

    if mood:
        # 🔑 configure Gemini API
        genai.configure(api_key="")

        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = f"""
        The user is feeling {mood.mood_type}.
        Their journal note is: "{mood.note}"

        Give a short, kind, emotionally supportive suggestion,
        exercises both physical and mental.
        Keep it calm, pastel, friendly, and comforting.
        Give little medical advice. Use some emojis.
        """

        response = model.generate_content(prompt)
        llm_suggestion = response.text

    return render(request, 'suggestion.html', {
        'llm_suggestion': llm_suggestion
    })
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("home")
        else:
            return render(request, "login.html", {
                "error": "Invalid username or password"
            })

    return render(request, "login.html")

@login_required(login_url="/login/")
def journaling_success(request):
    return render(request, "journaling_success.html")


def monthly_analysis(request):
    # Get current month moods
    moods = Mood.objects.filter(
        user=request.user,
        created_at__month=timezone.now().month,
        created_at__year=timezone.now().year
    )

    if not moods.exists():
        return render(request, 'monthly_analysis.html', {
            'error': "Not enough mood data for this month 🌸"
        })

    mood_text = "\n".join(
        [f"- {m.mood_type}: {m.note}" for m in moods]
    )

    # Configure Gemini
    genai.configure(api_key="")
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
You are a gentle and emotionally intelligent mental wellness assistant.

Based on the user's moods for this month below:
{mood_text}

Respond in the following STRUCTURED FORMAT ONLY:

Mood Overview:
(2–3 lines summarizing overall emotional state)

Patterns Observed:
- Pattern 1
- Pattern 2
- Pattern 3

Emotional Insight:
(A deeper reflection about emotional health)

Gentle Suggestions:
- Suggestion 1
- Suggestion 2
- Suggestion 3

Tone: warm, supportive, non-judgmental.
Do NOT add anything outside this structure.
"""

    response = model.generate_content(prompt)
    text = response.text

    # ✨ Split response safely
    sections = {
        "overview": "",
        "patterns": [],
        "insight": "",
        "suggestions": []
    }

    current = None
    for line in text.splitlines():
        line = line.strip()

        if line.startswith("Mood Overview"):
            current = "overview"
            continue
        elif line.startswith("Patterns Observed"):
            current = "patterns"
            continue
        elif line.startswith("Emotional Insight"):
            current = "insight"
            continue
        elif line.startswith("Gentle Suggestions"):
            current = "suggestions"
            continue

        if current == "overview":
            sections["overview"] += line + " "
        elif current == "patterns" and line.startswith("-"):
            sections["patterns"].append(line[1:].strip())
        elif current == "insight":
            sections["insight"] += line + " "
        elif current == "suggestions" and line.startswith("-"):
            sections["suggestions"].append(line[1:].strip())


@login_required(login_url="/login/")
def wellness_analytics(request):
    """Wellness Analytics page - Shows mood patterns and AI insights"""
    
    # Fetch all moods for the logged-in user in the current month
    current_month = timezone.now().month
    current_year = timezone.now().year
    
    moods = Mood.objects.filter(
        user=request.user,
        created_at__month=current_month,
        created_at__year=current_year
    ).order_by('-created_at')
    
    # Combine mood_type and note into a single string for AI analysis
    mood_text = ""
    if moods.exists():
        mood_entries = []
        for mood in moods:
            entry = f"{mood.mood_type}: {mood.note}"
            mood_entries.append(entry)
        mood_text = "\n".join(mood_entries)
    
    # Calculate mood distribution with counts
    mood_distribution = {}
    for mood in moods:
        mood_type = mood.mood_type
        mood_distribution[mood_type] = mood_distribution.get(mood_type, 0) + 1
    
    # Calculate mood distribution percentages
    total_moods = moods.count()
    mood_percentages = {}
    for mood_type, count in mood_distribution.items():
        percentage = round((count / total_moods * 100)) if total_moods > 0 else 0
        mood_percentages[mood_type] = percentage
    
    # Find most frequent mood
    most_frequent_mood = max(mood_distribution.items(), key=lambda x: x[1])[0] if mood_distribution else "neutral"
    most_frequent_count = mood_distribution.get(most_frequent_mood, 0)
    
    # Calculate mood streak (consecutive days with mood entries)
    mood_streak = 0
    today = timezone.now().date()
    last_date = None
    
    for mood in moods:
        mood_date = mood.created_at.date()
        if last_date is None:
            if mood_date == today:
                mood_streak += 1
                last_date = today
            elif mood_date == today - timedelta(days=1):
                mood_streak += 1
                last_date = mood_date
            else:
                break
        else:
            if mood_date == last_date - timedelta(days=1):
                mood_streak += 1
                last_date = mood_date
            else:
                break
    
    # Calculate emotional balance (positive / neutral / heavy moods)
    positive_moods = ['happy', 'calm']
    neutral_moods = ['tired']
    heavy_moods = ['sad', 'anxious', 'angry']
    
    positive_count = sum(count for mood_type, count in mood_distribution.items() if mood_type in positive_moods)
    neutral_count = sum(count for mood_type, count in mood_distribution.items() if mood_type in neutral_moods)
    heavy_count = sum(count for mood_type, count in mood_distribution.items() if mood_type in heavy_moods)
    
    # Determine emotional balance indicator
    if total_moods > 0:
        positive_percent = (positive_count / total_moods) * 100
        if positive_percent >= 60:
            balance_indicator = "Positive"
            balance_emoji = "✨"
        elif positive_percent >= 40:
            balance_indicator = "Balanced"
            balance_emoji = "⚖️"
        else:
            balance_indicator = "Reflective"
            balance_emoji = "🌙"
    else:
        balance_indicator = "No Data"
        balance_emoji = "📊"
    
    # Fallback data (if AI fails or no mood data)
    fallback_summary = "Your emotional wellness dashboard shows your mood patterns over time."
    fallback_insight = "Your recent mood trends show a positive pattern with more calm and happy moments. Keep maintaining your wellness routine!"
    fallback_suggestions = "Continue journaling regularly to track your emotional growth.\nPractice breathing exercises when you feel overwhelmed.\nSchedule regular breaks for mindfulness and self-care."
    fallback_patterns = "Keep tracking your moods to discover your emotional patterns."
    
    summary = fallback_summary
    insight = fallback_insight
    suggestions = fallback_suggestions
    patterns = fallback_patterns
    
    # Generate AI insights if mood data exists
    if mood_text:
        try:
            genai.configure(api_key="")
            model = genai.GenerativeModel("gemini-2.5-flash")
            
            prompt = f"""You are a gentle and emotionally intelligent mental wellness assistant.

Based on the user's mood entries for this month:
{mood_text}

Provide a comprehensive wellness analysis in the following STRUCTURED FORMAT ONLY:

EMOTIONAL SUMMARY:
(2-3 lines describing the overall emotional state)

MOOD PATTERNS:
(2-3 lines about observed patterns in moods)

EMOTIONAL INSIGHT:
(2-3 lines of deeper reflection about emotional health)

GENTLE SUGGESTIONS:
(3-4 lines of supportive, actionable suggestions)

Tone: warm, supportive, non-clinical, gentle, encouraging.
Do NOT include section labels in your output - just provide the content under each section naturally.
Do NOT add markdown formatting."""
            
            response = model.generate_content(prompt)
            ai_output = response.text.strip()
            
            # Parse the structured response into sections
            lines = ai_output.split('\n')
            current_section = None
            sections = {
                'summary': [],
                'patterns': [],
                'insight': [],
                'suggestions': []
            }
            
            for line in lines:
                line_lower = line.lower().strip()
                
                if 'emotional summary' in line_lower:
                    current_section = 'summary'
                    continue
                elif 'mood patterns' in line_lower:
                    current_section = 'patterns'
                    continue
                elif 'emotional insight' in line_lower:
                    current_section = 'insight'
                    continue
                elif 'gentle suggestions' in line_lower or 'suggestions' in line_lower:
                    current_section = 'suggestions'
                    continue
                
                if line.strip() and current_section:
                    sections[current_section].append(line.strip())
            
            # Convert sections to strings
            summary = ' '.join(sections['summary']) if sections['summary'] else fallback_summary
            patterns = ' '.join(sections['patterns']) if sections['patterns'] else fallback_patterns
            insight = ' '.join(sections['insight']) if sections['insight'] else fallback_insight
            suggestions = ' '.join(sections['suggestions']) if sections['suggestions'] else fallback_suggestions
            
        except Exception as e:
            # If AI fails, use fallback data
            pass
    
    context = {
        'summary': summary,
        'mood_distribution': mood_distribution,
        'mood_percentages': mood_percentages,
        'patterns': patterns,
        'insight': insight,
        'suggestions': suggestions,
        'total_moods': total_moods,
        'most_frequent_mood': most_frequent_mood,
        'most_frequent_count': most_frequent_count,
        'mood_streak': mood_streak,
        'balance_indicator': balance_indicator,
        'balance_emoji': balance_emoji,
        'positive_count': positive_count,
        'neutral_count': neutral_count,
        'heavy_count': heavy_count,
    }
    
    return render(request, 'wellness_analytics.html', context)

    return render(request, 'monthly_analysis.html', {
        "analysis": sections
    })


@login_required(login_url="/login/")
def mindful_challenges(request):
    """Mindful Challenges page - Generates personalized challenges based on recent moods"""
    
    # Fetch the last 7 moods of the logged-in user
    recent_moods = Mood.objects.filter(user=request.user).order_by('-created_at')[:7]
    
    # Format mood data into a string for AI analysis
    mood_text = ""
    if recent_moods.exists():
        mood_entries = []
        for mood in recent_moods:
            entry = f"{mood.mood_type}"
            mood_entries.append(entry)
        mood_text = ", ".join(mood_entries)
    
    # Fallback challenges if AI fails or no mood data
    fallback_challenges = [
        {
            "emoji": "🧘",
            "title": "5-Minute Meditation",
            "description": "Start your day with a brief meditation to calm your mind"
        },
        {
            "emoji": "🚶",
            "title": "Mindful Walk",
            "description": "Take a slow walk and notice the world around you"
        },
        {
            "emoji": "📓",
            "title": "Gratitude Journal",
            "description": "Write three things you're grateful for today"
        }
    ]
    
    personalized_challenges = fallback_challenges
    
    # Generate personalized challenges using AI if mood data exists
    if mood_text:
        try:
            genai.configure(api_key="")
            model = genai.GenerativeModel("gemini-2.5-flash")
            
            prompt = f"""You are a compassionate wellness coach. Based on the user's recent moods ({mood_text}), 
            generate EXACTLY 3 personalized mindful challenges to help them.

            For EACH challenge, provide ONLY:
            emoji: (one appropriate emoji)
            title: (short, 2-3 words)
            description: (one short, encouraging sentence)

            Format your response EXACTLY like this (3 times):
            emoji: 🧘
            title: Challenge Title
            description: A short encouraging description.

            Generate 3 personalized challenges now, considering their recent emotional state. Keep it simple and supportive."""
            
            response = model.generate_content(prompt)
            ai_output = response.text.strip()
            
            # Parse the response into challenge dictionaries
            challenges = []
            current_challenge = {}
            
            for line in ai_output.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('emoji:'):
                    if current_challenge:
                        challenges.append(current_challenge)
                    current_challenge = {'emoji': line.replace('emoji:', '').strip()}
                elif line.startswith('title:'):
                    current_challenge['title'] = line.replace('title:', '').strip()
                elif line.startswith('description:'):
                    current_challenge['description'] = line.replace('description:', '').strip()
            
            # Add the last challenge
            if current_challenge and 'emoji' in current_challenge:
                challenges.append(current_challenge)
            
            # Validate and use AI challenges if we got 3
            if len(challenges) >= 3:
                personalized_challenges = challenges[:3]
            
        except Exception as e:
            # If AI fails, use fallback challenges silently
            pass
    
    context = {
        'challenges': personalized_challenges,
    }
    
    return render(request, 'mindful_challenges.html', context)

@login_required(login_url='/login/')
def wellness_insights(request):
    """Wellness Insights page - Displays horizontal scrolling wellness metrics cards"""
    
    # Get all moods for the current user
    all_moods = Mood.objects.filter(user=request.user).order_by('-created_at')
    
    # Calculate total moods
    total_moods = all_moods.count()
    
    # Get most frequent mood
    mood_counts = all_moods.values('mood_type').annotate(count=Count('mood_type')).order_by('-count').first()
    most_frequent_mood = mood_counts['mood_type'] if mood_counts else "N/A"
    
    # Calculate mood streak (consecutive days tracked)
    mood_streak = 0
    if total_moods > 0:
        today = timezone.now().date()
        check_date = today
        
        for i in range(total_moods):
            mood_date = all_moods[i].created_at.date()
            if mood_date == check_date:
                mood_streak += 1
                check_date -= timedelta(days=1)
            else:
                break
    
    # Calculate emotional balance (positive vs neutral vs heavy)
    positive_moods = ['happy', 'peaceful', 'content', 'excited', 'grateful', 'energetic']
    neutral_moods = ['calm', 'neutral', 'okay', 'balanced']
    heavy_moods = ['sad', 'anxious', 'stressed', 'angry', 'overwhelmed', 'lonely']
    
    positive_count = all_moods.filter(mood_type__in=positive_moods).count()
    neutral_count = all_moods.filter(mood_type__in=neutral_moods).count()
    heavy_count = all_moods.filter(mood_type__in=heavy_moods).count()
    
    # Determine balance indicator
    if total_moods == 0:
        balance_indicator = "Getting Started"
        emotional_insight = "Start tracking to see your balance"
    else:
        if positive_count > (total_moods * 0.5):
            balance_indicator = "🌟 Thriving"
            emotional_insight = "You're in a positive state"
        elif neutral_count > (total_moods * 0.4):
            balance_indicator = "⚖️ Balanced"
            emotional_insight = "You're maintaining equilibrium"
        elif heavy_count > (total_moods * 0.4):
            balance_indicator = "🌙 Reflective"
            emotional_insight = "You're processing your emotions"
        else:
            balance_indicator = "🌈 Varied"
            emotional_insight = "You're experiencing different states"
    
    # Calculate positive percentage
    positive_percentage = int((positive_count / total_moods * 100)) if total_moods > 0 else 0
    
    # Calculate monthly entries
    from datetime import date
    current_month = timezone.now().strftime('%B')
    current_year = timezone.now().year
    monthly_entries = all_moods.filter(
        created_at__year=current_year,
        created_at__month=timezone.now().month
    ).count()
    
    context = {
        'total_moods': total_moods,
        'most_frequent_mood': most_frequent_mood.capitalize() if most_frequent_mood != "N/A" else "N/A",
        'mood_streak': mood_streak,
        'balance_indicator': balance_indicator,
        'emotional_insight': emotional_insight,
        'positive_percentage': positive_percentage,
        'monthly_entries': monthly_entries,
        'current_month': current_month,
    }
    
    return render(request, 'wellness_insights.html', context)

@login_required(login_url='/login/')
def personalized_playlist(request):
    """Personalized Playlist page - AI-generated music recommendations based on user's mood"""
    
    # Get the most recent mood from database
    recent_mood_obj = Mood.objects.filter(user=request.user).order_by('-created_at').first()
    recent_mood = recent_mood_obj.mood_type if recent_mood_obj else 'calm'
    recent_note = recent_mood_obj.note if recent_mood_obj else ''
    
    # Default playlists - fallback if AI fails
    fallback_playlists = {
        'happy': {
            'mood': 'Happy',
            'emoji': '😊',
            'songs': [
                {'artist': 'Pharrell Williams', 'title': 'Happy'},
                {'artist': 'Ben Folds', 'title': 'Not the Same'},
                {'artist': 'Walk the Moon', 'title': 'Shut Up and Dance'},
                {'artist': 'Lizzo', 'title': 'Good as Hell'},
                {'artist': 'MGMT', 'title': 'Kids'},
            ]
        },
        'calm': {
            'mood': 'Calm',
            'emoji': '🧘',
            'songs': [
                {'artist': 'Norah Jones', 'title': 'Don\'t Know Why'},
                {'artist': 'Enya', 'title': 'Only Time'},
                {'artist': 'Bon Iver', 'title': 'Holocene'},
                {'artist': 'Sigur Rós', 'title': 'Hoppípolla'},
                {'artist': 'The National', 'title': 'Bloodbuzz Ohio'},
            ]
        },
        'sad': {
            'mood': 'Sad',
            'emoji': '😢',
            'songs': [
                {'artist': 'Adele', 'title': 'Someone Like You'},
                {'artist': 'Radiohead', 'title': 'Fake Plastic Trees'},
                {'artist': 'Sam Smith', 'title': 'I\'m Not the Only One'},
                {'artist': 'Amy Winehouse', 'title': 'Back to Black'},
                {'artist': 'Nick Cave', 'title': 'Red Right Hand'},
            ]
        },
        'anxious': {
            'mood': 'Anxious',
            'emoji': '😰',
            'songs': [
                {'artist': 'Billie Eilish', 'title': 'breathe in'},
                {'artist': 'Florence + The Machine', 'title': 'Shake It Out'},
                {'artist': 'Coldplay', 'title': 'Fix You'},
                {'artist': 'The xx', 'title': 'Crystalised'},
                {'artist': 'Alt-J', 'title': 'Breezeblocks'},
            ]
        },
        'energetic': {
            'mood': 'Energetic',
            'emoji': '⚡',
            'songs': [
                {'artist': 'Queen', 'title': 'Don\'t Stop Me Now'},
                {'artist': 'The Killers', 'title': 'Mr. Brightside'},
                {'artist': 'Arctic Monkeys', 'title': 'Do I Wanna Know?'},
                {'artist': 'Dua Lipa', 'title': 'Don\'t Start Now'},
                {'artist': 'Tame Impala', 'title': 'The Less I Know The Better'},
            ]
        }
    }
    
    # Get appropriate playlist based on mood
    playlist = fallback_playlists.get(recent_mood.lower(), fallback_playlists['calm'])
    
    # Try to generate AI-enhanced recommendations
    try:
        genai.configure(api_key="")
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = f"""You are a music recommendation expert. Based on the user's current mood ({recent_mood}), 
        generate a brief playlist description (2-3 sentences) that explains why these songs would help them feel better.
        
        Make it warm, supportive, and encouraging. Focus on the emotional and therapeutic benefits of music.
        
        User's note: {recent_note if recent_note else 'No specific note provided'}
        
        Generate just the description, no songs list."""
        
        response = model.generate_content(prompt)
        playlist_description = response.text.strip()
    except:
        # Fallback description
        mood_descriptions = {
            'happy': 'Keep the good vibes flowing with uplifting tracks that celebrate joy and positivity.',
            'calm': 'Soothe your mind with gentle, peaceful music that helps you relax and find inner peace.',
            'sad': 'Allow yourself to feel and process your emotions with meaningful, reflective songs.',
            'anxious': 'Find comfort and grounding with music that eases tension and brings stability.',
            'energetic': 'Amplify your energy with dynamic, uplifting tracks that keep you moving forward.',
        }
        playlist_description = mood_descriptions.get(recent_mood.lower(), 
                                                    'Enjoy music tailored to your emotional needs right now.')
    
    context = {
        'playlist': playlist,
        'playlist_description': playlist_description,
        'user_mood': recent_mood.capitalize(),
        'username': request.user.username,
    }
    
    return render(request, 'personalized_playlist.html', context)

@login_required(login_url='/login/')
def mood_playlists(request):
    """Mood Playlists page - AI-generated playlists based on user's recent moods"""
    
    # Get last 4 moods for the user
    recent_moods = Mood.objects.filter(user=request.user).order_by('-created_at')[:4]
    
    # Format moods as text for AI
    mood_text = ', '.join([m.mood_type.capitalize() for m in recent_moods]) if recent_moods else 'calm, balanced'
    
    # Default fallback playlists in case AI fails
    fallback_playlists = [
        {
            'emoji': '😊',
            'title': 'Daily Boost',
            'description': 'Energize your day with uplifting melodies that inspire positivity and motivation.',
            'songs': [
                {'title': 'Good as Hell', 'artist': 'Lizzo'},
                {'title': 'Walking on Sunshine', 'artist': 'Katrina & The Waves'},
                {'title': 'Shut Up and Dance', 'artist': 'Walk the Moon'},
                {'title': 'Mr. Brightside', 'artist': 'The Killers'},
            ]
        },
        {
            'emoji': '🧘',
            'title': 'Calm Sanctuary',
            'description': 'Find peace and serenity with gentle soundscapes designed to soothe your mind.',
            'songs': [
                {'title': 'Only Time', 'artist': 'Enya'},
                {'title': 'Don\'t Know Why', 'artist': 'Norah Jones'},
                {'title': 'Holocene', 'artist': 'Bon Iver'},
                {'title': 'Weightless', 'artist': 'Marconi Union'},
            ]
        },
        {
            'emoji': '💪',
            'title': 'Power Hour',
            'description': 'Unlock your strength with dynamic, motivating tracks that fuel your ambition.',
            'songs': [
                {'title': 'Don\'t Stop Me Now', 'artist': 'Queen'},
                {'title': 'Eye of the Tiger', 'artist': 'Survivor'},
                {'title': 'Take On Me', 'artist': 'a-ha'},
                {'title': 'Don\'t Start Now', 'artist': 'Dua Lipa'},
            ]
        },
        {
            'emoji': '🌙',
            'title': 'Evening Unwind',
            'description': 'Transition into relaxation with calming tracks perfect for winding down your day.',
            'songs': [
                {'title': 'Someone Like You', 'artist': 'Adele'},
                {'title': 'Fake Plastic Trees', 'artist': 'Radiohead'},
                {'title': 'The Night We Met', 'artist': 'Lord Huron'},
                {'title': 'Back to Black', 'artist': 'Amy Winehouse'},
            ]
        },
        {
            'emoji': '🌈',
            'title': 'Mood Lifter',
            'description': 'Shift your perspective with songs that blend joy, hope, and gentle inspiration.',
            'songs': [
                {'title': 'Here Comes the Sun', 'artist': 'The Beatles'},
                {'title': 'Good Life', 'artist': 'Kanye West'},
                {'title': 'Three Little Birds', 'artist': 'Bob Marley'},
                {'title': 'Walking on Air', 'artist': 'Kerrie Roberts'},
            ]
        },
    ]
    
    playlists = fallback_playlists
    
    # Try to generate AI-powered playlists
    try:
        genai.configure(api_key="")
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = f"""You are a music therapy expert. Based on the user's recent moods ({mood_text}), 
        generate EXACTLY 5 personalized playlists. Each playlist should be tailored to help them emotionally.

        For EACH playlist, provide ONLY:
        emoji: (one appropriate emoji)
        title: (2-3 words, creative and catchy)
        description: (one supportive, encouraging sentence about how this playlist helps)
        tracks: (3-5 song/meditation titles with artist names, format: "Song Title - Artist Name")

        Format your response EXACTLY like this (repeat 5 times):
        emoji: 🎵
        title: Playlist Name
        description: A supportive description about this playlist's benefits.
        tracks:
        - Song Title 1 - Artist Name 1
        - Song Title 2 - Artist Name 2
        - Song Title 3 - Artist Name 3
        - Song Title 4 - Artist Name 4

        Generate 5 diverse, mood-appropriate playlists now. Focus on real, well-known songs and artists."""
        
        response = model.generate_content(prompt)
        ai_output = response.text.strip()
        
        # Parse the AI response into playlist dictionaries
        playlists = []
        current_playlist = {}
        current_tracks = []
        
        for line in ai_output.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('emoji:'):
                if current_playlist and 'emoji' in current_playlist:
                    if current_tracks:
                        current_playlist['songs'] = [
                            {'title': t.split(' - ')[0].strip(), 'artist': t.split(' - ')[1].strip()}
                            for t in current_tracks if ' - ' in t
                        ]
                    playlists.append(current_playlist)
                    current_tracks = []
                current_playlist = {'emoji': line.replace('emoji:', '').strip()}
            
            elif line.startswith('title:'):
                current_playlist['title'] = line.replace('title:', '').strip()
            
            elif line.startswith('description:'):
                current_playlist['description'] = line.replace('description:', '').strip()
            
            elif line.startswith('tracks:'):
                # Next lines will be the tracks
                continue
            
            elif line.startswith('- '):
                # This is a track line
                track = line.replace('- ', '').strip()
                current_tracks.append(track)
        
        # Add the last playlist
        if current_playlist and 'emoji' in current_playlist:
            if current_tracks:
                current_playlist['songs'] = [
                    {'title': t.split(' - ')[0].strip(), 'artist': t.split(' - ')[1].strip()}
                    for t in current_tracks if ' - ' in t
                ]
            playlists.append(current_playlist)
        
        # Validate we got 5 playlists with all required fields
        validated_playlists = []
        for p in playlists:
            if all(k in p for k in ['emoji', 'title', 'description', 'songs']) and len(p.get('songs', [])) >= 3:
                validated_playlists.append(p)
        
        # Use AI playlists if we got at least 5 valid ones
        if len(validated_playlists) >= 5:
            playlists = validated_playlists[:5]
        
    except Exception as e:
        # If AI fails, use fallback playlists silently
        pass
    
    context = {
        'playlists': playlists,
        'username': request.user.username,
        'mood_count': recent_moods.count(),
        'recent_moods': mood_text,
    }
    
    return render(request, 'mood_playlists.html', context)


@login_required(login_url='/login/')
def mood_history(request):
    """Mood History page - Shows user's past mood entries with filtering and pagination"""
    
    # Get all moods for the user
    moods = Mood.objects.filter(user=request.user).order_by('-created_at')
    
    # Apply filters
    sort_by = request.GET.get('sort', 'newest')
    mood_filter = request.GET.get('mood', '')
    
    if sort_by == 'oldest':
        moods = moods.order_by('created_at')
    else:
        moods = moods.order_by('-created_at')
    
    if mood_filter:
        moods = moods.filter(mood_type__iexact=mood_filter)
    
    # Calculate statistics
    total_entries = Mood.objects.filter(user=request.user).count()
    
    # Most common mood
    most_common_mood = 'N/A'
    if total_entries > 0:
        mood_counts = Mood.objects.filter(user=request.user).values('mood_type').annotate(count=Count('id')).order_by('-count')
        if mood_counts.exists():
            most_common_mood = mood_counts[0]['mood_type']
    
    # Entries this month
    current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_entries = Mood.objects.filter(user=request.user, created_at__gte=current_month_start).count()
    
    # Average entries per week
    seven_days_ago = timezone.now() - timedelta(days=7)
    week_entries = Mood.objects.filter(user=request.user, created_at__gte=seven_days_ago).count()
    avg_per_week = week_entries
    
    # Pagination - 20 entries per page
    paginator = Paginator(moods, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'moods': page_obj.object_list,
        'page_obj': page_obj,
        'total_entries': total_entries,
        'most_common_mood': most_common_mood,
        'month_entries': month_entries,
        'avg_per_week': avg_per_week,
        'username': request.user.username,
        'current_sort': sort_by,
        'current_mood_filter': mood_filter,
    }
    
    return render(request, 'mood_history.html', context)