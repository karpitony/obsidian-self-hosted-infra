import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import cast

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as OAuth2Credentials

from .config import CLIENT_SECRETS_FILE, TOKEN_FILE, GDRIVE_REDIRECT_URI, SERVER_IP, SERVER_PORT
from .logger import setup_logger

logger = setup_logger(__name__)

class AuthServer(HTTPServer):
    auth_code: str | None = None
    auth_url: str = ""

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    server: AuthServer

    def do_GET(self):
        # URL 파싱
        parsed_path = urlparse(self.path)
        params = parse_qs(parsed_path.query)
        
        # 1. 수동 입력(full_url) 처리 로직 추가
        if "full_url" in params:
            full_url = params["full_url"][0]
            # 입력된 전체 URL에서 다시 쿼리 파라미터(code 등) 추출
            inner_params = parse_qs(urlparse(full_url).query)
            if "code" in inner_params:
                self.server.auth_code = inner_params["code"][0]
                self._send_success_page()
                return
            else:
                self._send_error_page("URL에서 인증 코드를 찾을 수 없습니다. 다시 확인해 주세요.")
                return

        # 2. 초기 접속 페이지 (로그인 버튼 + JS 자동화)
        if parsed_path.path == '/':
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            
            # JS용 타겟 호스트 설정
            target_origin = f"http://{SERVER_IP}:{SERVER_PORT}"
            
            html = f"""
            <html>
                <head>
                    <title>Obsidian Remote Auth</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <script>
                        // [자동화 로직]
                        // 1. 현재 접속한 서버 주소를 로컬 스토리지에 임시 저장
                        if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {{
                            localStorage.setItem('remote_server_url', window.location.protocol + "//" + window.location.host);
                        }}
                        
                        // 2. 만약 localhost로 튕겼을 때 코드가 있다면 자동 복귀 시도
                        const urlParams = new URLSearchParams(window.location.search);
                        if ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && urlParams.has('code')) {{
                            const remoteUrl = localStorage.getItem('remote_server_url') || "{target_origin}";
                            window.location.href = remoteUrl + window.location.search;
                        }}
                    </script>
                </head>
                <body style="text-align:center; padding:20px; background:#1a1a1a; color:white; font-family:sans-serif;">
                    <h2 style="margin-bottom:30px;">📱 Remote Auth</h2>
                    <a href="{self.server.auth_url}" style="display:inline-block; padding:15px 25px; background:#4285F4; color:white; text-decoration:none; border-radius:8px; font-weight:bold; width:80%;">
                        Google 로그인 시작
                    </a>
                    
                    <div style="margin:40px 0; border-top:1px solid #333; padding-top:20px;">
                        <p style="font-size:0.9em; color:#aaa;">⚠️ 아이폰 등에서 '페이지를 찾을 수 없음'이 뜨면?</p>
                        <p style="font-size:0.8em; color:#888; margin-bottom:15px;">주소창의 URL을 복사해서 아래에 붙여넣어 주세요.</p>
                        
                        <form action="/" method="GET" style="display:flex; flex-direction:column; gap:10px;">
                            <input type="text" name="full_url" placeholder="http://127.0.0.1:8080/?code=..." 
                                style="padding:12px; border-radius:5px; border:1px solid #444; background:#222; color:white; font-size:0.8em;">
                            <button type="submit" style="padding:12px; background:#34A853; color:white; border:none; border-radius:5px; font-weight:bold;">인증 코드 수동 전송</button>
                        </form>
                    </div>
                </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))
            return

        # 3. 구글 리다이렉트 직접 수신 (code가 직접 전달된 경우)
        if "code" in params:
            self.server.auth_code = params["code"][0]
            self._send_success_page()
        else:
            self.send_response(400)
            self.end_headers()

    def _send_success_page(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("<h3>✅ 인증 완료!</h3><p>서버가 토큰을 저장했습니다. 이제 이 창을 닫으셔도 됩니다.</p>".encode("utf-8"))

    def _send_error_page(self, msg):
        self.send_response(400)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(f"<h3>❌ 오류 발생</h3><p>{msg}</p><a href='/'>다시 시도</a>".encode("utf-8"))
        

class GoogleDriveAuthenticator:
    SCOPES = ["https://www.googleapis.com/auth/drive.file"]

    def __init__(self, notifier):
        self.notifier = notifier

    def get_credentials(self) -> OAuth2Credentials:
        creds = None
        if TOKEN_FILE.exists():
            creds = OAuth2Credentials.from_authorized_user_file(str(TOKEN_FILE), self.SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("토큰 자동 갱신 완료")
                except Exception:
                    creds = self._auth_via_discord()
            else:
                creds = self._auth_via_discord()

            with open(TOKEN_FILE, "w") as token:
                token.write(creds.to_json())
        return creds

    def _auth_via_discord(self) -> OAuth2Credentials:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CLIENT_SECRETS_FILE), 
            self.SCOPES,
            redirect_uri=GDRIVE_REDIRECT_URI
        )
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

        # 디스코드로 보낼 서버 접속용 테일스케일 링크
        access_url = f"http://{SERVER_IP}:{SERVER_PORT}/"
        
        # 알림 메시지에 타임아웃 정보 추가
        self.notifier.info(
            "🔑 구글 인증 필요", 
            f"백업을 위해 인증이 필요합니다. **2시간 내**에 완료해 주세요.\n\n"
            f"[🔗 인증 페이지 열기]({access_url})\n\n"
            f"만약 타임아웃된 경우, 아침에 `uv run cli.py auth`를 실행하세요."
        )
        
        server = AuthServer(('0.0.0.0', SERVER_PORT), OAuthCallbackHandler)
        server.auth_url = auth_url
        server.timeout = 5 # 5초마다 루프 체크
        
        start_time = time.time()
        timeout_seconds = 2 * 3600 # 2시간 대기
        
        logger.info(f"인증 대기 중... (타임아웃: 2시간)")

        while server.auth_code is None:
            # 타임아웃 체크
            if time.time() - start_time > timeout_seconds:
                self.notifier.error("⏰ 인증 타임아웃", "2시간 동안 인증이 없어 백업 프로세스를 종료합니다. 나중에 수동으로 인증해 주세요.")
                logger.error("Auth timeout reached.")
                raise TimeoutError("인증 타임아웃(2시간)으로 auth 프로세스를 종료합니다.")
            
            server.handle_request()
        
        flow.fetch_token(code=server.auth_code)
        return cast(OAuth2Credentials, flow.credentials)