# AltStore 공유 문제 해결 가이드

## 문제점
AltStore로 사이드로드한 HTML Viewer 앱이 다른 앱의 공유 목록에 나타나지 않는 문제

## 수정 내용

### 1. Entitlements 파일 추가
`ios/App/App/App.entitlements` 파일 생성 완료

### 2. Info.plist 수정
- `LSHandlerRank`를 `Alternate`에서 `Owner`로 변경
- `UTExportedTypeDeclarations` 추가
- HTML 파일 타입 선언을 Export로 설정

## Xcode 설정 방법

### 단계 1: Xcode에서 프로젝트 열기
```bash
cd "C:\Users\ehgus\Desktop\1117HTML VIEWER"
npx cap open ios
```

### 단계 2: Entitlements 파일 프로젝트에 추가
1. Xcode 좌측 파일 트리에서 `App` 폴더를 우클릭
2. "Add Files to "App"..." 선택
3. `App.entitlements` 파일 선택
4. "Copy items if needed" 체크
5. "Add" 클릭

### 단계 3: 빌드 설정에 Entitlements 연결
1. 프로젝트 네비게이터에서 "App" 프로젝트 선택 (최상단 파란 아이콘)
2. TARGETS > App 선택
3. "Build Settings" 탭 선택
4. 검색창에 "entitlements" 입력
5. "Code Signing Entitlements" 항목 찾기
6. 값을 `App/App.entitlements`로 설정

### 단계 4: 재빌드 및 배포
1. Product > Clean Build Folder (Shift + Cmd + K)
2. Product > Archive
3. Distribute App > Development (또는 Ad Hoc)
4. IPA 파일 생성

### 단계 5: Appflow로 빌드하는 경우
Appflow에서 자동으로 변경사항을 감지하여 포함합니다:
```bash
git add .
git commit -m "Add entitlements and fix document type declarations"
git push
```

## 중요 참고사항

### AltStore의 제약사항
AltStore는 **무료 Apple Developer 계정**으로 서명하기 때문에 다음과 같은 제약이 있습니다:

1. **일부 Entitlements 제거됨**
   - App Groups는 작동하지 않을 수 있음
   - iCloud 기능은 제한됨

2. **공유 기능 제한**
   - 다른 앱에서 "공유" 시 HTML Viewer가 나타나지 않을 수 있음
   - 파일 연결(File Association)이 완벽하게 작동하지 않을 수 있음

3. **7일 만료**
   - 7일마다 AltStore로 재설치 필요

### 대안 방법

#### 방법 1: 앱 내에서 Files 접근 (권장)
현재 앱에는 이미 파일 선택 기능이 있습니다:
1. HTML Viewer 앱 실행
2. "HTML 파일 선택" 버튼 탭
3. Files 앱에서 HTML 파일 선택

#### 방법 2: Files 앱의 "On My iPhone" 사용
1. Files 앱 열기
2. HTML 파일을 "On My iPhone" > "HTML Viewer"로 복사
3. HTML Viewer 앱에서 파일 선택

#### 방법 3: Paid Apple Developer 계정 ($99/년)
완벽한 해결책:
- TestFlight를 통한 배포
- 모든 Entitlements 사용 가능
- 공유 기능 완전 지원
- 90일 만료 (TestFlight)

#### 방법 4: Xcode로 직접 설치
개발용으로만 사용 가능 (7일 만료):
1. iPhone을 Mac에 연결
2. Xcode에서 Product > Run
3. 기기에 직접 설치

## 테스트 방법

### 테스트 1: 파일 선택 기능
1. HTML Viewer 앱 실행
2. "HTML 파일 선택" 버튼 탭
3. Files 앱에서 HTML 파일 선택
4. 파일이 새 탭에서 열리는지 확인

### 테스트 2: 공유 기능 (제한적)
1. Files 앱에서 HTML 파일 찾기
2. 길게 누르기 > "공유" 선택
3. "HTML Viewer" 옵션이 나타나는지 확인
   - **주의**: AltStore에서는 나타나지 않을 수 있음

### 테스트 3: 최근 파일 기능
1. 파일을 한 번 열기
2. 앱 종료 후 재실행
3. "최근 파일" 목록에 나타나는지 확인

## 문제 해결

### Q: 여전히 공유 목록에 나타나지 않습니다
A: AltStore의 제약사항입니다. 앱 내 "파일 선택" 기능을 사용하거나 Paid Developer 계정을 사용하세요.

### Q: Xcode에서 "Provisioning profile doesn't support Entitlements" 오류
A: 무료 계정의 제약입니다. App.entitlements에서 다음 항목 제거:
- `com.apple.developer.icloud-container-identifiers`
- `com.apple.developer.ubiquity-kvstore-identifier`

### Q: 파일을 선택했는데 아무것도 안 나타납니다
A:
1. Safari 개발자 도구로 콘솔 확인
2. 파일이 올바른 HTML 형식인지 확인
3. 파일 크기가 너무 크지 않은지 확인 (localStorage 제한)

## 추가 개선 사항 제안

### 1. Shortcuts 앱 연동
Shortcuts 앱으로 자동화 가능하도록 URL Scheme 추가

### 2. 파일 브라우저 추가
앱 내에서 "On My iPhone" 폴더의 파일 목록 표시

### 3. WebDAV 지원
네트워크 드라이브에서 HTML 파일 직접 열기

원하시는 기능이 있으면 말씀해주세요!
