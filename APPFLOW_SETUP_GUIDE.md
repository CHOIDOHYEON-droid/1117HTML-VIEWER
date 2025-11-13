# Ionic Appflow 설정 가이드 (Mac 없이 iOS 앱 빌드)

이 가이드를 따라하면 Mac 없이 Windows에서 iOS 앱을 빌드할 수 있습니다.

---

## 1단계: Ionic Appflow 계정 생성

### 1-1. Appflow 웹사이트 접속
1. 브라우저에서 https://ionic.io/appflow 접속
2. 우측 상단 **"Start Free Trial"** 또는 **"Sign Up"** 클릭

### 1-2. 계정 생성
다음 중 하나를 선택:
- **GitHub 계정으로 가입** (권장)
- **이메일로 가입**

#### GitHub 계정으로 가입 (권장):
1. "Continue with GitHub" 클릭
2. GitHub 로그인
3. Ionic 앱 권한 승인

#### 이메일로 가입:
1. 이메일 주소 입력
2. 비밀번호 설정
3. 이메일 인증 완료

### 1-3. 무료 체험 시작
- **무료 체험 기간**: 14일
- **체험 후**: $29/월 (Starter 플랜) 또는 취소 가능

---

## 2단계: Ionic CLI에서 로그인

프로젝트 폴더에서 터미널을 열고:

```bash
ionic login
```

### 로그인 방법:
1. 이메일과 비밀번호 입력
2. 또는 웹 브라우저가 열리면 로그인

**성공 메시지:**
```
[OK] You are logged in!
```

---

## 3단계: Appflow에 프로젝트 연결

### 3-1. 프로젝트 연결 명령어 실행

```bash
ionic link
```

### 3-2. 옵션 선택

#### "Create a new app" 선택
```
? What would you like to do?
  Link an existing app on Ionic
❯ Create a new app on Ionic
```

**Enter** 키를 눌러 선택

### 3-3. 앱 이름 입력
```
? Name of new app: HTML Viewer
```

"HTML Viewer" 입력 후 Enter

### 3-4. Git 리모트 선택
```
? Which git remote would you like to use?
❯ ionic (https://git.ionicframework.com/...)
```

**Enter** 키를 눌러 ionic 선택

### 3-5. 연결 완료
```
[OK] Your app has been linked!

App ID: xxxxxxxx
```

App ID를 기록해두세요 (나중에 필요할 수 있음).

---

## 4단계: 코드를 Appflow에 푸시

### 4-1. Git 브랜치 확인 및 이름 변경 (필요시)

```bash
git branch -M main
```

### 4-2. Ionic Git 리모트에 푸시

```bash
git push ionic main
```

**처음 푸시 시 자격 증명 입력:**
- Username: Ionic 계정 이메일
- Password: Ionic 계정 비밀번호

**성공 메시지:**
```
To https://git.ionicframework.com/...
 * [new branch]      main -> main
```

### 4-3. Appflow 대시보드에서 확인

1. 브라우저에서 https://dashboard.ionicframework.com/ 접속
2. 로그인
3. "HTML Viewer" 앱 선택
4. 좌측 메뉴 "Commits" 클릭
5. 방금 푸시한 커밋이 보이는지 확인

---

## 5단계: Apple Developer 계정 준비 (필수)

iOS 앱을 빌드하려면 **Apple Developer 계정**이 필요합니다.

### 5-1. Apple Developer Program 가입

1. https://developer.apple.com/programs/ 접속
2. **"Enroll"** 클릭
3. Apple ID로 로그인
4. 개인 또는 조직 선택
5. **$99/년** 결제
6. 승인 대기 (1-2일 소요)

### 5-2. App ID 생성

승인 후:

1. https://developer.apple.com/account 접속
2. **"Certificates, Identifiers & Profiles"** 클릭
3. 좌측 메뉴 **"Identifiers"** 클릭
4. **"+"** 버튼 클릭
5. **"App IDs"** 선택 → Continue
6. **"App"** 선택 → Continue
7. 정보 입력:
   - **Description**: HTML Viewer
   - **Bundle ID**: **Explicit** 선택
   - **Bundle ID 입력**: `com.htmlviewer.app`
     (capacitor.config.json의 appId와 동일해야 함)
8. **Capabilities**: 필요한 기능 선택 (기본값으로도 가능)
9. **Continue** → **Register**

**Bundle ID를 반드시 기록해두세요!**

---

## 6단계: Appflow에서 iOS 인증서 설정

### 방법 A: 자동 생성 (권장)

Appflow는 자동으로 iOS 인증서를 생성할 수 있습니다 (Mac 불필요).

1. Appflow 대시보드에서 **HTML Viewer** 앱 선택
2. 좌측 메뉴 **"Settings"** 클릭
3. **"Signing Certificates"** 탭 클릭
4. **"Generate Certificate"** 클릭
5. Apple Developer 계정으로 로그인
6. 자동으로 인증서와 프로비저닝 프로파일 생성

### 방법 B: 수동 업로드 (Mac 필요)

Mac이 있는 경우:

1. Mac에서 Keychain Access로 .p12 인증서 생성
2. Apple Developer에서 Provisioning Profile 다운로드
3. Appflow에 업로드

**Mac이 없다면 방법 A를 사용하세요.**

---

## 7단계: iOS 빌드 설정

### 7-1. 빌드 환경 설정 파일 생성

프로젝트 루트에 `ionic.config.json` 파일이 자동 생성되었습니다.

확인:
```bash
cat ionic.config.json
```

### 7-2. package.json 확인

Capacitor 관련 스크립트가 있는지 확인:

```json
{
  "scripts": {
    "build": "echo 'Build completed'"
  }
}
```

Appflow는 `npm run build` 명령을 실행하므로 이 스크립트가 있어야 합니다.

---

## 8단계: Appflow에서 iOS 빌드 실행

### 8-1. 빌드 생성

1. Appflow 대시보드 → **HTML Viewer** 앱 선택
2. 좌측 메뉴 **"Builds"** 클릭
3. 우측 상단 **"New Build"** 클릭

### 8-2. 빌드 설정

다음 정보 입력:

**Commit:**
- 최신 커밋 선택 (main 브랜치)

**Target Platform:**
- **iOS** 선택

**Build Stack:**
- 최신 버전 선택 (예: macOS - 13)

**Build Type:**
- **Release** 선택 (App Store 배포용)
- 또는 **Debug** (테스트용)

**Signing Certificate:**
- 6단계에서 생성한 인증서 선택

**Provisioning Profile:**
- 자동 생성된 프로파일 선택

**Native Config:**
- **Use Capacitor** 선택

**Environment:**
- 기본값 사용

### 8-3. 빌드 시작

**"Start Build"** 클릭

### 8-4. 빌드 진행 상황 확인

- 빌드 시간: 약 **5-15분**
- 진행 상황은 실시간으로 표시됨
- 로그를 클릭하여 자세한 내용 확인 가능

**빌드 성공 시:**
```
✓ Build succeeded
```

**빌드 실패 시:**
- 로그를 확인하여 오류 수정
- 일반적인 오류:
  - 인증서 문제
  - Bundle ID 불일치
  - Capacitor 설정 오류

---

## 9단계: IPA 파일 다운로드

### 9-1. 빌드 완료 후

1. 빌드 목록에서 성공한 빌드 클릭
2. **"Download IPA"** 버튼 클릭
3. `.ipa` 파일 다운로드 (컴퓨터에 저장)

**IPA 파일은 iOS 앱 설치 파일입니다.**

---

## 10단계: App Store Connect에 앱 등록

### 10-1. App Store Connect 접속

1. https://appstoreconnect.apple.com/ 접속
2. Apple Developer 계정으로 로그인

### 10-2. 새 앱 생성

1. **"My Apps"** 클릭
2. **"+"** 버튼 클릭 → **"New App"** 선택
3. 정보 입력:
   - **Platform**: iOS
   - **Name**: HTML Viewer (또는 원하는 이름)
   - **Primary Language**: Korean
   - **Bundle ID**: `com.htmlviewer.app` (5단계에서 생성한 것)
   - **SKU**: HTMLVIEWER001 (고유 식별자, 임의로 입력)
4. **"Create"** 클릭

### 10-3. 앱 정보 입력

**App Information 탭:**
- Subtitle (부제목)
- Privacy Policy URL (개인정보 처리방침 URL - 필수)
- 카테고리 선택 (예: Medical, Utilities)

**Pricing and Availability:**
- 무료/유료 선택
- 배포 국가 선택

---

## 11단계: IPA 파일을 App Store Connect에 업로드

### 방법 A: Appflow에서 직접 업로드 (권장)

Appflow Pro 이상 플랜에서 가능:

1. Appflow 대시보드 → 빌드 선택
2. **"Deploy to App Store"** 클릭
3. App Store Connect API Key 입력
4. 자동 업로드

### 방법 B: Transporter 앱 사용 (Mac 필요)

Mac에서:

1. App Store에서 **"Transporter"** 앱 다운로드
2. Transporter 실행
3. .ipa 파일을 드래그 앤 드롭
4. **"Deliver"** 클릭
5. Apple ID 로그인
6. 업로드 완료 대기 (5-20분)

### 방법 C: 대안 (Mac이 없는 경우)

Windows에서 직접 업로드하는 공식 방법은 없습니다.

**대안:**
1. Mac을 사용하는 친구/지인에게 부탁
2. 클라우드 Mac 서비스 이용 (MacStadium, MacinCloud 등)
3. Appflow Pro 플랜으로 업그레이드 (자동 업로드 가능)

---

## 12단계: App Store Connect에서 앱 제출

### 12-1. 빌드 연결

IPA 업로드 후 (처리 시간: 10-30분):

1. App Store Connect → **HTML Viewer** 앱 선택
2. **"1.0 Prepare for Submission"** 클릭
3. **"Build"** 섹션에서 **"+"** 클릭
4. 업로드한 빌드 선택

### 12-2. 스크린샷 업로드 (필수)

다음 크기의 스크린샷 필요:

**6.7" Display (iPhone 14 Pro Max 등):**
- 1290 x 2796 픽셀
- 최소 3장, 최대 10장

**6.5" Display (iPhone 11 Pro Max 등):**
- 1242 x 2688 픽셀

**스크린샷 생성 방법:**
1. iOS 시뮬레이터 사용 (Mac 필요)
2. 또는 온라인 도구 사용:
   - https://www.screely.com/
   - https://mockuphone.com/

**임시 스크린샷:**
- 앱 아이콘과 간단한 설명을 포함한 이미지 제작
- 나중에 실제 앱 스크린샷으로 교체 가능

### 12-3. 앱 설명 작성

**필수 항목:**
- **Description**: 앱 설명 (최대 4,000자)
- **Keywords**: 검색 키워드 (최대 100자, 쉼표로 구분)
- **Support URL**: 지원 URL
- **Marketing URL**: 마케팅 URL (선택)

**예시:**
```
Description:
치과 3D 모델 HTML 파일을 쉽게 열고 볼 수 있는 전문 뷰어 앱입니다.

주요 기능:
- HTML 파일 빠른 열기
- 3D 모델 렌더링
- 최근 파일 목록 관리
- 오프라인 사용 가능

Keywords:
HTML, 뷰어, 치과, 3D, 모델, dental, viewer
```

### 12-4. 개인정보 처리방침

**Privacy Policy URL 필수:**
- 개인정보를 수집하지 않더라도 필수
- 간단한 개인정보 처리방침 웹페이지 생성 필요

**무료 생성 도구:**
- https://www.privacypolicies.com/
- https://app-privacy-policy-generator.firebaseapp.com/

### 12-5. 연령 등급 설정

1. **"Age Rating"** 클릭
2. 질문에 답변 (대부분 "No" 선택)
3. **"Done"** 클릭

### 12-6. 심사 정보 입력

**App Review Information:**
- **First Name**: 이름
- **Last Name**: 성
- **Phone Number**: 전화번호
- **Email**: 이메일
- **Notes**: 심사자를 위한 메모 (선택)

**Sign-In Information:**
- 로그인이 필요한 경우 테스트 계정 정보 제공

### 12-7. 제출

1. 모든 항목 입력 완료 확인
2. **"Add for Review"** 클릭
3. **"Submit for Review"** 클릭

---

## 13단계: 심사 대기 및 배포

### 심사 프로세스

1. **Waiting for Review**: 심사 대기 (1-3일)
2. **In Review**: 심사 중 (1-2일)
3. **Pending Developer Release**: 승인 완료 (수동 출시 대기)
4. **Ready for Sale**: App Store에 배포됨!

**거절된 경우:**
- 거절 사유 확인
- 문제 수정
- 다시 제출

### 앱 출시

승인 후:
- 자동 출시 또는
- 수동으로 **"Release This Version"** 클릭

**축하합니다! 앱이 App Store에 배포되었습니다!**

---

## 웹 파일 업데이트 시

앱을 업데이트하려면:

### 1. 웹 파일 수정
```bash
# www 폴더의 파일 수정
# 예: www/index.html
```

### 2. iOS 프로젝트에 동기화
```bash
npx cap sync ios
```

### 3. Git 커밋 및 푸시
```bash
git add .
git commit -m "Update: [변경 내용]"
git push ionic main
```

### 4. Appflow에서 새 빌드 생성
- 8단계 반복
- 버전 번호 증가 (package.json의 version)

### 5. App Store Connect에 새 빌드 업로드
- 11-13단계 반복
- 버전 번호 증가

---

## 버전 관리

### package.json에서 버전 증가

```json
{
  "version": "1.0.0"  // → "1.0.1", "1.1.0" 등
}
```

### iOS 버전 관리

`ios/App/App.xcodeproj/project.pbxproj` 파일은 Capacitor가 자동 관리합니다.

또는 직접 설정:
1. Xcode에서 프로젝트 열기 (Mac 필요)
2. General → Version 수정

---

## 비용 요약

### 필수 비용:
- **Apple Developer**: $99/년
- **Ionic Appflow**: $29/월 (Starter) 또는 $99/월 (Growth)
  - 14일 무료 체험

### 1년 총 비용:
- 최소: $99 + ($29 × 12) = **$447** (약 60만원)

### 절감 방법:
- 앱 개발 및 테스트 기간에만 Appflow 구독
- 배포 후 구독 취소 (업데이트 필요 시 재구독)

---

## 문제 해결

### 빌드 실패 시

#### 1. Bundle ID 불일치
**오류:** `Error: Bundle identifier mismatch`

**해결:**
- `capacitor.config.json`의 `appId` 확인
- Apple Developer의 App ID와 일치하는지 확인

#### 2. 인증서 오류
**오류:** `Code signing error`

**해결:**
- Appflow에서 인증서 재생성
- Provisioning Profile 재생성

#### 3. Capacitor 동기화 오류
**오류:** `Unable to find capacitor.config.json`

**해결:**
```bash
npx cap sync ios
git add .
git commit -m "Fix: Sync iOS"
git push ionic main
```

### 업로드 실패 시

**오류:** `Unable to process application`

**해결:**
- IPA 파일 재다운로드
- Transporter 앱 재시도
- App Store Connect 상태 확인

---

## 다음 단계

1. ✅ **Ionic Appflow 계정 생성** (1단계)
2. ✅ **CLI 로그인** (2단계)
3. ✅ **프로젝트 연결** (3단계)
4. ✅ **코드 푸시** (4단계)
5. ⏳ **Apple Developer 가입** (5단계)
6. ⏳ **iOS 빌드 실행** (8단계)
7. ⏳ **App Store 제출** (10-13단계)

---

## 참고 링크

- **Ionic Appflow**: https://ionic.io/appflow
- **Appflow 문서**: https://ionic.io/docs/appflow
- **Apple Developer**: https://developer.apple.com/
- **App Store Connect**: https://appstoreconnect.apple.com/
- **Capacitor 문서**: https://capacitorjs.com/docs

---

## 도움이 필요하신가요?

- **Ionic 포럼**: https://forum.ionicframework.com/
- **Ionic Discord**: https://ionic.link/discord
- **Stack Overflow**: [ionic-framework] 태그

**성공을 기원합니다! 🚀**
