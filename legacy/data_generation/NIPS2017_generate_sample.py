import os
import sys
import subprocess as sp
from PIL import Image
import numpy as np
import glob

FFMPEG_BIN = "ffmpeg"
DATASET_BASE_PATH = os.environ['YCL_DATA_ROOT']

opticalflow_version = True

target_rows = 227
target_cols = 227
target_length = 10

# frame strides
train_frame_strides = [1]
test_frame_stride = 1

# sample strides
train_sample_stride = 2
test_sample_stride = 5

target_datasets = ['avenue_train']

datasets = dict(
    avenue_train=dict(
        path=os.path.join(DATASET_BASE_PATH, 'avenue'),
        name='avenue',
        type='train',
        name_format='%02d.avi',
        num_videos=16,
        frame_stride=train_frame_strides,
        sample_stride=train_sample_stride
    ),
    avenue_test=dict(
        path=os.path.join(DATASET_BASE_PATH, 'avenue'),
        name='avenue',
        type='test',
        name_format='%02d.avi',
        num_videos=21,
        frame_stride=test_frame_stride,
        sample_stride=test_sample_stride
    ),
    enter_train=dict(
        path=os.path.join(DATASET_BASE_PATH, 'enter'),
        name='enter',
        type='train',
        name_format='%02d.avi',
        num_videos=1,
        frame_stride=train_frame_strides,
        sample_stride=train_sample_stride
    ),
    enter_test=dict(
        path=os.path.join(DATASET_BASE_PATH, 'enter'),
        name='enter',
        type='test',
        name_format='%02d.avi',
        num_videos=6,
        frame_stride=test_frame_stride,
        sample_stride=test_sample_stride
    ),
    exit_train=dict(
        path=os.path.join(DATASET_BASE_PATH, 'exit'),
        name='exit',
        type='train',
        name_format='%02d.avi',
        num_videos=1,
        frame_stride=train_frame_strides,
        sample_stride=train_sample_stride
    ),
    exit_test=dict(
        path=os.path.join(DATASET_BASE_PATH, 'exit'),
        name='exit',
        type='test',
        name_format='%02d.avi',
        num_videos=4,
        frame_stride=test_frame_stride,
        sample_stride=test_sample_stride
    ),
    ped1_train=dict(
        path=os.path.join(DATASET_BASE_PATH, 'ped1'),
        name='ped1',
        type='train',
        name_format='%02d.avi',
        num_videos=34,
        frame_stride=train_frame_strides,
        sample_stride=train_sample_stride
    ),
    ped1_test=dict(
        path=os.path.join(DATASET_BASE_PATH, 'ped1'),
        name='ped1',
        type='test',
        name_format='%02d.avi',
        num_videos=36,
        frame_stride=test_frame_stride,
        sample_stride=test_sample_stride
    ),
    ped2_train=dict(
        path=os.path.join(DATASET_BASE_PATH, 'ped2'),
        name='ped2',
        type='train',
        name_format='%02d.avi',
        num_videos=16,
        frame_stride=train_frame_strides,
        sample_stride=train_sample_stride
    ),
    ped2_test=dict(
        path=os.path.join(DATASET_BASE_PATH, 'ped2'),
        name='ped2',
        type='test',
        name_format='%02d.avi',
        num_videos=12,
        frame_stride=test_frame_stride,
        sample_stride=test_sample_stride
    ),
)


# =============================================================================
# SET DATASET LIST
# =============================================================================
def make_dir(path):
    # if there is no directory, make a directory.
    if not os.path.exists(path):
        os.makedirs(path)
    return


def get_file_paths(path, separator , file_type):
    # return file list of the given type in the given path.
    file_paths = []
    if not os.path.exists(path):
        return file_paths
    for extension in file_type:
        file_paths += glob.glob(path + separator + extension)
    file_paths.sort()
    return file_paths



# =============================================================================
# EXTRACT FRAMES FROM VIDEOS
# =============================================================================
def extract_video_frames():
    # FFMPEG -> frame extraction & rescale & gray scale  & save to disk(png)
    print('Extract images...')
    for name in target_datasets:
        for video in range(1, datasets[name]['num_videos'] + 1):
            filename = datasets[name]['name_format'] % video
            folder_path = os.path.join(datasets[name]['path'], '%sing_videos' % datasets[name]['type'])

            # output directory
            make_dir(os.path.join(folder_path, os.path.splitext(filename)[0]))

            # run ffmpeg command
            print('\tFrom: ' + filename)
            command = [FFMPEG_BIN,
                       '-i', os.path.join(folder_path, filename),
                       '-s', str(target_rows) + 'x' + str(target_cols),  # [rows x cols]
                       '-pix_fmt', 'gray',  # to gray scale
                       os.path.join(folder_path, os.path.splitext(filename)[0], 'frame_%05d.png')]
            sp.call(command)  # call command
    print("Extraction is done")


# make mean images
def get_mean_image():
    print('Get mean image...')
    for name in target_datasets:
        if datasets[name]['type'] is not 'train':
            continue

        # mean image over all videos in the dataset
        print('\tCalculate mean image with ' + name + '...')
        mean_image = np.zeros((target_rows, target_cols), dtype=np.float)  # mean image container
        count_image = 0.0
        for video in range(1, datasets[name]['num_videos'] + 1):
            sys.stdout.write('\t\tWith %s ... ' % datasets[name]['name_format'] % video)
            image_folder = os.path.join(datasets[name]['path'], '%sing_videos' % datasets[name]['type'],
                                        os.path.splitext(datasets[name]['name_format'] % video)[0])
            image_files = get_file_paths(image_folder, '/*.', ['png', 'PNG'])
            for path in image_files:
                mean_image += np.array(Image.open(path), dtype=np.float)
                count_image += 1.0
            print('done!')

        assert count_image > 0.0
        mean_image /= count_image   # make mean image.

        # save mean image .npy and .png
        np.save(os.path.join(datasets[name]['path'], 'mean_image'), mean_image)
        Image.fromarray(np.uint8(mean_image)).save(os.path.join(datasets[name]['path'], 'mean_image.png'))

    print('Getting mean image is done')


def get_mean_image_opticalflow():
    target_length_optical = target_length - 1
    print('Get mean image of opticalflow...')
    for name in target_datasets:
        if datasets[name]['type'] is not 'train':
            continue

        # mean image over all videos in the dataset
        print('\tCalculate mean image with ' + name + '...')
        mean_vx = np.zeros((target_rows, target_cols), dtype=np.float)  # mean image container
        mean_vy = np.zeros((target_rows, target_cols), dtype=np.float)  # mean image container
        count_image = 0.0
        for video in range(1, datasets[name]['num_videos'] + 1):
            sys.stdout.write('\t\tWith %s ... ' % datasets[name]['name_format'] % video)
            image_folder = os.path.join(DATASET_BASE_PATH, datasets[name]['name'], 'optical_flow',
                                        datasets[name]['type']+'ing_videos',
                                        os.path.splitext(datasets[name]['name_format'] % video)[0])

            vx_image_files = get_file_paths(image_folder, '/*vx.', ['png', 'PNG'])
            vy_image_files = get_file_paths(image_folder, '/*vy.', ['png', 'PNG'])
            for path in vx_image_files:
                mean_vx += np.array(Image.open(path), dtype=np.float)
                count_image += 1.0
            for path in vy_image_files:
                mean_vy += np.array(Image.open(path), dtype=np.float)
            print('done!')

        assert count_image > 0.0
        mean_vx /= count_image  # make mean image.
        mean_vy /= count_image  # make mean image.
        # save mean image .npy and .png

        Image.fromarray(np.uint8(mean_vx)).save(os.path.join(DATASET_BASE_PATH, datasets[name]['name'], 'optical_flow',
                                                             'mean_vx.png'))

        Image.fromarray(np.uint8(mean_vy)).save(os.path.join(DATASET_BASE_PATH, datasets[name]['name'], 'optical_flow',
                                                             'mean_vy.png'))

        mean_cube = np.zeros((target_length_optical*2, target_rows, target_cols), dtype=np.float)
        for frm in range(0, target_length_optical-1):
            mean_cube[frm] = mean_vx
            mean_cube[frm+9] = mean_vy

        np.save(os.path.join(DATASET_BASE_PATH, datasets[name]['name'], 'optical_flow', 'mean_cube'), mean_cube)

    print('Getting mean image is done')


# =============================================================================
# GENERATE SAMPLES
# =============================================================================
def generate_samples(centering=False):

    if centering:
        numpy_dtype = np.float32
    else:
        numpy_dtype = np.uint8

    # sample data container
    sample_data = np.zeros((target_length, target_rows, target_cols), dtype=numpy_dtype)

    for i, name in enumerate(target_datasets):

        print('Generate samples with "%s" dataset ... [%d/%d]' % (name, i+1, len(target_datasets)))

        sample_stride = datasets[name]['sample_stride']

        # output folder
        make_dir(os.path.join(datasets[name]['path'], datasets[name]['type']))

        # load mean image
        mean_image = np.load(os.path.join(datasets[name]['path'], 'mean_image.npy'))

        # loop to generate samples
        total_sample_count = 0

        frame_strides = [datasets[name]['frame_stride']] \
            if isinstance(datasets[name]['frame_stride'], int) else datasets[name]['frame_stride']

        for frame_stride in frame_strides:
            stride_sample_count = 0
            for video in range(1, datasets[name]['num_videos'] + 1):

                # print('  with frame stride %d and sample stride %d' % (frame_stride, sample_stride))
                # get paths of target images
                image_folder = os.path.join(datasets[name]['path'], '%sing_videos' % datasets[name]['type'],
                                            os.path.splitext(datasets[name]['name_format'] % video)[0])
                image_paths = get_file_paths(image_folder, ['png', 'PNG'])
                target_image_paths = image_paths[0::frame_stride]
                num_frames = len(target_image_paths)

                # read target images and preprocess them
                sys.stdout.write('\t"%s" with frame stride %d and sample stride %d ... [0/%d]'
                                 % (datasets[name]['name_format'] % video, frame_stride, sample_stride, num_frames))
                read_pos = 0
                sample_count_wrt_video = 0
                for start_pos in range(0, num_frames, sample_stride):
                    sys.stdout.write('\r\tAt "%s" with frame stride %d and sample stride %d ... [%d/%d]'
                                     % (datasets[name]['name_format'] % video, frame_stride, sample_stride, start_pos,
                                        num_frames))

                    # check end-of-processing
                    if start_pos + target_length > num_frames:
                        break

                    # reallocate already read images
                    sample_data = np.roll(sample_data, sample_stride, axis=0)

                    # read and preprocess only unread images
                    reading_images = target_image_paths[read_pos:start_pos+target_length]
                    for j, path in enumerate(reading_images):
                        image_data = np.array(Image.open(path), dtype=numpy_dtype)

                        # preprocessing
                        if centering:
                            image_data -= mean_image
                            image_data /= 255.0

                        # insert to sample container
                        sample_data[read_pos-start_pos+j] = image_data

                    # different file name format and index among set type
                    file_name_format = '%s_video_%02d' % (datasets[name]['name'], video) \
                                       + '_frame_interval_%d_stride_%d_%06d'
                    file_name_index = sample_count_wrt_video
                    save_file_path = os.path.join(datasets[name]['path'], datasets[name]['type'],
                                                  file_name_format % (frame_stride, sample_stride, file_name_index))
                    np.save(save_file_path, sample_data)

                    stride_sample_count += 1
                    sample_count_wrt_video += 1
                    read_pos = start_pos + target_length
                print('\r\tAt "%s" with frame stride %d and sample stride %d is done!          '
                      % (datasets[name]['name_format'] % video, frame_stride, sample_stride))

            total_sample_count += stride_sample_count

        print('%d samples are generated.' % total_sample_count)

def generate_samples_opticalflow(centering=False):
    target_length_optical = target_length - 1
    if centering:
        numpy_dtype = np.float32
    else:
        numpy_dtype = np.uint8

    # sample data container
    sample_data_x = np.zeros((target_length_optical, target_rows, target_cols), dtype=numpy_dtype)
    sample_data_y = np.zeros((target_length_optical, target_rows, target_cols), dtype=numpy_dtype)
    sample_data = np.zeros((target_length_optical*2, target_rows, target_cols), dtype=numpy_dtype)

    for i, name in enumerate(target_datasets):

        print('Generate samples with "%s" dataset ... [%d/%d]' % (name, i + 1, len(target_datasets)))

        sample_stride = datasets[name]['sample_stride']

        # output folder
        make_dir(os.path.join(DATASET_BASE_PATH, datasets[name]['name'], 'optical_flow', datasets[name]['type']))

        # load mean image
        mean_vx = np.load(os.path.join(DATASET_BASE_PATH, datasets[name]['name'], 'optical_flow', 'mean_vx.npy'))
        mean_vy = np.load(os.path.join(DATASET_BASE_PATH, datasets[name]['name'], 'optical_flow', 'mean_vy.npy'))

        # loop to generate samples
        total_sample_count = 0

        frame_strides = [datasets[name]['frame_stride']] \
            if isinstance(datasets[name]['frame_stride'], int) else datasets[name]['frame_stride']

        for frame_stride in frame_strides:
            stride_sample_count = 0
            for video in range(1, datasets[name]['num_videos'] + 1):

                # print('  with frame stride %d and sample stride %d' % (frame_stride, sample_stride))
                # get paths of target images
                image_folder = os.path.join(DATASET_BASE_PATH,  datasets[name]['name'],'optical_flow',
                                            '%sing_videos' % datasets[name]['type'],
                                            os.path.splitext(datasets[name]['name_format'] % video)[0])

                vx_image_paths = get_file_paths(image_folder, '/*vx.', ['png', 'PNG'])
                vy_image_paths = get_file_paths(image_folder, '/*vy.', ['png', 'PNG'])

                vx_target_image_paths = vx_image_paths[0::frame_stride]
                vy_target_image_paths = vy_image_paths[0::frame_stride]

                num_frames = len(vx_target_image_paths)

                # read target images and preprocess them
                sys.stdout.write('\t"%s" with frame stride %d and sample stride %d ... [0/%d]'
                                 % (datasets[name]['name_format'] % video, frame_stride, sample_stride, num_frames))
                read_pos = 0
                sample_count_wrt_video = 0

                for start_pos in range(0, num_frames, sample_stride):
                    sys.stdout.write('\r\tAt "%s" with frame stride %d and sample stride %d ... [%d/%d]'
                                     % (datasets[name]['name_format'] % video, frame_stride, sample_stride, start_pos, num_frames))

                    # check end-of-processing
                    if start_pos + target_length_optical > num_frames:
                        break

                    # reallocate already read images
                    sample_data_x = np.roll(sample_data_x, sample_stride, axis=0)
                    sample_data_y = np.roll(sample_data_y, sample_stride, axis=0)

                    # read and preprocess only unread images
                    vx_reading_images = vx_target_image_paths[read_pos:start_pos + target_length_optical]
                    vy_reading_images = vy_target_image_paths[read_pos:start_pos + target_length_optical]

                    for j, path in enumerate(vx_reading_images):
                        image_data = np.array(Image.open(path), dtype=numpy_dtype)

                        # preprocessing
                        if centering:
                            image_data -= mean_vx
                            image_data /= 255.0

                        # insert to sample container
                        sample_data_x[read_pos - start_pos + j] = image_data

                    for j, path in enumerate(vy_reading_images):
                        image_data = np.array(Image.open(path), dtype=numpy_dtype)

                        # preprocessing
                        if centering:
                            image_data -= mean_vy
                            image_data /= 255.0

                        # insert to sample container
                        sample_data_y[read_pos - start_pos + j] = image_data

                    # different file name format and index among set type
                    file_name_format = '%s_video_%02d' % (datasets[name]['name'], video) \
                                          + '_frame_interval_%d_stride_%d_%06d'

                    file_name_index = sample_count_wrt_video

                    save_file_path = os.path.join(DATASET_BASE_PATH, datasets[name]['name'], 'optical_flow', datasets[name]['type'],
                                                  file_name_format % (frame_stride, sample_stride, file_name_index))

                    sample_data[0:target_length_optical] = sample_data_x
                    sample_data[target_length_optical:2*target_length_optical] = sample_data_y

                    np.save(save_file_path, sample_data)

                    stride_sample_count += 1
                    sample_count_wrt_video += 1
                    read_pos = start_pos + target_length_optical

                print('\r\tAt "%s" with frame stride %d and sample stride %d is done!          '
                      % (datasets[name]['name_format'] % video, frame_stride, sample_stride))

            total_sample_count += stride_sample_count

        print('%d samples are generated.' % total_sample_count)
# todo - 저장한 파일의 명세서 저장할 것. 크기, 프레임 등
# =============================================================================
# MAIN PROCEDURE
# =============================================================================
if(opticalflow_version):
    get_mean_image_opticalflow()
    generate_samples_opticalflow()
else:
    extract_video_frames()
    get_mean_image()
    generate_samples()



# ()()
# ('')HAANJU.YOO

