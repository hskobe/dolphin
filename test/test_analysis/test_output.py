# -*- coding: utf-8 -*-
"""
Tests for output module.
"""
from pathlib import Path
import pytest
import numpy as np
import  matplotlib.pyplot as plt

from dolphin.processor import Processor
from dolphin.analysis.output import Output

_ROOT_DIR = Path(__file__).resolve().parents[2]
_TEST_IO_DIR = _ROOT_DIR / 'io_directory_example'


class TestOutput(object):

    def setup_class(self):
        self.output = Output(_TEST_IO_DIR)
        self.processor = Processor(_TEST_IO_DIR)

    @classmethod
    def teardown_class(cls):
        pass

    def test_swim(self):
        """
        Test that `swim` method is not accessible.
        :return:
        :rtype:
        """
        with pytest.raises(NotImplementedError):
            self.output.swim()

    def test_properties(self):
        """
        Test class properties.
        :return:
        :rtype:
        """
        with pytest.raises(ValueError):
            _ = self.output.fit_output

        with pytest.raises(ValueError):
            _ = self.output.kwargs_result

        with pytest.raises(ValueError):
            _ = self.output.model_settings

        assert self.output.samples_mcmc == []
        assert self.output.params_mcmc == []
        assert self.output.num_params_mcmc == 0

        self.output._params_mcmc = ['param1', 'param2']
        assert self.output.num_params_mcmc == 2

    def test_load_output(self):
        """
        Test that outputs are saved and corresponding class variables
        are not None.

        :return:
        :rtype:
        """
        save_dict = {
            'settings': {'some': 'settings'},
            'kwargs_result': {'0': None, '1': 'str', '2': [3, 4]},
            'fit_output': [
                ['EMCEE',
                 [[2, 2], [3, 3]],
                 ['param1', 'param2'],
                 [0.5, 0.2]
                 ]
            ]
        }

        self.processor.file_system.save_output('test', 'post_process_load',
                                               save_dict)

        self.output.load_output('test', 'post_process_load')

        assert np.all(self.output.fit_output[0][1]
                      == save_dict['fit_output'][0][1])
        assert np.all(self.output.fit_output[0][3]
                      == save_dict['fit_output'][0][3])
        assert self.output.kwargs_result == save_dict['kwargs_result']
        assert self.output.model_settings == save_dict['settings']

    def test_plot_model_overview(self):
        """
        Test `plot_model_overview` method.

        :return:
        :rtype:
        """
        with pytest.raises(ValueError):
            _ = self.output.plot_model_overview('demo_system1')

        fig = self.output.plot_model_overview('demo_system1', 'example')

        plt.close(fig)