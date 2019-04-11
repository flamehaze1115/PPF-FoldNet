import open3d
import os
import numpy as np
from input_preparation import _ppf
from model import PPFFoldNet

datapath = "./data/test/sun3d-hotel_umd-maryland_hotel3/"
interpath = "./data/intermediate-files-real/sun3d-hotel_umd-maryland_hotel3/"
savepath = "./data/intermediate-files-real/sun3d-hotel_umd-maryland_hotel3/"


def get_pcd(filename):
    return open3d.read_point_cloud(os.path.join(datapath, filename + '.ply'))


def get_keypts_desc(filename):
    keypts = np.fromfile(os.path.join(interpath, filename + '.keypts.bin'), dtype=np.float32)
    num_keypts = int(keypts[0])
    keypts = keypts[1:].reshape([num_keypts, 3])

    return keypts


def get_desc(filename):
    desc = np.fromfile(os.path.join(interpath, filename + '.desc.3dmatch.bin'), dtype=np.float32)
    num_desc = int(desc[0])
    desc_size = int(desc[1])
    desc = desc[2:].reshape([num_desc, desc_size])
    return desc


def build_ppf_input(pcd, keypts):
    kdtree = open3d.KDTreeFlann(pcd)
    keypts_id = []
    for i in range(keypts.shape[0]):
        _, id, _ = kdtree.search_knn_vector_3d(keypts[i], 1)
        keypts_id.append(id[0])
    print(keypts.shape)
    import time
    start_time = time.time()
    neighbor = collect_local_neighbor(keypts_id, pcd, vicinity=0.3, num_points=1024)
    print(time.time() - start_time)
    local_pachtes = build_local_patch(keypts_id, pcd, neighbor)
    print(local_pachtes.shape)
    print(time.time() - start_time)
    return local_pachtes


def collect_local_neighbor(ids, pcd, vicinity=0.3, num_points=1024):
    kdtree = open3d.geometry.KDTreeFlann(pcd)
    res = []
    for id in ids:
        [k, idx, variant] = kdtree.search_radius_vector_3d(pcd.points[id], vicinity)
        # random select fix number [num_points] of points to form the local patch.
        if k > num_points:
            idx = np.random.choice(idx[1:], num_points, replace=False)
        else:
            idx = np.random.choice(idx[1:], num_points)
        res.append(idx)
    return np.array(res)


def build_local_patch(ref_inds, pcd, neighbor):
    open3d.geometry.estimate_normals(pcd)
    num_patches = len(ref_inds)
    num_points_per_patch = len(neighbor[0])
    # shape: num_ref_point, num_point_per_patch, 4
    local_patch = np.zeros([num_patches, num_points_per_patch, 4], dtype=float)
    for i, ref_ind, inds in zip(range(num_patches), ref_inds, neighbor):
        ppfs = _ppf(pcd.points[ref_ind], pcd.normals[ref_ind], np.asarray(pcd.points)[inds],
                    np.asarray(pcd.normals)[inds])
        local_patch[i] = ppfs
    return local_patch


def prepare_ppf_input():
    for i in range(36):
        filename = 'cloud_bin_' + str(i)
        pcd = get_pcd(filename)
        keypts = get_keypts_desc(filename)
        local_patches = build_ppf_input(pcd, keypts)  # [num_keypts, 1024, 4]
        np.save(savepath + filename + ".ppf.bin", local_patches.astype(np.float32))
        print("save", filename + '.ppf.bin')
        break


def generate_descriptor(model):
    for i in range(36):
        filename = 'cloud_bin' + str(i) + ".ppf.bin"
        local_patches = np.load(filename)
        desc = model(local_patches)
        np.save(filename + ".desc.ppf.bin", desc.astype(np.float32))
        break
    # after generate the desc file, can u


if __name__ == '__main__':
    model = PPFFoldNet(1024)
    prepare_ppf_input()