"""Resize rendered views into the portable illustrated-report images."""
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parent
VIEWS={'进门':'entry','阳台回望':'balcony','俯视全景':'overview','左墙侧视':'left','右墙侧视':'right'}
(ROOT/'images').mkdir(exist_ok=True)
for title,key in VIEWS.items():
    im=Image.open(ROOT/'renders'/(title+'.png')).convert('RGB')
    im=im.resize((1600,round(im.height*1600/im.width)),Image.Resampling.LANCZOS)
    im.save(ROOT/'images'/(key+'.jpg'),quality=87,optimize=True,progressive=True,exif=b'')
