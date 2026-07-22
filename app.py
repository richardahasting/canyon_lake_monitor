import logging
import logging.handlers
from flask import Flask, jsonify, render_template, request, abort
from canyon_lake_data import CanyonLakeMonitor
from bot_detector import detect_bot
import os
import json
import threading
import time
from datetime import datetime, timedelta
import ipaddress
from dotenv import load_dotenv

load_dotenv()

# Configure logging: INFO+ to app.log, WARNING+ to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
monitor = CanyonLakeMonitor()

# Hit counter configuration
HITS_FILE = 'hits.json'
hits_lock = threading.Lock()

# Feedback rate limiting: {ip: [submission_timestamps]}
FEEDBACK_MAX_PER_HOUR = 3
feedback_lock = threading.Lock()
feedback_submissions = {}

def feedback_rate_limited(ip_address):
    """True if this IP has already submitted FEEDBACK_MAX_PER_HOUR in the last hour."""
    now = time.time()
    with feedback_lock:
        recent = [t for t in feedback_submissions.get(ip_address, []) if now - t < 3600]
        if len(recent) >= FEEDBACK_MAX_PER_HOUR:
            feedback_submissions[ip_address] = recent
            return True
        recent.append(now)
        feedback_submissions[ip_address] = recent
        return False

def client_ip():
    """Client IP, honoring X-Forwarded-For from the nginx proxy."""
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip_address and ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()
    return ip_address

# Analytics access control
ALLOWED_ANALYTICS_IPS = [
    '69.166.66.114',
    '127.0.0.1',
    '192.168.0.0/24'  # 192.168.0.* range
]

def is_ip_allowed(ip_str):
    """Check if IP address is allowed to access analytics"""
    try:
        ip = ipaddress.ip_address(ip_str)
        for allowed in ALLOWED_ANALYTICS_IPS:
            if '/' in allowed:
                # It's a network range
                if ip in ipaddress.ip_network(allowed, strict=False):
                    return True
            else:
                # It's a single IP
                if str(ip) == allowed:
                    return True
        return False
    except ValueError:
        return False

def load_hits():
    """Load hit counter from file"""
    try:
        with hits_lock:
            if os.path.exists(HITS_FILE):
                with open(HITS_FILE, 'r') as f:
                    data = json.load(f)
                    # Ensure new fields exist for backward compatibility
                    if 'unique_ips' not in data:
                        data['unique_ips'] = []
                    if 'recent_hits' not in data:
                        data['recent_hits'] = []
                    # New: permanent tracking of all unique visitors
                    if 'all_time_human_ips' not in data:
                        data['all_time_human_ips'] = {}  # {ip: first_seen_timestamp}
                    if 'all_time_bot_ips' not in data:
                        data['all_time_bot_ips'] = {}  # {ip: first_seen_timestamp}
                    return data
            return {'total': 0, 'routes': {}, 'first_hit': None, 'last_hit': None,
                    'unique_ips': [], 'recent_hits': [],
                    'all_time_human_ips': {}, 'all_time_bot_ips': {}}
    except Exception as e:
        logger.error("Error loading hits from %s: %s", HITS_FILE, e)
        return {'total': 0, 'routes': {}, 'first_hit': None, 'last_hit': None,
                'unique_ips': [], 'recent_hits': [],
                'all_time_human_ips': {}, 'all_time_bot_ips': {}}

def save_hits(hits_data):
    """Save hit counter to file"""
    try:
        with hits_lock:
            with open(HITS_FILE, 'w') as f:
                json.dump(hits_data, f, indent=2)
    except Exception as e:
        logger.error("Error saving hits to %s: %s", HITS_FILE, e)

def increment_hit_counter(route, ip_address, user_agent=None):
    """
    Increment hit counter for a specific route and track IP with bot detection.

    Args:
        route: The URL route being accessed
        ip_address: The client IP address
        user_agent: The User-Agent header (optional for backward compatibility)
    """
    hits_data = load_hits()
    hits_data['total'] = hits_data.get('total', 0) + 1

    if route not in hits_data['routes']:
        hits_data['routes'][route] = 0
    hits_data['routes'][route] += 1

    now = datetime.now().isoformat()
    if not hits_data.get('first_hit'):
        hits_data['first_hit'] = now
    hits_data['last_hit'] = now

    # Detect if this is a bot
    bot_info = detect_bot(user_agent) if user_agent else {'is_bot': False, 'category': None, 'matched_pattern': None}

    # Track unique IPs (separate for humans and bots)
    if ip_address not in hits_data['unique_ips']:
        hits_data['unique_ips'].append(ip_address)

    # Track all-time unique visitors permanently (separate humans and bots)
    if bot_info['is_bot']:
        if ip_address not in hits_data['all_time_bot_ips']:
            hits_data['all_time_bot_ips'][ip_address] = now
    else:
        if ip_address not in hits_data['all_time_human_ips']:
            hits_data['all_time_human_ips'][ip_address] = now

    # Add to recent hits (keep last 100)
    hit_record = {
        'timestamp': now,
        'route': route,
        'ip': ip_address,
        'user_agent': user_agent or 'unknown',
        'is_bot': bot_info['is_bot'],
        'bot_category': bot_info['category'],
        'bot_pattern': bot_info['matched_pattern']
    }
    hits_data['recent_hits'].append(hit_record)

    # Keep only the last 100 hits
    if len(hits_data['recent_hits']) > 100:
        hits_data['recent_hits'] = hits_data['recent_hits'][-100:]

    save_hits(hits_data)

@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    # Content Security Policy - allow inline scripts/styles for Chart.js and our site
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' https://waterservices.usgs.gov https://api.weather.gov; "
        "frame-ancestors 'none';"
    )
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # Enforce HTTPS (when deployed with HTTPS)
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    # Control referrer information
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # XSS protection (legacy browsers)
    response.headers['X-XSS-Protection'] = '1; mode=block'

    return response

@app.before_request
def track_hits():
    """Track page hits for main routes with bot detection"""
    if request.endpoint in ['index', 'chart']:
        # Get IP address, handle proxy forwarding
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip_address and ',' in ip_address:
            # X-Forwarded-For can contain multiple IPs, take the first one
            ip_address = ip_address.split(',')[0].strip()

        # Get User-Agent for bot detection
        user_agent = request.headers.get('User-Agent', '')

        increment_hit_counter(request.path, ip_address, user_agent)

@app.route('/')
def index():
    # Check if current IP can access analytics
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip_address and ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()
    show_analytics = is_ip_allowed(ip_address)
    return render_template('index.html', show_analytics=show_analytics)

@app.route('/chart')
def chart():
    # Check if current IP can access analytics
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip_address and ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()
    show_analytics = is_ip_allowed(ip_address)
    return render_template('chart.html', show_analytics=show_analytics)

@app.route('/analytics')
def analytics():
    # Get client IP address
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip_address and ',' in ip_address:
        # X-Forwarded-For can contain multiple IPs, take the first one
        ip_address = ip_address.split(',')[0].strip()

    # Check if IP is allowed
    if not is_ip_allowed(ip_address):
        abort(403)  # Forbidden

    return render_template('analytics.html')

@app.route('/community-info')
def community_info():
    return render_template('community-info.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/api/status')
def get_status():
    status = monitor.get_lake_status()
    return jsonify(status)

@app.route('/api/history')
def get_history():
    historical_data = monitor.fetch_historical_data(30)
    if historical_data:
        return jsonify({
            'status': 'success',
            'data': historical_data['lake_data']
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'Unable to fetch historical data'
        })

@app.route('/api/flow-12hr')
def get_flow_12hr():
    flow_data = monitor.fetch_river_flow_12hr(30)
    if flow_data:
        return jsonify({
            'status': 'success',
            'data': flow_data
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'Unable to fetch flow data'
        })

@app.route('/api/stats')
def get_stats():
    """
    Get hit counter statistics with bot vs human separation.

    Returns comprehensive analytics including:
    - Total hits (all, human, bot)
    - Unique visitors by time period (24h, 7d, all-time)
    - Bot category breakdown
    - Recent hits with bot classification
    """
    hits_data = load_hits()

    # Calculate unique visitors for different time periods
    now = datetime.now()
    twenty_four_hours_ago = now - timedelta(hours=24)
    seven_days_ago = now - timedelta(days=7)

    # Separate tracking for humans and bots
    unique_humans_24h = set()
    unique_humans_7d = set()
    unique_bots_24h = set()
    unique_bots_7d = set()

    # Bot category counters
    bot_categories = {}
    bot_categories_24h = {}
    bot_categories_7d = {}

    # Hit counters
    human_hits = 0
    bot_hits = 0

    # Process recent hits for time-limited stats (24h, 7d) and bot categories
    for hit in hits_data.get('recent_hits', []):
        try:
            hit_time = datetime.fromisoformat(hit['timestamp'])
            ip = hit['ip']
            is_bot = hit.get('is_bot', False)
            bot_category = hit.get('bot_category', None)

            # Count total hits by type
            if is_bot:
                bot_hits += 1
            else:
                human_hits += 1

            # Track unique IPs by type and time period (only for 24h and 7d)
            if is_bot:
                if bot_category:
                    bot_categories[bot_category] = bot_categories.get(bot_category, 0) + 1

                if hit_time >= twenty_four_hours_ago:
                    unique_bots_24h.add(ip)
                    if bot_category:
                        bot_categories_24h[bot_category] = bot_categories_24h.get(bot_category, 0) + 1

                if hit_time >= seven_days_ago:
                    unique_bots_7d.add(ip)
                    if bot_category:
                        bot_categories_7d[bot_category] = bot_categories_7d.get(bot_category, 0) + 1
            else:
                if hit_time >= twenty_four_hours_ago:
                    unique_humans_24h.add(ip)

                if hit_time >= seven_days_ago:
                    unique_humans_7d.add(ip)

        except (ValueError, KeyError) as e:
            logger.warning("Error processing hit record: %s", e)
            continue

    # All-time counts come from permanent tracking (not limited to recent_hits)
    unique_humans_all = len(hits_data.get('all_time_human_ips', {}))
    unique_bots_all = len(hits_data.get('all_time_bot_ips', {}))

    # Build comprehensive response
    response = {
        'status': 'success',
        'stats': {
            # Legacy fields for backward compatibility
            'total': hits_data.get('total', 0),
            'routes': hits_data.get('routes', {}),
            'first_hit': hits_data.get('first_hit'),
            'last_hit': hits_data.get('last_hit'),
            'unique_ips': hits_data.get('unique_ips', []),
            'recent_hits': hits_data.get('recent_hits', []),

            # New: Hit counts by type
            'human_hits': human_hits,
            'bot_hits': bot_hits,

            # New: Unique visitors - Humans only
            'unique_humans_24h': len(unique_humans_24h),
            'unique_humans_7d': len(unique_humans_7d),
            'unique_humans_all': unique_humans_all,  # Already a count from permanent tracking

            # New: Unique visitors - Bots only
            'unique_bots_24h': len(unique_bots_24h),
            'unique_bots_7d': len(unique_bots_7d),
            'unique_bots_all': unique_bots_all,  # Already a count from permanent tracking

            # New: Bot category breakdown
            'bot_categories': bot_categories,
            'bot_categories_24h': bot_categories_24h,
            'bot_categories_7d': bot_categories_7d,

            # Legacy: Combined unique visitors (kept for backward compatibility)
            'unique_visitors_24h': len(unique_humans_24h) + len(unique_bots_24h),
            'unique_visitors_7d': len(unique_humans_7d) + len(unique_bots_7d),
        }
    }

    return jsonify(response)

@app.route('/api/environment')
def get_environment():
    """Get environmental data: weather, moon phase, and day/night status"""
    env_data = monitor.get_environment_data()
    return jsonify(env_data)

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """
    Accept visitor feedback and route it via feedback.py
    (bugs/suggestions -> GitHub issue, everything else -> email).

    The site is anonymous, so this endpoint defends itself:
    honeypot field, bot User-Agent screening, and a per-IP rate limit.
    Bots and honeypot hits get a fake success so they don't probe further.
    """
    import feedback as fb

    ip_address = client_ip()
    user_agent = request.headers.get('User-Agent', '')

    # Honeypot: real users never see or fill the 'website' field
    if request.form.get('website', '').strip():
        logger.info("Feedback honeypot triggered from %s", ip_address)
        return jsonify({'ok': True, 'action': 'email'})

    bot_info = detect_bot(user_agent) if user_agent else {'is_bot': True}
    if bot_info.get('is_bot'):
        logger.info("Feedback from bot UA rejected: %s (%s)", ip_address, user_agent)
        return jsonify({'ok': True, 'action': 'email'})

    text = request.form.get('feedback_text', '').strip()
    if len(text) < 10:
        return jsonify({'ok': False,
                        'error': 'Please describe your feedback (at least 10 characters).'}), 400
    if len(text) > 4000:
        return jsonify({'ok': False,
                        'error': 'Feedback must be 4000 characters or fewer.'}), 400

    name = request.form.get('name', '').strip()[:100]
    email = request.form.get('email', '').strip()[:200]
    if email and '@' not in email:
        return jsonify({'ok': False, 'error': 'That email address does not look right.'}), 400
    page = request.form.get('page', '').strip()[:200]

    # Rate-limit only submissions that passed validation, so a visitor who
    # trips the length checks a few times isn't locked out for an hour.
    if feedback_rate_limited(ip_address):
        return jsonify({'ok': False,
                        'error': 'Too many submissions. Please try again later.'}), 429

    logger.info("Feedback submission from %s (page=%s, %d chars)",
                ip_address, page, len(text))
    ok, action, github_url = fb.process_feedback(name, email, text, page)
    if not ok:
        return jsonify({'ok': False,
                        'error': 'Could not deliver your feedback. Please try again.'}), 500
    return jsonify({'ok': True, 'action': action, 'github_url': github_url})

@app.route('/robots.txt')
def robots_txt():
    """Serve robots.txt for search engine crawlers"""
    from flask import send_from_directory
    return send_from_directory('static', 'robots.txt', mimetype='text/plain')

@app.route('/sitemap.xml')
def sitemap_xml():
    """Serve sitemap.xml for search engines"""
    from flask import send_from_directory
    return send_from_directory('static', 'sitemap.xml', mimetype='application/xml')

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    app.run(debug=False, host='0.0.0.0', port=8081)