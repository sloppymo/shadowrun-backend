from flask import Blueprint, request, Response, current_app
import requests
import urllib.parse

stream_proxy = Blueprint('stream_proxy', __name__)

@stream_proxy.route('/api/chat/stream-proxy')
def proxy():
    # Forward query params to the backend /api/chat endpoint as POST JSON
    session_id = request.args.get('session_id')
    user_id = request.args.get('user_id')
    role = request.args.get('role', 'player')
    user_input = request.args.get('input', '')
    backend_url = f"http://127.0.0.1:5000/api/chat"
    headers = {'Content-Type': 'application/json'}
    payload = {
        'input': user_input,
        'session_id': session_id,
        'user_id': user_id,
        'role': role
    }
    # Stream the response from backend
    with requests.post(backend_url, json=payload, stream=True) as r:
        def generate():
            for chunk in r.iter_content(chunk_size=None):
                if chunk:
                    yield chunk
        return Response(generate(), content_type=r.headers.get('Content-Type', 'text/event-stream'))
