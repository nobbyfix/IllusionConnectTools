from PIL import Image, ImageOps
from pathlib import Path
import os

CCZ_HEAD = bytes([0x43, 0x43, 0x5A, 0x21])

def apply_alpha(srcimg: Path):
	# ensure the image isn't a pvr.ccz file
	with open(srcimg, 'rb') as f:
		if f.read(4) == CCZ_HEAD: return

	# default paths and check if a corresponding alpha PVR file exists
	alpha_path = srcimg.with_stem(srcimg.stem + "_alpha")
	pvr_alphasrc_path = srcimg.with_suffix(srcimg.suffix+"@alpha")
	if not pvr_alphasrc_path.exists(): return

	# rename PVR file so TexturePacker recognizes it
	pvr_alpha_path = pvr_alphasrc_path.with_suffix(".pvr.ccz")
	pvr_alphasrc_path.rename(pvr_alpha_path)
	
	# extract alpha png from PVR
	command = f'TexturePacker "{pvr_alpha_path}" --sheet "{alpha_path}" --algorithm Basic --allow-free-size --trim-mode None'
	os.system(command)

	# load images and apply alpha channel to source image
	img = Image.open(srcimg)
	imgalpha = Image.open(alpha_path)
	img.putalpha(imgalpha.getchannel('A'))
	img.save(srcimg.with_suffix('.png'))

	# remove the leftover files
	pvr_alpha_path.unlink()
	alpha_path.unlink()

def recursive_apply_dir(src_dir: Path):
	for img in src_dir.rglob('*.png'):
		apply_alpha(img)
	for img in src_dir.rglob('*.jpg'):
		apply_alpha(img)

if __name__ == "__main__":
	ASSET_DIRECTORY = Path('Assets', 'asset')
	recursive_apply_dir(ASSET_DIRECTORY)