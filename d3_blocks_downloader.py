from __future__ import print_function
import argparse
import base64
from io import BytesIO
import json
import re
import subprocess32 as subprocess
import sys
import time
from PIL import Image
from selenium.webdriver import PhantomJS
from little_pger import LittlePGer


DB_NAME = 'd3_blocks'
THROTTLE_DELAY = 3  # all in seconds
RENDER_DELAY = 3
RENDER_TIMEOUT = 15


def render(gist_id, commit):
    block_url = 'http://bl.ocks.org/' + gist_id
    d3_block_rec = {'gist_id': gist_id}
    try:
        driver = PhantomJS()
        driver.get(block_url)
        time.sleep(RENDER_DELAY)  # let it render
        fullpage_im = Image.open(BytesIO(driver.get_screenshot_as_png()))
        fimb = BytesIO()
        fullpage_im.save(fimb, 'png')
        d3_block_rec['fullpage_base64'] = base64.b64encode(fimb.getvalue())
        d3_block_rec['block_url'] = driver.current_url
    except Exception as e:
        # we got nothing
        with LittlePGer('dbname=' + DB_NAME, commit=commit) as pg:
            d3_block_rec['error'] = str(e)
            pg.insert('d3_block', values=d3_block_rec)
        exit(10)

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
        with LittlePGer('dbname=' + DB_NAME, commit=commit) as pg:
            d3_block_rec['error'] = str(e)
            pg.insert('d3_block', values=d3_block_rec)
        exit(11)

    # all good, save everything
    with LittlePGer('dbname=' + DB_NAME, commit=commit) as pg:
        pg.insert('d3_block', values=d3_block_rec)


if __name__ == '__main__':

    parser = argparse.ArgumentParser('d3 blocks downloader')
    parser.add_argument('--gist-id')
    parser.add_argument('--commit', action='store_true')
    args = parser.parse_args()

    #######################################################################

    if args.gist_id:
        render(args.gist_id, args.commit)
        exit(0)

    #######################################################################

    with LittlePGer('dbname=' + DB_NAME) as pg:
        excluded = {
            rec['gist_id'] for rec in pg.select('d3_block', what='gist_id')
        }

    bs = json.load(open('list_of_d3_blocks.json'))
    n_todo = len(bs) - len(excluded)
    n_done = 0

    for b in bs:

        gist_id = re.search(
            'https?://api.github.com/gists/(\w+)', b['url']
        ).group(1)

        if gist_id in excluded:
            continue

        time.sleep(THROTTLE_DELAY)
        n_done += 1

        block_url = 'http://bl.ocks.org/' + gist_id
        d3_block_rec = {'gist_id': gist_id}

        print('%d/%d %s..' % (n_done, n_todo, block_url), end=' ')

        cmd = 'python d3_blocks_downloader.py --gist-id {} {}'
        cmd = cmd.format(gist_id, '--commit' if args.commit else '')
        try:
            retcode = subprocess.call(cmd.split(), timeout=RENDER_TIMEOUT)
        except subprocess.TimeoutExpired as e:
            retcode = 12
            with LittlePGer('dbname=' + DB_NAME, commit=True) as pg:
                pg.insert(
                    'd3_block',
                    values={'gist_id': gist_id, 'error': 'timeout'}
                )

        print({10: '!', 11: '!!', 12: '!!!', 0: 'ok'}[retcode])

        subprocess.call('killall phantomjs 2> /dev/null', shell=True)
