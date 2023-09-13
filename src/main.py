import asyncio
import js
import os
import io
import base64
import uuid
from datetime import datetime

import pyodide_js
from pyodide.code import run_js
from pyodide.ffi import create_proxy, to_js, JsBuffer
from pyodide.ffi.wrappers import add_event_listener
from pyodide.http import open_url, pyfetch
from pyscript import Element, HTML
import pandas as pd


RESULT_FILE = 'result.xlsx'


class MemFSFile:

    def __init__(self, filename):
        self.filename = filename

    def as_jsarray(self):
        return pyodide_js.FS.readFile(self.filename)

    def as_url(self, filetype="application/octet-stream"):
        js_array = self.as_jsarray()
        random_filename = f'{uuid.uuid4()}.bin'
        file = js.File.new([js_array], random_filename, {type: filetype})
        url = js.URL.createObjectURL(file)
        return url

    def as_base64_str(self):
        data = open(self.filename, 'rb').read()
        base64_encoded = base64.b64encode(data).decode('UTF-8')
        return base64_encoded

    def as_base64_download_str(self):
        base64_encoded = self.as_base64_str()
        octet_string = "data:application/octet-stream;base64,"
        download_string = octet_string + base64_encoded
        return download_string


def pandas_excel_export(df, filename):
    excel_filename = f'{filename}.xlsx'

    # save to virtual filesystem
    df.to_excel(excel_filename, index=None, header=True)

    # binary xlsx to base64 encoded downloadable string
    download_string = MemFSFile(filename).as_base64_download_str()

    # create new helper DOM element, click (download) and remove
    element = js.document.createElement('a')
    element.setAttribute("href", download_string)
    element.setAttribute("download", excel_filename)
    element.click()
    element.remove()


async def write_local_file(fileHandle, content):
    file = await fileHandle.createWritable()
    await file.write(content)
    await file.close()


async def copy_file_to_user(src, dest):
    js_array = MemFSFile(src).as_jsarray()
    await write_local_file(dest, js_array)


async def save_result(event):
    try:
        options = {
            "startIn": "documents",
            "suggestedName": RESULT_FILE
        }

        user_selected_file = await js.window.showSaveFilePicker(js.Object.fromEntries(to_js(options)))
        await copy_file_to_user(RESULT_FILE, user_selected_file)

    except Exception as e:
        js.console.log('Exception: ' + str(e))
        return


def create_download_link(filename, container='#save-container'):
    url = MemFSFile(filename).as_url()

    link = js.document.createElement("a")
    link.setAttribute("download", filename)
    link.setAttribute("href", url)
    link.innerText = 'Скачать результат'
    js.document.querySelector(container).appendChild(link)


async def remoteurl_excel_load(url="/downloads/test.xlsx"):
    response = await pyfetch(url=url, method="GET")
    bytes_response = await response.bytes()
    df = pd.read_excel(io.BytesIO(bytes_response))
    return df


async def load_remote_excel(file):
    url = js.URL.createObjectURL(file)
    response = await pyfetch(url, method="GET")
    response_bytes = await response.bytes()
    df = pd.read_excel(io.BytesIO(response_bytes))
    js.URL.revokeObjectURL(url)
    return df


def load_remote_csv(file):
    url = js.URL.createObjectURL(file)
    df = pd.read_csv(open_url(url))
    js.URL.revokeObjectURL(url)
    return df


async def data_processor(*args):
    js.console.log('Processing...')

    file1, file2, *_ = args
    df1 = await load_remote_excel(file1)
    df2 = await load_remote_excel(file2)

    # - do some processing
    df = pd.concat([df1, df2])
    df.to_excel(RESULT_FILE, index=None, header=True)

    btn_save_result = Element('save_result')
    if btn_save_result.element is None:
        # add save button
        save_container = Element('save-container')
        save_container.write(HTML(r'<button type="button" id="save_result">Сохранить результат</button>'))
        add_event_listener(btn_save_result.element, "click", save_result)

        # add save link
        create_download_link(RESULT_FILE)


async def process_form_files() -> None:

    file1 = Element('file1').element.files.item(0)
    file2 = Element('file2').element.files.item(0)

    if not (file1 and file2):
        js.console.log('Form is not complete!')
        return

    await data_processor(file1, file2)


def list_files():
    for current_dir, subdirs, files in os.walk('.'):
        print(current_dir)
        for dirname in subdirs:
            print('\t' + dirname )
            
        for filename in files:
            relative_path = os.path.join(current_dir, filename)
            absolute_path = os.path.abspath(relative_path)
            print('\t' + absolute_path)


def write_to_page(*args):
    display(HTML("<b>Display function example</b><br>"), target="manual-write", append=False)


async def clock_forever():
    while True:
        now = datetime.now()
        Element('clock-output').write(f"{now.hour}:{now.minute:02}:{now.second:02}")
        await asyncio.sleep(1)

