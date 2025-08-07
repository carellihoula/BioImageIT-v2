
import sys
from pathlib import Path
import multiprocessing
import logging
import numpy as np
from PIL import Image
import h5py


current_file = Path(__file__)
src_path = current_file.resolve().parents[1]  
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

try:
    multiprocessing.set_start_method('spawn')
except RuntimeError:
    pass

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.FileHandler('thumbnails.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def openH5array(filename, datasetName='dataset'):
    with h5py.File(filename, 'r') as h5file:
        return h5file[datasetName][:]

def normalizeAndConvert(data):
    dmax, dmin = data.max(), data.min()
    data = 255.0 * (data - dmin) / (dmax - dmin) if abs(dmax - dmin) > 0 else data
    return Image.fromarray(data.astype(np.uint8))

def thumbnail(inputPath, outputPath, size=(128,128)): 
    try:
        if Path(inputPath).suffix == '.h5':
            data = openH5array(inputPath)
            im = normalizeAndConvert(data[data.shape[0]//2,:,:])
        else:
            im = Image.open(inputPath)
            if im.mode[0] in ['I', 'F', 'L']:
                im = normalizeAndConvert(np.asarray(im))
        im.thumbnail(size)
        im.save(outputPath)
        return (inputPath, outputPath)
    except Exception as e:
        logger.error(f"Error creating thumbnail for {inputPath}: {e}")
        return None

def generateThumbnails(taskData):
    logger.info(f'[subprocess] Starting generation of {len(taskData["images"])} thumbnails')
    
    pool = multiprocessing.Pool(8)
    results = pool.starmap(thumbnail, taskData['images'])
    pool.close()  # No more tasks can be submitted to the pool
    pool.join()   # Wait for all worker processes to finish
    
    successful_results = [r for r in results if r is not None]
    logger.info(f'[subprocess] Generated {len(successful_results)} thumbnails successfully')
    
    return dict(paths=successful_results, workflowPath=taskData['workflowPath'])
