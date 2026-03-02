"""
PowerSaver Dashboard
Real-time monitoring web interface
"""

from flask import Flask, render_template_string, jsonify, request
import asyncio
import time

app = Flask(__name__)

# Global state
engine_state = {
    "is_running": False,
    "engine_type": None,
    "profit": 0.0,
    "trades": 0,
    "win_rate": 0.0,
    "positions": [],
    "prices": {},
    "logs": []
}

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>PowerSaver Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Courier New', monospace; 
            background: #0a0a0a; 
            color: #00ff00;
            min-height: 100vh;
        }
        
        .header {
            background: linear-gradient(90deg, #1a1a2e, #16213e);
            padding: 20px;
            border-bottom: 2px solid #00ff00;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 { font-size: 24px; }
        .status-badge {
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
        }
        .running { background: #00ff00; color: #000; }
        .stopped { background: #ff0000; color: #fff; }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            padding: 20px;
        }
        
        .stat-card {
            background: #1a1a2e;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #00ff00;
        }
        
        .stat-value { font-size: 32px; font-weight: bold; }
        .stat-label { color: #888; font-size: 14px; }
        
        .profit { color: #00ff00; }
        .loss { color: #ff0000; }
        
        .grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
            padding: 20px;
        }
        
        .panel {
            background: #1a1a2e;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #333;
        }
        
        .panel h2 { 
            margin-bottom: 15px; 
            border-bottom: 1px solid #333;
            padding-bottom: 10px;
        }
        
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #333; }
        th { color: #888; }
        
        .log-entry {
            padding: 8px;
            margin: 4px 0;
            background: #0a0a0a;
            border-radius: 4px;
            font-size: 12px;
        }
        .log-buy { border-left: 3px solid #00ff00; }
        .log-sell { border-left: 3px solid #ff0000; }
        .log-info { border-left: 3px solid #00aaff; }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            margin: 5px;
        }
        .btn-start { background: #00ff00; color: #000; }
        .btn-stop { background: #ff0000; color: #fff; }
        
        .prices { display: flex; gap: 20px; flex-wrap: wrap; }
        .price-card {
            background: #0a0a0a;
            padding: 15px;
            border-radius: 8px;
            min-width: 150px;
        }
        .price-token { color: #888; }
        .price-value { font-size: 24px; font-weight: bold; }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .live { animation: pulse 1s infinite; }
    </style>
</head>
<body>
    <div class="header">
        <h1>⚡ PowerSaver Dashboard</h1>
        <div>
            <span id="statusBadge" class="status-badge stopped">STOPPED</span>
        </div>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value" id="profit">0.00 ETH</div>
            <div class="stat-label">Total Profit</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" id="trades">0</div>
            <div class="stat-label">Total Trades</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" id="winRate">0%</div>
            <div class="stat-label">Win Rate</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" id="uptime">0s</div>
            <div class="stat-label">Uptime</div>
        </div>
    </div>
    
    <div class="grid">
        <div class="panel">
            <h2>📊 Live Prices</h2>
            <div class="prices" id="prices">
                <div class="price-card">
                    <div class="price-token">ETH</div>
                    <div class="price-value">$0.00</div>
                </div>
            </div>
            
            <h2 style="margin-top: 20px;">📋 Active Positions</h2>
            <table>
                <thead>
                    <tr>
                        <th>Token</th>
                        <th>Entry</th>
                        <th>Current</th>
                        <th>P&L</th>
                    </tr>
                </thead>
                <tbody id="positions">
                </tbody>
            </table>
            
            <h2 style="margin-top: 20px;">🎮 Controls</h2>
            <button class="btn btn-start" onclick="startEngine()">START</button>
            <button class="btn btn-stop" onclick="stopEngine()">STOP</button>
        </div>
        
        <div class="panel">
            <h2>📜 Activity Log</h2>
            <div id="logs" style="max-height: 500px; overflow-y: auto;">
            </div>
        </div>
    </div>
    
    <script>
        let startTime = null;
        
        async function update() {
            const resp = await fetch('/api/state');
            const state = await resp.json();
            
            // Update status
            const badge = document.getElementById('statusBadge');
            badge.textContent = state.is_running ? 'RUNNING' : 'STOPPED';
            badge.className = 'status-badge ' + (state.is_running ? 'running' : 'stopped');
            
            // Update stats
            document.getElementById('profit').textContent = 
                state.profit >= 0 ? '+' + state.profit.toFixed(4) + ' ETH' : state.profit.toFixed(4) + ' ETH';
            document.getElementById('profit').className = 'stat-value ' + (state.profit >= 0 ? 'profit' : 'loss');
            
            document.getElementById('trades').textContent = state.trades;
            document.getElementById('winRate').textContent = (state.win_rate * 100).toFixed(1) + '%';
            
            if (state.is_running && !startTime) startTime = Date.now();
            if (!state.is_running) startTime = null;
            
            if (startTime) {
                const uptime = Math.floor((Date.now() - startTime) / 1000);
                document.getElementById('uptime').textContent = uptime + 's';
            }
            
            // Update prices
            const pricesHtml = Object.entries(state.prices).map(([token, price]) => 
                `<div class="price-card">
                    <div class="price-token">${token}</div>
                    <div class="price-value live">$${price.toFixed(2)}</div>
                </div>`
            ).join('');
            document.getElementById('prices').innerHTML = pricesHtml;
            
            // Update positions
            const positionsHtml = state.positions.map(p => 
                `<tr>
                    <td>${p.token}</td>
                    <td>$${p.entry.toFixed(2)}</td>
                    <td>$${p.current.toFixed(2)}</td>
                    <td class="${p.pnl >= 0 ? 'profit' : 'loss'}">${p.pnl >= 0 ? '+' : ''}${p.pnl.toFixed(4)} ETH</td>
                </tr>`
            ).join('');
            document.getElementById('positions').innerHTML = positionsHtml || '<tr><td colspan="4">No positions</td></tr>';
            
            // Update logs
            const logsHtml = state.logs.slice(-20).reverse().map(log => 
                `<div class="log-entry log-${log.type}">[${log.time}] ${log.msg}</div>`
            ).join('');
            document.getElementById('logs').innerHTML = logsHtml;
        }
        
        async function startEngine() {
            await fetch('/api/start', { method: 'POST' });
            update();
        }
        
        async function stopEngine() {
            await fetch('/api/stop', { method: 'POST' });
            update();
        }
        
        setInterval(update, 1000);
        update();
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML)


@app.route('/api/state')
def get_state():
    return jsonify(engine_state)


@app.route('/api/start', methods=['POST'])
def start():
    engine_state['is_running'] = True
    engine_state['engine_type'] = 'ultimate'
    engine_state['logs'].append({
        'time': time.strftime('%H:%M:%S'),
        'type': 'info',
        'msg': 'Engine started'
    })
    return jsonify({'status': 'ok'})


@app.route('/api/stop', methods=['POST'])
def stop():
    engine_state['is_running'] = False
    engine_state['logs'].append({
        'time': time.strftime('%H:%M:%S'),
        'type': 'info',
        'msg': 'Engine stopped'
    })
    return jsonify({'status': 'ok'})


@app.route('/api/log', methods=['POST'])
def add_log():
    data = request.json
    engine_state['logs'].append({
        'time': time.strftime('%H:%M:%S'),
        'type': data.get('type', 'info'),
        'msg': data.get('msg', '')
    })
    return jsonify({'status': 'ok'})


def run_dashboard(port=5000):
    print(f"🚀 Dashboard running at http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    run_dashboard()
