from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import base64
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://fdrxhcpq.gensparkspace.com"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

KAKAO_REST_API_KEY  = "c4c25da779364681dc4df48c81060f34"
KAKAO_CLIENT_SECRET = "0coRrzVaDtECJE7rW9ImjzYpX3FnuaRz"

TOSS_SECRET_KEY    = "test_sk_ZLKGPx4M3MbdjM2bPEoRVBaWypv1"
TOSS_BILLING_URL   = "https://api.tosspayments.com/v1/billing/authorizations/issue"
TOSS_PAYMENT_URL   = "https://api.tosspayments.com/v1/billing"

REPLIT_API_URL     = "https://ousystem.replit.app/order"

# 플랜 → Replit product 코드 매핑
PLAN_TO_PRODUCT = {
    "베이직":       "1pan",
    "BEST":         "2pan",
    "패밀리":       "3pan",
    "VIP 프리미엄": "4pan",
}

# 메모리 DB
users_db         = {}
subscriptions_db = {}


# ========================================
# 카카오 로그인
# ========================================
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
        data         = request.json
        code         = data.get('code')
        redirect_uri = "https://fdrxhcpq.gensparkspace.com/kakao-callback.html"

        res = requests.post("https://kauth.kakao.com/oauth/token", data={
            "grant_type":    "authorization_code",
            "client_id":     KAKAO_REST_API_KEY,
            "client_secret": KAKAO_CLIENT_SECRET,
            "redirect_uri":  redirect_uri,
            "code":          code
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})

        if res.status_code != 200:
            print(f"[Kakao Error] {res.json()}")
            return jsonify({"error": "토큰 발급 실패", "detail": res.json()}), 400

        token  = res.json().get("access_token")
        u_res  = requests.get("https://kapi.kakao.com/v2/user/me", headers={
            "Authorization": f"Bearer {token}"
        })
        u_data        = u_res.json()
        kakao_account = u_data.get("kakao_account", {})
        properties    = u_data.get("properties", {})
        nickname      = properties.get("nickname") or kakao_account.get("profile", {}).get("nickname")

        user_info = {
            "kakao_id":      str(u_data.get("id")),
            "nickname":      nickname,
            "profile_image": properties.get("profile_image") or kakao_account.get("profile", {}).get("profile_image_url"),
            "email":         kakao_account.get("email")
        }

        user = save_or_update_user(user_info)
        return jsonify({"status": "ok", "user": user})

    except Exception as e:
        print(f"[Server Error] {str(e)}")
        return jsonify({"error": "서버 오류", "msg": str(e)}), 500


# ========================================
# 구독 등록 (토스 빌링키 발급 + 첫 결제 + Replit 전송)
# ========================================
@app.route('/api/subscription/register', methods=['POST', 'OPTIONS'])
def register_subscription():
    if request.method == 'OPTIONS':
        return '', 204
    try:
        data             = request.json
        auth_key         = data.get('authKey')
        customer_key     = data.get('customerKey')
        kakao_id         = data.get('kakaoId')
        plan             = data.get('plan')
        price            = int(data.get('price', 0))
        eggs             = data.get('eggs')
        start_date       = data.get('startDate')
        start_date_label = data.get('startDateLabel')
        delivery         = data.get('delivery', {})
        user_name        = data.get('userName', '고객')
        user_email       = data.get('userEmail', '')

        # 1. 빌링키 발급
        secret_b64 = base64.b64encode(f"{TOSS_SECRET_KEY}:".encode()).decode()
        billing_res = requests.post(
            TOSS_BILLING_URL,
            json={"authKey": auth_key, "customerKey": customer_key},
            headers={
                "Authorization": f"Basic {secret_b64}",
                "Content-Type":  "application/json"
            }
        )
        billing_data = billing_res.json()
        print(f"[Toss Billing] {billing_data}")

        if billing_res.status_code != 200:
            return jsonify({"error": "빌링키 발급 실패", "detail": billing_data}), 400

        billing_key = billing_data.get("billingKey")

        # 2. 첫 결제
        order_id    = f"ou-{kakao_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        payment_res = requests.post(
            f"{TOSS_PAYMENT_URL}/{billing_key}",
            json={
                "customerKey":  customer_key,
                "amount":       price,
                "orderId":      order_id,
                "orderName":    f"O.U 유정란 {plan} 구독",
                "customerEmail": user_email,
                "customerName":  user_name
            },
            headers={
                "Authorization": f"Basic {secret_b64}",
                "Content-Type":  "application/json"
            }
        )
        payment_data = payment_res.json()
        print(f"[Toss Payment] {payment_data}")

        if payment_res.status_code != 200:
            return jsonify({"error": "첫 결제 실패", "detail": payment_data}), 400

        # 3. 구독 정보 저장 (메모리)
        subscription = {
            "kakao_id":         kakao_id,
            "plan":             plan,
            "price":            price,
            "eggs":             eggs,
            "billing_key":      billing_key,
            "customer_key":     customer_key,
            "start_date":       start_date,
            "start_date_label": start_date_label,
            "next_payment_date": start_date,
            "delivery":         delivery,
            "status":           "active",
            "created_at":       datetime.now().isoformat(),
            "orders": [{
                "order_id":  order_id,
                "amount":    price,
                "paid_at":   datetime.now().isoformat(),
                "status":    "paid"
            }]
        }
        subscriptions_db[kakao_id] = subscription

        # 4. Replit 관리자 시스템으로 주문 전송
        replit_product = PLAN_TO_PRODUCT.get(plan, "1pan")
        replit_payload = {
            "name":         delivery.get("name") or user_name,
            "phone":        delivery.get("phone", ""),
            "address":      delivery.get("address", ""),
            "product":      replit_product,
            "payment_type": "monthly",
            "created_at":   start_date,
            "status":       "paid",
            "payment_status": "paid",
            "memo":         f"카카오 구독 | {plan} | {eggs}구 | 배송메모: {delivery.get('memo', '')} | kakao_id: {kakao_id}"
        }

        try:
            # Replit 서버 먼저 깨우기
            try:
                requests.get("https://ousystem.replit.app/login", timeout=5)
            except:
                pass

            replit_res = requests.post(
                REPLIT_API_URL,
                json=replit_payload,
                timeout=15
            )
            print(f"[Replit] 전송 결과: {replit_res.status_code} / {replit_res.text[:200]}")
        except Exception as re:
            print(f"[Replit] 전송 실패 (구독은 정상 처리됨): {str(re)}")

        return jsonify({"status": "ok", "subscription": subscription})

    except Exception as e:
        print(f"[Subscription Error] {str(e)}")
        return jsonify({"error": "서버 오류", "msg": str(e)}), 500


# ========================================
# 구독 정보 조회
# ========================================
@app.route('/api/subscription/<kakao_id>', methods=['GET', 'OPTIONS'])
def get_subscription(kakao_id):
    if request.method == 'OPTIONS':
        return '', 204
    sub = subscriptions_db.get(kakao_id)
    if not sub:
        return jsonify({"status": "none"}), 200
    return jsonify({"status": "ok", "subscription": sub})


# ========================================
# 구독 해지
# ========================================
@app.route('/api/subscription/<kakao_id>/cancel', methods=['POST', 'OPTIONS'])
def cancel_subscription(kakao_id):
    if request.method == 'OPTIONS':
        return '', 204
    sub = subscriptions_db.get(kakao_id)
    if not sub:
        return jsonify({"error": "구독 정보 없음"}), 404
    sub['status']       = 'cancelled'
    sub['cancelled_at'] = datetime.now().isoformat()
    return jsonify({"status": "ok", "message": "구독이 해지되었습니다."})

# ========================================
# 헬스 체크
# ========================================
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "서버 정상 작동 중"})


# ========================================
# 네이버 로그인
# ========================================
NAVER_CLIENT_ID     = "QwT0sDitiiCijlC5_KxB"
NAVER_CLIENT_SECRET = "f8thiPUdJD"
NAVER_TOKEN_URL     = "https://nid.naver.com/oauth2.0/token"
NAVER_USER_INFO_URL = "https://openapi.naver.com/v1/nid/me"

@app.route('/api/auth/naver', methods=['POST', 'OPTIONS'])
def naver_login():
    if request.method == 'OPTIONS':
        return '', 204
    try:
        data  = request.json
        code  = data.get('code')
        state = data.get('state')

        if not code or not state:
            return jsonify({"error": "code와 state는 필수입니다"}), 400

        # 1. 액세스 토큰 발급
        res = requests.post(NAVER_TOKEN_URL, data={
            "grant_type":    "authorization_code",
            "client_id":     NAVER_CLIENT_ID,
            "client_secret": NAVER_CLIENT_SECRET,
            "code":          code,
            "state":         state
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})

        if res.status_code != 200:
            return jsonify({"error": "네이버 토큰 발급 실패", "detail": res.json()}), 400

        access_token = res.json().get("access_token")

        # 2. 사용자 정보 조회
        u_res = requests.get(NAVER_USER_INFO_URL, headers={
            "Authorization": f"Bearer {access_token}"
        })
        u_data = u_res.json()

        if u_data.get("resultcode") != "00":
            return jsonify({"error": "사용자 정보 조회 실패", "detail": u_data}), 400

        profile  = u_data.get("response", {})
        naver_id = profile.get("id")

        user_info = {
            "naver_id":      naver_id,
            "nickname":      profile.get("nickname", ""),
            "email":         profile.get("email", ""),
            "profile_image": profile.get("profile_image", ""),
            "name":          profile.get("name", ""),
            "mobile":        profile.get("mobile", "")
        }

        # 3. 메모리 DB 저장
        if naver_id not in users_db:
            users_db[naver_id] = user_info
        else:
            users_db[naver_id].update(user_info)

        return jsonify({"status": "ok", "user": users_db[naver_id]})

    except Exception as e:
        print(f"[Naver Login Error] {str(e)}")
        return jsonify({"error": "서버 오류", "msg": str(e)}), 500
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
