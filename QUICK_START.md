# 빠른 시작 가이드 - Ionic Appflow로 iOS 앱 빌드

## 현재 상태 ✅

- ✅ Capacitor 프로젝트 설정 완료
- ✅ iOS 플랫폼 추가 완료
- ✅ 앱 아이콘 설정 완료
- ✅ Ionic CLI 설치 완료
- ✅ Git 저장소 초기화 완료
- ✅ Ionic 프로젝트 초기화 완료

## 다음 단계 (직접 실행 필요)

### 1단계: Ionic Appflow 계정 생성

1. 브라우저에서 https://ionic.io/appflow 접속
2. **"Start Free Trial"** 클릭
3. GitHub 계정 또는 이메일로 가입
4. 14일 무료 체험 시작

### 2단계: Ionic 로그인 (터미널에서 실행)

프로젝트 폴더에서:

```bash
ionic login
```

웹 브라우저가 열리면 Ionic 계정으로 로그인하세요.

**성공 메시지:**
```
[OK] You are logged in!
```

### 3단계: Appflow에 프로젝트 연결

```bash
ionic link
```

**선택 사항:**
1. "Create a new app on Ionic" 선택
2. 앱 이름 입력: `HTML Viewer`
3. Git remote: `ionic` 선택

**성공 메시지:**
```
[OK] Your app has been linked!
```

### 4단계: 코드 푸시

```bash
git push ionic main
```

**로그인 정보 입력:**
- Username: Ionic 이메일
- Password: Ionic 비밀번호

**성공 메시지:**
```
To https://git.ionicframework.com/...
 * [new branch]      main -> main
```

### 5단계: Apple Developer 계정 준비

1. https://developer.apple.com/programs/ 접속
2. **$99/년** 결제하여 가입
3. App ID 생성:
   - Bundle ID: `com.htmlviewer.app`

### 6단계: Appflow에서 iOS 빌드

1. https://dashboard.ionicframework.com/ 접속
2. HTML Viewer 앱 선택
3. 좌측 메뉴 **"Builds"** → **"New Build"** 클릭
4. Platform: **iOS** 선택
5. Build Type: **Release** 선택
6. 인증서 설정 (자동 생성 가능)
7. **"Start Build"** 클릭
8. 약 5-15분 대기
9. 빌드 완료 후 **IPA 다운로드**

### 7단계: App Store Connect에 제출

자세한 내용은 `APPFLOW_SETUP_GUIDE.md` 파일을 참고하세요.

---

## 명령어 요약

```bash
# 1. Ionic 로그인
ionic login

# 2. Appflow 연결
ionic link

# 3. 코드 푸시
git push ionic main

# 웹 파일 수정 시:
# 1. 파일 수정 (www 폴더)
# 2. iOS 동기화
npx cap sync ios

# 3. 커밋 및 푸시
git add .
git commit -m "Update: 변경사항"
git push ionic main

# 4. Appflow에서 새 빌드 생성
```

---

## 필요한 계정

1. **Ionic Appflow** 계정 (무료 체험 14일)
   - 가입: https://ionic.io/appflow
   - 비용: $29/월 (체험 후)

2. **Apple Developer** 계정 (필수)
   - 가입: https://developer.apple.com/programs/
   - 비용: $99/년

---

## 다음 실행할 명령어

Windows PowerShell 또는 명령 프롬프트에서:

```bash
# 프로젝트 폴더로 이동
cd "C:\Users\ehgus\Desktop\1113HTML VIEWER"

# Ionic 로그인
ionic login
```

웹 브라우저가 열리면 로그인하세요!

---

## 도움말

- 자세한 가이드: `APPFLOW_SETUP_GUIDE.md` 참고
- Ionic 문서: https://ionic.io/docs/appflow
- 문제 발생 시: https://forum.ionicframework.com/
