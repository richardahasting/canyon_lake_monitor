from flask import Flask, jsonify, render_template, request
from canyon_lake_data import CanyonLakeMonitor
import os
import json
import threading
from datetime import datetime

app = Flask(__name__)
monitor = CanyonLakeMonitor()

# Hit counter configuration
HITS_FILE = 'hits.json'
hits_lock = threading.Lock()

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

def increment_hit_counter(route, ip_address):
    """Increment hit counter for a specific route and track IP"""
    hits_data = load_hits()
    hits_data['total'] = hits_data.get('total', 0) + 1

    if route not in hits_data['routes']:
        hits_data['routes'][route] = 0
    hits_data['routes'][route] += 1

    now = datetime.now().isoformat()
    if not hits_data.get('first_hit'):
        hits_data['first_hit'] = now
    hits_data['last_hit'] = now

    # Track unique IPs
    if ip_address not in hits_data['unique_ips']:
        hits_data['unique_ips'].append(ip_address)

    # Add to recent hits (keep last 100)
    hits_data['recent_hits'].append({
        'timestamp': now,
        'route': route,
        'ip': ip_address
    })
    # Keep only the last 100 hits
    if len(hits_data['recent_hits']) > 100:
        hits_data['recent_hits'] = hits_data['recent_hits'][-100:]

    save_hits(hits_data)

@app.before_request
def track_hits():
    """Track page hits for main routes"""
    if request.endpoint in ['index', 'chart']:
        # Get IP address, handle proxy forwarding
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip_address and ',' in ip_address:
            # X-Forwarded-For can contain multiple IPs, take the first one
            ip_address = ip_address.split(',')[0].strip()
        increment_hit_counter(request.path, ip_address)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chart')
def chart():
    return render_template('chart.html')

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
    """Get hit counter statistics"""
    hits_data = load_hits()
    return jsonify({
        'status': 'success',
        'stats': hits_data
    })

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    app.run(debug=False, host='0.0.0.0', port=8081)