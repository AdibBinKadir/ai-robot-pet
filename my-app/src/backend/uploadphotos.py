from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
from dotenv import load_dotenv
from storage3.exceptions import StorageApiError
import os, uuid

# load .env from this folder if present (convenience for local dev)
load_dotenv()

app = Flask(__name__)
# enable CORS for local development (change for production)
# This will allow the React dev server to call the API. In production lock this down to your domain.
# Configure allowed origins via env var (comma-separated) so we can return the explicit Origin header
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get('ALLOWED_ORIGINS', 'http://localhost:5173').split(',') if o.strip()]
# Use flask-cors but also keep after_request to guarantee headers on errors
CORS(app, resources={r"/images": {"origins": ALLOWED_ORIGINS}}, supports_credentials=True)


@app.after_request
def _add_cors_headers(response):
    # ensure browser always receives CORS headers even on errors
    origin = request.headers.get('Origin')
    # If origin is allowed, echo it back and allow credentials. Otherwise default to '*'.
    if origin and origin in ALLOWED_ORIGINS:
        response.headers.setdefault('Access-Control-Allow-Origin', origin)
        response.headers.setdefault('Access-Control-Allow-Credentials', 'true')
    else:
        response.headers.setdefault('Access-Control-Allow-Origin', '*')
    response.headers.setdefault('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    response.headers.setdefault('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, x-user-id')
    response.headers.setdefault('Access-Control-Max-Age', '3600')
    return response


@app.errorhandler(Exception)
def _handle_exception(e):
    # Log exception server-side and return JSON (with CORS headers added by after_request)
    app.logger.exception('Unhandled exception: %s', e)
    resp = jsonify({'error': 'internal server error', 'detail': str(e)})
    resp.status_code = 500
    return resp

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
BUCKET = os.environ.get('BUCKET_NAME', 'images')
SAVE_PHOTO_METADATA = os.environ.get('SAVE_PHOTO_METADATA', 'false').lower() in ('1', 'true', 'yes')

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    # don't crash the server on import; let the upload endpoint return an error with a clear message
    app.logger.warning('SUPABASE_URL and/or SUPABASE_SERVICE_ROLE_KEY not set. upload endpoint will return error until configured.')
    supabase = None
else:
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    # Log a masked view to help debugging without printing the full secret
    try:
        key_info = f"len={len(SUPABASE_SERVICE_ROLE_KEY)} prefix={SUPABASE_SERVICE_ROLE_KEY[:8]}..."
    except Exception:
        key_info = 'missing'
    app.logger.info(f"Supabase client created. Using storage bucket: {BUCKET}; service_key={key_info}")
    
app.logger.info(f"Using storage bucket: {BUCKET}")


@app.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200


@app.route('/debug')
def debug_info():
    # Return masked configuration useful for debugging (do not reveal full keys)
    try:
        key_len = len(SUPABASE_SERVICE_ROLE_KEY) if SUPABASE_SERVICE_ROLE_KEY else 0
        key_prefix = SUPABASE_SERVICE_ROLE_KEY[:8] + '...' if SUPABASE_SERVICE_ROLE_KEY else None
    except Exception:
        key_len = 0
        key_prefix = None
    return jsonify({
        'supabase_url': SUPABASE_URL,
        'service_key_len': key_len,
        'service_key_prefix': key_prefix,
        'bucket': BUCKET,
        'save_photo_metadata': SAVE_PHOTO_METADATA,
        'supabase_client_present': supabase is not None,
    }), 200


@app.route('/images', methods=['OPTIONS'])
def images_options():
    # Preflight response for the upload endpoint
    resp = jsonify({'ok': True})
    resp.status_code = 204
    return resp

@app.route('/images', methods=['POST'])
def upload_photos():
    # optional: client can send x-user-id header to associate files
    if supabase is None:
        return jsonify({'error': 'Server not configured: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing'}), 500
    user_id = request.headers.get('x-user-id') or 'anonymous'
    # Accept files under either "images" or "photos" (frontend may use either)
    files = []
    for key in ('images', 'photos'):
        found = request.files.getlist(key) or []
        files.extend(found)
    # filter out empty entries and require a filename
    files = [f for f in files if f and getattr(f, 'filename', None)]
    if not files:
        return jsonify({'error': 'no files uploaded', 'hint': 'send multipart files under form key "images" or "photos"'}), 400
    # limit to first 3 files
    files = files[:3]
    app.logger.info("Received %d file(s) for user=%s (using up to 3)", len(files), user_id)
    uploaded_urls = []
    for f in files[:3]:
        ext = os.path.splitext(f.filename)[1] or ''
        key = f"{user_id}/{uuid.uuid4().hex}{ext}"
        data = f.read()
        app.logger.info(f"Uploading file key={key} size={len(data)} content_type={f.content_type}")
        # upload bytes to storage
        try:
            res = supabase.storage.from_(BUCKET).upload(key, data, {'content-type': f.content_type})
        except StorageApiError as e:
            # StorageApiError contains a dict-like payload with statusCode/message
            app.logger.exception('Storage upload failed: %s', e)
            return jsonify({'error': 'storage_upload_failed', 'detail': str(e)}), 500
        except Exception as e:
            app.logger.exception('Unexpected error during storage upload: %s', e)
            return jsonify({'error': 'unexpected_storage_error', 'detail': str(e)}), 500

        # check supabase response for error (some client versions return dict)
        if isinstance(res, dict) and res.get('error'):
            app.logger.error('Supabase storage returned error dict: %s', res)
            return jsonify({'error': 'storage_api_error', 'detail': res}), 500

        # get public URL
        try:
            public = supabase.storage.from_(BUCKET).get_public_url(key)
            url = public.get('publicURL') if isinstance(public, dict) else public
        except Exception as e:
            app.logger.exception('Failed to get public url for key=%s: %s', key, e)
            return jsonify({'error': 'get_public_url_failed', 'detail': str(e)}), 500

        uploaded_urls.append(url)
        # optional: insert metadata to DB (ensure table exists)
        if SAVE_PHOTO_METADATA:
            try:
                resp = supabase.table('photos').insert({'user_id': user_id, 'url': url}).execute()
                # log the DB response for debugging
                app.logger.info('Inserted photo metadata: %s', resp)
                # If resp contains an error shape, surface it
                if isinstance(resp, dict) and resp.get('error'):
                    app.logger.error('DB insert returned error: %s', resp)
                    return jsonify({'error': 'db_insert_error', 'detail': resp}), 500
            except Exception as e:
                # Most likely a row-level security policy rejection if anon key used
                app.logger.exception('DB insert failed: %s', e)
                return jsonify({'error': 'db_insert_failed', 'detail': str(e)}), 500
        else:
            app.logger.info('Skipping DB metadata insert because SAVE_PHOTO_METADATA is false')

    return jsonify({'uploaded': uploaded_urls}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)