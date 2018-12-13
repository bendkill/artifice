"""Provides semantic segmentation capability for artifice. The specific
algorithm isn't important, as long as it returns an output in familiar form.

We implement the U-Net segmentation architecture
(http://arxiv.org/abs/1505.04597), loosely inspired by implementation at:
https://github.com/tks10/segmentation_unet/

"""

import os
from shutil import rmtree
import numpy as np
import logging

import tensorflow as tf
from artifice.utils import dataset

logging.basicConfig(level=logging.INFO, format='%(levelnam)s:%(asctime)s:%(message)s')


"""A model implementing semantic segmentation.
args:
* channels: number of channels in the image (grayscale by default)
* num_classes: number of classes of objects to be detected (including background)

In this context, `image` is the input to the model, and `annotation`, is the
SEMANTIC annotation (groung truth) of `image`, a [image_shape[0],
image_shape[1], num_classes] shape array which one-hot encoedes each pixel's
class. `prediction` is the network's prediction for that annotation.

`annotation` is always an array with 3 dimensions.

"""

class SemanticModel:
  num_shuffle = 10000
  num_steps = 10
  def __init__(self, image_shape, num_classes, model_dir=None):
    self.image_shape = list(image_shape)
    assert(len(self.image_shape) == 3)
    self.num_classes = num_classes

    feature_columns = [tf.feature_column.numeric_column(
      'image', shape=self.image_shape, dtype=tf.uint8)]
    
    self.params = {'feature_columns' : feature_columns}

    self.model_dir = model_dir

  @staticmethod
  def create(image_shape, num_classes, l2_reg_scale=None):
    raise NotImplementedError("SemanticModel subclass should implement model_fn.")

  def train(self, train_data, batch_size=16, test_data=None, overwrite=True):
    """Train the model with tf Dataset object train_data. If test_data is not None,
    evaluate the model with it, and log the results (at INFO level).

    """
    if overwrite and os.path.exists(self.model_dir):
      rmtree(self.model_dir)

    sess = tf.InteractiveSession() # TODO: not this, lazy piece of shit

    self.estimator = tf.estimator.Estimator(model_fn=self.create(training=True),
                                            model_dir=self.model_dir,
                                            params=self.params)
    
    input_train = lambda : (
      train_data.shuffle(self.num_shuffle)
      .batch(batch_size)
      .repeat()
      .make_one_shot_iterator()
      .get_next())
    
    self.estimator.train(input_fn=input_train, steps=self.num_steps)
    
    if test_data is not None:
      logging.info(estimator.evaluate(input_fn=input_test))

  def predict(self, test_data):
    """Return the estimator's predictions on test_data.

    """
    if self.model_dir is None:
      logging.warning("prediction FAILED (no model_dir)")
      return None

    input_pred = lambda : (
      test_data.batch(batch_size)
      .make_one_shot_iterator()
      .get_next())
  
    self.estimator = tf.estimator.Estimator(model_fn=self.create(training=False),
                                            model_dir=self.model_dir,
                                            params=self.params)

    predictions = estimator.predict(input_fn=input_pred)
    return predictions


"""Implementation of UNet."""
class UNet(SemanticModel):
  @staticmethod
  def create(training=True, l2_reg_scale=None):
    """Create the unet model function for a custom estimator.

    args:
    :image_shape: shape of input image. Includes channels.
    :num_classes: number of object classes, including background.

    returns:
    :image: the input tensor
    :prediction: the output tensor of the model
    :annotation: the ground truth tensor
    :training: placeholder tensor for training boolean

    """
    
    logging.info("Creating unet graph...")

    def model_fn(features, labels, mode, params):
      
      image = tf.reshape(tf.feature_column.input_layer(
        features, params['feature_columns']), [-1] + self.image_shape)
    
      # The UNet architecture has two stages, up and down. We denote layers in the
      # down-stage with "dn" and those in the up stage with "up," even though the
      # up_conv layers are just performing regular, dimension-preserving
      # convolution. "up_deconv" layers are doing the convolution transpose or
      # "upconv-ing."

      # block level 1
      dn_conv1_1 = UNet.conv(image, filters=64, l2_reg_scale=l2_reg_scale,
                             training=training)
      dn_conv1_2 = UNet.conv(dn_conv1_1, filters=64, l2_reg_scale=l2_reg_scale,
                             training=training)
      dn_pool1 = UNet.pool(dn_conv1_2)

      # block level 2
      dn_conv2_1 = UNet.conv(dn_pool1, filters=128, l2_reg_scale=l2_reg_scale,
                             training=training)
      dn_conv2_2 = UNet.conv(dn_conv2_1, filters=128, l2_reg_scale=l2_reg_scale,
                             training=training)
      dn_pool2 = UNet.pool(dn_conv2_2)

      # block level 3
      dn_conv3_1 = UNet.conv(dn_pool2, filters=256, l2_reg_scale=l2_reg_scale,
                             training=training)
      dn_conv3_2 = UNet.conv(dn_conv3_1, filters=256, l2_reg_scale=l2_reg_scale,
                             training=training)
      dn_pool3 = UNet.pool(dn_conv3_2)

      # block level 4
      dn_conv4_1 = UNet.conv(dn_pool3, filters=512, l2_reg_scale=l2_reg_scale,
                             training=training)
      dn_conv4_2 = UNet.conv(dn_conv4_1, filters=512, l2_reg_scale=l2_reg_scale,
                             training=training)
      dn_pool4 = UNet.pool(dn_conv4_2)

      # block level 5 (bottom). No max pool; instead deconv and concat.
      dn_conv5_1 = UNet.conv(dn_pool4, filters=1024, l2_reg_scale=l2_reg_scale,
                             training=training)
      dn_conv5_2 = UNet.conv(dn_conv5_1, filters=1024, l2_reg_scale=l2_reg_scale,
                             training=training)
      up_deconv5 = UNet.deconv(dn_conv5_2, filters=512, l2_reg_scale=l2_reg_scale)
      up_concat5 = tf.concat([dn_conv4_2, up_deconv5], axis=3)

      # block level 4 (going up)
      up_conv4_1 = UNet.conv(up_concat5, filters=512, l2_reg_scale=l2_reg_scale)
      up_conv4_2 = UNet.conv(up_conv4_1, filters=512, l2_reg_scale=l2_reg_scale)
      up_deconv4 = UNet.deconv(up_conv4_2, filters=256, l2_reg_scale=l2_reg_scale)
      up_concat4 = tf.concat([dn_conv3_2, up_deconv4], axis=3)

      # block level 3
      up_conv3_1 = UNet.conv(up_concat4, filters=256, l2_reg_scale=l2_reg_scale)
      up_conv4_2 = UNet.conv(up_conv3_1, filters=256, l2_reg_scale=l2_reg_scale)
      up_deconv3 = UNet.deconv(up_conv3_2, filters=128, l2_reg_scale=l2_reg_scale)
      up_concat3 = tf.concat([dn_conv2_2, up_deconv3], axis=3)

      up_conv2_1 = UNet.conv(up_concat3, filters=128, l2_reg_scale=l2_reg_scale)
      up_conv2_2 = UNet.conv(up_conv2_1, filters=128, l2_reg_scale=l2_reg_scale)
      up_deconv2 = UNet.deconv(up_conv2_2, filters=64, l2_reg_scale=l2_reg_scale)
      up_concat2 = tf.concat([dn_conv1_2, up_deconv2], axis=3)

      up_conv1_1 = UNet.conv(up_concat2, filters=64, l2_reg_scale=l2_reg_scale)
      up_conv1_2 = UNet.conv(up_conv1_1, filters=64, l2_reg_scale=l2_reg_scale)
      annotation_logits = UNet.conv(up_conv1_2, filters=num_classes,
                                    kernel_size=[1, 1], activation=None)

      predictions = tf.argmax(annotation_logits, 3)

      # In PREDICT mode, return the output asap.
      if mode == tf.estimator.ModeKeys.PREDICT:
        return tf.estimator.EstimatorSpec(
          mode=mode, predictions={'annotation' : predictions})

      # Calculate loss:
      # TODO: one-hot encode the labels???
      cross_entropy = tf.nn.softmax_cross_entropy_with_logits_v2(
        labels=labels, logits=annotation_logits)

      # Return an optimizer, if mode is TRAIN
      if mode == tf.estimator.ModeKeys.TRAIN:
        optimizer = tf.train.AdamOptimizer(0.001)
        train_op = optimizer.minimize(loss=cross_entropy,
                                      global_step=tf.train.get_global_step())
        return tf.estimator.EstimatorSpec(mode=mode, 
                                          loss=cross_entropy, 
                                          train_op=train_op)
    
      assert mode == tf.estimator.ModeKeys.EVAL
      accuracy = tf.metrics.accuracy(labels=labels,
                                     predictions=predictions)
      return tf.estimator.EstimatorSpec(mode=mode,
                                        loss=cross_entropy)


    return model_fn
    
  @staticmethod
  def conv(inputs, filters=64, kernel_size=[3,3], activation=tf.nn.relu,
           l2_reg_scale=None, training=True):
    """Apply a single convolutional layer with the given activation function applied
    afterword. If l2_reg_scale is not None, specifies the Lambda factor for
    weight normalization in the kernels. If training is not None, indicates that
    batch_normalization should occur, based on whether training is happening.
    """

    if l2_reg_scale is None:
      regularizer = None
    else:
      regularizer = tf.contrib.layers.l2_regularizer(scale=l2_reg_scale)

    output = tf.layers.conv2d(
      inputs=inputs,
      filters=filters,
      kernel_size=kernel_size,
      padding="same",
      activation=activation,
      kernel_regularizer=regularizer)

    # normalize the weights in the kernel
    output = tf.layers.batch_normalization(
      inputs=output,
      axis=-1,
      momentum=0.9,
      epsilon=0.001,
      center=True,
      scale=True,
      training=training)
    
    return output
                 
  @staticmethod
  def pool(inputs):
    """Apply 2x2 maxpooling."""
    return tf.layers.max_pooling2d(inputs=inputs, pool_size=[2, 2], strides=2)

  @staticmethod
  def deconv(inputs, filters, l2_reg_scale=None):
    """Perform "de-convolution" or "up-conv" to the inputs, increasing shape."""
    if l2_reg_scale is None:
      regularizer = None
    else:
      regularizer = tf.contrib.layers.l2_regularizer(scale=l2_reg_scale) 

    output = tf.layers.conv2d_transpose(
      inputs=inputs,
      filters=filters,
      strides=[2, 2],
      kernel_size=[2, 2],
      padding='same',
      activation=tf.nn.relu,
      kernel_regularizer=regularizer
    )
    return output
