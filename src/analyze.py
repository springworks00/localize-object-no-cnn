import cv2
import numpy as np
import util
from util import Frame
from typing import Iterable
from typing import List
import matplotlib.pyplot as plt

from sklearn.cluster import KMeans
from sklearn.metrics import pairwise_distances_argmin_min

def orb_features(fs: List[Frame], n=500) -> List[Frame]:
    orb = cv2.ORB_create(nfeatures=n)
    fs_len = len(fs)
    results = []
    i = 1
    for f in fs:
        kps, dcs = orb.detectAndCompute(f.raw, None)
        results.append(Frame(raw=f.raw, kps=kps, dcs=dcs))
        util.status(f"analyzing orb features: {100*(i*n)//(fs_len*n)}%")
        i += 1
    print()
    return results

def __match(query: Frame, train: Frame, threshold):
    matches = cv2.BFMatcher().knnMatch(query.dcs, train.dcs, k=2)

    return [m for m,n in matches if m.distance < threshold*n.distance]

def most_similar(query: Frame, trains: Iterable[Frame], confidence_floor, threshold) -> Frame:
    nfeats=len(query.dcs)

    best_score = -1
    best = None
    for t in trains:
        this_score = len(__match(query, t, threshold=threshold))
        if this_score < nfeats*confidence_floor:
            # not enough matches to assert the object is even present
            continue
        if this_score > best_score:
            best_score = this_score
            best = t
    #print(best_score, f"(required = {nfeats*confidence_floor})")
    return best

def __acc_match(query: np.ndarray, train: np.ndarray):
    matches = cv2.BFMatcher().knnMatch(query, train, k=2)

    good, bad = [], []
    for m,n in matches:
        if m.distance < 0.75*n.distance:
            good.append(n.trainIdx)
        else:
            bad.append(m.queryIdx)
    
    for x in query[bad]:
        train = np.vstack((train, x))

    return good, train

def cluster(frames: List[Frame], k) -> List[Frame]:
    dcss = list(map(lambda x: x.dcs, frames))

    xs, ys = [], []
    train = np.array(dcss[0])

    len_dcss = len(dcss)
    for frameIdx, dcs in enumerate(dcss):
        this_ys, train = __acc_match(dcs, train)
        this_xs = [frameIdx]*len(this_ys)
        
        ys += this_ys
        xs += this_xs
        util.status(f"building cluster set: {100*(frameIdx+1)//len_dcss}%")
    print()
    util.status(f"clustering to {k} frames: ") 
    points = np.array(list(zip(xs, ys)))
    kmeans = KMeans(n_clusters=k, random_state=1)
    kmeans.fit(points)
    best_indexes = pairwise_distances_argmin_min(kmeans.cluster_centers_, points)[0]
    print("100%")
    return list(map(lambda i: frames[i], points[best_indexes, 0]))
