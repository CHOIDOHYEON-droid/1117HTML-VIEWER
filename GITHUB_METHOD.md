# GitHub를 통한 Ionic Appflow 연결 (더 쉬운 방법)

SSH 키 설정 없이 GitHub를 통해 Appflow에 연결할 수 있습니다.

## 방법: GitHub 저장소를 통한 연결

### 1단계: GitHub 저장소 생성

1. https://github.com/ 접속 및 로그인
2. 우측 상단 **"+"** → **"New repository"** 클릭
3. 정보 입력:
   - **Repository name**: `html-viewer`
   - **Description**: HTML Viewer iOS App
   - **Public** 또는 **Private** 선택 (Private 권장)
   - **Add a README file**: 체크 안 함
   - **Add .gitignore**: 체크 안 함
4. **"Create repository"** 클릭

### 2단계: GitHub 저장소 URL 복사

생성 후 나타나는 페이지에서:
- **HTTPS URL** 복사 (예: `https://github.com/CHOIDOHYEON-droid/html-viewer.git`)

### 3단계: Git Remote 추가 및 푸시

프로젝트 폴더에서:

```bash
# GitHub remote 추가
git remote add origin https://github.com/CHOIDOHYEON-droid/html-viewer.git

# 푸시
git push -u origin main
```

**GitHub 로그인 정보 입력:**
- Username: GitHub 사용자명
- Password: Personal Access Token (아래 참조)

#### GitHub Personal Access Token 생성 (비밀번호 대신 사용)

1. GitHub → Settings → Developer settings
2. Personal access tokens → Tokens (classic)
3. **"Generate new token"** → **"Generate new token (classic)"**
4. Note: `Ionic Appflow`
5. Expiration: `90 days` 또는 원하는 기간
6. 권한 선택:
   - ✅ **repo** (전체 선택)
7. **"Generate token"** 클릭
8. **토큰 복사** (다시 볼 수 없으니 저장!)

### 4단계: Ionic Appflow에서 GitHub 연결

1. https://dashboard.ionicframework.com/ 접속
2. **HTML Viewer** 앱 선택
3. 좌측 메뉴 **"Settings"** 클릭
4. **"Git"** 탭 클릭
5. **"Connect to GitHub"** 클릭
6. GitHub 로그인 및 권한 승인
7. Repository 선택: `html-viewer`
8. Branch 선택: `main`
9. **"Connect"** 클릭

### 5단계: 완료!

이제 GitHub에 푸시하면 Appflow에서 자동으로 감지합니다:

```bash
# 코드 수정 후
git add .
git commit -m "Update app"
git push origin main
```

Appflow 대시보드 → Commits에서 확인 가능!

---

## 다음 단계: iOS 빌드

### 1. Apple Developer 계정 준비
- https://developer.apple.com/programs/
- $99/년 결제

### 2. Appflow에서 빌드
1. Builds → New Build
2. Platform: iOS
3. Build Type: Release
4. Start Build

---

## 명령어 요약

```bash
# 1. GitHub remote 추가
git remote add origin https://github.com/CHOIDOHYEON-droid/html-viewer.git

# 2. 푸시
git push -u origin main

# 향후 업데이트 시:
git add .
git commit -m "변경 내용"
git push origin main
```

GitHub를 통하면 SSH 키 설정 없이 쉽게 연결할 수 있습니다!
