    1	# O.U 카카오 로그인 Flask 백엔드
     2	# Python 3.8+
     3	
     4	from flask import Flask, request, jsonify
     5	from flask_cors import CORS
     6	import requests
     7	from datetime import datetime
     8	import os
     9	
    10	app = Flask(__name__)
    11	
    12	# ========================================
    13	# CORS 설정
    14	# ========================================
    15	CORS(app, resources={
    16	    r"/api/*": {
    17	        "origins": [
    18	            "https://fdrxhcpq.gensparkspace.com",
    19	            "http://localhost:8080",
    20	            "http://127.0.0.1:8080"
    21	        ],
    22	        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    23	        "allow_headers": ["Content-Type", "Authorization"]
    24	    }
    25	})
    26	
    27	# ========================================
    28	# 카카오 API 설정
    29	# ========================================
    30	KAKAO_REST_API_KEY = "c4c25da779364681dc4df48c81060f34"
    31	KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
    32	KAKAO_USER_INFO_URL = "https://kapi.kakao.com/v2/user/me"
    33	
    34	# ========================================
    35	# 데이터베이스 설정 (임시: 딕셔너리 사용)
    36	# 실제 운영 시 MySQL, PostgreSQL, MongoDB 등 사용
    37	# ========================================
    38	users_db = {}
    39	
    40	# ========================================
    41	# 헬스 체크 엔드포인트
    42	# ========================================
    43	@app.route('/health', methods=['GET'])
    44	def health_check():
    45	    """서버 상태 확인"""
    46	    return jsonify({
    47	        "status": "ok",
    48	        "message": "Flask 서버가 정상 작동 중입니다.",
    49	        "timestamp": datetime.utcnow().isoformat()
    50	    })
    51	
    52	# ========================================
    53	# 카카오 OAuth 로그인 엔드포인트
    54	# ========================================
    55	@app.route('/api/auth/kakao', methods=['POST', 'OPTIONS'])
    56	def kakao_login():
    57	    """
    58	    카카오 OAuth 로그인 처리
    59	    
    60	    Request Body:
    61	    {
    62	        "code": "카카오 인증 코드",
    63	        "redirect_uri": "https://fdrxhcpq.gensparkspace.com/kakao-callback.html"
    64	    }
    65	    
    66	    Response:
    67	    {
    68	        "status": "ok",
    69	        "user": {
    70	            "kakao_id": "123456789",
    71	            "email": "user@example.com",
    72	            "nickname": "홍길동",
    73	            "profile_image": "https://..."
    74	        },
    75	        "token": "JWT_TOKEN_HERE"
    76	    }
    77	    """
    78	    
    79	    # OPTIONS 요청 처리 (CORS preflight)
    80	    if request.method == 'OPTIONS':
    81	        return '', 204
    82	    
    83	    try:
    84	        # 요청 데이터 추출
    85	        data = request.json
    86	        code = data.get('code')
    87	        redirect_uri = data.get('redirect_uri')
    88	        
    89	        if not code:
    90	            return jsonify({"error": "code는 필수입니다"}), 400
    91	        
    92	        if not redirect_uri:
    93	            return jsonify({"error": "redirect_uri는 필수입니다"}), 400
    94	        
    95	        print(f"[Kakao Login] 인증 코드 수신: {code[:10]}...")
    96	        print(f"[Kakao Login] Redirect URI: {redirect_uri}")
    97	        
    98	        # ========================================
    99	        # 1단계: 카카오 액세스 토큰 발급
   100	        # ========================================
   101	        token_response = requests.post(KAKAO_TOKEN_URL, data={
   102	            "grant_type": "authorization_code",
   103	            "client_id": KAKAO_REST_API_KEY,
   104	            "redirect_uri": redirect_uri,
   105	            "code": code
   106	        }, headers={
   107	            "Content-Type": "application/x-www-form-urlencoded"
   108	        })
   109	        
   110	        if token_response.status_code != 200:
   111	            error_detail = token_response.json()
   112	            print(f"[Kakao Token Error] {error_detail}")
   113	            return jsonify({
   114	                "error": "카카오 토큰 발급 실패",
   115	                "detail": error_detail
   116	            }), 400
   117	        
   118	        token_data = token_response.json()
   119	        access_token = token_data.get("access_token")
   120	        
   121	        print(f"[Kakao Token] 액세스 토큰 발급 성공: {access_token[:20]}...")
   122	        
   123	        # ========================================
   124	        # 2단계: 카카오 사용자 정보 조회
   125	        # ========================================
   126	        user_response = requests.get(KAKAO_USER_INFO_URL, headers={
   127	            "Authorization": f"Bearer {access_token}",
   128	            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
   129	        })
   130	        
   131	        if user_response.status_code != 200:
   132	            error_detail = user_response.json()
   133	            print(f"[Kakao User Info Error] {error_detail}")
   134	            return jsonify({
   135	                "error": "카카오 사용자 정보 조회 실패",
   136	                "detail": error_detail
   137	            }), 400
   138	        
   139	        user_data = user_response.json()
   140	        
   141	        # ========================================
   142	        # 3단계: 사용자 정보 추출
   143	        # ========================================
   144	        kakao_id = str(user_data.get("id"))
   145	        kakao_account = user_data.get("kakao_account", {})
   146	        profile = kakao_account.get("profile", {})
   147	        
   148	        user_info = {
   149	            "kakao_id": kakao_id,
   150	            "email": kakao_account.get("email", ""),
   151	            "nickname": profile.get("nickname", ""),
   152	            "profile_image": profile.get("profile_image_url", ""),
   153	            "phone": "",
   154	            "address": ""
   155	        }
   156	        
   157	        print(f"[Kakao User Info] 사용자 정보 조회 완료: {user_info['nickname']} ({kakao_id})")
   158	        
   159	        # ========================================
   160	        # 4단계: 데이터베이스 저장 (신규 회원가입 or 기존 회원 업데이트)
   161	        # ========================================
   162	        user = save_or_update_user(user_info)
   163	        
   164	        # ========================================
   165	        # 5단계: JWT 토큰 생성 (선택사항)
   166	        # ========================================
   167	        # 실제 운영 시 JWT 라이브러리 사용
   168	        auth_token = generate_auth_token(user)
   169	        
   170	        print(f"[Kakao Login] 로그인 성공: {user['nickname']}")
   171	        
   172	        # ========================================
   173	        # 응답 반환
   174	        # ========================================
   175	        return jsonify({
   176	            "status": "ok",
   177	            "user": user,
   178	            "token": auth_token
   179	        })
   180	    
   181	    except Exception as e:
   182	        print(f"[Kakao Login Error] {str(e)}")
   183	        return jsonify({
   184	            "error": "서버 내부 오류",
   185	            "message": str(e)
   186	        }), 500
   187	
   188	# ========================================
   189	# 사용자 정보 저장/업데이트
   190	# ========================================
   191	def save_or_update_user(user_info):
   192	    """
   193	    사용자 정보를 DB에 저장하거나 업데이트
   194	    
   195	    실제 운영 시:
   196	    - MySQL: INSERT ... ON DUPLICATE KEY UPDATE
   197	    - PostgreSQL: INSERT ... ON CONFLICT DO UPDATE
   198	    - MongoDB: db.users.updateOne(..., upsert=True)
   199	    """
   200	    kakao_id = user_info['kakao_id']
   201	    
   202	    # 기존 회원 확인
   203	    if kakao_id in users_db:
   204	        print(f"[DB] 기존 회원 정보 업데이트: {kakao_id}")
   205	        users_db[kakao_id].update({
   206	            "email": user_info['email'],
   207	            "nickname": user_info['nickname'],
   208	            "profile_image": user_info['profile_image'],
   209	            "updated_at": datetime.utcnow().isoformat(),
   210	            "last_login_at": datetime.utcnow().isoformat()
   211	        })
   212	    else:
   213	        print(f"[DB] 신규 회원 등록: {kakao_id}")
   214	        users_db[kakao_id] = {
   215	            "id": len(users_db) + 1,
   216	            "kakao_id": kakao_id,
   217	            "email": user_info['email'],
   218	            "nickname": user_info['nickname'],
   219	            "profile_image": user_info['profile_image'],
   220	            "phone": user_info.get('phone', ''),
   221	            "address": user_info.get('address', ''),
   222	            "created_at": datetime.utcnow().isoformat(),
   223	            "updated_at": datetime.utcnow().isoformat(),
   224	            "last_login_at": datetime.utcnow().isoformat()
   225	        }
   226	    
   227	    return users_db[kakao_id]
   228	
   229	# ========================================
   230	# JWT 토큰 생성 (선택사항)
   231	# ========================================
   232	def generate_auth_token(user):
   233	    """
   234	    JWT 토큰 생성
   235	    
   236	    실제 운영 시:
   237	    pip install PyJWT
   238	    
   239	    import jwt
   240	    token = jwt.encode({
   241	        'kakao_id': user['kakao_id'],
   242	        'exp': datetime.utcnow() + timedelta(days=30)
   243	    }, SECRET_KEY, algorithm='HS256')
   244	    """
   245	    # 임시 토큰 (실제로는 JWT 사용)
   246	    return f"temp_token_{user['kakao_id']}_{datetime.utcnow().timestamp()}"
   247	
   248	# ========================================
   249	# 사용자 조회 엔드포인트 (선택사항)
   250	# ========================================
   251	@app.route('/api/user/<kakao_id>', methods=['GET'])
   252	def get_user(kakao_id):
   253	    """특정 사용자 정보 조회"""
   254	    if kakao_id in users_db:
   255	        return jsonify({
   256	            "status": "ok",
   257	            "user": users_db[kakao_id]
   258	        })
   259	    else:
   260	        return jsonify({"error": "사용자를 찾을 수 없습니다"}), 404
   261	
   262	# ========================================
   263	# 모든 사용자 조회 (개발/테스트용)
   264	# ========================================
   265	@app.route('/api/users', methods=['GET'])
   266	def get_all_users():
   267	    """모든 사용자 목록 (개발용)"""
   268	    return jsonify({
   269	        "status": "ok",
   270	        "total": len(users_db),
   271	        "users": list(users_db.values())
   272	    })
   273	
   274	# ========================================
   275	# 서버 실행
   276	# ========================================
   277	if __name__ == '__main__':
   278	    print("=" * 60)
   279	    print("🚀 O.U 카카오 로그인 Flask 서버 시작")
   280	    print("=" * 60)
   281	    print(f"📍 서버 주소: http://localhost:5000")
   282	    print(f"🔑 REST API 키: {KAKAO_REST_API_KEY}")
   283	    print(f"🌐 허용된 Origin: https://fdrxhcpq.gensparkspace.com")
   284	    print("=" * 60)
   285	    
   286	    # 개발 서버 실행
   287	    # 실제 운영 시: gunicorn, uWSGI 사용
   288	    app.run(
   289	        host='0.0.0.0',
   290	        port=5000,
   291	        debug=True  # 운영 환경에서는 False로 설정
   292	    )
   293	