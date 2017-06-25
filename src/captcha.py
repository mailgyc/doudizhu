from os.path import realpath, dirname, join

from PIL import Image
from PIL import ImageFilter
from PIL.ImageDraw import Draw
from PIL.ImageFont import truetype

current_dir = dirname(realpath(__file__))


def draw_text(image, text):
    font = truetype(join(current_dir, 'font.ttf'), 36)
    color = '#5C87B2'

    draw = Draw(image)
    char_images = []
    for ch in text:
        c_width, c_height = draw.textsize(ch, font=font)
        char_image = Image.new('RGB', (c_width, c_height), (0, 0, 0))
        char_draw = Draw(char_image)
        char_draw.text((0, 0), ch, font=font, fill=color)
        char_image = char_image.crop(char_image.getbbox())
        char_images.append(char_image)

    width, height = image.size
    total = len(char_images)
    for i, char_image in enumerate(char_images):
        c_width, c_height = char_image.size
        mask = char_image.convert('L').point(lambda i: i * 1.97)
        upper = int((height - c_height) / 2)
        left = int((width * (i + 1) / (total + 1)) - c_width/2)
        image.paste(char_image, (left, upper), mask)
    return image


def generate_button(params):

    width, height = 160, 60

    for file, text in params:
        image = Image.new('RGB', (width, height), (255, 255, 255))

        # background
        Draw(image).rectangle([(0, 0), image.size], fill='#eeeecc')

        # draw text
        draw_text(image, text)

        image.filter(ImageFilter.SMOOTH)
        image.save(join(current_dir, 'static/i/btn/' + file + '.png'), 'PNG', quality=75)

if __name__ == '__main__':
    db = (
        ('quick', '快速开始'),
        ('exit', '退出游戏'),
        ('start', '开始'),
        ('setting', '设置'),
        ('score_0', '不叫'),
        ('score_1', '一分'),
        ('score_2', '两分'),
        ('score_3', '三分'),
        ('pass', '不出'),
        ('hint', '提示'),
        ('shot', '出牌'),
    )
    generate_button(db)
