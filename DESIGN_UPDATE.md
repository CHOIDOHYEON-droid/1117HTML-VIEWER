# 디자인 업데이트 완료

## 변경 사항

### 1. 앱 아이콘 변경
- 기존: 기본 HTML Viewer 아이콘
- 변경: DLAS logo.ico
- 파일: `ios/App/App/Assets.xcassets/AppIcon.appiconset/AppIcon-512@2x.png` (1024x1024)

### 2. GUI 스타일 변경 - DLAS 테마 적용

#### 배경색
- 기존: 그라데이션 (#667eea → #764ba2)
- 변경: #f5f7fa (연한 회색)

#### 폰트
- 기존: 시스템 기본 폰트
- 변경: 'Malgun Gothic' (Windows), Apple SD Gothic Neo (macOS)

#### 메인 컬러
- 기존: #667eea (보라색)
- 변경: #3498db (파란색)

#### 카드 스타일
- 배경: #FFFFFF
- border-radius: 12px (기존 20px)
- box-shadow: 0 2px 8px rgba(0,0,0,0.1) (더 은은한 그림자)

#### 업로드 박스
- border: 2px dashed #cfd8dc (기존 3px)
- border-radius: 8px (기존 15px)
- hover border-color: #3498db

#### 버튼 컬러
- 메인 버튼: #3498db
- 삭제 버튼: #e74c3c → hover: #c0392b
- border-radius: 6px (더 모던한 느낌)

#### 텍스트 컬러
- 제목: #2c3e50 (진한 회색)
- 부제목/설명: #5a6c7d
- 날짜/기타: #95a5a6

#### 최근 파일 항목
- 배경: #f8f9fa
- border: 1px solid #e9ecef
- hover: #ffffff, border-color: #3498db

## DLAS 스타일 일관성

이번 업데이트로 HTML Viewer 앱이 DLAS 데스크톱 프로그램과 동일한 디자인 언어를 사용하게 되었습니다:

### DLAS 디자인 시스템
1. **컬러 팔레트**
   - Primary: #3498db (파란색)
   - Danger: #e74c3c (빨간색)
   - Background: #f5f7fa
   - Card: #FFFFFF
   - Text: #2c3e50
   - Muted: #95a5a6

2. **타이포그래피**
   - 제목: 18px, font-weight: 600
   - 본문: 13-14px
   - 작은 텍스트: 10-11px

3. **Spacing**
   - 카드 패딩: 20-30px
   - 요소 간격: 8-10px

4. **Border Radius**
   - 큰 요소: 12px
   - 버튼: 6-8px
   - 입력 필드: 7-8px

## 다음 단계

### 1. 로컬 테스트
```bash
npx cap open ios
```
Xcode에서 시뮬레이터로 실행하여 디자인 확인

### 2. Appflow 빌드
```bash
git add .
git commit -m "Update app icon and GUI to DLAS theme"
git push
```

### 3. AltStore 설치
1. Appflow에서 IPA 다운로드
2. AltStore로 설치
3. 디자인 확인

## 주요 파일 변경

1. `www/index.html` - GUI 스타일 변경
2. `index.html` - 루트 파일 업데이트
3. `logo.ico` - DLAS 로고로 변경
4. `ios/App/App/Assets.xcassets/AppIcon.appiconset/AppIcon-512@2x.png` - iOS 아이콘
5. `ios/App/App/Info.plist` - 앱 설정 (이전 업데이트)
6. `ios/App/App/App.entitlements` - 권한 설정 (이전 업데이트)

## 참고

DLAS 프로그램의 디자인을 참고했습니다:
- 경로: `C:\Users\ehgus\Desktop\DLAS 프로그램 -백업\1112\intro\main.py`
- LoginWindow 클래스의 스타일 시트를 기반으로 작성
