# -*- coding: utf-8 -*-
"""
This module loads settings from a configuration file.
"""

__author__ = 'ajshajib'

import yaml
import numpy as np

from lenstronomy.Data.coord_transforms import Coordinates
import lenstronomy.Util.util as util
import lenstronomy.Util.mask as mask_util


class Config(object):
    """
    This class contains the methods to load an read YAML configuration
    files. This is a parent class for other classes that needs to load
    a configuration file. If the file type of the configuration files
    changes, then only this class needs to be modified.
    """

    def __init__(self):
        pass

    @classmethod
    def load(cls, file):
        """
        Load configuration from `file`.
        :return:
        :rtype:
        """
        with open(file,'r') as f:
            settings = yaml.load(f, yaml.FullLoader)

        return settings


class ModelConfig(Config):
    """
    This class contains the methods to load and interact with modeling
    settings for a particular system.
    """

    def __init__(self, file):
        """
        Initiate a Model Config object from a given file.
        :param file: path to a settings file
        :type file: `string` or
        """
        super(ModelConfig, self).__init__()

        self.settings = self.load(file)

    @property
    def pixel_size(self):
        """
        Get the pixel size.
        :return:
        :rtype:
        """
        return self.settings['pixel-size']

    @property
    def deflector_center_ra(self):
        """
        Get the RA offset for the deflector's center from the zero-point
        in the coordinate system of the data. Default is 0.
        :return:
        :rtype:
        """
        if 'deflector-option' in self.settings and 'centroid-init' in \
                self.settings['deflector-option']:
            return float(self.settings['deflector-option'][
                             'centroid-init'][0])
        else:
            return 0.

    @property
    def deflector_center_dec(self):
        """
        Get the dec offset for the deflector's center from the zero-point
        in the coordinate system of the data. Default is 0.
        :return:
        :rtype:
        """
        if 'deflector-option' in self.settings and 'centroid-init' in \
                self.settings['deflector-option']:
            return float(self.settings['deflector-option'][
                             'centroid-init'][1])
        else:
            return 0.

    @property
    def deflector_centroid_bound(self):
        """
        Get half of the box width to constrain the deflector's centroid.
        Default is 0.5 arcsec.
        :return:
        :rtype:
        """
        if 'deflector-option' in self.settings:
            if 'centroid-bound' in self.settings['deflector-option']:
                bound = self.settings['deflector-option']['centroid-bound']
                if bound is not None:
                    return bound

        return 0.5

    @property
    def band_number(self):
        """
        Get the number of bands
        :return:
        :rtype:
        """
        num = len(self.settings['band'])

        if num < 1:
            raise ValueError("Number of bands less than 1!")
        else:
            return num

    def get_kwargs_model(self):
        """
        Create `kwargs_model`.
        :return:
        :rtype:
        """
        kwargs_model = {
            'lens_model_list': self.get_lens_model_list(),
            'source_light_model_list': self.get_source_light_model_list(),
            'lens_light_model_list': self.get_lens_light_model_list(),
            'point_source_model_list': self.get_point_source_model_list(),
        }

        if 'kwargs-model' in self.settings and self.settings['kwargs-model']\
                is not None:
            for key, value in self.settings['kwargs-model'].iteritems():
                kwargs_model[key] = value

        return kwargs_model

    def get_kwargs_constraints(self):
        """
        Create `kwargs_constraints`.
        :return:
        :rtype:
        """
        joint_source_with_source = []
        num_source_profiles = len(self.get_source_light_model_list())

        if num_source_profiles > 1:
            for n in range(1, num_source_profiles):
                joint_source_with_source.append([
                    0, n, ['center_x', 'center_y']
                ])

        joint_lens_light_with_lens_light = []
        num_lens_light_profiles = len(self.get_lens_light_model_list())
        if num_lens_light_profiles > 1:
            for n in range(1, num_lens_light_profiles):
                joint_lens_light_with_lens_light.append([
                    0, n, ['center_x', 'center_y']
                ])

        joint_source_with_point_source = []

        if len(self.get_point_source_model_list()) > 1 and \
                num_source_profiles > 1:
            for n in range(num_source_profiles):
                joint_source_with_point_source.append([
                    0, n, ['center_x','center_y']
                ])

        kwargs_constraints = {
            'joint_source_with_source': joint_source_with_source,
            'joint_lens_light_with_lens_light':
                joint_lens_light_with_lens_light,
            'joint_source_with_point_source': joint_source_with_point_source
        }

        return kwargs_constraints

    def get_kwargs_likelihood(self):
        """
        Create `kwargs_likelihood`.
        :return:
        :rtype:
        """
        kwargs_likelihood = {
            'force_no_add_image': False,
            'source_marg': False,
            #'point_source_likelihood': True,
            'position_uncertainty': 0.00004,
            'check_solver': False,
            'solver_tolerance': 0.001,
            'check_positive_flux': True,
            'check_bounds': True,
            'bands_compute': [True]*self.band_number,
            'image_likelihood_mask_list': self.get_masks()
        }

        return kwargs_likelihood

    def get_masks(self):
        """
        Create masks.
        :return:
        :rtype:
        """
        if 'mask' in self.settings:
            if self.settings['mask'] is not None:
                if 'provided' in self.settings['mask'] and self.settings[
                                        'mask']['provided'] is not None:
                    return self.settings['mask']['provided']
                else:
                    masks = []
                    mask_options = self.settings['mask']

                    for n in range(self.band_number):
                        ra_at_xy_0 = mask_options['ra-at-xy-0'][n]
                        dec_at_xy_0 = mask_options['dec-at-xy-0'][n]
                        transform_pix2angle = np.array(
                            mask_options['transform-matrix'][n]
                        )
                        num_pixel = mask_options['size'][n]
                        radius = mask_options['radius'][n]
                        offset = mask_options['centroid-offset'][n]

                        coords = Coordinates(transform_pix2angle,
                                             ra_at_xy_0, dec_at_xy_0)

                        x_coords, y_coords = coords.coordinate_grid(num_pixel,
                                                                    num_pixel)

                        mask_outer = mask_util.mask_center_2d(
                            self.deflector_center_ra,
                            self.deflector_center_dec,
                            radius,
                            util.image2array(x_coords),
                            util.image2array(y_coords)
                        )

                        mask = 1. - mask_outer

                        # sanity check
                        mask[mask >= 1.] = 1.
                        mask[mask <= 0.] = 0.

                        masks.append(mask)

                return masks

        return None

    def get_kwargs_psf_iteration(self):
        """
        Create `kwargs_psf_iteration`.
        :return:
        :rtype:
        """
        # temporary return {} as test function is not written
        return {}

        # if 'psf-iteration' in self.settings['fitting'] and self.settings[
        #     'fittiing']['psf-iteration']:
        #     kwargs_psf_iteration = {
        #         'stacking_method': 'median',
        #         'keep_psf_error_map': True,
        #         'psf_symmetry': self.settings['fitting'][
        #             'psf-iteration-settinigs']['psf-symmetry'],
        #         'block_center_neighbour': self.settings['fitting'][
        #             'psf-iteration-settings']['block-neighbour'],
        #         'num_iter': self.settings['fitting'][
        #             'psf-iteration-settings']['psf-iteration-factor'],
        #         'psf_iter_factor': self.settings['fitting'][
        #             'psf-iteration-settings']['psf-iteration-factor']
        #     }
        #
        #     return kwargs_psf_iteration
        # else:
        #     return {}

    def get_kwargs_numerics(self):
        """
        Create `kwargs_numerics`.
        :return:
        :rtype:
        """
        try:
            self.settings['numeric-option']['supersampling-option']
        except (KeyError, NameError):
            supersampling_factor = [3] * self.band_number
        else:
            supersampling_factor = self.settings['numeric-option'][
                                                    'supersampling-option']

            if supersampling_factor is None:
                supersampling_factor = [3] * self.band_number


        kwargs_numerics = []
        for n in range(self.band_number):
            kwargs_numerics.append({
                'supersampling_factor': supersampling_factor[n],
                'supersampling_convolution': False,
                'supersampling_kernel_size': 3,
                'flux_evaluate_indexes': None,
                'point_source_supersampling_factor': 1,
                'compute_mode': 'regular',
            })

        return kwargs_numerics

    def get_lens_model_list(self):
        """
        Return `lens_model_list`.
        :return:
        :rtype:
        """
        if 'lens' in self.settings['model']:
            return self.settings['model']['lens']
        else:
            return []

    def get_source_light_model_list(self):
        """
        Return `source_model_list`.
        :return:
        :rtype:
        """
        if 'source-light' in self.settings['model']:
            return self.settings['model']['source-light']
        else:
            return []

    def get_lens_light_model_list(self):
        """
        Return `lens_light_model_list`.
        :return:
        :rtype:
        """
        if 'lens-light' in self.settings['model']:
            return self.settings['model']['lens-light']
        else:
            return []

    def get_point_source_model_list(self):
        """
        Return `ps_model_list`.
        :return:
        :rtype:
        """
        if 'point-source' in self.settings['model']:
            return self.settings['model']['point-source']
        else:
            return []

    def get_lens_model_params(self):
        """
        Create `lens_params`.
        :return:
        :rtype:
        """
        lens_model_list = self.get_lens_model_list()

        fixed = []
        init = []
        sigma = []
        lower = []
        upper = []

        for model in lens_model_list:
            if model == 'SPEMD':
                fixed.append({})

                init.append({
                    'center_x': self.deflector_center_ra,
                    'center_y': self.deflector_center_dec,
                    'e1':  0., 'e2': 0.,
                    'gamma': 2., 'theta_E': 1.
                })

                sigma.append({
                    'theta_E': .1, 'e1':0.1, 'e2':0.1,
                    'gamma': 0.02, 'center_x': 0.1,
                    'center_y': 0.1
                })

                lower.append({
                     'theta_E': 0.01, 'e1': -0.5, 'e2': -0.5, 'gamma': 1.5,
                     'center_x': self.deflector_center_ra
                                    - self.deflector_centroid_bound,
                     'center_y': self.deflector_center_dec
                                    - self.deflector_centroid_bound
                })

                upper.append({
                    'theta_E': 2., 'e1': 0.5, 'e2': 0.5, 'gamma': 2.5,
                    'center_x': self.deflector_center_ra
                                    + self.deflector_centroid_bound,
                    'center_y': self.deflector_center_dec
                                    + self.deflector_centroid_bound
                })

            elif model == 'SHEAR_GAMMA_PSI':
                fixed.append({'ra_0': 0, 'dec_0': 0})
                init.append({'gamma_ext': 0.05, 'psi_ext': 0.0})
                sigma.append({'gamma_ext': 0.01, 'psi_ext': np.pi / 90.})
                lower.append({'gamma_ext': 0.0, 'psi_ext': -np.pi})
                upper.append({'gamma_ext': 0.5, 'psi_ext': np.pi})
            else:
                raise ValueError('{} not implemented as a lens '
                                 'model!'.format(model))

        params = [init, sigma, fixed, lower, upper]
        return params

    def get_lens_light_model_params(self):
        """
        Create `lens_light_params`.
        :return:
        :rtype:
        """
        lens_light_model_list = self.get_lens_light_model_list()

        fixed = []
        init = []
        sigma = []
        lower = []
        upper = []

        for n in range(self.band_number):
            for model in lens_light_model_list:
                if model == 'SERSIC_ELLIPSE':
                    fixed.append({})

                    init.append({
                        'amp': 1., 'R_sersic': .2,
                        'center_x': self.deflector_center_ra,
                        'center_y': self.deflector_center_dec,
                        'e1': 0, 'e2': 0, 'n_sersic': 4.0
                    })

                    sigma.append({
                        'center_x': self.pixel_size/10.,
                        'center_y': self.pixel_size/10.,
                        'R_sersic': 0.05, 'n_sersic': 0.5,
                        'e1': 0.1, 'e2': 0.1
                    })

                    lower.append({
                        'e1': -0.5, 'e2': -0.5,
                        'n_sersic': .5, 'R_sersic': 0.1,
                        'center_x': self.deflector_center_ra
                                        - self.deflector_centroid_bound,
                        'center_y': self.deflector_center_dec
                                        -  self.deflector_centroid_bound
                    })

                    upper.append({
                        'e1': 0.5, 'e2': 0.5,
                        'n_sersic': 8., 'R_sersic': 10.,
                        'center_x': self.deflector_center_ra
                                        + self.deflector_centroid_bound,
                        'center_y': self.deflector_center_dec
                                        + self.deflector_centroid_bound
                    })
                else:
                    raise ValueError('{} not implemented as a lens light'
                                     'model!'.format(model))

        params = [init, sigma, fixed, lower, upper]
        return params

    def get_source_light_model_params(self):
        """
        Create `source_params`.
        :return:
        :rtype:
        """
        source_light_model_list = self.get_source_light_model_list()

        fixed = []
        init = []
        sigma = []
        lower = []
        upper = []

        for n in range(self.band_number):
            for model in source_light_model_list:
                if model == 'SERSIC_ELLIPSE':
                    fixed.append({})

                    init.append({
                        'amp': 1., 'R_sersic': 0.2, 'n_sersic': 1.,
                        'center_x': 0.,
                        'center_y': 0.,
                        'e1': 0., 'e2': 0.
                    })

                    sigma.append({
                        'center_x': 0.01,
                        'center_y': 0.01,
                        'R_sersic': 0.01, 'n_sersic': 0.5,
                        'e1': 0.05, 'e2': 0.05
                    })

                    lower.append({
                        'R_sersic': 0.04, 'n_sersic': .5,
                        'center_y': -2., 'center_x': -2.,
                        'e1': -0.5, 'e2': -0.5
                    })

                    upper.append({
                        'R_sersic': .5, 'n_sersic': 8.,
                        'center_y': 2., 'center_x': 2.,
                        'e1': 0.5, 'e2': 0.5
                    })

        params = [init, sigma, fixed, lower, upper]
        return params

    def get_point_source_params(self):
        """
        Create 'ps_params`.
        :return:
        :rtype:
        """
        # return empty dictionaries as test is not implemented
        return [{}]*5


        point_source_model_list = self.get_point_source_model_list()

        fixed = []
        init = []
        sigma = []
        lower = []
        upper = []

        if len(point_source_model_list) > 0:
            fixed.append({})

            init.append({
                'ra_image': self.settings['point-source-option']['ra-init'],
                'dec_image': self.settings['point-source-option']['dec-init'],
            })

            num_point_sources = len(init[0]['ra_image'])
            sigma.append({
                'ra_image': self.pixel_size * np.ones(num_point_sources),
                'dec_image': self.pixel_size * np.ones(num_point_sources),
            })

            lower.append({
                'ra_image': init[0]['ra_image']
                                - self.settings['point-source-option']['bound'],
                'dec_image': init[0]['dec_image']
                                - self.settings['point-source-option']['bound'],
            })

            upper.append({
                'ra_image': init[0]['ra_image']
                                + self.settings['point-source-option']['bound'],
                'dec_image': init[0]['dec_image']
                                + self.settings['point-source-option']['bound'],
            })

        params = [init, sigma, fixed, lower, upper]
        return params

    def get_kwargs_params(self):
        """
        Create `kwargs_params`.
        :return:
        :rtype:
        """
        kwargs_params = {
            'lens_model': self.get_lens_model_params(),
            'source_model': self.get_source_light_model_params(),
            'lens_light_model': self.get_lens_light_model_params(),
            'point_source_model': self.get_point_source_params(),
            #'cosmography': []
        }

        return kwargs_params

    def get_fitting_sequence(self):
        """
        Create `fitting_sequence`.
        :return:
        :rtype:
        """
        try:
            self.settings['fitting']['pso']
        except (NameError, KeyError):
            do_pso = False
        else:
            do_pso = self.settings['fitting']['pso']

            if do_pso is None:
                do_pso = False

        try:
            self.settings['fitting']['psf-iteration']
        except (NameError, KeyError):
            reconstruct_psf = False
        else:
            reconstruct_psf = self.settings['fitting']['psf-iteration']

            if reconstruct_psf is None:
                reconstruct_psf = False

        try:
            self.settings['fitting']['mcmc']
        except (NameError, KeyError):
            sample_mcmc = False
        else:
            sample_mcmc = self.settings['fitting']['mcmc']

            if sample_mcmc is None:
                sample_mcmc = False

        fitting_sequence = []

        pso_range_multipliers = [10., 1., 1., 0.1, 0.01]

        for multiplier in pso_range_multipliers:
            if do_pso:
                fitting_sequence.append([
                    ['PSO',
                     {
                        'sigma_scale': multiplier,
                        'n_particles': self.settings['fitting'][
                                                        'pso']['num-particle'],
                        'n_iterations': self.settings['fitting'][
                                                        'pso']['num-iteration']
                     }]
                ])
            if reconstruct_psf:
                fitting_sequence.append(
                    ['psf_iteration', self.get_kwargs_psf_iteration()]
                )

        if sample_mcmc:
            if self.settings['fitting']['mcmc-sampler'] == 'emcee':
                fitting_sequence.append(
                    ['emcee',
                     {
                         'n_burn': self.settings['fitting']['mcmc-settings'][
                                                                'burnin-step'],
                         'n_run': self.settings['fitting']['mcmc-settings'][
                                                            'iteration-step'],
                         'walkerRatio': self.settings['fitting'][
                                                'mcmc-settings']['walker-ratio']
                     }
                     ]
                )
            else:
                raise ValueError("{} sampler not implemented yet!".format(
                                                self.settings['mcmc-sampler']))

        return fitting_sequence

