# O.U 카카오 로그인 Flask 백엔드
# Python 3.8+

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from datetime import datetime
import os

app = Flask(__name__)

# ========================================
# CORS 설정 (젠스파크 주소 허용)
# ========================================
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://fdrxhcpq.gensparkspace.com",
            "http://localhost:8080",
            "http://127.0.0.1:8080"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# ========================================
# 카카오 API 설정
# ========================================
KAKAO_REST_API_KEY = "c4c25da779364681dc4df48c81060f34"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USER_INFO_URL = "https://kapi.kakao.com/v2/user/me"

# 임시 DB
users_db = {}

def save_or_update_user(user_info):
    kakao_id = user_info['kakao_id']
    if kakao_id in users_db:
        users_db[kakao_id].update({
            "email": user_info['email'],
            "nickname": user_info['nickname'],
            "profile_image": user_info['profile_image'],
            "updated_at": datetime.utcnow().isoformat(),
            "last_login_at": datetime.utcnow().isoformat()
        })
    else:
        users_db[kakao_id] = {
            "id": len(users_db) + 1,
            "kakao_id": kakao_id,
            "email": user_info['email'],
            "nickname": user_info['nickname'],
            "profile_image": user_info['profile_image'],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "last_login_at": datetime.utcnow().isoformat()
        }
    return users_db[kakao_id]

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Flask 서버 정상 작동 중"})

@app.route('/api/auth/kakao', methods=['POST', 'OPTIONS'])
def kakao_login():
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.json
        code = data.get('code')
        redirect_uri = "https://fdrxhcpq.gensparkspace.com/kakao-callback.html"
        
        if not code or not redirect_uri:
            return jsonify({"error": "code와 redirect_uri는 필수입니다"}), 400

        # 1. 토큰 발급
        token_response = requests.post(KAKAO_TOKEN_URL, data={
            "grant_type": "authorization_code",
            "client_id": KAKAO_REST_API_KEY,
            "redirect_uri": redirect_uri,
            "code": code
        }, headers={"Content-Type": "application/x-form-urlencoded"})
        
        if token_response.status_code != 200:
            return jsonify({"error": "토큰 발급 실패", "detail": token_response.json()}), 400
        
        access_token = token_response.json().get("access_token")

        # 2. 사용자 정보 조회
        user_response = requests.get(KAKAO_USER_INFO_URL, headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/x-form-urlencoded;charset=utf-8"
        })
        
        user_data = user_response.json()
        kakao_account = user_data.get("kakao_account", {})
        profile = kakao_account.get("profile", {})
        
        user_info = {
            "kakao_id": str(user_data.get("id")),
            "email": kakao_account.get("email", ""),
            "nickname": profile.get("nickname", ""),
            "profile_image": profile.get("profile_image_url", "")
        }

        user = save_or_update_user(user_info)
        return jsonify({"status": "ok", "user": user})

    except Exception as e:
        return jsonify({"error": "서버 오류", "message": str(e)}), 500

if __name__ == '__main__':
    # 렌더 배포 시 PORT 환경변수를 사용해야 합니다.
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
