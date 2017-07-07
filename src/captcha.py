from os.path import realpath, dirname, join

from PIL import Image
from PIL import ImageFilter
from PIL.ImageDraw import Draw
from PIL.ImageFont import truetype

current_dir = dirname(realpath(__file__))


def draw_text(image, text, font_size):
    font = truetype(join(current_dir, 'static/font.ttf'), font_size)
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

    for file, text, wh, fs in params:
        image = Image.new('RGB', wh, (255, 255, 255))

        # background
        Draw(image).rectangle([(0, 0), image.size], fill='#eeeecc')
        # draw text
        draw_text(image, text, fs)

        image.filter(ImageFilter.SMOOTH)
        image.save(join(current_dir, 'static/i/btn/' + file + '.png'), 'PNG', quality=75)

if __name__ == '__main__':
    db = (
        ('quick', '挑战AI', (160, 60), 36),
        ('start', '真人对抗', (160, 60), 36),
        ('exit',  '退出游戏', (160, 60), 36),
        ('setting', '设置', (160, 60), 36),
        ('register', '注册', (160, 60), 36),

        ('score_0', '不叫', (128, 48), 28),
        ('score_1', '一分', (128, 48), 28),
        ('score_2', '两分', (128, 48), 28),
        ('score_3', '三分', (128, 48), 28),
        ('pass',    '不出', (128, 48), 28),
        ('hint',    '提示', (128, 48), 28),
        ('shot',    '出牌', (128, 48), 28),
    )
    generate_button(db)
    print('generate done')
