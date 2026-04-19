"""
GRIDWATCH: Real-Time Electricity Theft Detection
Main Flask Application with WebSocket Support
"""
 
import threading, time, statistics, logging
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
app = Flask(__name__)
app.config['SECRET_KEY'] = 'gridwatch-secret-2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
 
from models.data_ingestion    import DataIngestionLayer
from models.expected_load     import ExpectedLoadCalculator
from models.anomaly_detection import AnomalyDetectionEngine
from models.theft_classifier  import TheftFingerprintClassifier
from models.socioeconomic     import SocioeconomicOverlay
from models.audit_roi         import AuditROIEngine
from models.simulator         import GridSimulator
 
simulator        = GridSimulator()
ingestion        = DataIngestionLayer(simulator)
expected_load    = ExpectedLoadCalculator()
anomaly_engine   = AnomalyDetectionEngine()
theft_classifier = TheftFingerprintClassifier()
socioeconomic    = SocioeconomicOverlay()
audit_roi        = AuditROIEngine()
 
grid_state = {'transformers':[], 'meters':[], 'alerts':[], 'audit_queue':[], 'stats':{}}
 
def update_grid_state():
    global grid_state
    raw_data    = ingestion.ingest()
    expected    = expected_load.calculate(raw_data)
    anomalies   = anomaly_engine.detect(raw_data, expected)
    theft_types = theft_classifier.classify(anomalies, raw_data)
    enriched    = socioeconomic.enrich(theft_types)
    audit_queue = audit_roi.score(enriched)
 
    transformers = []
    for t in raw_data['transformers']:
        tid     = t['id']
        anomaly = anomalies.get(tid, {})
        theft   = theft_types.get(tid, {})
        enrich  = enriched.get(tid, {})
        roi     = audit_queue.get(tid, {})
        prob    = anomaly.get('ensemble_score', 0)
        status  = 'red' if prob > 70 else 'yellow' if prob > 40 else 'green'
        transformers.append({
            'id': tid, 'name': t['name'], 'lat': t['lat'], 'lon': t['lon'],
            'zone': enrich.get('zone', t.get('zone','Unknown')),
            'income_band': enrich.get('income_band','—'),
            'response_flag': enrich.get('response_flag','—'),
            'status': status,
            'theft_probability': round(prob, 1),
            'expected_kw': round(expected.get(tid,{}).get('expected_kw',0), 2),
            'actual_kw': round(t['actual_kw'], 2),
            'gap_pct': round(expected.get(tid,{}).get('gap_pct',0), 1),
            'theft_type': theft.get('type','none'),
            'theft_label': theft.get('label','—'),
            'theft_action': theft.get('action','—'),
            'theft_icon': theft.get('icon','—'),
            'theft_color': theft.get('color','#888'),
            'roi_value': round(roi.get('roi_value',0), 0),
            'stolen_units': round(roi.get('stolen_units',0), 1),
            'recovery_value': round(roi.get('recovery_value',0), 0),
            'field_cost': round(roi.get('field_cost',0), 0),
            'priority_rank': roi.get('priority_rank', 99),
            'isolation_score': round(anomaly.get('isolation_score',0), 1),
            'lstm_score': round(anomaly.get('lstm_score',0), 1),
            'zscore': round(anomaly.get('zscore',0), 2),
            'zscore_score': round(anomaly.get('zscore_score',0), 1),
            'peer_score': round(anomaly.get('peer_score',0), 1),
            'meters': t.get('meters',[]),
            'history': t.get('history',[]),
        })
 
    audit_list  = sorted(transformers, key=lambda x: x['priority_rank'])
    red_c  = sum(1 for t in transformers if t['status']=='red')
    yel_c  = sum(1 for t in transformers if t['status']=='yellow')
    grid_state = {
        'transformers': transformers,
        'meters': raw_data.get('meters',[]),
        'alerts': [t for t in transformers if t['status']!='green'],
        'audit_queue': audit_list,
        'stats': {
            'total_transformers': len(transformers),
            'red': red_c, 'yellow': yel_c,
            'green': len(transformers)-red_c-yel_c,
            'total_stolen_units': round(sum(t['stolen_units'] for t in transformers),1),
            'total_recovery_value': round(sum(t['recovery_value'] for t in transformers),0),
            'timestamp': time.strftime('%H:%M:%S'),
        }
    }
    return grid_state
 
def background_updater():
    while True:
        try:
            state = update_grid_state()
            socketio.emit('grid_update', {
                'transformers': state['transformers'],
                'stats': state['stats'],
                'audit_queue': state['audit_queue'][:15],
            })
            logger.info(f"[GW] pushed — {state['stats']['red']} critical alerts")
        except Exception as e:
            logger.error(f"Updater error: {e}")
        time.sleep(5)
 
# ── Page routes ───────────────────────────────────────────────────────────────
@app.route('/')
def index(): return render_template('map.html')
 
@app.route('/map')
def map_dashboard(): return render_template('map.html')
 
@app.route('/meters')
def meters_dashboard(): return render_template('meters.html')
 
@app.route('/transformers')
def transformers_dashboard(): return render_template('transformers.html')
 
# ── API routes ────────────────────────────────────────────────────────────────
@app.route('/api/state')
def api_state(): return jsonify(grid_state)
 
@app.route('/api/stats')
def api_stats(): return jsonify(grid_state.get('stats',{}))
 
@app.route('/api/transformers')
def api_transformers(): return jsonify(grid_state.get('transformers',[]))
 
@app.route('/api/meters')
def api_meters(): return jsonify(grid_state.get('meters',[]))
 
@app.route('/api/audit')
def api_audit(): return jsonify(grid_state.get('audit_queue',[]))
 
@app.route('/api/alerts')
def api_alerts():
    alerts = sorted([t for t in grid_state.get('transformers',[]) if t.get('theft_probability',0)>35],
                    key=lambda x: -x['theft_probability'])
    return jsonify(alerts[:15])
 
@app.route('/api/transformer/<tid>')
def api_transformer_detail(tid):
    for t in grid_state.get('transformers',[]):
        if t['id']==tid: return jsonify(t)
    return jsonify({'error':'Not found'}), 404
 
@app.route('/api/forensic/<tid>')
def api_forensic(tid):
    for t in grid_state.get('transformers',[]):
        if t['id']==tid:
            history = t.get('history',[])
            gap_series = []
            for pt in history:
                gap = pt['expected'] - pt['actual']
                gp  = (gap / max(pt['expected'],1)) * 100
                try: hour = int(pt['time'].split(':')[0])
                except: hour = 12
                gap_series.append({'time':pt['time'],'gap_pct':round(gp,1),'gap_kw':round(gap,1),'hour':hour})
            night = [g['gap_pct'] for g in gap_series if g['hour'] in range(0,6)]
            day   = [g['gap_pct'] for g in gap_series if g['hour'] in range(8,22)]
            return jsonify({
                **t,
                'gap_series': gap_series,
                'night_mean_gap': round(statistics.mean(night),1) if night else 0,
                'day_mean_gap':   round(statistics.mean(day),1)   if day   else 0,
                'peak_gap':       round(max((abs(g['gap_pct']) for g in gap_series),default=0),1),
                'suspicious_meters': [m for m in t.get('meters',[]) if m.get('suspicious')],
            })
    return jsonify({'error':'Not found'}), 404
 
@app.route('/api/summary')
def api_summary():
    tfs = grid_state.get('transformers',[])
    by_type = {}
    for t in tfs: by_type[t.get('theft_type','none')] = by_type.get(t.get('theft_type','none'),0)+1
    return jsonify({
        'stats': grid_state.get('stats',{}),
        'by_theft_type': by_type,
        'top_alerts': [{'id':t['id'],'name':t['name'],'probability':t['theft_probability'],
                        'type':t['theft_label'],'roi':t['roi_value']}
                       for t in sorted(tfs,key=lambda x:-x['theft_probability'])[:5]],
    })
 
# ── WebSocket ─────────────────────────────────────────────────────────────────
@socketio.on('connect')
def on_connect():
    emit('grid_update',{'transformers':grid_state.get('transformers',[]),
                        'stats':grid_state.get('stats',{}),'audit_queue':grid_state.get('audit_queue',[])[:15]})
 
@socketio.on('disconnect')
def on_disconnect(): pass
 
@socketio.on('request_update')
def handle_request_update():
    state = update_grid_state()
    emit('grid_update',{'transformers':state['transformers'],'stats':state['stats'],'audit_queue':state['audit_queue'][:15]})
 
# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    logger.info("🔌 GRIDWATCH initializing...")
    update_grid_state()
    bg = threading.Thread(target=background_updater, daemon=True)
    bg.start()
    logger.info("=" * 52)
    logger.info("  GRIDWATCH → http://localhost:5050")
    logger.info("  /map  /transformers  /meters")
    logger.info("=" * 52)
    socketio.run(app, host='0.0.0.0', port=5050, debug=False, allow_unsafe_werkzeug=True)
