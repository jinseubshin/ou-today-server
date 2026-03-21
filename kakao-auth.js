// O.U 카카오 로그인 인증 모듈
// ⚠️ REST API 방식 ONLY - JavaScript SDK 사용 안 함!

const KAKAO_REST_API_KEY = 'c4c25da779364681dc4df48c81060f34';
const KAKAO_REDIRECT_URI = 'https://sprightly-licorice-18063d.netlify.app/kakao-callback.html';
const FLASK_API_URL      = 'https://ou-today-server.onrender.com/api/auth/kakao';

console.log('[Kakao Auth] REDIRECT_URI:', KAKAO_REDIRECT_URI);

function getKakaoAuthUrl() {
  return `https://kauth.kakao.com/oauth/authorize?client_id=${KAKAO_REST_API_KEY}&redirect_uri=${encodeURIComponent(KAKAO_REDIRECT_URI)}&response_type=code`;
}

function startKakaoLogin() {
  window.location.href = getKakaoAuthUrl();
}

function initKakaoLogin() {
  const btn = document.getElementById('kakaoLogin');
  if (btn) {
    btn.addEventListener('click', (e) => { e.preventDefault(); startKakaoLogin(); });
    btn.addEventListener('mouseenter', () => { btn.style.opacity = '0.85'; });
    btn.addEventListener('mouseleave', () => { btn.style.opacity = '1'; });
  }
}

async function sendKakaoCodeToFlask(code) {
  try {
    const res = await fetch(FLASK_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, redirect_uri: KAKAO_REDIRECT_URI })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(`HTTP ${res.status}: ${err.error || '알 수 없는 에러'}`);
    }
    const data = await res.json();
    return { success: true, user: data.user };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

function saveUserSession(userData) {
  localStorage.setItem('isLoggedIn',         'true');
  localStorage.setItem('user_name',          userData.nickname || '');
  localStorage.setItem('user_nickname',      userData.nickname || '');
  localStorage.setItem('user_email',         userData.email    || '');
  localStorage.setItem('user_profile_image', userData.profile_image || '');
  localStorage.setItem('kakao_id',           userData.kakao_id || '');
  localStorage.setItem('user_phone',         userData.phone    || '');
  localStorage.setItem('user_address',       userData.address  || '');
  localStorage.setItem('login_provider',     'kakao');
  if (userData.token) localStorage.setItem('auth_token', userData.token);
}

function logout() {
  localStorage.clear();
  window.location.href = 'login.html';
}

function isLoggedIn() {
  return localStorage.getItem('isLoggedIn') === 'true';
}

function getCurrentUser() {
  if (!isLoggedIn()) return null;
  return {
    kakao_id:      localStorage.getItem('kakao_id'),
    nickname:      localStorage.getItem('user_nickname'),
    email:         localStorage.getItem('user_email'),
    profile_image: localStorage.getItem('user_profile_image'),
    phone:         localStorage.getItem('user_phone'),
    address:       localStorage.getItem('user_address')
  };
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initKakaoLogin);
} else {
  initKakaoLogin();
}

window.KakaoAuth = { startKakaoLogin, sendKakaoCodeToFlask, saveUserSession, logout, isLoggedIn, getCurrentUser };
