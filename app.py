from flask import Flask, jsonify, render_template, request, abort
from canyon_lake_data import CanyonLakeMonitor
from bot_detector import detect_bot
import os
import json
import threading
from datetime import datetime, timedelta
import ipaddress

app = Flask(__name__)
monitor = CanyonLakeMonitor()

# Hit counter configuration
HITS_FILE = 'hits.json'
hits_lock = threading.Lock()

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
                    return data
            return {'total': 0, 'routes': {}, 'first_hit': None, 'last_hit': None,
                    'unique_ips': [], 'recent_hits': []}
    except Exception as e:
        print(f"Error loading hits: {e}")
        return {'total': 0, 'routes': {}, 'first_hit': None, 'last_hit': None,
                'unique_ips': [], 'recent_hits': []}

def save_hits(hits_data):
    """Save hit counter to file"""
    try:
        with hits_lock:
            with open(HITS_FILE, 'w') as f:
                json.dump(hits_data, f, indent=2)
    except Exception as e:
        print(f"Error saving hits: {e}")

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
    unique_humans_all = set()
    unique_bots_24h = set()
    unique_bots_7d = set()
    unique_bots_all = set()

    # Bot category counters
    bot_categories = {}
    bot_categories_24h = {}
    bot_categories_7d = {}

    # Hit counters
    human_hits = 0
    bot_hits = 0

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

            # Track unique IPs by type and time period
            if is_bot:
                unique_bots_all.add(ip)
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
                unique_humans_all.add(ip)

                if hit_time >= twenty_four_hours_ago:
                    unique_humans_24h.add(ip)

                if hit_time >= seven_days_ago:
                    unique_humans_7d.add(ip)

        except (ValueError, KeyError) as e:
            print(f"Error processing hit record: {e}")
            continue

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
            'unique_humans_all': len(unique_humans_all),

            # New: Unique visitors - Bots only
            'unique_bots_24h': len(unique_bots_24h),
            'unique_bots_7d': len(unique_bots_7d),
            'unique_bots_all': len(unique_bots_all),

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