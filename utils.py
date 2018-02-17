import numpy as np
import cv2
from matplotlib import pyplot as plt
import glob
import os
from itertools import groupby
import sys
from collections import OrderedDict

# Read images/masks from a directory

def getImageListFromDir(img_dir, filetype='png'):
    """
    :param img_dir: imgs root dir, string
    :param filetype: "png", "jpg" or "bmp", string
    :return: list of images, list
    """
    img_dir = img_dir + '*.'+filetype
    print img_dir
    l = sorted(glob.glob(img_dir))
    return l

# read images with img generator

def img_generator(img_list):
    """
    :param img_list: list of iamges, list of string
    :return: yield a pair of sequences images
    """
    while len(img_list)> 0:
        f1 = img_list.pop(0)
        print("read img: ", f1.split('/')[-1])
        img = cv2.imread(f1)
        yield img

# generator descriptors
def generator_descriptor(fileaddr, save_addr, desp_type='orb'):
    """
    :param fileaddr: string, images dir
    :param save_addr: string, where to save
    :param desp_type: 'orb'
    :return: None
    """

    # create save directory
    if not os.path.isdir(save_addr):
        os.makedirs(save_addr)
        print 'create ' + save_addr
    if fileaddr[-1] != '/':
        fileaddr += '/'
    fileList = os.listdir(fileaddr)
    for filename in fileList:
        if '.png' in filename:
            print filename
            filename_des = filename.split('.')[0]
            img = cv2.imread(fileaddr+filename, 0)
            # Initiate STAR detector

            orb = []
            kp = []

            #todo: add new detectors here !

            if desp_type == 'orb':
                if cv2.__version__[0] == '3':
                    orb = cv2.ORB_create()
                else:
                    orb = cv2.ORB()

                # find the keypoints with ORB
                kp = orb.detect(img, None)

                # compute the descriptors with ORB
                kp, des = orb.compute(img, kp)

            # creat file to store descriptor
            np.save(save_addr+'/'+filename_des+'_'+desp_type, des)
            #np.save(save_addr+'/'+filename_des+'_kp', kp)


# generator hists (global descriptors) from data (local descriptors or image)
def generateHist(model, data, data_type, decpt_tpye):
    """
    :param model: k-means model trained by descriptors in database.
    :param data: numpy array grayscale image for getting histo or local descriptors for an images
    :param data_type : string, "dscpt" or "image"
    :param decpt_tpye : string , type of descriptor, e.g. "orb"
    :return: an histogramme for the given data
    """

    if data_type == "dscpt":
        # from k-means prediction to histogram (global descriptor) (#bins = #classes)
        res = np.zeros((1, model.get_params()['n_clusters']), dtype=np.float32)
        if data is None : # if orb cannot get any keypoints
            return res

        label = model.predict(data)
        for value in label:
            res[0,value] += 1.0

        return res / np.sum(res)  # normalized histogram

    elif data_type == "image":

        # todo: add new detectors here !

        if decpt_tpye == "orb":
            if cv2.__version__[0] == '3':
                orb = cv2.ORB_create()
            else:
                orb = cv2.ORB()

            # find the keypoints with ORB
            kp = orb.detect(data, None)

            # compute the descriptors with ORB
            kp, des = orb.compute(data, kp)
            # from k-means prediction to histogram (#bins = #classes)
            res = np.zeros((1, model.get_params()['n_clusters']), dtype=np.float32)
            if des is None:  # if orb cannot get any keypoints
                return res

            label = model.predict(des)
            for value in label:
                res[0, value] += 1.0

            return res/np.sum(res) # normalized histogram
    else:
        print ("data type error")
        return 0


# search similar images of a given target (gs image) in terms of distance of hists.

def searchFromBase(base_dir, target, model, has_hist):
    """
    :param base_dir: search base of images
    :param target: target image numpy grayscale image
    :param model : kmeans pretrained model
    :param has_hist : bool, if true base_dir is the addr for the hists, else it is the addr for images
    :return: a list of ranking of top 10 similars images, [ (index, distance value)] and a list of image dir
    """
    if has_hist:
        imgs_addr = getImageListFromDir(base_dir, 'npy')
    else :
        imgs_addr = getImageListFromDir(base_dir)
    dist = {}
    target_hist = generateHist(model, target, 'image', 'orb').astype(np.float32)
    print np.sum(target_hist)
    # calculate distance between target hist and base hists
    for idx, img_addr in enumerate(imgs_addr):
        img_gs = []
        hist = []
        if has_hist == False:
            print img_addr
            img_gs = cv2.imread(img_addr,'0')
            hist = generateHist(model, img_gs, 'image', 'orb')
        else:
            hist = np.load(img_addr)
        dist[idx] = np.linalg.norm(hist-target_hist)  # eucudian distance

    # get the top 10 ranking
    sorted_d = OrderedDict(sorted(dist.items(), key=lambda x: x[1]))
    dictlist = []
    for key, value in sorted_d.items():
        temp = [key, value] # [index, distance]
        dictlist.append(temp)
    return dictlist[0:10], imgs_addr
