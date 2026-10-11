import copy
import unittest

import cv2
import numpy as np

from vision import keep_grid_geometry


class GridGeometryTests(unittest.TestCase):
    def setUp(self):
        self.grid={'rows':2,'cols':3,'cell_size':20,
                   'x_centers':[25,55,85],'y_centers':[25,55],
                   'detected':[[True]*3 for _ in range(2)],'detected_count':6}
        rng=np.random.default_rng(42)
        self.image=rng.integers(0,256,(90,120,3),dtype=np.uint8)

    def test_estimator_jitter_preserves_geometry_and_updates_contours(self):
        observed=copy.deepcopy(self.grid)
        observed['cell_size']=19
        observed['y_centers']=[26,56]
        observed['x_centers']=[25.25,55.25,85.25]
        observed['detected'][0][0]=False
        observed['detected_count']=5
        after=self.image.copy()
        after[15:36,15:36]=0
        fixed=keep_grid_geometry(self.grid,observed,self.image,after)
        for key in ('cell_size','x_centers','y_centers'):
            self.assertEqual(fixed[key],self.grid[key])
        self.assertFalse(fixed['detected'][0][0])
        self.assertTrue(self.grid['detected'][0][0])

    def test_actual_one_pixel_translation_stops_even_with_small_estimator_delta(self):
        observed=copy.deepcopy(self.grid)
        observed['y_centers']=[26,56]
        after=cv2.warpAffine(self.image,np.float32([[1,0,0],[0,1,1]]),(120,90))
        with self.assertRaises(RuntimeError):
            keep_grid_geometry(self.grid,observed,self.image,after)

    def test_large_translation_stops_even_if_pixels_match(self):
        observed=copy.deepcopy(self.grid)
        observed['x_centers']=[30,60,90]
        with self.assertRaises(RuntimeError):
            keep_grid_geometry(self.grid,observed,self.image,self.image)

    def test_resize_and_dimension_changes_stop(self):
        for key,value in [('cell_size',25),('rows',3)]:
            observed=copy.deepcopy(self.grid)
            observed[key]=value
            with self.assertRaises(RuntimeError):
                keep_grid_geometry(self.grid,observed,self.image,self.image)
        with self.assertRaises(RuntimeError):
            keep_grid_geometry(self.grid,self.grid,self.image,self.image[:80])

    def test_no_unchanged_tiles_stops_conservatively(self):
        with self.assertRaises(RuntimeError):
            keep_grid_geometry(self.grid,self.grid,self.image,255-self.image)
