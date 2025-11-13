# iOS 앱 빌드 가이드

## 프로젝트 구조
- **웹 파일**: `www/` 폴더
- **iOS 프로젝트**: `ios/App/` 폴더
- **앱 아이콘**: `ios/App/App/Assets.xcassets/AppIcon.appiconset/`

## 앱 정보
- **앱 이름**: HTML Viewer
- **Bundle ID**: com.htmlviewer.app
- **아이콘**: icon-512.png를 기반으로 1024x1024 크기로 생성됨

## iOS 앱 빌드 방법

### 필수 요구사항
- macOS 컴퓨터
- Xcode (최신 버전 권장)
- Apple Developer 계정 (App Store 배포 시)

### 빌드 단계

1. **Mac에서 프로젝트 열기**
   ```bash
   # 프로젝트 폴더를 Mac으로 옮긴 후
   cd "1113HTML VIEWER"
   npm install
   ```

2. **Xcode에서 프로젝트 열기**
   ```bash
   npx cap open ios
   ```
   또는 직접 열기:
   ```bash
   open ios/App/App.xcworkspace
   ```

3. **Xcode에서 설정**
   - **Signing & Capabilities** 탭에서
   - Team 선택 (Apple Developer 계정)
   - Bundle Identifier 확인: `com.htmlviewer.app`
   - Provisioning Profile 설정

4. **테스트**
   - 시뮬레이터 선택 (예: iPhone 15)
   - `Cmd + R`로 빌드 및 실행

5. **실제 기기에서 테스트**
   - 기기 연결
   - 기기를 대상으로 선택
   - `Cmd + R`로 빌드 및 실행
   - 기기에서 "Settings > General > Device Management"에서 개발자 인증

6. **App Store 배포**
   - Xcode에서 `Product > Archive` 선택
   - Archive가 완료되면 `Distribute App` 선택
   - App Store Connect에 업로드
   - App Store Connect에서 앱 정보 입력 및 제출

## 웹 파일 업데이트 후

웹 파일을 수정한 후에는 iOS 프로젝트에 동기화해야 합니다:

```bash
# www 폴더에 파일 복사 후
npx cap sync ios
```

## 아이콘 변경 방법

다른 로고 이미지를 사용하려면:

1. 새로운 이미지 파일(512x512 이상)을 `icon-512.png`로 저장
2. `resize_for_ios.py` 스크립트 실행:
   ```bash
   python resize_for_ios.py
   ```
3. iOS 프로젝트 다시 빌드

## 참고 자료
- [Capacitor iOS 문서](https://capacitorjs.com/docs/ios)
- [iOS App Distribution](https://developer.apple.com/documentation/xcode/distributing-your-app-for-beta-testing-and-releases)
