"""
CloudLab Intelligence - Analytics Engine
Implements Rule-Based Activity Classification, Context-Switch Analysis, and Session Duration Analytics.
"""

import re
from urllib.parse import urlparse

# Rule sets for activity classification
AI_CHATBOT_DOMAINS = [
    "chatgpt.com", "openai.com", "chat.openai.com", "gemini.google.com",
    "bard.google.com", "claude.ai", "anthropic.com", "deepseek.com",
    "chat.deepseek.com", "perplexity.ai", "blackbox.ai", "phind.com",
    "v0.dev", "cursor.com", "copilot.microsoft.com", "poe.com", "you.com",
    "qwenlm.ai", "mistral.ai", "groq.com", "chat.mistral.ai"
]

AI_CHATBOT_APPS = [
    "chatgpt", "claude", "cursor", "copilot", "perplexity"
]

PROGRAMMING_KEYWORDS = [
    "code", "vscode", "pycharm", "eclipse", "intellij", "sublime", "vim", "nvim",
    "terminal", "cmd", "powershell", "bash", "python", "gcc", "g++", "clang",
    "java", "javac", "node", "npm", "cargo", "go", "clion", "devcpp", "netbeans",
    "jupyter", "colab", "git"
]

DATABASE_KEYWORDS = [
    "mysql", "workbench", "pgadmin", "dbeaver", "mongodb", "compass", "sqlite",
    "phpmyadmin", "oracle", "sql developer", "datagrip", "redis", "postman", "insomnia"
]

RESEARCH_DOMAINS = [
    "stackoverflow.com", "github.com", "geeksforgeeks.org", "w3schools.com",
    "developer.mozilla.org", "docs.python.org", "aws.amazon.com", "martinfowler.com",
    "leetcode.com", "hackerrank.com", "coursera.org", "edx.org", "nptel.ac.in",
    "sonatech.ac.in", "sonaversity.org", "wikipedia.org", "medium.com", "dev.to",
    "sciencedirect.com", "ieeexplore.ieee.org", "springer.com", "kaggle.com",
    "fastapi.tiangolo.com", "flask.palletsprojects.com", "react.dev", "angular.io"
]

DOCUMENTATION_KEYWORDS = [
    "word", "winword", "docs.google.com", "overleaf.com", "notion", "obsidian",
    "powerpoint", "excel", "acrobat", "pdf", "latex", "canva.com", "draw.io", "miro.com"
]

OFF_TASK_DOMAINS = [
    "instagram.com", "facebook.com", "twitter.com", "x.com", "reddit.com",
    "netflix.com", "primevideo.com", "twitch.tv", "tiktok.com", "pinterest.com",
    "chess.com", "crazygames.com", "spotify.com", "discord.com"
]

OFF_TASK_APPS = [
    "spotify", "discord", "steam", "epicgames", "vlc", "game", "torrent"
]


def extract_domain(url_or_str):
    """Safely extracts domain name from URL or browser window title."""
    if not url_or_str:
        return ""
    
    url_or_str = str(url_or_str).strip().lower()
    if url_or_str.startswith("http://") or url_or_str.startswith("https://"):
        try:
            parsed = urlparse(url_or_str)
            return parsed.netloc.replace("www.", "")
        except Exception:
            pass
            
    # Check known popular domains directly
    known_domains = [
        "chatgpt.com", "deepseek.com", "openai.com", "claude.ai", "gemini.google.com",
        "stackoverflow.com", "github.com", "geeksforgeeks.org", "w3schools.com",
        "google.com", "youtube.com", "leetcode.com", "hackerrank.com",
        "overleaf.com", "notion.so", "reddit.com", "instagram.com", "medium.com"
    ]
    for kd in known_domains:
        if kd.split(".")[0] in url_or_str or kd in url_or_str:
            return kd

    domain_match = re.search(r'([a-zA-Z0-9-]+\.(?:com|org|edu|in|io|gov|net|dev|ac\.in))', url_or_str)
    if domain_match:
        return domain_match.group(1).replace("www.", "")
        
    return url_or_str


def sanitize_tab_title(window_title, app_name=""):
    """
    Cleans browser window title by stripping browser suffixes like '- Google Chrome', '- Microsoft Edge'.
    Example: 'Dijkstra Algorithm - GeeksforGeeks - Google Chrome' -> 'Dijkstra Algorithm - GeeksforGeeks'
    """
    if not window_title:
        return ""
    title = window_title
    for suffix in [" - Google Chrome", " - Microsoft Edge", " - Mozilla Firefox", " - Brave", " - Opera"]:
        if title.endswith(suffix):
            title = title[:-len(suffix)]
            break
    return title.strip()


def classify_activity(app_name="", window_title="", browser_domain=""):
    """
    Rule-Based Activity Classification Algorithm:
    Categorizes student activity into:
    - AI Assistance (ChatGPT, Claude, Gemini, DeepSeek, Copilot, etc.)
    - Programming
    - Database
    - Research & Learning
    - Documentation
    - Off-Task / Entertainment
    - General
    """
    app_lower = (app_name or "").lower()
    title_lower = (window_title or "").lower()
    domain_lower = extract_domain(browser_domain or "").lower()

    # 1. Check AI Chatbots / LLM tools first (Critical for assessment monitoring)
    for ai_dom in AI_CHATBOT_DOMAINS:
        if ai_dom in domain_lower or ai_dom in title_lower:
            return "AI Assistance"

    for ai_app in AI_CHATBOT_APPS:
        if ai_app in app_lower:
            return "AI Assistance"

    # 2. Check Off-task / Entertainment
    for off_dom in OFF_TASK_DOMAINS:
        if off_dom in domain_lower or off_dom in title_lower:
            return "Off-Task"
            
    for off_app in OFF_TASK_APPS:
        if off_app in app_lower:
            return "Off-Task"

    # YouTube: classify as Research/Learning if tutorial/lecture, else Off-Task
    if "youtube.com" in domain_lower or "youtube" in title_lower:
        edu_cues = ["tutorial", "lecture", "course", "algorithm", "python", "java", "database", "coding", "sona", "cloud"]
        if any(cue in title_lower for cue in edu_cues):
            return "Research & Learning"
        return "Off-Task"

    # 2. Check Database tools
    for db_kw in DATABASE_KEYWORDS:
        if db_kw in app_lower or db_kw in title_lower or db_kw in domain_lower:
            return "Database"

    # 3. Check Programming IDEs & tools
    for prog_kw in PROGRAMMING_KEYWORDS:
        if prog_kw in app_lower or prog_kw in title_lower:
            return "Programming"

    # 4. Check Research & Learning domains
    for res_dom in RESEARCH_DOMAINS:
        if res_dom in domain_lower or res_dom in title_lower:
            return "Research & Learning"

    # 5. Check Documentation
    for doc_kw in DOCUMENTATION_KEYWORDS:
        if doc_kw in app_lower or doc_kw in title_lower or doc_kw in domain_lower:
            return "Documentation"

    # Browsers default to Research & Learning if not off-task
    if any(b in app_lower for b in ["chrome", "msedge", "firefox", "brave", "safari"]):
        if domain_lower:
            return "Research & Learning"

    return "General"


def analyze_context_switches(events, is_assessment_mode=False):
    """
    Context-Switch Analysis Algorithm:
    Evaluates switching frequency between applications and browser tabs,
    and computes a Focus Score (0 - 100%) along with a Distraction Index.
    
    Formula:
    - Focus Score base = 100.0
    - Context switch penalty: If switches per hour > 20, subtract 0.8 pts per excess switch
    - Off-task penalty: Subtract 1.5 * (Off-task duration / Total duration * 100)
    - AI penalty: ONLY deducted when Assessment Mode is ON (2.0 * AI%)
    - Idle penalty: Subtract 0.5 * (Idle duration / Total duration * 100)
    - Focus Score clamped to [10.0, 100.0]
    """
    if not events:
        return {
            "total_switches": 0,
            "switches_per_hour": 0.0,
            "avg_task_duration_sec": 0.0,
            "focus_score": 100.0,
            "distraction_index": 0.0,
            "rating": "Excellent"
        }

    total_duration = sum(e.get("duration_seconds", 0) for e in events) or 1
    total_switches = sum(1 for e in events if e.get("is_tab_switch", 0) == 1)
    
    # Calculate switches per hour
    duration_hours = max(total_duration / 3600.0, 0.1)
    switches_per_hour = round(total_switches / duration_hours, 1)

    # Calculate average task interval duration
    valid_intervals = [e.get("duration_seconds", 5) for e in events if e.get("duration_seconds", 0) > 0]
    avg_task_duration = round(sum(valid_intervals) / max(len(valid_intervals), 1), 1)

    # Durations by category
    off_task_sec = sum(e.get("duration_seconds", 0) for e in events if e.get("category") == "Off-Task")
    ai_sec = sum(e.get("duration_seconds", 0) for e in events if e.get("category") == "AI Assistance")
    idle_sec = sum(e.get("duration_seconds", 0) for e in events if e.get("is_idle", 0) == 1)

    off_task_pct = (off_task_sec / total_duration) * 100.0
    ai_pct = (ai_sec / total_duration) * 100.0
    idle_pct = (idle_sec / total_duration) * 100.0

    # Focus / Integrity Score Computation
    excess_switches = max(0, switches_per_hour - 20)
    switch_penalty = excess_switches * 0.8
    off_task_penalty = off_task_pct * 1.5
    ai_penalty = (ai_pct * 2.0) if is_assessment_mode else 0.0  # Penalize AI ONLY during active assessments
    idle_penalty = idle_pct * 0.5

    focus_score = 100.0 - switch_penalty - off_task_penalty - ai_penalty - idle_penalty
    focus_score = max(10.0, min(100.0, round(focus_score, 1)))

    distraction_index = min(100.0, round((off_task_penalty + ai_penalty + switch_penalty + idle_penalty) / 1.5, 1))

    if is_assessment_mode and ai_sec > 0:
        rating = "🚨 AI Malpractice Detected (Assessment Mode)"
    elif not is_assessment_mode and ai_sec > 0:
        rating = "🤖 AI-Assisted Learning (Authorized)"
    elif focus_score >= 85:
        rating = "Highly Focused"
    elif focus_score >= 70:
        rating = "Good Engagement"
    elif focus_score >= 50:
        rating = "Moderate / Frequent Context Switches"
    else:
        rating = "High Distraction / Needs Guidance"

    return {
        "total_switches": total_switches,
        "switches_per_hour": switches_per_hour,
        "avg_task_duration_sec": avg_task_duration,
        "focus_score": focus_score,
        "distraction_index": distraction_index,
        "ai_sec": ai_sec,
        "ai_pct": round(ai_pct, 1),
        "rating": rating
    }


def compute_student_summary(session, events, is_assessment_mode=False):
    """
    Computes complete statistical breakdown for a student session.
    """
    total_sec = sum(e.get("duration_seconds", 0) for e in events)
    active_sec = sum(e.get("duration_seconds", 0) for e in events if not e.get("is_idle", 0))
    idle_sec = sum(e.get("duration_seconds", 0) for e in events if e.get("is_idle", 0))

    # Category breakdown
    categories = {}
    ai_events = []
    for e in events:
        cat = e.get("category", "General")
        categories[cat] = categories.get(cat, 0) + e.get("duration_seconds", 0)
        if cat == "AI Assistance":
            ai_events.append({
                "app": e.get("app_name"),
                "domain": e.get("browser_domain") or e.get("window_title"),
                "duration_sec": e.get("duration_seconds", 5),
                "timestamp": e.get("timestamp")
            })

    # App usage breakdown
    app_usage = {}
    for e in events:
        app = e.get("app_name", "Unknown")
        app_usage[app] = app_usage.get(app, 0) + e.get("duration_seconds", 0)

    # Browser tab / domain breakdown
    domain_usage = {}
    tab_titles = []
    for e in events:
        dom = e.get("browser_domain") or extract_domain(e.get("window_title", ""))
        if dom and dom not in ["", "unknown", "None"]:
            domain_usage[dom] = domain_usage.get(dom, 0) + e.get("duration_seconds", 0)
        
        tab_title = e.get("browser_tab_title") or e.get("window_title")
        if tab_title and tab_title not in tab_titles:
            tab_titles.append(tab_title)

    # Context switch analysis
    switch_stats = analyze_context_switches(events, is_assessment_mode=is_assessment_mode)

    return {
        "session_id": session.get("session_id"),
        "reg_no": session.get("reg_no"),
        "student_name": session.get("student_name"),
        "lab_id": session.get("lab_id"),
        "pc_id": session.get("pc_id"),
        "login_time": session.get("login_time"),
        "logout_time": session.get("logout_time"),
        "status": session.get("status"),
        "total_duration_sec": total_sec,
        "active_duration_sec": active_sec,
        "idle_duration_sec": idle_sec,
        "active_pct": round((active_sec / max(total_sec, 1)) * 100, 1),
        "idle_pct": round((idle_sec / max(total_sec, 1)) * 100, 1),
        "categories": categories,
        "app_usage": app_usage,
        "domain_usage": domain_usage,
        "unique_tabs_count": len(tab_titles),
        "tab_titles": tab_titles[:25],
        "context_switches": switch_stats,
        "ai_violations": ai_events,
        "has_ai_violation": (len(ai_events) > 0 and is_assessment_mode),
        "is_assessment_mode": is_assessment_mode
    }
