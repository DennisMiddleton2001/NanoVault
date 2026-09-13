class Banner:
    def __init__(self):
        m = open('./model_utils/banner.txt','r', encoding='utf-8')
        for l in m:
            print(f'{l[:-1]}')

