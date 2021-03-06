"""Create a (test) dataset of a single sphere flying in a parabolic arc.
Outputs a tfrecord in data/arcing_sphere. (Should be run from $ARTIFICE)

"""

import vapory
import numpy as np
import matplotlib.pyplot as plt

from test_utils import experiment
from artifice.utils import dataset

debug = False

# helpers
color = lambda col : vapory.Texture(vapory.Pigment('color', col))

# dataset parameters
root = "data/arcing_sphere/"    # root dir for fname
fps = 30                        # frame rate of the video
time_step = 1/float(fps)        # time per frame
seconds = 5                     # number of seconds in the video
N = int(seconds / time_step)    # number of frames
output_formats = {'mp4'}        # write to a video
fname = root + 'arcing_sphere'  # extensions from output_formats
image_shape = (512, 512)        # image shape
num_classes = 2                 # including background

# physical sphere parameters. 1 povray unit = 1 cm
radius = 50                     # radius
mass = 2                        # mass in kilograms
x = -200                        # initial x position in world
y = -200                        # initial y position in world
vx = 200                        # initial x velocity
vy = 500                       # initial y velocity
g = -981                        # gravity acceleration

# experiment sphere parameters
def argsf(t_):
  t = t_ * time_step
  return ([vx*t + x, 0.5*g*t**2 + vy*t + y, 0], radius)

ball = experiment.ExperimentSphere(argsf, color('Red'))

# experiment
exp = experiment.Experiment(image_shape=image_shape,
                            num_classes=num_classes,
                            N=N, fname=fname,
                            output_format=output_formats,
                            fps=fps, mode='L')
exp.add_object(vapory.LightSource([0, 5*image_shape[0], -5*image_shape[1]],
                                  'color', [1,1,1]))
exp.add_object(vapory.Plane([0,1,0], y - radius, color('White'))) # ground
exp.add_object(vapory.Plane([0,0,1], 5*radius, color('White')))  # back wall
exp.add_object(ball)

if debug:
  image, annotation = exp.render_scene(2*fps)
  plt.imshow(image[:,:,0], cmap='gray')
  plt.show()
else:
  exp.run(verbose=True)

