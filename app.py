from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from datetime import datetime
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
    if request.method == 'OPTIONS': return '', 204
    try:
        data = request.json
        code = data.get('code')
        # ⭐ 주소 끝에 공백 없게 철저히 고정
        redirect_uri = "https://fdrxhcpq.gensparkspace.com/kakao-callback.html"
        
        # 1. 카카오 토큰 요청 (AI가 말한 '비밀번호 제거' 버전)
        res = requests.post("https://kauth.kakao.com/oauth/token", data={
            "grant_type": "authorization_code",
            "client_id": KAKAO_REST_API_KEY.strip(),
            "redirect_uri": redirect_uri.strip(),
            "code": code.strip()
        }, headers={"Content-Type": "application/x-form-urlencoded"})
        
        if res.status_code != 200:
            # 에러 나면 로그에 상세히 찍히게 함
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
