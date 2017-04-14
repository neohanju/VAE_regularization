import os
import numpy as np
from visdom import Visdom

viz = Visdom()
target_sample_index = 0
target_frame_index = 5
mean_images = {}


def pick_frame_from_batch(batch_data, sample_index=target_sample_index, frame_index=target_frame_index):
    return batch_data[sample_index, frame_index].cpu().numpy()


def gray_single_to_image(image):
    return np.uint8(image[np.newaxis, :, :].repeat(3, axis=0))


def sample_batch_to_image(batch_data):
    single_image = ((pick_frame_from_batch(batch_data) * 0.5) + 0.5) * 255  # [-1, +1] to [0, 255]
    # un-normalize
    return gray_single_to_image(single_image)


def decentering(image, mean_image):
    return gray_single_to_image(image * 255 + mean_image)


def draw_images(win_dict, input_batch, recon_batch, setnames):
    # visualize input / reconstruction pair
    input_data = pick_frame_from_batch(input_batch)
    recon_data = pick_frame_from_batch(recon_batch)
    viz_input_frame = decentering(input_data, mean_images[setnames[target_sample_index]])
    viz_input_data = sample_batch_to_image(input_batch)
    viz_recon_data = sample_batch_to_image(recon_batch)
    # viz_recon_frame = decentering(recon_data, mean_images[setnames[target_sample_index]])
    # viz_recon_error = np.flip(np.abs(input_data - recon_data), 0)  # for reverse y-axis in heat map
    viz_recon_error = gray_single_to_image(np.abs(input_data - recon_data) * 127.5)
    if not win_dict['exist']:
        win_dict['exist'] = True
        win_dict['input_frame'] = viz.image(viz_input_frame, opts=dict(title='Input'))
        win_dict['input_data'] = viz.image(viz_input_data, opts=dict(title='Input'))
        win_dict['recon_data'] = viz.image(viz_recon_data, opts=dict(title='Reconstruction'))
        # win_dict['recon_frame'] = viz.image(viz_recon_frame, opts=dict(title='Reconstructed video frame'))
        # win_dict['recon_error'] = viz.heatmap(X=viz_recon_error,
        #                                       opts=dict(title='Reconstruction error', xmin=0, xmax=2))
        win_dict['recon_error'] = viz.image(viz_recon_error, opts=dict(title='Reconstruction error'))
    else:
        viz.image(viz_input_frame, win=win_dict['input_frame'])
        viz.image(viz_input_data, win=win_dict['input_data'])
        viz.image(viz_recon_data, win=win_dict['recon_data'])
        # viz.image(viz_recon_frame, win=win_dict['recon_frame'])
        # viz.heatmap(X=viz_recon_error, win=win_dict['recon_error'])
        viz.image(viz_recon_error, win=win_dict['recon_error'])
    return win_dict


def draw_loss_function(win, losses, iter):
    cur_loss = np.zeros([1, len(losses.values())])
    x_values = np.ones([1, len(losses.values())]) * iter
    for i , value in enumerate(losses.values()):
        cur_loss[0][i] = value

    if win is None:
        legends = []
        for key in losses.keys():
            legends.append(key)
        win = viz.line(X=x_values, Y=cur_loss,
            opts=dict(
                title='losses at each iteration',
                xlabel='iterations',
                ylabel='loss',
                xtype='linear',
                ytype='linear',
                legend=legends,
                makers=False
            )
        )
    else:
        viz.line(X=x_values, Y=cur_loss, win=win, update='append')

    return win


def get_loss_string(losses):
    str_losses = 'Total: %.4f Recon: %.4f' % (losses['total'], losses['recon'])
    if 'variational' in losses:
        str_losses += ' Var: %.4f' % (losses['variational'])
    if 'l1_reg' in losses:
        str_losses += ' L1: %.4f' % (losses['l1_reg'])
    if 'l2_reg' in losses:
        str_losses += ' L2: %.4f' % (losses['l2_reg'])
    return str_losses