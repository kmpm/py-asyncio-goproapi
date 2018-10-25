from goprocam import GoProCamera
import asyncio

gpCam = GoProCamera.GoPro()
TIMER = 4


async def run():
    photo = await gpCam.take_photo(TIMER)
    print('photo taken', photo)
    await gpCam.downloadLastMedia(photo)  # take a photo in 4 seconds and download it.
    print('Done')
    await gpCam.quit()


asyncio.get_event_loop().run_until_complete(run())
