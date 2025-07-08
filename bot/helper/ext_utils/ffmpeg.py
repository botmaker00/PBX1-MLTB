import os
import re
import logging
from re import sub as re_sub
from aioshutil import move
from asyncio import create_subprocess_exec
from asyncio.subprocess import PIPE
from bot import LOGGER, bot_cache
from bot.helper.ext_utils.fs_utils import clean_target
import os.path as ospath

LOGGER = logging.getLogger(__name__)

########-------- Attachment by PBX1 -------------#########
async def edit_attachment(listener, base_dir: str, media_file: str, outfile: str, attachment: str = ''):
    from aiohttp import ClientSession
    from aiofiles import open as async_open

    LOGGER.info("🔗 [PBX1] Attachment Processing Started")
    
    try:
        # Download attachment file from URL
        async with ClientSession() as session:
            async with session.get(attachment) as resp:
                if resp.status == 200:
                    attach_path = ospath.join(base_dir, 'attach_' + ospath.basename(attachment))
                    async with async_open(attach_path, 'wb') as f:
                        await f.write(await resp.read())
                    LOGGER.info(f"📥 [PBX1] Attachment downloaded to {attach_path}")
                else:
                    LOGGER.error(f"❌ [PBX1] Attachment URL not reachable: {attachment}")
                    return
    except Exception as e:
        LOGGER.error(f"❌ [PBX1] Error downloading attachment: {e}")
        return

    # Detect MIME and extension
    pbx1 = "photo"
    attachment_ext = attach_path.split('.')[-1].lower()
    mime_type = "application/octet-stream"
    if attachment_ext in ["jpg", "jpeg"]:
        mime_type = "image/jpeg"
    elif attachment_ext == "png":
        mime_type = "image/png"

    # Build FFmpeg command
    cmd = [
        bot_cache['pkgs'][2], '-hide_banner', '-loglevel', 'error', '-progress', 'pipe:1',
        '-i', media_file,
        '-attach', attach_path,
        '-metadata:s:t', f'mimetype={mime_type}',
        '-metadata:s:t', f'filename={pbx1}.{attachment_ext}',
        '-disposition:t', 'default',
        '-c', 'copy',
        '-map', '0',
        '-map', '0:t?',
        outfile
    ]

    LOGGER.info(f"🛠️ [PBX1] FFmpeg command: {' '.join(cmd)}")

    # Run FFmpeg
    listener.suproc = await create_subprocess_exec(*cmd, stderr=PIPE)
    code = await listener.suproc.wait()

    if code == 0:
        await clean_target(media_file)
        listener.seed = False
        await move(outfile, base_dir)
        LOGGER.info("✅ [PBX1] Attachment added and file saved.")
    else:
        error = (await listener.suproc.stderr.read()).decode()
        LOGGER.error(f"❌ [PBX1] FFmpeg Error: {error}")
        await clean_target(outfile)
