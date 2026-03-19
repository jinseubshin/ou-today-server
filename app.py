from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://fdrxhcpq.gensparkspace.com"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

KAKAO_REST_API_KEY = "c4c25da779364681dc4df48c81060f34"
KAKAO_CLIENT_SECRET = "0coRrzVaDtECJE7rW9ImjzYpX3FnuaRz"

users_db = {}

def save_or_update_user(user_info):
    uid = user_info['kakao_id']
    if uid in users_db:
        users_db[uid].update(user_info)
    else:
        users_db[uid] = user_info
    return users_db[uid]

@app.route('/api/auth/kakao', methods=['POST', 'OPTIONS'])
def kakao_login():
    if request.method == 'OPTIONS':
        return '', 204
    try:
        data = request.json
        code = data.get('code')
        redirect_uri = "https://fdrxhcpq.gensparkspace.com/kakao-callback.html"

        res = requests.post("https://kauth.kakao.com/oauth/token", data={
            "grant_type": "authorization_code",
            "client_id": KAKAO_REST_API_KEY,
            "client_secret": KAKAO_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "code": code
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})

        if res.status_code != 200:
            print(f"[Kakao Error] {res.json()}")
            return jsonify({"error": "토큰 발급 실패", "detail": res.json()}), 400

        token = res.json().get("access_token")

        u_res = requests.get("https://kapi.kakao.com/v2/user/me", headers={
            "Authorization": f"Bearer {token}"
        })

        u_data = u_res.json()
        user_info = {
            "kakao_id": str(u_data.get("id")),
            "nickname": u_data.get("properties", {}).get("nickname"),
            "profile_image": u_data.get("properties", {}).get("profile_image"),
            "email": u_data.get("kakao_account", {}).get("email")
        }

        user = save_or_update_user(user_info)
        return jsonify({"status": "ok", "user": user})

    except Exception as e:
        return jsonify({"error": "서버 오류", "msg": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
