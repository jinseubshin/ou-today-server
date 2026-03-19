from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from datetime import datetime

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

TOSS_SECRET_KEY = "test_sk_ZLKGPx4M3MbdjM2bPEoRVBaWypv1"
TOSS_BILLING_URL = "https://api.tosspayments.com/v1/billing/authorizations/issue"
TOSS_PAYMENT_URL = "https://api.tosspayments.com/v1/billing"

# 메모리 DB (나중에 실제 DB로 교체)
users_db = {}
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
        kakao_account = u_data.get("kakao_account", {})
        properties = u_data.get("properties", {})

        nickname = properties.get("nickname") or kakao_account.get("profile", {}).get("nickname")

        user_info = {
            "kakao_id": str(u_data.get("id")),
            "nickname": nickname,
            "profile_image": properties.get("profile_image") or kakao_account.get("profile", {}).get("profile_image_url"),
            "email": kakao_account.get("email")
        }

        user = save_or_update_user(user_info)
        return jsonify({"status": "ok", "user": user})

    except Exception as e:
        print(f"[Server Error] {str(e)}")
        return jsonify({"error": "서버 오류", "msg": str(e)}), 500


# ========================================
# 구독 등록 (토스페이먼츠 빌링키 발급 + 첫 결제)
# ========================================
@app.route('/api/subscription/register', methods=['POST', 'OPTIONS'])
def register_subscription():
    if request.method == 'OPTIONS':
        return '', 204
    try:
        data = request.json
        auth_key = data.get('authKey')
        customer_key = data.get('customerKey')
        kakao_id = data.get('kakaoId')
        plan = data.get('plan')
        price = int(data.get('price', 0))
        eggs = data.get('eggs')
        start_date = data.get('startDate')
        start_date_label = data.get('startDateLabel')
        delivery = data.get('delivery', {})
        user_name = data.get('userName', '고객')
        user_email = data.get('userEmail', '')

        # 1. 빌링키 발급
        import base64
        secret_b64 = base64.b64encode(f"{TOSS_SECRET_KEY}:".encode()).decode()

        billing_res = requests.post(
            TOSS_BILLING_URL,
            json={
                "authKey": auth_key,
                "customerKey": customer_key
            },
            headers={
                "Authorization": f"Basic {secret_b64}",
                "Content-Type": "application/json"
            }
        )

        billing_data = billing_res.json()
        print(f"[Toss Billing] {billing_data}")

        if billing_res.status_code != 200:
            return jsonify({"error": "빌링키 발급 실패", "detail": billing_data}), 400

        billing_key = billing_data.get("billingKey")

        # 2. 첫 결제 실행
        order_id = f"ou-{kakao_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        payment_res = requests.post(
            f"{TOSS_PAYMENT_URL}/{billing_key}",
            json={
                "customerKey": customer_key,
                "amount": price,
                "orderId": order_id,
                "orderName": f"O.U 유정란 {plan} 구독",
                "customerEmail": user_email,
                "customerName": user_name
            },
            headers={
                "Authorization": f"Basic {secret_b64}",
                "Content-Type": "application/json"
            }
        )

        payment_data = payment_res.json()
        print(f"[Toss Payment] {payment_data}")

        if payment_res.status_code != 200:
            return jsonify({"error": "첫 결제 실패", "detail": payment_data}), 400

        # 3. 구독 정보 저장
        subscription = {
            "kakao_id": kakao_id,
            "plan": plan,
            "price": price,
            "eggs": eggs,
            "billing_key": billing_key,
            "customer_key": customer_key,
            "start_date": start_date,
            "start_date_label": start_date_label,
            "next_payment_date": start_date,
            "delivery": delivery,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "orders": [{
                "order_id": order_id,
                "amount": price,
                "paid_at": datetime.now().isoformat(),
                "status": "paid"
            }]
        }

        subscriptions_db[kakao_id] = subscription

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
    sub['status'] = 'cancelled'
    sub['cancelled_at'] = datetime.now().isoformat()
    return jsonify({"status": "ok", "message": "구독이 해지되었습니다."})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
