import asyncio
from pyrogram import Client
import os,pickle,time
from aligo import Aligo
import config

chat_dir_map = {}
id_map = {}
ali = None
app = None
tfs_dir_file_id = None

async def progress(current, total,args):
    print(f"{current * 100 / args:.1f}%")

async def download_file(app,file_id,file_name,total):
    app.download_media(file_id,file_name=file_name, block = True,progress=progress,progress_args =(total,))

async def load_chat_dir_map():
    global chat_dir_map,ali,app
    if not os.path.exists(".tfsc"):
        with open('.tfsc', 'wb') as f:
            pickle.dump(chat_dir_map, f)
    else:
        with open('.tfsc', 'rb') as f:
            chat_dir_map = pickle.load(f)
    for chat_ADDR in config.SYNC_CHAT_ADDR_LIST:
        chat = await app.get_chat(chat_ADDR)
        chat_dir_map[chat_ADDR] = chat.title
        res = ali.get_folder_by_path(config.TFS_PAN_DIR + "/"+chat_dir_map[chat_ADDR])
        if not res:
            res = ali.create_folder(chat_dir_map[chat_ADDR],parent_file_id=tfs_dir_file_id)
            dir_id = res.file_id
        else:
            dir_id = res.file_id
        id_map[chat_ADDR] = {"dir_id":dir_id,"chat_id":chat.id}

    with open('.tfsc', 'wb') as f:
        pickle.dump(chat_dir_map, f)

def check_and_save_tfs_dir_exists():
    global tfs_dir_file_id
    if not os.path.exists(config.TMP_DOWNLOAD_PATH):
        os.mkdir(config.TMP_DOWNLOAD_PATH)
    res = ali.get_folder_by_path(config.TFS_PAN_DIR)
    if not res:
        res = ali.create_folder(config.TFS_PAN_DIR)
        tfs_dir_file_id = res.file_id
    else:
        tfs_dir_file_id = res.file_id
    print("加载同步文件夹根目录id[{}]".format(tfs_dir_file_id))

async def main():
    global chat_dir_map,ali,app
    ali = Aligo()
    check_and_save_tfs_dir_exists()
    async with Client("tg_account", config.TG_API_ID, config.TG_API_HASH,proxy=config.TG_PROXY) as tg_app:
        app = tg_app
        await load_chat_dir_map()
        while True:
            for chart_addr in chat_dir_map:
                chart_id = id_map[chart_addr]["chat_id"]
                dir_id = id_map[chart_addr]["dir_id"]
                msg_count = await app.search_messages_count(chart_id)
                if msg_count > 1:
                    print("[{}]发现[{}]个待同步文件".format(chat_dir_map[chart_addr],msg_count-1))
                    async for message in app.search_messages(chart_id,limit=500):
                        msg_id = message.id
                        if message.media:
                            file_id = eval("message.{}.file_id".format(message.media.value))
                            file_name = eval("message.{}.file_name".format(message.media.value))
                            file_size = eval("message.{}.file_size".format(message.media.value))
                            print("文件id[{}],文件名[{}],大小[{}MB]".format(file_id,file_name,int(file_size/1024/1024)))
                            d_file_path = config.TMP_DOWNLOAD_PATH + file_name
                            await app.download_media(file_id,file_name=d_file_path, block = True,progress=progress,progress_args =(file_size,))
                            ali.upload_file(d_file_path,parent_file_id=dir_id)
                            os.remove(d_file_path)
                            print("文件[{}]同步完成".format(file_name))
                        await app.delete_messages(chart_id,msg_id)
            time.sleep(60)

asyncio.run(main())