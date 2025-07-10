from flask import Flask, jsonify, render_template
from canyon_lake_data import CanyonLakeMonitor
import os

app = Flask(__name__)
monitor = CanyonLakeMonitor()

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
            'data': historical_data
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'Unable to fetch historical data'
        })

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)