from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import tensorflow as tf
import numpy as np

import sys
import time

import fgan_model as fgan

sys.path.append('../')
import image_utils as iu
from datasets import MNISTDataSet as DataSet


results = {
    'output': './gen_img/',
    'model': './model/',
}

train_step = {
    'batch_size': 4096,
    'global_steps': 20001,
    'logging_interval': 1000,
}


def main():
    start_time = time.time()  # Clocking start

    # Loading MNIST DataSet
    mnist = DataSet(ds_path="D:\\DataSet/mnist/").data

    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True

    idx = 1
    divergences = ['GAN', 'KL', 'Reverse-KL', 'JS',
                   'JS-Weighted', 'Squared-Hellinger', 'Pearson', 'Neyman',
                   'Jeffrey', 'Total-Variation']
    assert (0 <= idx < len(divergences))

    results['output'] += '%s/' % divergences[idx]
    results['model'] += '%s/fGAN-model.ckpt' % divergences[idx]

    with tf.Session(config=config) as s:
        # f-GAN model
        model = fgan.FGAN(s, batch_size=train_step['batch_size'],
                          divergence_method=divergences[idx],
                          use_tricky_g_loss=True)

        # Initializing variables
        s.run(tf.global_variables_initializer())

        # Load model & Graph & Weights
        saved_global_step = 0

        ckpt = tf.train.get_checkpoint_state('./model/%s/' % divergences[idx])
        if ckpt and ckpt.model_checkpoint_path:
            # Restores from checkpoint
            model.saver.restore(s, ckpt.model_checkpoint_path)

            saved_global_step = int(ckpt.model_checkpoint_path.split('/')[-1].split('-')[-1])
            print("[+] global step : %d" % saved_global_step, " successfully loaded")
        else:
            print('[-] No checkpoint file found')

        for global_step in range(saved_global_step, train_step['global_steps']):
            batch_x, _ = mnist.train.next_batch(model.batch_size)
            batch_z = np.random.uniform(-1., 1., [model.batch_size, model.z_dim]).astype(np.float32)

            # Update D network
            _, d_loss = s.run([model.d_op, model.d_loss],
                              feed_dict={
                                  model.x: batch_x,
                                  model.z: batch_z,
                              })

            # Update G network
            _, g_loss = s.run([model.g_op, model.g_loss],
                              feed_dict={
                                  model.x: batch_x,
                                  model.z: batch_z,
                              })

            if global_step % train_step['logging_interval'] == 0:
                summary = s.run(model.merged,
                                feed_dict={
                                    model.x: batch_x,
                                    model.z: batch_z,
                                })

                # Print loss
                print("[+] Global step %06d => " % global_step,
                      " D loss : {:.8f}".format(d_loss),
                      " G loss : {:.8f}".format(g_loss))

                # Training G model with sample image and noise
                sample_z = np.random.uniform(-1., 1., [model.sample_num, model.z_dim])
                samples = s.run(model.g,
                                feed_dict={
                                    model.z: sample_z,
                                })
                samples = np.reshape(samples, (-1, 28, 28, 1))

                # Summary saver
                model.writer.add_summary(summary, global_step)

                # Export image generated by model G
                sample_image_height = model.sample_size
                sample_image_width = model.sample_size
                sample_dir = results['output'] + 'train_{0}.png'.format(global_step)

                # Generated image save
                iu.save_images(samples,
                               size=[sample_image_height, sample_image_width],
                               image_path=sample_dir,
                               inv_type='255')

                # Model save
                model.saver.save(s, results['model'], global_step)

        end_time = time.time() - start_time  # Clocking end

        # Elapsed time
        print("[+] Elapsed time {:.8f}s".format(end_time))

        # Close tf.Session
        s.close()


if __name__ == '__main__':
    main()
