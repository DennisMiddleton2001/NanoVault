class Banner:
    def __init__(self, show_banner=False):
        if show_banner:
            m = open('./model_utils/banner.txt','r', encoding='utf-8')
            for l in m:
                print(f'{l[:-1]}')

