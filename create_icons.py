from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size, filename):
    # 배경 그라디언트를 위한 이미지 생성
    img = Image.new('RGB', (size, size))
    draw = ImageDraw.Draw(img)

    # 그라디언트 배경 (보라색 계열)
    for y in range(size):
        r = int(102 + (118 - 102) * y / size)
        g = int(126 + (75 - 126) * y / size)
        b = int(234 + (162 - 234) * y / size)
        draw.line([(0, y), (size, y)], fill=(r, g, b))

    # 흰색 문서 모양 그리기
    padding = int(size * 0.15)
    doc_width = int(size * 0.5)
    doc_height = int(size * 0.65)
    doc_x = (size - doc_width) // 2
    doc_y = (size - doc_height) // 2
    corner_size = int(size * 0.1)

    # 문서 본체
    points = [
        (doc_x, doc_y + corner_size),
        (doc_x + doc_width - corner_size, doc_y + corner_size),
        (doc_x + doc_width, doc_y + corner_size * 2),
        (doc_x + doc_width, doc_y + doc_height),
        (doc_x, doc_y + doc_height),
        (doc_x, doc_y + corner_size)
    ]
    draw.polygon(points, fill='white')

    # 접힌 모서리
    corner_points = [
        (doc_x + doc_width - corner_size, doc_y + corner_size),
        (doc_x + doc_width, doc_y + corner_size * 2),
        (doc_x + doc_width - corner_size, doc_y + corner_size * 2)
    ]
    draw.polygon(corner_points, fill='#f0f0f0')

    # HTML 텍스트
    try:
        font_size = int(size * 0.12)
        # Windows 기본 폰트 사용
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()

    text = "HTML"
    # 텍스트 크기 계산
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    text_x = (size - text_width) // 2
    text_y = size // 2 - text_height // 2 + int(size * 0.05)

    draw.text((text_x, text_y), text, fill='#667eea', font=font)

    # 3D 큐브 (작은 큐브)
    cube_size = int(size * 0.08)
    cube_x = size // 2 - cube_size
    cube_y = size // 2 - int(size * 0.15)

    # 큐브 앞면
    draw.rectangle([cube_x, cube_y, cube_x + cube_size, cube_y + cube_size], fill='#43e97b')

    # 큐브 오른쪽면
    right_points = [
        (cube_x + cube_size, cube_y),
        (cube_x + cube_size + cube_size // 2, cube_y - cube_size // 2),
        (cube_x + cube_size + cube_size // 2, cube_y - cube_size // 2 + cube_size),
        (cube_x + cube_size, cube_y + cube_size)
    ]
    draw.polygon(right_points, fill='#38f9d7')

    # 큐브 윗면
    top_points = [
        (cube_x, cube_y),
        (cube_x + cube_size // 2, cube_y - cube_size // 2),
        (cube_x + cube_size + cube_size // 2, cube_y - cube_size // 2),
        (cube_x + cube_size, cube_y)
    ]
    draw.polygon(top_points, fill='#2dd4bf')

    # 저장
    img.save(filename, 'PNG')
    print(f"Created {filename}")

# 현재 스크립트 디렉토리에 아이콘 생성
script_dir = os.path.dirname(os.path.abspath(__file__))

try:
    create_icon(192, os.path.join(script_dir, 'icon-192.png'))
    create_icon(512, os.path.join(script_dir, 'icon-512.png'))
    print("\n아이콘 생성 완료!")
except Exception as e:
    print(f"오류 발생: {e}")
    print("\nPillow 라이브러리가 필요합니다.")
    print("다음 명령어로 설치하세요: pip install Pillow")
