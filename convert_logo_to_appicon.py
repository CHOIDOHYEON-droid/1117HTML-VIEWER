from PIL import Image
import os

# 현재 디렉토리
current_dir = os.path.dirname(os.path.abspath(__file__))

# 입력 파일 (logo.ico)
input_file = os.path.join(current_dir, 'logo.ico')

# 출력 파일 경로
output_dir = os.path.join(current_dir, 'ios', 'App', 'App', 'Assets.xcassets', 'AppIcon.appiconset')
output_file = os.path.join(output_dir, 'AppIcon-512@2x.png')

try:
    # ICO 파일 열기
    img = Image.open(input_file)

    # ICO 파일에 여러 크기가 포함되어 있으면 가장 큰 것을 선택
    # 또는 RGBA 모드로 변환
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    # 1024x1024로 리사이즈 (고품질)
    img_resized = img.resize((1024, 1024), Image.Resampling.LANCZOS)

    # 배경이 투명한 경우 흰색 배경 추가
    if img_resized.mode == 'RGBA':
        # 흰색 배경 생성
        background = Image.new('RGB', (1024, 1024), (255, 255, 255))
        # 알파 채널을 사용하여 합성
        background.paste(img_resized, mask=img_resized.split()[3])
        img_resized = background

    # PNG로 저장
    img_resized.save(output_file, 'PNG')

    print(f"[OK] iOS app icon created successfully!")
    print(f"  Input: {input_file}")
    print(f"  Output: {output_file}")
    print(f"  Size: 1024x1024")
    print("")
    print("Next steps:")
    print("1. npx cap sync ios")
    print("2. Build in Appflow")
    print("3. Install with AltStore")

except FileNotFoundError:
    print(f"[ERROR] Cannot find {input_file}")
    print("Make sure logo.ico exists in the current directory.")
except Exception as e:
    print(f"[ERROR] {e}")
    print("")
    print("Pillow library is required.")
    print("Install it with: pip install Pillow")
