from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
import os, uuid

app = Flask(__name__)
# enable CORS for local development (change for production)
# This will allow the React dev server to call the API. In production lock this down to your domain.
CORS(app)  # allow all origins for dev

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
BUCKET = os.environ.get('BUCKET_NAME', 'images')

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    # don't crash the server on import; let the upload endpoint return an error with a clear message
    app.logger.warning('SUPABASE_URL and/or SUPABASE_SERVICE_ROLE_KEY not set. upload endpoint will return error until configured.')
    supabase = None
else:
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

app.logger.info(f"Using storage bucket: {BUCKET}")


@app.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200

@app.route('/images', methods=['POST'])
def upload_photos():
    # optional: client can send x-user-id header to associate files
    if supabase is None:
        return jsonify({'error': 'Server not configured: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing'}), 500
    user_id = request.headers.get('x-user-id') or 'anonymous'
    files = request.files.getlist('photos')
    if not files:
        return jsonify({'error': 'no files uploaded'}), 400

    uploaded_urls = []
    for f in files[:3]:
        ext = os.path.splitext(f.filename)[1] or ''
        key = f"{user_id}/{uuid.uuid4().hex}{ext}"
        data = f.read()
        # upload bytes to storage
        res = supabase.storage.from_(BUCKET).upload(key, data, {'content-type': f.content_type})
        # check supabase response for error
        if isinstance(res, dict) and res.get('error'):
            return jsonify({'error': res['error']['message']}), 500
        # get public URL
        public = supabase.storage.from_(BUCKET).get_public_url(key)
        # public may be dict { 'publicURL': '...' }
        url = public.get('publicURL') if isinstance(public, dict) else public
        uploaded_urls.append(url)
        # optional: insert metadata to DB (ensure table exists)
        try:
            supabase.table('photos').insert({'user_id': user_id, 'url': url}).execute()
        except Exception:
            pass

    return jsonify({'uploaded': uploaded_urls}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)