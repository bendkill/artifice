"""Module containing inpainting functions on tensors.

Every inpaint function takes two positional arguments: 
:image: the image tensor, usually batched.
:indices: the indices tensor of the region to inpaint, as in tf.gather_nd().
as well as optional keyword arguments, depending on the function.

Returns: the inpainted image.

"""

import tensorflow as tf

def gaussian(image, indices, **kwargs):
  """Inpaints with values drawn from a gaussian distribution, clipping by
  0,1. Accepts keyword arguments:

  :mu: mean of the normal distribution, default 0.5.
  :std: standard deviation of the distribution, default 0.1.
  :name: name of the operation.

  """
  mu = kwargs.get('mu', 0.5)
  std = kwargs.get('std', 0.1)
  name = kwargs.get('name', 'inpaint_gaussian')

  updates = tf.distributions.Normal(mu, std).sample(indices.shape[0])
  return tf.scatter_nd_update(image, indices, updates, name=name)


def background(image, indices, **kwargs):
  """Inpaints with values drawn from a provided background image.
  :background: tensor with the same shape as image, defaults to uniform zeros.
  :name: name of the operation

  """
  background_image = kwargs.get('background_image')
  if background_image is None:
    background_image = tf.zeros_like(image)
  name = kwargs.get('name', 'inpaint_background')

  updates = tf.gather_nd(background_image, indices)
  return tf.scatter_nd_update(image, indices, updates, name=name)


def annotation(annotation, indices, **kwargs):
  """Inpaint the entries of annotation pointed to by indices with
  [0,max(annotation)].
  """
  bg_semantic = kwargs.get('bg_label', 0)
  bg_distance = kwargs.get('bg_distance')
  name = kwargs.get('name', 'inpaint_annotation')
  
  bg_semantic = tf.constant(bg_semantic, dtype=annotation.dtype)
  if bg_distance is None:
    bg_distance = tf.reduce_max(annotation[:,:,:,1])
  else:
    bg_distance = tf.constant(bg_semantic, dtype=annotation.dtype)

  updates = tf.reshape(tf.stack([bg_semantic, bg_distance]), [1,1,1,2])
  return tf.scatter_nd_update(annotation, indices, updates, name=name)