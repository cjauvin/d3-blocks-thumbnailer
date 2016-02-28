from __future__ import print_function

import base64
import json
import re
import sys
import time
from io import BytesIO

from PIL import Image
from selenium.webdriver import PhantomJS

import psycopg2
from little_pger import LittlePGer

RENDER_DELAY = 3
THROTTLE_DELAY = 3

if __name__ == '__main__':

    driver = PhantomJS()

    for b in json.load(open('list_of_d3_blocks.json')):

        gist_id = re.search(
            'https?://api.github.com/gists/(\w+)', b['url']
        ).group(1)

        block_url = 'http://bl.ocks.org/' + gist_id
        d3_block_rec = {'gist_id': gist_id}

        try:
            print(block_url, end='.. ')
            driver.get(block_url)
            time.sleep(RENDER_DELAY)  # let it render
            fullpage_im = Image.open(BytesIO(driver.get_screenshot_as_png()))
            fimb = BytesIO()
            fullpage_im.save(fimb, 'png')
            d3_block_rec['fullpage_base64'] = base64.b64encode(fimb.getvalue())
            d3_block_rec['block_url'] = driver.current_url
        except Exception as e:
            # we got nothing
            with LittlePGer('dbname=d3_blocks', commit=True) as pg:
                d3_block_rec['error'] = str(e)
                pg.insert('d3_block', values=d3_block_rec)
            print('!!')
            continue

        try:
            f = driver.find_element_by_xpath('//iframe')
            x, y = int(f.location['x']), int(f.location['y'])
            w, h = x + int(f.size['width']), y + int(f.size['height'])
            block_im = fullpage_im.crop((x, y, w, h))
            bimb = BytesIO()
            block_im.save(bimb, 'png')
            d3_block_rec['block_base64'] = base64.b64encode(bimb.getvalue())
            d3_block_rec['block_size'] = list(block_im.size)
        except Exception as e:
            # at least we got the fullpage im, save it
            with LittlePGer('dbname=d3_blocks', commit=True) as pg:
                d3_block_rec['error'] = str(e)
                pg.insert('d3_block', values=d3_block_rec)
            print('!!')
            continue

        # all good, save everything
        with LittlePGer('dbname=d3_blocks', commit=True) as pg:
            pg.insert('d3_block', values=d3_block_rec)

        print(d3_block_rec['block_size'])

        time.sleep(THROTTLE_DELAY)

    driver.quit()
