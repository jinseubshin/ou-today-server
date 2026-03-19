   1	// O.U 카카오 로그인 인증 모듈
     2	// ⚠️ REST API 방식 ONLY - JavaScript SDK 사용 안 함!
     3	
     4	// ========================================
     5	// 설정
     6	// ========================================
     7	
     8	// 카카오 REST API 키
     9	const KAKAO_REST_API_KEY = 'c4c25da779364681dc4df48c81060f34';
    10	const KAKAO_REDIRECT_URI = 'https://fdrxhcpq.gensparkspace.com/kakao-callback.html';
    11	
    12	// ⭐ Flask API URL (실제 서버 주소로 변경 필요!)
    13	// 로컬 테스트: 'http://localhost:5000/api/auth/kakao'
    14	// 배포 후: 'https://your-flask-server.com/api/auth/kakao'
    15	const FLASK_API_URL = 'http://localhost:5000/api/auth/kakao';
    16	
    17	console.log('========================================');
    18	console.log('[Kakao Auth] 실제 카카오 연동 모드 (Mock 제거됨)');
    19	console.log('[REST API 키]:', KAKAO_REST_API_KEY);
    20	console.log('[Redirect URI]:', KAKAO_REDIRECT_URI);
    21	console.log('[Flask API URL]:', FLASK_API_URL);
    22	console.log('========================================');
    23	
    24	// ========================================
    25	// 카카오 OAuth 2.0 로그인 (REST API 방식)
    26	// ========================================
    27	
    28	/**
    29	 * 카카오 OAuth 인증 URL 생성
    30	 * @returns {string} 카카오 로그인 URL
    31	 */
    32	function getKakaoAuthUrl() {
    33	  // REST API 방식 URL
    34	  const kakaoAuthUrl = `https://kauth.kakao.com/oauth/authorize?client_id=${KAKAO_REST_API_KEY}&redirect_uri=${encodeURIComponent(KAKAO_REDIRECT_URI)}&response_type=code`;
    35	  
    36	  console.log('[Kakao OAuth] 생성된 인증 URL:', kakaoAuthUrl);
    37	  
    38	  return kakaoAuthUrl;
    39	}
    40	
    41	/**
    42	 * 카카오 로그인 시작
    43	 */
    44	function startKakaoLogin() {
    45	  console.log('========================================');
    46	  console.log('[Kakao Login] 카카오 로그인 시작 (REST API 방식)');
    47	  console.log('[client_id]:', KAKAO_REST_API_KEY);
    48	  console.log('[redirect_uri]:', KAKAO_REDIRECT_URI);
    49	  console.log('========================================');
    50	  
    51	  // 카카오 OAuth 인증 페이지로 리다이렉트
    52	  const authUrl = getKakaoAuthUrl();
    53	  window.location.href = authUrl;
    54	}
    55	
    56	/**
    57	 * 카카오 로그인 버튼 초기화
    58	 */
    59	function initKakaoLogin() {
    60	  const kakaoLoginBtn = document.getElementById('kakaoLogin');
    61	  
    62	  if (kakaoLoginBtn) {
    63	    console.log('[Kakao Login] 카카오 로그인 버튼 초기화 완료');
    64	    
    65	    // 클릭 이벤트
    66	    kakaoLoginBtn.addEventListener('click', (e) => {
    67	      e.preventDefault();
    68	      startKakaoLogin();
    69	    });
    70	    
    71	    // 호버 효과
    72	    kakaoLoginBtn.addEventListener('mouseenter', () => {
    73	      kakaoLoginBtn.style.opacity = '0.85';
    74	    });
    75	    
    76	    kakaoLoginBtn.addEventListener('mouseleave', () => {
    77	      kakaoLoginBtn.style.opacity = '1';
    78	    });
    79	  }
    80	}
    81	
    82	// ========================================
    83	// 카카오 콜백 처리 (kakao-callback.html에서 사용)
    84	// ========================================
    85	
    86	/**
    87	 * 카카오 인증 코드를 Flask API로 전송
    88	 * @param {string} code - 카카오 인증 코드
    89	 * @returns {Promise<Object>} 사용자 정보
    90	 */
    91	async function sendKakaoCodeToFlask(code) {
    92	  try {
    93	    console.log('[Kakao API] Flask로 인증 코드 전송:', code);
    94	    console.log('[Kakao API] Flask 서버 URL:', FLASK_API_URL);
    95	    
    96	    const response = await fetch(FLASK_API_URL, {
    97	      method: 'POST',
    98	      headers: {
    99	        'Content-Type': 'application/json',
   100	      },
   101	      body: JSON.stringify({
   102	        code: code,
   103	        redirect_uri: KAKAO_REDIRECT_URI
   104	      })
   105	    });
   106	
   107	    console.log('[Kakao API] HTTP 상태 코드:', response.status);
   108	
   109	    if (!response.ok) {
   110	      // HTTP 405 에러 감지
   111	      if (response.status === 405) {
   112	        throw new Error('Flask 서버가 POST 요청을 허용하지 않습니다. (HTTP 405)\n\nflask-backend/app.py를 배포하고 FLASK_API_URL을 실제 서버 주소로 변경해주세요.\n\n자세한 내용: HTTP_405_ERROR_FIX.md 참고');
   113	      }
   114	      
   115	      // 기타 HTTP 에러
   116	      const errorData = await response.json().catch(() => ({}));
   117	      throw new Error(`HTTP ${response.status}: ${errorData.error || errorData.message || '알 수 없는 에러'}`);
   118	    }
   119	
   120	    const data = await response.json();
   121	    console.log('[Kakao API] Flask 응답:', data);
   122	    
   123	    return {
   124	      success: true,
   125	      user: data.user,
   126	      token: data.token
   127	    };
   128	
   129	  } catch (error) {
   130	    console.error('[Kakao API] Flask 연동 실패:', error);
   131	    
   132	    // 네트워크 에러 감지
   133	    if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
   134	      return {
   135	        success: false,
   136	        error: 'Flask 서버에 연결할 수 없습니다.\n\n1. Flask 서버가 실행 중인지 확인하세요.\n2. FLASK_API_URL이 올바른지 확인하세요.\n\n현재 URL: ' + FLASK_API_URL
   137	      };
   138	    }
   139	    
   140	    return {
   141	      success: false,
   142	      error: error.message
   143	    };
   144	  }
   145	}
   146	
   147	/**
   148	 * 로그인 성공 후 사용자 정보 저장
   149	 * @param {Object} userData - 사용자 정보
   150	 */
   151	function saveUserSession(userData) {
   152	  console.log('[Session] 📥 사용자 세션 저장 시작:', userData.nickname);
   153	  
   154	  // ⭐ localStorage에 저장 (isLoggedIn 키 사용!)
   155	  localStorage.setItem('isLoggedIn', 'true');  // ⭐⭐⭐ 필수!
   156	  localStorage.setItem('user_name', userData.nickname);
   157	  localStorage.setItem('user_email', userData.email || '');
   158	  localStorage.setItem('user_profile_image', userData.profile_image || '');
   159	  localStorage.setItem('kakao_id', userData.kakao_id);
   160	  localStorage.setItem('user_nickname', userData.nickname);
   161	  localStorage.setItem('user_phone', userData.phone || '');
   162	  localStorage.setItem('user_address', userData.address || '');
   163	  localStorage.setItem('login_provider', 'kakao');
   164	  
   165	  // 토큰 저장
   166	  if (userData.token) {
   167	    localStorage.setItem('auth_token', userData.token);
   168	  }
   169	  
   170	  console.log('[Session] ✅ localStorage 저장 완료');
   171	  console.log('[Session] isLoggedIn:', localStorage.getItem('isLoggedIn'));
   172	  console.log('[Session] user_name:', localStorage.getItem('user_name'));
   173	}
   174	
   175	/**
   176	 * 로그아웃
   177	 */
   178	function logout() {
   179	  // localStorage 클리어
   180	  localStorage.removeItem('isLoggedIn');
   181	  localStorage.removeItem('kakao_id');
   182	  localStorage.removeItem('user_name'); // ⭐ 추가
   183	  localStorage.removeItem('user_nickname');
   184	  localStorage.removeItem('user_email');
   185	  localStorage.removeItem('user_profile_image');
   186	  localStorage.removeItem('user_phone');
   187	  localStorage.removeItem('user_address');
   188	  localStorage.removeItem('login_provider'); // ⭐ 추가
   189	  localStorage.removeItem('auth_token');
   190	  
   191	  console.log('[Logout] 로그아웃 완료');
   192	  
   193	  // 로그인 페이지로 이동
   194	  window.location.href = 'login.html';
   195	}
   196	
   197	/**
   198	 * 로그인 상태 확인
   199	 * @returns {boolean} 로그인 여부
   200	 */
   201	function isLoggedIn() {
   202	  const loginStatus = localStorage.getItem('isLoggedIn');
   203	  console.log('[Auth] isLoggedIn 확인:', loginStatus);
   204	  return loginStatus === 'true';
   205	}
   206	
   207	/**
   208	 * 현재 사용자 정보 가져오기
   209	 * @returns {Object|null} 사용자 정보 또는 null
   210	 */
   211	function getCurrentUser() {
   212	  if (!isLoggedIn()) {
   213	    return null;
   214	  }
   215	  
   216	  return {
   217	    kakao_id: localStorage.getItem('kakao_id'),
   218	    nickname: localStorage.getItem('user_nickname'),
   219	    email: localStorage.getItem('user_email'),
   220	    profile_image: localStorage.getItem('user_profile_image'),
   221	    phone: localStorage.getItem('user_phone'),
   222	    address: localStorage.getItem('user_address')
   223	  };
   224	}
   225	
   226	// ========================================
   227	// 페이지 로드 시 초기화
   228	// ========================================
   229	
   230	// DOM 로드 후 초기화
   231	if (document.readyState === 'loading') {
   232	  document.addEventListener('DOMContentLoaded', initKakaoLogin);
   233	} else {
   234	  initKakaoLogin();
   235	}
   236	
   237	// 전역 노출
   238	window.KakaoAuth = {
   239	  startKakaoLogin,
   240	  sendKakaoCodeToFlask,
   241	  saveUserSession,
   242	  logout,
   243	  isLoggedIn,
   244	  getCurrentUser
   245	};
   246	
   247	console.log('[Kakao Auth Module] REST API 방식으로 로드 완료');
   248	console.log('[client_id 확인]:', KAKAO_REST_API_KEY);
   249	