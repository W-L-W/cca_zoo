import itertools
from abc import abstractmethod
from typing import Tuple, List

import numpy as np
import numpy.ma as ma
import pandas as pd
from joblib import Parallel, delayed
from sklearn.base import BaseEstimator

import cca_zoo.data
import cca_zoo.models.innerloop
import cca_zoo.utils.plot_utils


# from hyperopt import fmin, tpe, Trials

class _CCA_Base(BaseEstimator):
    """
    A class used as the base for methods in the package. Allows methods to inherit fit_transform, predict_corr, and gridsearch_fit
    when only fit (and transform where it is different to the default) is provided.

    :param latent_dims: number of latent dimensions to learn
    """

    @abstractmethod
    def __init__(self, latent_dims: int = 1):
        """
        Constructor for _CCA_Base

        """
        self.weights_list = None
        self.train_correlations = None
        self.latent_dims = latent_dims

    @abstractmethod
    def fit(self, *views: Tuple[np.ndarray, ...]):
        """
        Fits a given model

        :param views: numpy arrays with the same number of rows (samples) separated by commas
        """
        pass
        return self

    def transform(self, *views: Tuple[np.ndarray, ...], view_indices: List[int] = None, **kwargs):
        """
        Transforms data given a fit model

        :param views: numpy arrays with the same number of rows (samples) separated by commas
        :param view_indices:
        :param kwargs: any additional keyword arguments required by the given model
        """
        transformed_views = []
        if view_indices is None:
            view_indices = np.arange(len(views))
        for i, (view, view_index) in enumerate(zip(views, view_indices)):
            transformed_view = np.ma.array((view - self.view_means[view_index]) @ self.weights_list[view_index])
            transformed_views.append(transformed_view)
        return transformed_views

    def fit_transform(self, *views: Tuple[np.ndarray, ...], view_indices: List[int] = None, **kwargs):
        """
        Fits and then transforms the training data

        :param views: numpy arrays with the same number of rows (samples) separated by commas
        :param view_indices:
        :param kwargs: any additional keyword arguments required by the given model
        :rtype: Tuple[np.ndarray, ...]
        """
        return self.fit(*views).transform(*views, view_indices=view_indices, **kwargs)

    def predict_corr(self, *views: Tuple[np.ndarray, ...], view_indices: List[int] = None, **kwargs) -> np.ndarray:
        """
        Predicts the correlation for the given data using the fit model

        :param views: numpy arrays with the same number of rows (samples) separated by commas
        :param kwargs: any additional keyword arguments required by the given model
        :param view_indices:
        :return: all_corrs: an array of the pairwise correlations (k,k,self.latent_dims) where k is the number of views
        :rtype: np.ndarray
        """
        # Takes two views and predicts their out of sample correlation using trained model
        transformed_views = self.transform(*views, view_indices=view_indices, **kwargs)
        all_corrs = []
        for x, y in itertools.product(transformed_views, repeat=2):
            all_corrs.append(np.diag(ma.corrcoef(x.T, y.T)[:self.latent_dims, self.latent_dims:]))
        all_corrs = np.array(all_corrs).reshape((len(views), len(views), self.latent_dims))
        return all_corrs

    def demean_data(self, *views: Tuple[np.ndarray, ...]):
        """
        Removes the mean of the training data for each view and stores it

        :param views: numpy arrays with the same number of rows (samples) separated by commas
        :return: train_views: the demeaned numpy arrays to be used to fit the model
        :rtype: Tuple[np.ndarray, ...]
        """
        train_views = []
        self.view_means = []
        for view in views:
            self.view_means.append(view.mean(axis=0))
            train_views.append(view - view.mean(axis=0))
        return train_views

    def gridsearch_fit(self, *views: Tuple[np.ndarray, ...], K=None, param_candidates=None, folds: int = 5,
                       verbose: bool = False,
                       jobs: int = 0,
                       plot: bool = False):
        """
        Implements a gridsearch over the parameters in param_candidates and returns a model fit with the optimal parameters
        in cross validation (measured by sum of correlations).

        :param views: numpy arrays with the same number of rows (samples) separated by commas
        :param K: observation matrix which can be used by GCCA
        :param param_candidates:
        :param folds: number of cross-validation folds
        :param verbose: print results of training folds
        :param jobs: number of jobs. If jobs>1 then the function can use parallelism
        :param plot: produce a hyperparameter surface plot
        """
        if verbose:
            print('cross validation', flush=True)
            print('number of folds: ', folds, flush=True)

        # Set up an array for each set of hyperparameters
        assert (len(param_candidates) > 0)
        param_names = list(param_candidates.keys())
        param_values = list(param_candidates.values())
        param_combinations = list(itertools.product(*param_values))

        param_sets = []
        for param_set in param_combinations:
            param_dict = {}
            for i, param_name in enumerate(param_names):
                param_dict[param_name] = param_set[i]
            param_sets.append(param_dict)

        cv = _CrossValidate(self, folds=folds, verbose=verbose)

        if jobs > 0:
            out = Parallel(n_jobs=jobs)(delayed(cv.score)(*views, **param_set, K=K) for param_set in param_sets)
        else:
            out = [cv.score(*views, **param_set) for param_set in param_sets]
        cv_scores, cv_stds = zip(*out)
        max_index = cv_scores.index(max(cv_scores))

        if verbose:
            print('Best score : ', max(cv_scores), flush=True)
            print('Standard deviation : ', cv_stds[max_index], flush=True)
            print(param_sets[max_index], flush=True)

        self.cv_results_table = pd.DataFrame(zip(param_sets, cv_scores, cv_stds), columns=['params', 'scores', 'std'])
        self.cv_results_table = self.cv_results_table.join(pd.json_normalize(self.cv_results_table.params))
        self.cv_results_table.drop(columns=['params'], inplace=True)

        if plot:
            cca_zoo.utils.plot_utils.cv_plot(cv_scores, param_sets, self.__class__.__name__)

        self.set_params(**param_sets[max_index])
        self.fit(*views)
        return self

    """
    def bayes_fit(self, *views: Tuple[np.ndarray, ...], space=None, folds: int = 5, verbose=True):
        :param views: numpy arrays separated by comma e.g. fit(view_1,view_2,view_3)
        :param space:
        :param folds: number of folds used for cross validation
        :param verbose: whether to return scores for each set of parameters
        :return: fit model with best parameters
        trials = Trials()

        cv = CrossValidate(self, folds=folds, verbose=verbose)

        best_params = fmin(
            fn=cv.score(*views),
            space=space,
            algo=tpe.suggest,
            max_evals=100,
            trials=trials,
        )
        self.set_params(**param_sets[max_index])
        self.fit(*views)
        return self
    """


class _CrossValidate:
    """
    Base class used for cross validation
    """

    def __init__(self, model, folds: int = 5, verbose: bool = True):
        self.folds = folds
        self.verbose = verbose
        self.model = model

    def score(self, *views: Tuple[np.ndarray, ...], K=None, **cvparams):
        scores = np.zeros(self.folds)
        inds = np.arange(views[0].shape[0])
        np.random.shuffle(inds)
        if self.folds == 1:
            # If 1 fold do an 80:20 split
            fold_inds = np.array_split(inds, 5)
        else:
            fold_inds = np.array_split(inds, self.folds)
        for fold in range(self.folds):
            train_sets = [np.delete(view, fold_inds[fold], axis=0) for view in views]
            val_sets = [view[fold_inds[fold], :] for view in views]
            if K is not None:
                train_obs = np.delete(K, fold_inds[fold], axis=1)
                val_obs = K[:, fold_inds[fold]]
                scores[fold] = self.model.set_params(**cvparams).fit(
                    *train_sets, K=train_obs).predict_corr(
                    *val_sets).sum(axis=-1)[np.triu_indices(len(views), 1)].sum()
            else:
                self.model.set_params(**cvparams).fit(
                    *train_sets)
                scores[fold] = self.model.predict_corr(
                    *val_sets).sum(axis=-1)[np.triu_indices(len(views), 1)].sum()
        metric = scores.sum(axis=0) / self.folds
        std = scores.std(axis=0)
        if np.isnan(metric):
            metric = 0
        if self.verbose:
            print(cvparams)
            print(metric)
            print(std)
        return metric, std