from flask import Flask, request, jsonify, render_template
from playwrite_mcp import run_playwright_action

app = Flask(__name__, template_folder='templates')
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run', methods=['POST'])
def run():
    data = request.json
    action = data.get('action')
    params = data.get('params', {})
    try:
        result = run_playwright_action(action, params)
        return jsonify({'status': 'success', 'result': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
