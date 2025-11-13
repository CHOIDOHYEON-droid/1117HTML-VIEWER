from PIL import Image
import os

# 현재 디렉토리
current_dir = os.path.dirname(os.path.abspath(__file__))

# 입력 파일
input_file = os.path.join(current_dir, 'icon-512.png')

# 출력 파일 경로
output_file = os.path.join(current_dir, 'ios', 'App', 'App', 'Assets.xcassets', 'AppIcon.appiconset', 'AppIcon-512@2x.png')

try:
    # 이미지 열기
    img = Image.open(input_file)

    # 1024x1024로 리사이즈 (고품질)
    img_resized = img.resize((1024, 1024), Image.Resampling.LANCZOS)

    # 저장
    img_resized.save(output_file, 'PNG')

    print(f"iOS app icon created: {output_file}")
    print(f"Size: 1024x1024")

except FileNotFoundError:
    print(f"Error: Cannot find {input_file}")
except Exception as e:
    print(f"Error: {e}")
    print("\nPillow library is required.")
    print("Install it with: pip install Pillow")
